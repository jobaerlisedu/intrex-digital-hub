import logging
from datetime import datetime
from config.firebase import db
from config.firestore_utils import fs_create
from .event_bus import event_bus

logger = logging.getLogger(__name__)


class IntegrationService:

    @staticmethod
    def grn_to_vendor_bill(grn_data, po_data, user):
        """When a GRN is created, auto-generate an AP Vendor Bill."""
        try:
            bill_count = len(list(db.collection('fin_vendor_bills').stream()))
            bill_number = f"BILL-{datetime.now().year}-{bill_count + 1001}"

            total_amount = sum(
                float(item.get('quantity_accepted', 0)) * float(item.get('unit_price', 0))
                for item in grn_data.get('items', [])
            )

            bill_data = {
                'bill_number': bill_number,
                'vendor_name': po_data.get('vendor_name', 'Unknown Vendor'),
                'vendor_id': po_data.get('vendor_id', ''),
                'issue_date': grn_data.get('received_date', datetime.now().strftime('%Y-%m-%d')),
                'due_date': '',
                'po_reference': po_data.get('po_code', ''),
                'grn_reference': grn_data.get('grn_code', ''),
                'grand_total': total_amount,
                'status': 'Pending',
                'notes': f'Auto-generated from GRN {grn_data.get("grn_code", "")} for PO {po_data.get("po_code", "")}',
                'created_by': user.username,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            fs_create('fin_vendor_bills', bill_data)
            logger.info(f"AP Bill {bill_number} auto-created from GRN {grn_data.get('grn_code')}")

            event_bus.publish('vendor_bill.created', {
                'bill_number': bill_number,
                'vendor_name': po_data.get('vendor_name'),
                'amount': total_amount,
                'grn_code': grn_data.get('grn_code'),
            }, source='integration_service.grn_to_vendor_bill')

            return bill_number
        except Exception as e:
            logger.error(f"Failed to create AP Bill from GRN: {e}")
            return None

    @staticmethod
    def training_payment_to_journal_entry(payment_data, user):
        """When a training payment/installment is recorded, auto-create a journal entry."""
        try:
            amount = float(payment_data.get('amount', 0))
            student_name = payment_data.get('student_name', 'Unknown')
            course_name = payment_data.get('course_name', 'Unknown')
            entry_code = f"JE-TRN-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            accounts = {}
            try:
                for doc in db.collection('fin_chart_of_accounts').stream():
                    a = doc.to_dict()
                    accounts[a.get('name', '').lower()] = {'id': doc.id, 'name': a.get('name', '')}
            except Exception:
                pass

            cash_acct = None
            ar_acct = None
            for key, val in accounts.items():
                if 'cash' in key:
                    cash_acct = val
                if 'accounts receivable' in key:
                    ar_acct = val

            lines = []
            if cash_acct:
                lines.append({
                    'account_id': cash_acct['id'],
                    'account_name': cash_acct['name'],
                    'debit_amount': amount,
                    'credit_amount': 0.0,
                })
            if ar_acct:
                lines.append({
                    'account_id': ar_acct['id'],
                    'account_name': ar_acct['name'],
                    'debit_amount': 0.0,
                    'credit_amount': amount,
                })

            if not lines:
                logger.warning("No COA accounts found for training payment journal entry")
                return None

            je_data = {
                'entry_code': entry_code,
                'posting_date': payment_data.get('payment_date', datetime.now().strftime('%Y-%m-%d')),
                'reference_document': f"TRN-{payment_data.get('student_id', '')}",
                'narration': f'Training fee payment - {student_name} ({course_name})',
                'status': 'Posted',
                'created_by': 'System',
                'approved_by': user.username,
                'lines': lines,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            fs_create('fin_journal_entries', je_data)
            logger.info(f"Journal entry {entry_code} auto-created for training payment")

            event_bus.publish('journal_entry.created', {
                'entry_code': entry_code,
                'reference': f"TRN-{payment_data.get('student_id', '')}",
                'amount': amount,
                'narration': je_data['narration'],
            }, source='integration_service.training_payment_to_journal_entry')

            return entry_code
        except Exception as e:
            logger.error(f"Failed to create journal entry from training payment: {e}")
            return None

    @staticmethod
    def investment_loan_to_journal_entry(loan_data, user):
        """When an investment loan is disbursed, auto-create a journal entry."""
        try:
            amount = float(loan_data.get('principal_amount', 0))
            investor_name = loan_data.get('investor_name', 'Unknown')
            entry_code = f"JE-INVST-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            accounts = {}
            try:
                for doc in db.collection('fin_chart_of_accounts').stream():
                    a = doc.to_dict()
                    accounts[a.get('name', '').lower()] = {'id': doc.id, 'name': a.get('name', '')}
            except Exception:
                pass

            loan_acct = None
            cash_acct = None
            for key, val in accounts.items():
                if 'loan' in key or 'investment' in key:
                    loan_acct = val
                if 'cash' in key:
                    cash_acct = val

            lines = []
            if cash_acct:
                lines.append({
                    'account_id': cash_acct['id'],
                    'account_name': cash_acct['name'],
                    'debit_amount': amount,
                    'credit_amount': 0.0,
                })
            if loan_acct:
                lines.append({
                    'account_id': loan_acct['id'],
                    'account_name': loan_acct['name'],
                    'debit_amount': 0.0,
                    'credit_amount': amount,
                })

            if not lines:
                logger.warning("No COA accounts found for investment loan journal entry")
                return None

            je_data = {
                'entry_code': entry_code,
                'posting_date': loan_data.get('disbursement_date', datetime.now().strftime('%Y-%m-%d')),
                'reference_document': f"LOAN-{loan_data.get('loan_id', '')}",
                'narration': f'Loan disbursement - {investor_name}',
                'status': 'Posted',
                'created_by': 'System',
                'approved_by': user.username,
                'lines': lines,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            fs_create('fin_journal_entries', je_data)
            logger.info(f"Journal entry {entry_code} auto-created for loan disbursement")

            event_bus.publish('journal_entry.created', {
                'entry_code': entry_code,
                'reference': f"LOAN-{loan_data.get('loan_id', '')}",
                'amount': amount,
                'narration': je_data['narration'],
            }, source='integration_service.investment_loan_to_journal_entry')

            return entry_code
        except Exception as e:
            logger.error(f"Failed to create journal entry from loan disbursement: {e}")
            return None

    @staticmethod
    def project_requisition_to_po(requisition_data, user):
        """When a project requisition is approved, auto-create a Purchase Order."""
        try:
            po_count = len(list(db.collection('inv_purchase_orders').stream()))
            po_code = f"PO-{datetime.now().year}-{po_count + 1001}"

            items = [{
                'product_name': requisition_data.get('item_name', 'Unknown'),
                'quantity_ordered': float(requisition_data.get('quantity', 1)),
                'quantity_received': 0,
                'unit_price': float(requisition_data.get('estimated_cost', 0) / max(float(requisition_data.get('quantity', 1)), 1)),
                'line_total': float(requisition_data.get('estimated_cost', 0)),
            }]

            po_data = {
                'po_code': po_code,
                'vendor_id': '',
                'vendor_name': 'To be assigned',
                'requisition_id': requisition_data.get('id', ''),
                'requisition_code': requisition_data.get('requisition_ref', ''),
                'project_id': requisition_data.get('project_id', ''),
                'project_name': requisition_data.get('project_name', ''),
                'quotation_id': '',
                'payment_terms': '',
                'shipping_address': '',
                'status': 'Draft',
                'grand_total': float(requisition_data.get('estimated_cost', 0)),
                'items': items,
                'created_by': user.username,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            fs_create('inv_purchase_orders', po_data)
            logger.info(f"Purchase Order {po_code} auto-created from project requisition")

            event_bus.publish('purchase_order.created', {
                'po_code': po_code,
                'project_id': requisition_data.get('project_id', ''),
                'amount': float(requisition_data.get('estimated_cost', 0)),
            }, source='integration_service.project_requisition_to_po')

            return po_code
        except Exception as e:
            logger.error(f"Failed to create PO from project requisition: {e}")
            return None

    @staticmethod
    def employee_to_user_registry(employee_data):
        """Ensure employee has a Person record in the registry, optionally create auth User."""
        from registry.services import get_or_create_person

        email = employee_data.get('email', '')
        name = employee_data.get('name', '') or f"{employee_data.get('first_name', '')} {employee_data.get('last_name', '')}"
        name = name.strip() or employee_data.get('emp_id', 'Unknown')
        phone = employee_data.get('phone', '')

        person, created = get_or_create_person(
            email=email,
            display_name=name,
            person_type='employee',
            phone=phone,
            roles=['employee'],
        )
        employee_id = employee_data.get('id', '')
        if employee_id:
            person.firestore_employee_id = employee_id
            person.save()

        if not person.auth_user and email:
            try:
                from django.contrib.auth.models import User
                username = email.split('@')[0]
                base_username = username
                suffix = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{suffix}"
                    suffix += 1

                import secrets, hashlib
                temp_password = secrets.token_urlsafe(12)

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=temp_password,
                    first_name=employee_data.get('first_name', ''),
                    last_name=employee_data.get('last_name', ''),
                )
                person.auth_user = user
                person.save()
                logger.info(f"Auth user {username} created for employee {name}")

                # Sync to Firestore so employee can log in via FirestoreBackend
                try:
                    from accounts.auth_backend import _sync_user_to_firestore
                    _sync_user_to_firestore(user)
                except Exception:
                    logger.warning(f"Could not sync user {username} to Firestore")
            except Exception as e:
                logger.error(f"Failed to create auth user for employee {name}: {e}")

        # Ensure employee users do NOT have admin hrm_access group
        if person.auth_user:
            from django.contrib.auth.models import Group
            hrm_group = Group.objects.filter(name='hrm_access').first()
            if hrm_group and hrm_group in person.auth_user.groups.all():
                person.auth_user.groups.remove(hrm_group)
                logger.info(f"Removed hrm_access from employee user {person.auth_user.username}")
                # Sync updated groups to Firestore so it persists across logins
                try:
                    from accounts.auth_backend import _sync_user_to_firestore
                    _sync_user_to_firestore(person.auth_user)
                except Exception:
                    logger.warning(f"Could not sync removed hrm_access for {person.auth_user.username}")

        return person

    @staticmethod
    def student_to_person_registry(student_data):
        """Ensure student has a Person record in the registry."""
        from registry.services import get_or_create_person

        email = student_data.get('email', '')
        name = student_data.get('fullName', '') or student_data.get('studentName', 'Unknown')
        phone = student_data.get('phone', '')

        person, created = get_or_create_person(
            email=email,
            display_name=name,
            person_type='student',
            phone=phone,
            roles=['student'],
        )
        student_id = student_data.get('studentId', '') or student_data.get('id', '')
        if student_id:
            person.firestore_student_id = student_id
            person.save()
        return person

    @staticmethod
    def investor_to_person_registry(investor_data):
        """Ensure investor has a Person record in the registry."""
        from registry.services import get_or_create_person

        email = investor_data.get('email', '')
        name = investor_data.get('name', 'Unknown')
        phone = investor_data.get('phone', '')

        person, created = get_or_create_person(
            email=email,
            display_name=name,
            person_type='investor',
            phone=phone,
            roles=['investor'],
        )
        investor_id = investor_data.get('id', '')
        if investor_id:
            person.firestore_investor_id = investor_id
            person.save()
        return person
