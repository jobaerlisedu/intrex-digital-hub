"""
Firestore Schema v2 Migration — Intrex ERP

Migrates all collections from the flat/non-standard v1 schema to the
modular v2 schema with consistent naming, DocumentReferences, standard
audit fields, and subcollections where appropriate.

Usage:
    python manage.py migrate_firestore_v2              # Run all migrations
    python manage.py migrate_firestore_v2 --dry-run     # Preview only (no writes)
    python manage.py migrate_firestore_v2 --collection hrm_employees  # Single collection
    python manage.py migrate_firestore_v2 --force       # Re-migrate even if already done

User Management Isolation:
    The `sys_users` collection is treated as a READ-ONLY replica of Django's
    auth.User (SQLite). Migration only normalizes field names — it does NOT
    change the write direction.  The ERP User Management module continues
    to use Django SQLite as source of truth.

Schema v2 Naming Convention:
    {module_prefix}_{entity_name}

    Module prefixes:
        sys_    — System (users, audit, config)
        org_    — Organization (companies, departments, positions)
        hrm_    — Human Resources (employees, attendance, leaves)
        inv_    — Inventory / Procurement
        fin_    — Finance / Billing
        trn_    — Training
        sol_    — Solutions / Projects
        invst_  — Investment
"""

import os
import sys
import time
from datetime import datetime, timezone
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth.models import User

# ── Firestore imports (safe fail if unavailable) ──────────────────────
try:
    from config.firebase import db
    from google.cloud import firestore as google_firestore
    from google.api_core.exceptions import GoogleAPICallError
    FIRESTORE_AVAILABLE = True
except Exception as e:
    FIRESTORE_AVAILABLE = False
    _import_error = e


# ══════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════

NOW = datetime.now(timezone.utc)
BATCH_LIMIT = 500  # Firestore batch write limit

TRACKING_COLLECTION = '_migrations'
TRACKING_DOC = 'v2_schema'

# ══════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════

def server_timestamp():
    return google_firestore.SERVER_TIMESTAMP


def doc_ref(collection, doc_id):
    """Build a Firestore DocumentReference."""
    return db.collection(collection).document(doc_id)


def safe_str(val, default=''):
    if val is None:
        return default
    return str(val).strip()


def safe_bool(val, default=False):
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    return str(val).lower() in ('true', '1', 'yes', 'on')


def safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return safe_float(val, default)


def ensure_audit_fields(data, is_new=True):
    """Add standard audit fields to a document dict."""
    now = server_timestamp()
    data['created_at'] = data.get('created_at', data.get('createdAt', now))
    data['updated_at'] = now
    data['is_active'] = safe_bool(data.get('is_active', data.get('status') == 'Active' if data.get('status') else True))
    # Remove old-style timestamps
    data.pop('createdAt', None)
    data.pop('updatedAt', None)
    return data


def stream_collection(name):
    """Stream all docs from a collection with error handling."""
    try:
        return list(db.collection(name).stream())
    except Exception as e:
        print(f"  ⚠  Could not stream '{name}': {e}")
        return []


def delete_collection(name, batch_size=BATCH_LIMIT):
    """Delete all docs in a collection (for cleanup)."""
    docs = stream_collection(name)
    total = len(docs)
    if total == 0:
        return 0
    deleted = 0
    for i in range(0, total, batch_size):
        batch = db.batch()
        chunk = docs[i:i + batch_size]
        for doc in chunk:
            batch.delete(doc.reference)
        batch.commit()
        deleted += len(chunk)
        print(f"    Deleted {deleted}/{total} from '{name}'")
    return deleted


def commit_batch(batch, ops_count):
    """Commit a batch and return a new empty batch."""
    if ops_count > 0:
        batch.commit()
    return db.batch(), 0


# ══════════════════════════════════════════════════════════════════════
#  MIGRATION TRACKING
# ══════════════════════════════════════════════════════════════════════

def is_migrated(collection_name):
    """Check if a collection has already been migrated."""
    try:
        doc = db.collection(TRACKING_COLLECTION).document(collection_name).get()
        return doc.exists
    except Exception:
        return False


def mark_migrated(collection_name, stats=None):
    """Mark a collection as migrated."""
    data = {
        'migrated_at': server_timestamp(),
        'schema_version': 'v2',
        'documents_migrated': (stats or {}).get('migrated', 0),
        'documents_skipped': (stats or {}).get('skipped', 0),
        'documents_errors': (stats or {}).get('errors', 0),
    }
    db.collection(TRACKING_COLLECTION).document(collection_name).set(data)


# ══════════════════════════════════════════════════════════════════════
#  TRANSFORM FUNCTIONS
#  Each takes old document data + doc_id, returns new document dict
# ══════════════════════════════════════════════════════════════════════

def transform_user(data, doc_id):
    """sys_users: normalize fields from auth.User replica."""
    return ensure_audit_fields({
        'username': doc_id,
        'email': safe_str(data.get('email')),
        'first_name': safe_str(data.get('first_name')),
        'last_name': safe_str(data.get('last_name')),
        'is_active': safe_bool(data.get('is_active'), True),
        'is_staff': safe_bool(data.get('is_staff')),
        'is_superuser': safe_bool(data.get('is_superuser')),
        'groups': data.get('groups', []),
        'last_synced_at': data.get('updated_at', data.get('last_synced_at', server_timestamp())),
    }, is_new=False)


def transform_employee(data, doc_id):
    """hrm_employees: restructure salary, bank, contacts into sub-maps."""
    emp_name = safe_str(data.get('name'))
    return ensure_audit_fields({
        'emp_id': doc_id,
        'emp_code': safe_str(data.get('emp_id', data.get('employee_id', data.get('code', '')))),
        'first_name': safe_str(data.get('first_name')) or emp_name.split(' ')[0] if emp_name else '',
        'last_name': safe_str(data.get('last_name')) or ' '.join(emp_name.split(' ')[1:]) if emp_name else '',
        'email': safe_str(data.get('email')),
        'phone': safe_str(data.get('phone')),
        'alt_phone': safe_str(data.get('alt_phone')),
        'national_id': safe_str(data.get('national_id')),
        'department': safe_str(data.get('department')),
        'sub_department': safe_str(data.get('sub_department')),
        'position': safe_str(data.get('position')),
        'additional_roles': data.get('additional_roles', []),
        'employee_type': safe_str(data.get('employee_type', 'permanent')),
        'joining_date': data.get('joining_date', data.get('joiningDate')),
        'confirmation_date': data.get('confirmation_date'),
        'status': safe_str(data.get('status', 'Active')),
        'exit_date': data.get('exit_date'),
        'exit_type': safe_str(data.get('exit_type')),
        'exit_reason': safe_str(data.get('exit_reason')),
        'dob': data.get('dob'),
        'gender': safe_str(data.get('gender')),
        'marital_status': safe_str(data.get('marital_status')),
        'religion': safe_str(data.get('religion')),
        'address': {
            'city': safe_str(data.get('city')),
            'zip': safe_str(data.get('zip')),
        },
        'emergency_contacts': [
            {
                'name': safe_str(data.get('ec_primary_name')),
                'relation': safe_str(data.get('ec_primary_relation')),
                'phone': safe_str(data.get('ec_primary_mobile')),
            },
            {
                'name': safe_str(data.get('ec_secondary_name')),
                'relation': safe_str(data.get('ec_secondary_relation')),
                'phone': safe_str(data.get('ec_secondary_mobile')),
            },
        ] if data.get('ec_primary_name') else [],
        'bank_details': {
            'account_holder': safe_str(data.get('account_holder')),
            'account_number': safe_str(data.get('account_number')),
            'bank_name': safe_str(data.get('bank_name')),
            'branch_name': safe_str(data.get('branch_name')),
        } if data.get('account_holder') else {},
        'salary': {
            'basic': safe_float(data.get('basic_salary')),
            'house_rent': safe_float(data.get('house_rent')),
            'medical_allowance': safe_float(data.get('medical_allowance')),
            'conveyance_allowance': safe_float(data.get('conveyance_allowance')),
            'utility': safe_float(data.get('utility')),
            'mobile_bill': safe_float(data.get('mobile_bill')),
            'gross': safe_float(data.get('gross_salary')),
        } if data.get('basic_salary') else {},
        'contact_id': safe_str(data.get('contact_id')),
    })


def transform_attendance(data, doc_id):
    """hrm_employees/{emp_id}/attendance: employee-scoped subcollection doc."""
    return {
        'att_id': doc_id,
        'date': safe_str(data.get('date')),
        'check_in': safe_str(data.get('check_in')),
        'check_out': safe_str(data.get('check_out')),
        'status': safe_str(data.get('status', 'Present')),
        'notes': safe_str(data.get('notes')),
        'resolved': safe_bool(data.get('resolved')),
        'created_at': data.get('createdAt', data.get('created_at', server_timestamp())),
    }


def transform_leave(data, doc_id):
    """hrm_employees/{emp_id}/leaves: employee-scoped subcollection doc."""
    return {
        'leave_id': doc_id,
        'leave_type': safe_str(data.get('leave_type', data.get('type', 'annual'))),
        'start_date': data.get('from_date', data.get('start_date')),
        'end_date': data.get('to_date', data.get('end_date')),
        'total_days': safe_int(data.get('total_days', data.get('days', 0))),
        'reason': safe_str(data.get('reason')),
        'status': safe_str(data.get('status', 'Pending')),
        'approved_by': safe_str(data.get('approved_by')),
        'created_at': data.get('createdAt', data.get('created_at', server_timestamp())),
    }


def transform_document(data, doc_id):
    """hrm_employees/{emp_id}/documents: employee-scoped subcollection doc."""
    return {
        'doc_id': doc_id,
        'doc_type': safe_str(data.get('doc_type', data.get('type', 'document'))),
        'title': safe_str(data.get('title', data.get('name', ''))),
        'file_url': safe_str(data.get('file_url', data.get('url', ''))),
        'description': safe_str(data.get('description', data.get('notes', ''))),
        'created_at': data.get('createdAt', data.get('created_at', server_timestamp())),
    }


def transform_department(data, doc_id):
    """org_departments: consolidated from hrm_departments + hrm_sub_departments."""
    return ensure_audit_fields({
        'dept_id': doc_id,
        'name': safe_str(data.get('name', data.get('department_name', ''))),
        'code': safe_str(data.get('code', data.get('department_code', ''))),
        'description': safe_str(data.get('description', '')),
        'parent_dept_id': safe_str(data.get('parent_dept', data.get('parent_dept_id'))),
        'head_employee_id': safe_str(data.get('head_employee', data.get('head_employee_id'))),
        'is_department': safe_bool(data.get('is_department', True)),
    })


def transform_position(data, doc_id):
    """org_positions: from hrm_positions."""
    return ensure_audit_fields({
        'position_id': doc_id,
        'title': safe_str(data.get('title', data.get('name', ''))),
        'description': safe_str(data.get('description', '')),
        'department_id': safe_str(data.get('department', data.get('department_id'))),
        'min_salary': safe_float(data.get('min_salary')),
        'max_salary': safe_float(data.get('max_salary')),
    })


def transform_candidate(data, doc_id):
    """hrm_recruitment_candidates: from hrm_candidates."""
    return ensure_audit_fields({
        'candidate_id': doc_id,
        'first_name': safe_str(data.get('first_name', data.get('name', '').split(' ')[0] if data.get('name') else '')),
        'last_name': safe_str(data.get('last_name', ' '.join(data.get('name', '').split(' ')[1:]) if data.get('name') else '')),
        'email': safe_str(data.get('email')),
        'phone': safe_str(data.get('phone')),
        'position_id': safe_str(data.get('position', data.get('position_id'))),
        'source': safe_str(data.get('source', 'manual')),
        'status': safe_str(data.get('status', 'New')),
        'resume_url': safe_str(data.get('resume_url', data.get('resume', ''))),
        'notes': safe_str(data.get('notes')),
        'applied_at': data.get('appliedAt', data.get('createdAt', server_timestamp())),
    })


def transform_shortlist(data, doc_id):
    """hrm_recruitment_shortlists."""
    return ensure_audit_fields({
        'shortlist_id': doc_id,
        'candidate_id': safe_str(data.get('candidate', data.get('candidate_id'))),
        'position_id': safe_str(data.get('position', data.get('position_id'))),
        'round': safe_int(data.get('round', 1)),
        'notes': safe_str(data.get('notes')),
        'status': safe_str(data.get('status', 'Shortlisted')),
    })


def transform_interview(data, doc_id):
    """hrm_recruitment_interviews."""
    return ensure_audit_fields({
        'interview_id': doc_id,
        'candidate_id': safe_str(data.get('candidate', data.get('candidate_id'))),
        'interviewer': safe_str(data.get('interviewer')),
        'scheduled_at': data.get('scheduled_at', data.get('date')),
        'mode': safe_str(data.get('mode', 'in-person')),
        'score': safe_float(data.get('score')),
        'feedback': safe_str(data.get('feedback')),
        'status': safe_str(data.get('status', 'Scheduled')),
    })


def transform_selection(data, doc_id):
    """hrm_recruitment_selections."""
    return ensure_audit_fields({
        'selection_id': doc_id,
        'candidate_id': safe_str(data.get('candidate', data.get('candidate_id'))),
        'position_id': safe_str(data.get('position', data.get('position_id'))),
        'offer_date': data.get('offer_date', data.get('date')),
        'joining_date': data.get('joining_date'),
        'offered_salary': safe_float(data.get('offered_salary', data.get('salary'))),
        'status': safe_str(data.get('status', 'Offered')),
    })


def transform_product(data, doc_id):
    """inv_products: from products."""
    return ensure_audit_fields({
        'product_id': doc_id,
        'sku': safe_str(data.get('sku', data.get('product_id', ''))),
        'name': safe_str(data.get('name', data.get('product_name', ''))),
        'description': safe_str(data.get('description', '')),
        'category': safe_str(data.get('category')),
        'unit': safe_str(data.get('unit', 'pcs')),
        'unit_price': safe_float(data.get('unit_price', data.get('price'))),
        'tax_rate': safe_float(data.get('tax_rate', 0)),
        'min_stock': safe_int(data.get('min_stock', data.get('min_quantity', 0))),
    })


def transform_vendor(data, doc_id):
    """inv_vendors: from vendors."""
    return ensure_audit_fields({
        'vendor_id': doc_id,
        'legal_name': safe_str(data.get('legal_name', data.get('name', ''))),
        'email': safe_str(data.get('email')),
        'phone': safe_str(data.get('phone')),
        'address': safe_str(data.get('address')),
        'tax_id': safe_str(data.get('tax_id', data.get('tin', ''))),
        'payment_terms': safe_str(data.get('payment_terms', data.get('terms', 'net30'))),
        'contact_person': safe_str(data.get('contact_person', data.get('contact', ''))),
    })


def transform_requisition(data, doc_id):
    """inv_requisitions: from requisitions."""
    return ensure_audit_fields({
        'req_id': doc_id,
        'req_number': safe_str(data.get('req_number', data.get('requisition_number', data.get('id', doc_id)))),
        'requested_by': safe_str(data.get('requested_by', data.get('employee', data.get('requester')))),
        'department': safe_str(data.get('department', data.get('department_id'))),
        'line_items': data.get('line_items', data.get('items', [])),
        'notes': safe_str(data.get('notes', data.get('description', ''))),
        'status': safe_str(data.get('status', 'Pending')),
        'priority': safe_str(data.get('priority', 'normal')),
        'required_date': data.get('required_date', data.get('requiredDate')),
    })


def transform_purchase_order(data, doc_id):
    """inv_purchase_orders: from purchase_orders."""
    return ensure_audit_fields({
        'po_id': doc_id,
        'po_number': safe_str(data.get('po_number', data.get('purchase_order_number', data.get('id', doc_id)))),
        'vendor_id': safe_str(data.get('vendor', data.get('vendor_id'))),
        'req_id': safe_str(data.get('requisition', data.get('requisition_id', data.get('req_id')))),
        'line_items': data.get('line_items', data.get('items', [])),
        'status': safe_str(data.get('status', 'Draft')),
        'total_amount': safe_float(data.get('total_amount', data.get('total'))),
        'order_date': data.get('order_date', data.get('createdAt')),
        'expected_date': data.get('expected_date', data.get('delivery_date', data.get('expectedDate'))),
        'notes': safe_str(data.get('notes', '')),
    })


def transform_goods_receipt(data, doc_id):
    """inv_goods_receipts: from goods_receipts."""
    return ensure_audit_fields({
        'grn_id': doc_id,
        'grn_number': safe_str(data.get('grn_number', data.get('goods_receipt_number', doc_id))),
        'po_id': safe_str(data.get('po_id', data.get('purchase_order', data.get('purchase_order_id')))),
        'received_items': data.get('received_items', data.get('items', [])),
        'received_date': data.get('received_date', data.get('date', data.get('createdAt'))),
        'received_by': safe_str(data.get('received_by', data.get('receiver'))),
        'notes': safe_str(data.get('notes', '')),
    })


def transform_invoice(data, doc_id):
    """fin_invoices: from invoices."""
    return ensure_audit_fields({
        'invoice_id': doc_id,
        'invoice_number': safe_str(data.get('invoice_number', data.get('invoice_no', data.get('id', doc_id)))),
        'customer_name': safe_str(data.get('customer_name', data.get('customer', data.get('client')))),
        'customer_email': safe_str(data.get('customer_email', data.get('email'))),
        'invoice_date': data.get('invoice_date', data.get('date', data.get('createdAt'))),
        'due_date': data.get('due_date', data.get('dueDate')),
        'line_items': data.get('line_items', data.get('items', [])),
        'subtotal': safe_float(data.get('subtotal', 0)),
        'tax_total': safe_float(data.get('tax_total', data.get('tax', 0))),
        'grand_total': safe_float(data.get('grand_total', data.get('total', data.get('amount', 0)))),
        'amount_paid': safe_float(data.get('amount_paid', data.get('paid', 0))),
        'status': safe_str(data.get('status', 'Pending')),
    })


def transform_vendor_bill(data, doc_id):
    """fin_vendor_bills: from vendor_bills."""
    return ensure_audit_fields({
        'bill_id': doc_id,
        'bill_number': safe_str(data.get('bill_number', data.get('bill_no', doc_id))),
        'vendor_name': safe_str(data.get('vendor_name', data.get('vendor'))),
        'bill_date': data.get('bill_date', data.get('date', data.get('createdAt'))),
        'due_date': data.get('due_date', data.get('dueDate')),
        'line_items': data.get('line_items', data.get('items', [])),
        'total_amount': safe_float(data.get('total_amount', data.get('total', data.get('amount', 0)))),
        'amount_paid': safe_float(data.get('amount_paid', data.get('paid', 0))),
        'status': safe_str(data.get('status', 'Pending')),
    })


def transform_journal_entry(data, doc_id):
    """fin_journal_entries: from journal_entries."""
    return ensure_audit_fields({
        'entry_id': doc_id,
        'entry_number': safe_str(data.get('entry_number', data.get('journal_no', doc_id))),
        'entry_date': data.get('entry_date', data.get('date', data.get('createdAt'))),
        'description': safe_str(data.get('description', data.get('narration', ''))),
        'lines': data.get('lines', data.get('entries', data.get('journal_lines', []))),
        'status': safe_str(data.get('status', 'Posted')),
        'approved_by': safe_str(data.get('approved_by')),
    })


def transform_chart_of_account(data, doc_id):
    """fin_chart_of_accounts: from chart_of_accounts."""
    return ensure_audit_fields({
        'account_id': doc_id,
        'account_code': safe_str(data.get('account_code', data.get('code', ''))),
        'name': safe_str(data.get('name', data.get('account_name', ''))),
        'account_type': safe_str(data.get('account_type', data.get('type', 'expense'))),
        'currency': safe_str(data.get('currency', 'USD')),
        'parent_account_id': safe_str(data.get('parent_account', data.get('parent_id'))),
        'opening_balance': safe_float(data.get('opening_balance', 0)),
        'is_active': safe_bool(data.get('is_active', True)),
    })


def transform_tax_code(data, doc_id):
    """fin_tax_codes: from tax_codes."""
    return ensure_audit_fields({
        'tax_id': doc_id,
        'name': safe_str(data.get('name', data.get('tax_name', ''))),
        'rate': safe_float(data.get('rate', data.get('tax_rate', 0))),
        'type': safe_str(data.get('type', 'sales')),
        'is_active': safe_bool(data.get('is_active', True)),
    })


def transform_project(data, doc_id):
    """sol_projects: from projects."""
    return ensure_audit_fields({
        'project_id': doc_id,
        'name': safe_str(data.get('name', data.get('project_name', ''))),
        'code': safe_str(data.get('code', data.get('project_code', ''))),
        'description': safe_str(data.get('description', '')),
        'status': safe_str(data.get('status', 'Planning')),
        'manager_id': safe_str(data.get('manager', data.get('manager_id'))),
        'client_name': safe_str(data.get('client', data.get('client_name', ''))),
        'start_date': data.get('start_date', data.get('startDate')),
        'end_date': data.get('end_date', data.get('endDate', data.get('deadline'))),
        'budget': safe_float(data.get('budget', 0)),
        'spent': safe_float(data.get('spent', 0)),
        'priority': safe_str(data.get('priority', 'medium')),
    })


def transform_project_phase(data, doc_id):
    """sol_project_phases: from project_phases."""
    return ensure_audit_fields({
        'phase_id': doc_id,
        'project_id': safe_str(data.get('project', data.get('project_id'))),
        'name': safe_str(data.get('name', data.get('phase_name', ''))),
        'description': safe_str(data.get('description', '')),
        'order': safe_int(data.get('order', 0)),
        'start_date': data.get('start_date'),
        'end_date': data.get('end_date'),
        'status': safe_str(data.get('status', 'Pending')),
    })


def transform_task(data, doc_id):
    """sol_tasks: from project_tasks."""
    return ensure_audit_fields({
        'task_id': doc_id,
        'project_id': safe_str(data.get('project', data.get('project_id'))),
        'phase_id': safe_str(data.get('phase', data.get('phase_id'))),
        'title': safe_str(data.get('title', data.get('name', ''))),
        'description': safe_str(data.get('description', '')),
        'status': safe_str(data.get('status', 'To Do')),
        'priority': safe_str(data.get('priority', 'medium')),
        'assignee_id': safe_str(data.get('assignee', data.get('assignee_id'))),
        'due_date': data.get('due_date', data.get('dueDate')),
        'labels': data.get('labels', data.get('tags', [])),
        'estimated_hours': safe_float(data.get('estimated_hours', 0)),
    })


def transform_meeting(data, doc_id):
    """sol_meetings: from meetings."""
    return ensure_audit_fields({
        'meeting_id': doc_id,
        'title': safe_str(data.get('title', data.get('meeting_title', ''))),
        'description': safe_str(data.get('description', '')),
        'project_id': safe_str(data.get('project', data.get('project_id'))),
        'scheduled_at': data.get('scheduled_at', data.get('date', data.get('datetime'))),
        'duration_minutes': safe_int(data.get('duration_minutes', data.get('duration', 60))),
        'location': safe_str(data.get('location', data.get('meeting_link', ''))),
        'attendees': data.get('attendees', data.get('participants', [])),
        'status': safe_str(data.get('status', 'Scheduled')),
    })


def transform_investor(data, doc_id):
    """invst_investors: from investors."""
    return ensure_audit_fields({
        'investor_id': doc_id,
        'legal_name': safe_str(data.get('legal_name', data.get('name', ''))),
        'email': safe_str(data.get('email')),
        'phone': safe_str(data.get('phone')),
        'address': safe_str(data.get('address', '')),
        'investor_type': safe_str(data.get('investor_type', data.get('type', 'individual'))),
        'risk_profile': safe_str(data.get('risk_profile', 'moderate')),
        'kyc_status': safe_str(data.get('kyc_status', 'pending')),
        'notes': safe_str(data.get('notes', '')),
    })


def transform_loan(data, doc_id):
    """invst_loans: from investor_loans."""
    return ensure_audit_fields({
        'loan_id': doc_id,
        'investor_id': safe_str(data.get('investor', data.get('investor_id'))),
        'principal': safe_float(data.get('principal', data.get('amount', 0))),
        'interest_rate': safe_float(data.get('interest_rate', data.get('rate', 0))),
        'interest_type': safe_str(data.get('interest_type', 'simple')),
        'term_months': safe_int(data.get('term_months', data.get('term', 12))),
        'disbursement_date': data.get('disbursement_date', data.get('date')),
        'status': safe_str(data.get('status', 'Active')),
        'outstanding': safe_float(data.get('outstanding', data.get('principal', 0))),
    })


def transform_loan_schedule(data, doc_id):
    """invst_loan_schedules: from loan_amortization_schedules."""
    return ensure_audit_fields({
        'schedule_id': doc_id,
        'loan_id': safe_str(data.get('loan', data.get('loan_id'))),
        'installment_number': safe_int(data.get('installment_number', data.get('installment_no', 0))),
        'due_date': data.get('due_date'),
        'principal_amount': safe_float(data.get('principal_amount', data.get('principal', 0))),
        'interest_amount': safe_float(data.get('interest_amount', data.get('interest', 0))),
        'total_amount': safe_float(data.get('total_amount', data.get('total', 0))),
        'paid_amount': safe_float(data.get('paid_amount', data.get('paid', 0))),
        'status': safe_str(data.get('status', 'Pending')),
    })


def transform_course(data, doc_id):
    """trn_courses: from learn_courses."""
    return ensure_audit_fields({
        'course_id': doc_id,
        'title': safe_str(data.get('title', data.get('course_name', ''))),
        'description': safe_str(data.get('description', '')),
        'category': safe_str(data.get('category', data.get('course_category', ''))),
        'duration': safe_str(data.get('duration', data.get('course_duration', ''))),
        'format': safe_str(data.get('format', data.get('course_format', 'online'))),
        'fee': safe_float(data.get('fee', data.get('course_fee', 0))),
        'curriculum': safe_str(data.get('curriculum', data.get('syllabus', ''))),
        'is_public': safe_bool(data.get('is_public', data.get('public', False))),
        'image_url': safe_str(data.get('image_url', data.get('image', ''))),
    })


def transform_batch(data, doc_id):
    """trn_batches: from learn_batches."""
    return ensure_audit_fields({
        'batch_id': doc_id,
        'course_id': safe_str(data.get('course', data.get('course_id'))),
        'name': safe_str(data.get('name', data.get('batch_name', ''))),
        'code': safe_str(data.get('code', data.get('batch_code', ''))),
        'start_date': data.get('start_date', data.get('startDate')),
        'end_date': data.get('end_date', data.get('endDate')),
        'schedule': safe_str(data.get('schedule', data.get('class_schedule', ''))),
        'status': safe_str(data.get('status', 'Upcoming')),
        'capacity': safe_int(data.get('capacity', 0)),
        'trainer_id': safe_str(data.get('trainer', data.get('trainer_id'))),
    })


def transform_registration(data, doc_id):
    """trn_registrations: from learn_registrations."""
    return ensure_audit_fields({
        'reg_id': doc_id,
        'student_id': safe_str(data.get('studentId', data.get('student_id'))),
        'student_name': safe_str(data.get('studentName', data.get('student_name', ''))),
        'student_email': safe_str(data.get('studentEmail', data.get('student_email', ''))),
        'student_phone': safe_str(data.get('studentPhone', data.get('student_phone', ''))),
        'course_id': safe_str(data.get('courseId', data.get('course_id'))),
        'batch_id': safe_str(data.get('batchId', data.get('batch_id'))),
        'registration_date': data.get('registrationDate', data.get('registration_date', data.get('createdAt'))),
        'status': safe_str(data.get('status', 'Active')),
        'total_fee': safe_float(data.get('totalFee', data.get('total_fee', 0))),
        'amount_paid': safe_float(data.get('amountPaid', data.get('amount_paid', 0))),
        'due_amount': safe_float(data.get('dueAmount', data.get('due_amount', 0))),
        'source': safe_str(data.get('source', 'manual')),
    })


def transform_payment(data, doc_id):
    """trn_payments: from learn_payments."""
    return ensure_audit_fields({
        'payment_id': doc_id,
        'reg_id': safe_str(data.get('regId', data.get('reg_id', data.get('registration_id')))),
        'student_name': safe_str(data.get('studentName', data.get('student_name', ''))),
        'payment_date': data.get('paymentDate', data.get('payment_date', data.get('date', data.get('createdAt')))),
        'amount': safe_float(data.get('amount', 0)),
        'method': safe_str(data.get('method', data.get('payment_method', 'cash'))),
        'reference': safe_str(data.get('reference', data.get('transaction_id', ''))),
        'installment_name': safe_str(data.get('installmentName', data.get('installment_name', ''))),
        'notes': safe_str(data.get('notes', '')),
    })


def transform_assessment(data, doc_id):
    """trn_assessments: from learn_course_assessments."""
    return ensure_audit_fields({
        'assessment_id': doc_id,
        'course_id': safe_str(data.get('courseId', data.get('course_id'))),
        'batch_id': safe_str(data.get('batchId', data.get('batch_id'))),
        'title': safe_str(data.get('title', data.get('assessment_title', ''))),
        'type': safe_str(data.get('type', data.get('assessment_type', 'quiz'))),
        'max_score': safe_float(data.get('maxScore', data.get('max_score', 100))),
        'passing_score': safe_float(data.get('passingScore', data.get('passing_score', 40))),
        'date': data.get('date', data.get('assessment_date')),
    })


def transform_certificate(data, doc_id):
    """trn_certificates: from learn_certificates."""
    return ensure_audit_fields({
        'cert_id': doc_id,
        'cert_number': safe_str(data.get('certNumber', data.get('cert_number', data.get('certificate_no', '')))),
        'student_id': safe_str(data.get('studentId', data.get('student_id'))),
        'student_name': safe_str(data.get('studentName', data.get('student_name', ''))),
        'course_id': safe_str(data.get('courseId', data.get('course_id'))),
        'batch_id': safe_str(data.get('batchId', data.get('batch_id'))),
        'issue_date': data.get('issueDate', data.get('issue_date', data.get('date', server_timestamp()))),
        'verification_code': safe_str(data.get('verificationCode', data.get('verification_code', ''))),
        'status': safe_str(data.get('status', 'Issued')),
        'grade': safe_str(data.get('grade', '')),
    })


def transform_expense(data, doc_id):
    """trn_expenses: from learn_expenses."""
    return ensure_audit_fields({
        'expense_id': doc_id,
        'category': safe_str(data.get('category', data.get('expense_category', ''))),
        'description': safe_str(data.get('description', safe_str(data.get('notes', '')))),
        'amount': safe_float(data.get('amount', 0)),
        'date': data.get('date', data.get('expense_date', data.get('createdAt'))),
        'paid_by': safe_str(data.get('paid_by', data.get('paidBy', ''))),
        'payment_method': safe_str(data.get('payment_method', data.get('method', 'cash'))),
    })


def transform_audit_log(data, doc_id):
    """sys_audit_logs: unified from erp_audit_logs and learn_tbl_audit_logs."""
    return {
        'log_id': doc_id,
        'user_id': safe_str(data.get('user_id', data.get('userId', data.get('user', '')))),
        'username': safe_str(data.get('username', data.get('userName', 'Anonymous'))),
        'action': safe_str(data.get('action', 'UNKNOWN')),
        'module': safe_str(data.get('module', 'unknown')),
        'description': safe_str(data.get('description', '')),
        'ip_address': safe_str(data.get('ip_address', data.get('ipAddress', ''))),
        'before_state': data.get('before_state', data.get('beforeState')),
        'after_state': data.get('after_state', data.get('afterState')),
        'sha256_hash': safe_str(data.get('sha256_hash', data.get('sha256Hash', ''))),
        'timestamp': data.get('timestamp', data.get('createdAt', data.get('created_at', server_timestamp()))),
    }


# ══════════════════════════════════════════════════════════════════════
#  COLLECTION MIGRATION DEFINITIONS
# ══════════════════════════════════════════════════════════════════════

MIGRATIONS = [
    # ── System ──────────────────────────────────────────────────────
    {
        'name': 'sys_users',
        'source': 'users',
        'transform': transform_user,
        'description': 'User replica (Django auth.User → read-only Firestore)',
    },
    {
        'name': 'sys_audit_logs',
        'source': 'erp_audit_logs',
        'transform': transform_audit_log,
        'description': 'ERP audit logs → unified sys_audit_logs',
    },
    {
        'name': 'sys_audit_logs_from_training',
        'source': 'learn_tbl_audit_logs',
        'transform': transform_audit_log,
        'description': 'Training audit logs → unified sys_audit_logs',
    },

    # ── Organization ────────────────────────────────────────────────
    {
        'name': 'org_departments',
        'source': 'hrm_departments',
        'transform': transform_department,
        'description': 'HR departments → org_departments',
    },
    {
        'name': 'org_departments_sub',
        'source': 'hrm_sub_departments',
        'transform': lambda d, i: {**transform_department(d, i), 'is_department': False},
        'description': 'HR sub-departments → org_departments (is_department=false)',
    },
    {
        'name': 'org_positions',
        'source': 'hrm_positions',
        'transform': transform_position,
        'description': 'HR positions → org_positions',
    },

    # ── HRM ─────────────────────────────────────────────────────────
    {
        'name': 'hrm_employees',
        'source': 'employees',
        'transform': transform_employee,
        'description': 'Employees → hrm_employees (restructured)',
    },
    {
        'name': 'hrm_recruitment_candidates',
        'source': 'hrm_candidates',
        'transform': transform_candidate,
        'description': 'Candidates → hrm_recruitment_candidates',
    },
    {
        'name': 'hrm_recruitment_shortlists',
        'source': 'hrm_shortlists',
        'transform': transform_shortlist,
        'description': 'Shortlists → hrm_recruitment_shortlists',
    },
    {
        'name': 'hrm_recruitment_interviews',
        'source': 'hrm_interviews',
        'transform': transform_interview,
        'description': 'Interviews → hrm_recruitment_interviews',
    },
    {
        'name': 'hrm_recruitment_selections',
        'source': 'hrm_selections',
        'transform': transform_selection,
        'description': 'Selections → hrm_recruitment_selections',
    },
    {
        'name': 'hrm_holidays',
        'source': 'hrm_holidays',
        'transform': lambda d, i: ensure_audit_fields({
            'holiday_id': i,
            'name': safe_str(d.get('holiday_name', d.get('name', ''))),
            'from_date': d.get('from_date', d.get('start_date')),
            'to_date': d.get('to_date', d.get('end_date')),
            'type': safe_str(d.get('type', 'public')),
            'is_active': True,
        }),
        'description': 'Holidays → hrm_holidays (standardized)',
    },
    {
        'name': 'hrm_advances',
        'source': 'hrm_advances',
        'transform': lambda d, i: ensure_audit_fields({
            'advance_id': i,
            'employee_name': safe_str(d.get('employee', d.get('employee_name', ''))),
            'amount': safe_float(d.get('amount', 0)),
            'reason': safe_str(d.get('reason', d.get('notes', ''))),
            'deduct_month': safe_str(d.get('deduct_month', '')),
            'installments': safe_int(d.get('installments', 1)),
            'status': safe_str(d.get('status', 'Pending')),
        }),
        'description': 'Advances → hrm_advances (standardized)',
    },
    {
        'name': 'hrm_onboarding_tasks',
        'source': 'hrm_onboarding_tasks',
        'transform': lambda d, i: ensure_audit_fields({
            'task_id': i,
            'employee_name': safe_str(d.get('employee', d.get('employee_name', ''))),
            'task': safe_str(d.get('task', d.get('task_name', ''))),
            'assigned_to': safe_str(d.get('assigned_to', '')),
            'due_date': d.get('due_date'),
            'status': safe_str(d.get('status', 'Pending')),
        }),
        'description': 'Onboarding tasks → hrm_onboarding_tasks',
    },
    {
        'name': 'hrm_exit_clearance',
        'source': 'hrm_exit_clearance',
        'transform': lambda d, i: ensure_audit_fields({
            'clearance_id': i,
            'employee_name': safe_str(d.get('employee', d.get('employee_name', ''))),
            'clearance_item': safe_str(d.get('clearance_item', d.get('item', ''))),
            'department': safe_str(d.get('department', '')),
            'status': safe_str(d.get('status', 'Pending')),
        }),
        'description': 'Exit clearance → hrm_exit_clearance',
    },
    {
        'name': 'hrm_employee_shifts',
        'source': 'hrm_employee_shifts',
        'transform': lambda d, i: ensure_audit_fields({
            'shift_id': i,
            'employee_name': safe_str(d.get('employee', d.get('employee_name', d.get('name', '')))),
            'shift_type': safe_str(d.get('shift_type', d.get('type', 'morning'))),
            'start_time': safe_str(d.get('start_time', '')),
            'end_time': safe_str(d.get('end_time', '')),
            'date': d.get('date'),
        }),
        'description': 'Employee shifts → hrm_employee_shifts',
    },
    {
        'name': 'hrm_expense_claims',
        'source': 'hrm_expense_claims',
        'transform': lambda d, i: ensure_audit_fields({
            'claim_id': i,
            'employee_name': safe_str(d.get('employee', d.get('employee_name', ''))),
            'category': safe_str(d.get('category', '')),
            'description': safe_str(d.get('description', '')),
            'amount': safe_float(d.get('amount', 0)),
            'date': d.get('date', d.get('expense_date')),
            'status': safe_str(d.get('status', 'Pending')),
        }),
        'description': 'Expense claims → hrm_expense_claims',
    },
    {
        'name': 'hrm_payrolls',
        'source': 'hrm_payrolls',
        'transform': lambda d, i: ensure_audit_fields({
            'payroll_id': i,
            'employee_name': safe_str(d.get('employee', d.get('employee_name', ''))),
            'period': safe_str(d.get('period', d.get('pay_period', ''))),
            'gross_salary': safe_float(d.get('gross_salary', d.get('gross', 0))),
            'deductions': safe_float(d.get('deductions', d.get('total_deductions', 0))),
            'net_pay': safe_float(d.get('net_pay', d.get('net', 0))),
            'status': safe_str(d.get('status', 'Draft')),
            'disbursed_at': d.get('disbursed_at', d.get('disbursement_date')),
        }),
        'description': 'Payrolls → hrm_payrolls (standardized)',
    },
    {
        'name': 'hrm_assets',
        'source': 'hrm_assets',
        'transform': lambda d, i: ensure_audit_fields({
            'asset_id': i,
            'employee_name': safe_str(d.get('employee', d.get('employee_name', ''))),
            'asset_name': safe_str(d.get('asset_name', d.get('name', ''))),
            'asset_type': safe_str(d.get('asset_type', d.get('type', 'equipment'))),
            'serial_number': safe_str(d.get('serial_number', '')),
            'assigned_date': d.get('assigned_date', d.get('date')),
            'status': safe_str(d.get('status', 'Assigned')),
            'notes': safe_str(d.get('notes', '')),
        }),
        'description': 'Assets → hrm_assets',
    },

    # ── Inventory ───────────────────────────────────────────────────
    {
        'name': 'inv_products',
        'source': 'products',
        'transform': transform_product,
        'description': 'Products → inv_products',
    },
    {
        'name': 'inv_vendors',
        'source': 'vendors',
        'transform': transform_vendor,
        'description': 'Vendors → inv_vendors',
    },
    {
        'name': 'inv_requisitions',
        'source': 'requisitions',
        'transform': transform_requisition,
        'description': 'Requisitions → inv_requisitions',
    },
    {
        'name': 'inv_purchase_orders',
        'source': 'purchase_orders',
        'transform': transform_purchase_order,
        'description': 'Purchase orders → inv_purchase_orders',
    },
    {
        'name': 'inv_goods_receipts',
        'source': 'goods_receipts',
        'transform': transform_goods_receipt,
        'description': 'Goods receipts → inv_goods_receipts',
    },
    {
        'name': 'inv_rfqs',
        'source': 'rfqs',
        'transform': lambda d, i: ensure_audit_fields({
            'rfq_id': i,
            'rfq_number': safe_str(d.get('rfq_number', d.get('number', i))),
            'title': safe_str(d.get('title', d.get('rfq_title', ''))),
            'description': safe_str(d.get('description', '')),
            'status': safe_str(d.get('status', 'Open')),
            'issue_date': d.get('issue_date', d.get('date', d.get('createdAt'))),
            'closing_date': d.get('closing_date', d.get('deadline')),
        }),
        'description': 'RFQs → inv_rfqs',
    },
    {
        'name': 'inv_quotations',
        'source': 'quotations',
        'transform': lambda d, i: ensure_audit_fields({
            'quotation_id': i,
            'rfq_id': safe_str(d.get('rfq', d.get('rfq_id'))),
            'vendor_id': safe_str(d.get('vendor', d.get('vendor_id'))),
            'amount': safe_float(d.get('amount', d.get('total', 0))),
            'currency': safe_str(d.get('currency', 'USD')),
            'valid_until': d.get('valid_until', d.get('expiry_date')),
            'status': safe_str(d.get('status', 'Submitted')),
            'notes': safe_str(d.get('notes', '')),
        }),
        'description': 'Quotations → inv_quotations',
    },
    {
        'name': 'inv_deliveries',
        'source': 'deliveries',
        'transform': lambda d, i: ensure_audit_fields({
            'delivery_id': i,
            'delivery_number': safe_str(d.get('delivery_number', d.get('number', i))),
            'requisition_id': safe_str(d.get('requisition', d.get('requisition_id'))),
            'customer_name': safe_str(d.get('customer', d.get('customer_name', ''))),
            'delivery_date': d.get('delivery_date', d.get('date')),
            'status': safe_str(d.get('status', 'Pending')),
            'items': d.get('items', d.get('line_items', [])),
            'notes': safe_str(d.get('notes', '')),
        }),
        'description': 'Deliveries → inv_deliveries',
    },
    {
        'name': 'inv_inventory_ledger',
        'source': 'inventory_ledger',
        'transform': lambda d, i: ensure_audit_fields({
            'ledger_id': i,
            'product_id': safe_str(d.get('product', d.get('product_id'))),
            'transaction_type': safe_str(d.get('transaction_type', d.get('type', 'adjustment'))),
            'quantity_change': safe_int(d.get('quantity_change', d.get('qty', 0))),
            'balance_after': safe_int(d.get('balance_after', d.get('balance', 0))),
            'reference_id': safe_str(d.get('reference', d.get('reference_id', ''))),
            'reference_type': safe_str(d.get('reference_type', '')),
            'notes': safe_str(d.get('notes', '')),
            'date': d.get('date', d.get('createdAt', server_timestamp())),
        }),
        'description': 'Inventory ledger → inv_inventory_ledger',
    },

    # ── Finance ─────────────────────────────────────────────────────
    {
        'name': 'fin_chart_of_accounts',
        'source': 'chart_of_accounts',
        'transform': transform_chart_of_account,
        'description': 'Chart of accounts → fin_chart_of_accounts',
    },
    {
        'name': 'fin_journal_entries',
        'source': 'journal_entries',
        'transform': transform_journal_entry,
        'description': 'Journal entries → fin_journal_entries',
    },
    {
        'name': 'fin_invoices',
        'source': 'invoices',
        'transform': transform_invoice,
        'description': 'Invoices → fin_invoices (AR)',
    },
    {
        'name': 'fin_vendor_bills',
        'source': 'vendor_bills',
        'transform': transform_vendor_bill,
        'description': 'Vendor bills → fin_vendor_bills (AP)',
    },
    {
        'name': 'fin_payments',
        'source': 'payments',
        'transform': lambda d, i: ensure_audit_fields({
            'payment_id': i,
            'invoice_id': safe_str(d.get('invoice', d.get('invoice_id'))),
            'payment_date': d.get('payment_date', d.get('date', d.get('createdAt'))),
            'amount': safe_float(d.get('amount', 0)),
            'method': safe_str(d.get('method', d.get('payment_method', 'cash'))),
            'reference_number': safe_str(d.get('reference_number', d.get('reference', d.get('transaction_id', '')))),
            'notes': safe_str(d.get('notes', '')),
        }),
        'description': 'Payments → fin_payments',
    },
    {
        'name': 'fin_tax_codes',
        'source': 'tax_codes',
        'transform': transform_tax_code,
        'description': 'Tax codes → fin_tax_codes',
    },
    {
        'name': 'fin_audit_trail',
        'source': 'financial_audit_trail',
        'transform': lambda d, i: {
            'log_id': i,
            'user_id': safe_str(d.get('user_id', d.get('user', ''))),
            'action': safe_str(d.get('action', '')),
            'entity_type': safe_str(d.get('entity_type', d.get('module', ''))),
            'entity_id': safe_str(d.get('entity_id', '')),
            'changes': d.get('changes', d.get('details', {})),
            'ip_address': safe_str(d.get('ip_address', '')),
            'timestamp': d.get('timestamp', d.get('createdAt', server_timestamp())),
        },
        'description': 'Financial audit trail → fin_audit_trail',
    },

    # ── Training ────────────────────────────────────────────────────
    {
        'name': 'trn_courses',
        'source': 'learn_courses',
        'transform': transform_course,
        'description': 'Courses → trn_courses',
    },
    {
        'name': 'trn_batches',
        'source': 'learn_batches',
        'transform': transform_batch,
        'description': 'Batches → trn_batches',
    },
    {
        'name': 'trn_registrations',
        'source': 'learn_registrations',
        'transform': transform_registration,
        'description': 'Registrations → trn_registrations',
    },
    {
        'name': 'trn_registrations_online',
        'source': 'learn_online_registrations',
        'transform': lambda d, i: {**transform_registration(d, i), 'source': 'online'},
        'description': 'Online registrations → trn_registrations (source=online)',
    },
    {
        'name': 'trn_payments',
        'source': 'learn_payments',
        'transform': transform_payment,
        'description': 'Payments → trn_payments',
    },
    {
        'name': 'trn_assessments',
        'source': 'learn_course_assessments',
        'transform': transform_assessment,
        'description': 'Assessments → trn_assessments',
    },
    {
        'name': 'trn_certificates',
        'source': 'learn_certificates',
        'transform': transform_certificate,
        'description': 'Certificates → trn_certificates',
    },
    {
        'name': 'trn_expenses',
        'source': 'learn_expenses',
        'transform': transform_expense,
        'description': 'Training expenses → trn_expenses',
    },
    {
        'name': 'trn_inquiries',
        'source': 'learn_online_inquiries',
        'transform': lambda d, i: ensure_audit_fields({
            'inquiry_id': i,
            'name': safe_str(d.get('name', d.get('full_name', ''))),
            'email': safe_str(d.get('email')),
            'phone': safe_str(d.get('phone')),
            'course_id': safe_str(d.get('courseId', d.get('course_id'))),
            'message': safe_str(d.get('message', d.get('notes', ''))),
            'status': safe_str(d.get('status', 'New')),
            'source': safe_str(d.get('source', 'website')),
        }),
        'description': 'Inquiries → trn_inquiries',
    },
    {
        'name': 'trn_job_placements',
        'source': 'learn_job_placements',
        'transform': lambda d, i: ensure_audit_fields({
            'placement_id': i,
            'student_id': safe_str(d.get('studentId', d.get('student_id'))),
            'student_name': safe_str(d.get('studentName', d.get('student_name', ''))),
            'company': safe_str(d.get('company', d.get('company_name', ''))),
            'position': safe_str(d.get('position', d.get('job_title', ''))),
            'placement_date': d.get('placementDate', d.get('placement_date', d.get('date'))),
            'salary': safe_float(d.get('salary', d.get('offered_salary', 0))),
            'status': safe_str(d.get('status', 'Placed')),
        }),
        'description': 'Job placements → trn_job_placements',
    },
    {
        'name': 'trn_institutes',
        'source': 'learn_public_institutes',
        'transform': lambda d, i: ensure_audit_fields({
            'institute_id': i,
            'name': safe_str(d.get('name', d.get('institute_name', ''))),
            'contact_person': safe_str(d.get('contact_person', d.get('contact', ''))),
            'email': safe_str(d.get('email')),
            'phone': safe_str(d.get('phone')),
            'address': safe_str(d.get('address', '')),
            'is_active': True,
        }),
        'description': 'Institutes → trn_institutes',
    },
    {
        'name': 'trn_ambassadors',
        'source': 'learn_brand_ambassadors',
        'transform': lambda d, i: ensure_audit_fields({
            'ambassador_id': i,
            'name': safe_str(d.get('name', d.get('ambassador_name', ''))),
            'email': safe_str(d.get('email')),
            'phone': safe_str(d.get('phone')),
            'student_id': safe_str(d.get('studentId', d.get('student_id'))),
            'commission_rate': safe_float(d.get('commissionRate', d.get('commission_rate', 0))),
            'total_commission': safe_float(d.get('totalCommission', d.get('total_commission', 0))),
            'is_active': safe_bool(d.get('is_active', True)),
        }),
        'description': 'Brand ambassadors → trn_ambassadors',
    },
    {
        'name': 'trn_commissions',
        'source': 'learn_commissions',
        'transform': lambda d, i: ensure_audit_fields({
            'commission_id': i,
            'ambassador_name': safe_str(d.get('ambassadorName', d.get('ambassador_name', ''))),
            'student_name': safe_str(d.get('studentName', d.get('student_name', ''))),
            'amount': safe_float(d.get('amount', 0)),
            'status': safe_str(d.get('status', 'Pending')),
            'paid_date': d.get('paidDate', d.get('paid_date')),
        }),
        'description': 'Commissions → trn_commissions',
    },
    {
        'name': 'trn_classes',
        'source': 'learn_classes',
        'transform': lambda d, i: ensure_audit_fields({
            'class_id': i,
            'batch_id': safe_str(d.get('batch', d.get('batch_id'))),
            'date': d.get('date'),
            'start_time': safe_str(d.get('start_time', d.get('startTime', ''))),
            'end_time': safe_str(d.get('end_time', d.get('endTime', ''))),
            'topic': safe_str(d.get('topic', '')),
            'trainer': safe_str(d.get('trainer', d.get('trainer_name', ''))),
        }),
        'description': 'Classes → trn_classes',
    },

    # ── Solutions ───────────────────────────────────────────────────
    {
        'name': 'sol_projects',
        'source': 'projects',
        'transform': transform_project,
        'description': 'Projects → sol_projects',
    },
    {
        'name': 'sol_project_phases',
        'source': 'project_phases',
        'transform': transform_project_phase,
        'description': 'Project phases → sol_project_phases',
    },
    {
        'name': 'sol_tasks',
        'source': 'project_tasks',
        'transform': transform_task,
        'description': 'Tasks → sol_tasks',
    },
    {
        'name': 'sol_meetings',
        'source': 'meetings',
        'transform': transform_meeting,
        'description': 'Meetings → sol_meetings',
    },
    {
        'name': 'sol_project_requisitions',
        'source': 'project_requisitions',
        'transform': lambda d, i: ensure_audit_fields({
            'req_id': i,
            'project_id': safe_str(d.get('project', d.get('project_id'))),
            'title': safe_str(d.get('title', d.get('req_title', ''))),
            'description': safe_str(d.get('description', '')),
            'estimated_cost': safe_float(d.get('estimated_cost', d.get('cost', 0))),
            'status': safe_str(d.get('status', 'Pending')),
            'vendor': safe_str(d.get('vendor', '')),
            'notes': safe_str(d.get('notes', '')),
        }),
        'description': 'Project requisitions → sol_project_requisitions',
    },
    {
        'name': 'sol_software_licenses',
        'source': 'software_licenses',
        'transform': lambda d, i: ensure_audit_fields({
            'license_id': i,
            'name': safe_str(d.get('name', d.get('license_name', ''))),
            'vendor': safe_str(d.get('vendor', d.get('vendor_name', ''))),
            'license_key': safe_str(d.get('license_key', d.get('key', ''))),
            'seats': safe_int(d.get('seats', d.get('quantity', 0))),
            'purchase_date': d.get('purchase_date', d.get('date')),
            'expiry_date': d.get('expiry_date', d.get('expiryDate')),
            'cost': safe_float(d.get('cost', d.get('price', 0))),
            'status': safe_str(d.get('status', 'Active')),
        }),
        'description': 'Software licenses → sol_software_licenses',
    },
    {
        'name': 'sol_project_stakeholders',
        'source': 'project_stakeholders',
        'transform': lambda d, i: ensure_audit_fields({
            'stakeholder_id': i,
            'project_id': safe_str(d.get('project', d.get('project_id'))),
            'name': safe_str(d.get('name', d.get('stakeholder_name', ''))),
            'email': safe_str(d.get('email')),
            'phone': safe_str(d.get('phone')),
            'role': safe_str(d.get('role', d.get('stakeholder_role', 'stakeholder'))),
            'organization': safe_str(d.get('organization', d.get('org', ''))),
        }),
        'description': 'Stakeholders → sol_project_stakeholders',
    },
    {
        'name': 'sol_service_tickets',
        'source': 'service_tickets',
        'transform': lambda d, i: ensure_audit_fields({
            'ticket_id': i,
            'title': safe_str(d.get('title', d.get('subject', ''))),
            'description': safe_str(d.get('description', '')),
            'priority': safe_str(d.get('priority', 'normal')),
            'status': safe_str(d.get('status', 'Open')),
            'assigned_to': safe_str(d.get('assigned_to', d.get('assignee', ''))),
            'customer_name': safe_str(d.get('customer', d.get('customer_name', ''))),
            'created_at': d.get('createdAt', d.get('created_at', server_timestamp())),
        }),
        'description': 'Service tickets → sol_service_tickets',
    },
    {
        'name': 'sys_contacts',
        'source': 'contacts',
        'transform': lambda d, i: ensure_audit_fields({
            'contact_id': i,
            'legal_name': safe_str(d.get('legal_name', d.get('name', ''))),
            'email': safe_str(d.get('email', '')),
            'phone': safe_str(d.get('phone', '')),
            'roles': d.get('roles', []),
        }),
        'description': 'V1 contacts → sys_contacts (deprecated, backward compat)',
    },

    # ── Investment ──────────────────────────────────────────────────
    {
        'name': 'invst_investors',
        'source': 'investors',
        'transform': transform_investor,
        'description': 'Investors → invst_investors',
    },
    {
        'name': 'invst_loans',
        'source': 'investor_loans',
        'transform': transform_loan,
        'description': 'Investor loans → invst_loans',
    },
    {
        'name': 'invst_loan_schedules',
        'source': 'loan_amortization_schedules',
        'transform': transform_loan_schedule,
        'description': 'Amortization schedules → invst_loan_schedules',
    },
    {
        'name': 'invst_transactions',
        'source': 'investment_transactions',
        'transform': lambda d, i: ensure_audit_fields({
            'transaction_id': i,
            'investor_id': safe_str(d.get('investor', d.get('investor_id'))),
            'type': safe_str(d.get('type', d.get('transaction_type', 'deposit'))),
            'amount': safe_float(d.get('amount', 0)),
            'currency': safe_str(d.get('currency', 'USD')),
            'date': d.get('date', d.get('createdAt')),
            'reference': safe_str(d.get('reference', d.get('reference_number', ''))),
            'notes': safe_str(d.get('notes', '')),
        }),
        'description': 'Investment transactions → invst_transactions',
    },
    {
        'name': 'invst_outbound_placements',
        'source': 'outbound_investments',
        'transform': lambda d, i: ensure_audit_fields({
            'placement_id': i,
            'instrument_name': safe_str(d.get('instrument_name', d.get('instrument', ''))),
            'institution': safe_str(d.get('institution', d.get('bank', ''))),
            'amount': safe_float(d.get('amount', 0)),
            'expected_return': safe_float(d.get('expected_return', d.get('return_rate', 0))),
            'start_date': d.get('start_date', d.get('date')),
            'maturity_date': d.get('maturity_date', d.get('maturityDate')),
            'status': safe_str(d.get('status', 'Active')),
        }),
        'description': 'Outbound investments → invst_outbound_placements',
    },
    {
        'name': 'invst_financial_instruments',
        'source': 'financial_instruments',
        'transform': lambda d, i: ensure_audit_fields({
            'instrument_id': i,
            'name': safe_str(d.get('name', d.get('instrument_name', ''))),
            'type': safe_str(d.get('type', d.get('instrument_type', 'bond'))),
            'issuer': safe_str(d.get('issuer', d.get('issuer_name', ''))),
            'face_value': safe_float(d.get('face_value', d.get('value', 0))),
            'interest_rate': safe_float(d.get('interest_rate', d.get('rate', 0))),
            'maturity_date': d.get('maturity_date', d.get('maturityDate')),
            'status': safe_str(d.get('status', 'Active')),
        }),
        'description': 'Financial instruments → invst_financial_instruments',
    },
    {
        'name': 'invst_pl_ledger',
        'source': 'pl_ledger_monthly',
        'transform': lambda d, i: ensure_audit_fields({
            'ledger_id': i,
            'month': safe_str(d.get('month', d.get('period', ''))),
            'year': safe_int(d.get('year', 0)),
            'income': safe_float(d.get('income', d.get('total_income', 0))),
            'expense': safe_float(d.get('expense', d.get('total_expense', 0))),
            'net_profit': safe_float(d.get('net_profit', d.get('profit', 0))),
            'notes': safe_str(d.get('notes', '')),
        }),
        'description': 'P&L ledger → invst_pl_ledger',
    },
    {
        'name': 'invst_portfolios',
        'source': 'portfolios',
        'transform': lambda d, i: ensure_audit_fields({
            'portfolio_id': i,
            'name': safe_str(d.get('name', d.get('portfolio_name', ''))),
            'investor_id': safe_str(d.get('investor', d.get('investor_id'))),
            'total_invested': safe_float(d.get('total_invested', d.get('invested_amount', 0))),
            'current_value': safe_float(d.get('current_value', 0)),
            'roi': safe_float(d.get('roi', d.get('return_rate', 0))),
            'currency': safe_str(d.get('currency', 'USD')),
        }),
        'description': 'Portfolios → invst_portfolios',
    },

    # ── Subcollection migrations (run after parent collections) ─────
    {
        'name': '_sub_attendance',
        'source': 'hrm_attendance',
        'transform': transform_attendance,
        'is_subcollection': True,
        'parent_collection': 'hrm_employees',
        'parent_id_field': 'name',
        'subcollection_name': 'attendance',
        'description': 'Attendance logs → hrm_employees/{id}/attendance',
    },
    {
        'name': '_sub_leaves',
        'source': 'hrm_leaves',
        'transform': transform_leave,
        'is_subcollection': True,
        'parent_collection': 'hrm_employees',
        'parent_id_field': 'name',
        'subcollection_name': 'leaves',
        'description': 'Leaves → hrm_employees/{id}/leaves',
    },
    {
        'name': '_sub_documents',
        'source': 'hrm_documents',
        'transform': transform_document,
        'is_subcollection': True,
        'parent_collection': 'hrm_employees',
        'parent_id_field': 'employee',
        'subcollection_name': 'documents',
        'description': 'Documents → hrm_employees/{id}/documents',
    },
]


# ══════════════════════════════════════════════════════════════════════
#  COMMAND
# ══════════════════════════════════════════════════════════════════════

class Command(BaseCommand):
    help = 'Migrate Firestore collections from v1 (flat) to v2 (modular) schema'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview only, no writes')
        parser.add_argument('--collection', type=str, help='Migrate only this target collection')
        parser.add_argument('--force', action='store_true', help='Re-migrate even if already done')
        parser.add_argument('--cleanup', action='store_true', help='Delete old v1 collections after migration')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        cleanup = options['cleanup']
        filter_collection = options['collection']

        if not FIRESTORE_AVAILABLE:
            raise CommandError(f'Firestore is not available: {_import_error}')

        self.stdout.write(self.style.MIGRATE_HEADING('Firestore Schema v2 Migration'))
        self.stdout.write(f'  Dry run: {dry_run}')
        self.stdout.write(f'  Force:   {force}')
        self.stdout.write(f'  Cleanup: {cleanup}')
        if filter_collection:
            self.stdout.write(f'  Filter:  {filter_collection}')
        self.stdout.write('')

        # Build employee name→id mapping for subcollection migrations
        employee_name_map = {}
        total_migrated = 0
        total_skipped = 0
        total_errors = 0

        for migration in MIGRATIONS:
            target_name = migration['name']
            source_name = migration['source']

            if filter_collection and target_name != filter_collection and source_name != filter_collection:
                continue

            # Skip subcollections initially — build map first
            if migration.get('is_subcollection'):
                continue

            # Check if already migrated
            if not force and is_migrated(target_name):
                self.stdout.write(f"  ◷  {target_name}: already migrated (use --force to re-run)")
                total_skipped += 1
                continue

            self.stdout.write(f"  →  {source_name}  ──→  {target_name}")
            self.stdout.write(f"     {migration['description']}")

            source_docs = stream_collection(source_name)
            if not source_docs:
                self.stdout.write(f"     ∅  No documents found in '{source_name}', skipping")
                if not dry_run:
                    mark_migrated(target_name, {'migrated': 0, 'skipped': 0, 'errors': 0})
                continue

            self.stdout.write(f"     📄  Found {len(source_docs)} document(s)")

            stats = {'migrated': 0, 'skipped': 0, 'errors': 0}
            batch = db.batch()
            ops = 0

            for doc in source_docs:
                raw = doc.to_dict() or {}
                doc_id = doc.id

                try:
                    transformed = migration['transform'](raw, doc_id)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"     ✗  Error transforming {doc_id}: {e}"))
                    stats['errors'] += 1
                    continue

                if dry_run:
                    stats['migrated'] += 1
                    continue

                # Write to new collection
                new_doc_id = doc_id  # Preserve original ID
                ref = db.collection(target_name).document(new_doc_id)
                batch.set(ref, transformed)
                ops += 1

                if ops >= BATCH_LIMIT:
                    batch.commit()
                    batch = db.batch()
                    ops = 0
                    stats['migrated'] += len(source_docs) if stats['migrated'] == 0 else 0  # approximate
                
                # Build employee mapping for later subcollection migration
                if target_name == 'hrm_employees':
                    emp_name = raw.get('name', '').strip()
                    if emp_name:
                        employee_name_map[emp_name.lower()] = doc_id

            # Commit remaining batch
            if ops > 0 and not dry_run:
                batch.commit()

            stats['migrated'] = len(source_docs) if not dry_run else len(source_docs)
            total_migrated += stats['migrated']
            total_errors += stats['errors']

            if not dry_run:
                mark_migrated(target_name, stats)

            status = '✓' if stats['errors'] == 0 else '⚠'
            self.stdout.write(self.style.SUCCESS(
                f"     {status}  Migrated {stats['migrated']}, "
                f"errors {stats['errors']}"
            ))
            self.stdout.write('')

        # ── Now handle subcollection migrations ─────────────────
        if not dry_run and (not filter_collection or any(filter_collection in m['name'] for m in MIGRATIONS if m.get('is_subcollection'))):
            self.stdout.write(self.style.MIGRATE_HEADING('Subcollection Migrations'))
            self.stdout.write(f'  Employee name→id map: {len(employee_name_map)} entries')
            self.stdout.write('')

            for migration in MIGRATIONS:
                if not migration.get('is_subcollection'):
                    continue

                target_name = migration['name']
                source_name = migration['source']
                parent_col = migration['parent_collection']
                parent_field = migration['parent_id_field']
                sub_name = migration['subcollection_name']

                if filter_collection and target_name != filter_collection:
                    continue

                if not force and is_migrated(target_name):
                    self.stdout.write(f"  ◷  {target_name}: already migrated")
                    continue

                self.stdout.write(f"  →  {source_name}  ──→  {parent_col}/{{id}}/{sub_name}")

                source_docs = stream_collection(source_name)
                if not source_docs:
                    self.stdout.write(f"     ∅  No documents found, skipping")
                    mark_migrated(target_name, {'migrated': 0, 'skipped': 0, 'errors': 0})
                    continue

                self.stdout.write(f"     📄  Found {len(source_docs)} document(s)")

                stats = {'migrated': 0, 'skipped': 0, 'errors': 0}
                batch = db.batch()
                ops = 0

                for doc in source_docs:
                    raw = doc.to_dict() or {}
                    doc_id = doc.id

                    # Find parent employee ID
                    parent_key = (raw.get(parent_field) or '').strip().lower()
                    parent_id = employee_name_map.get(parent_key)

                    if not parent_id:
                        # Try matching by exact name in the ID
                        self.stdout.write(f"     ⚠  No employee found for '{raw.get(parent_field)}', skipping")
                        stats['skipped'] += 1
                        continue

                    try:
                        transformed = migration['transform'](raw, doc_id)
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"     ✗  Error transforming {doc_id}: {e}"))
                        stats['errors'] += 1
                        continue

                    # Write to subcollection: parent_col/{parent_id}/subcollection_name/{doc_id}
                    sub_ref = db.collection(parent_col).document(parent_id).collection(sub_name).document(doc_id)
                    batch.set(sub_ref, transformed)
                    ops += 1

                    if ops >= BATCH_LIMIT:
                        batch.commit()
                        batch = db.batch()
                        ops = 0

                if ops > 0:
                    batch.commit()

                stats['migrated'] = len(source_docs) - stats['skipped'] - stats['errors']
                total_migrated += stats['migrated']
                total_errors += stats['errors']

                mark_migrated(target_name, stats)
                self.stdout.write(self.style.SUCCESS(
                    f"     ✓  Migrated {stats['migrated']}, skipped {stats['skipped']}, errors {stats['errors']}"
                ))
                self.stdout.write('')

        # ── User Management Isolation Notice ─────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('User Management Isolation'))
        self.stdout.write(self.style.WARNING(
            '  The sys_users collection is a READ-ONLY replica of Django auth.User.\n'
            '  All user management writes flow through Django SQLite → post_save signal → Firestore.\n'
            '  No changes to the ERP User Management UI are needed.\n'
            '  See config/management/commands/migrate_firestore_v2.py for details.'
        ))
        self.stdout.write('')

        # ── Cleanup old collections if requested ──────────────────
        if cleanup and not dry_run:
            self.stdout.write(self.style.MIGRATE_HEADING('Cleanup: Deleting Old v1 Collections'))
            for migration in MIGRATIONS:
                if migration.get('is_subcollection'):
                    continue
                old_name = migration['source']
                if old_name in ('users',):  # Keep users collection for backward compat
                    continue
                deleted = delete_collection(old_name)
                if deleted > 0:
                    self.stdout.write(f"  ✓  Deleted '{old_name}' ({deleted} docs)")
            # Delete tracking collection
            delete_collection(TRACKING_COLLECTION)
            self.stdout.write('')

        # ── Summary ───────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('Migration Complete'))
        self.stdout.write(f'  Total migrated: {total_migrated}')
        self.stdout.write(f'  Total skipped:  {total_skipped}')
        self.stdout.write(f'  Total errors:   {total_errors}')
        self.stdout.write(f'  Collections:    {len(MIGRATIONS)}')

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\n  This was a DRY RUN. No data was written.\n'
                '  Run without --dry-run to execute the migration.'
            ))
