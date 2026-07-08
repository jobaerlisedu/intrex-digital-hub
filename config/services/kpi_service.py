import logging
from datetime import datetime, timedelta
from config.firestore_utils import fs_query, fs_stream

logger = logging.getLogger(__name__)


class KPIService:

    @staticmethod
    def get_cross_module_kpis():
        """Aggregate KPIs across all modules."""
        kpis = {
            'total_revenue': 0.0,
            'total_expenses': 0.0,
            'net_profit': 0.0,
            'total_employees': 0,
            'total_students': 0,
            'total_products': 0,
            'active_projects': 0,
            'pending_invoices': 0,
            'pending_bills': 0,
            'pending_approvals': 0,
            'low_stock_items': 0,
            'expiring_licenses': 0,
            'open_positions': 0,
            'total_invested': 0.0,
        }

        try:
            # Employee count
            employees = fs_stream('hrm_employees')
            kpis['total_employees'] = len(employees)
            kpis['pending_approvals'] += len([
                e for e in employees
                if e.get('status') not in ('Active', 'Resigned', 'Inactive')
            ])

            # Positions
            kpis['open_positions'] = len(fs_stream('org_positions'))

            # Products / Inventory
            products = fs_stream('inv_products')
            kpis['total_products'] = len(products)
            kpis['low_stock_items'] = sum(1 for p in products if int(p.get('quantity', 0)) <= 10)

            # Invoices (Revenue)
            invoices = fs_stream('fin_invoices')
            for inv in invoices:
                total = float(inv.get('grand_total', 0.0))
                kpis['total_revenue'] += total
                if inv.get('status') != 'Paid':
                    kpis['pending_invoices'] += 1

            # Bills (Expenses)
            bills = fs_stream('fin_vendor_bills')
            for bill in bills:
                total = float(bill.get('grand_total', 0.0))
                kpis['total_expenses'] += total
                if bill.get('status') != 'Paid':
                    kpis['pending_bills'] += 1

            # Journal entries for additional revenue/expense
            journals = fs_stream('fin_journal_entries')
            for j in journals:
                if j.get('status') == 'Posted':
                    for line in j.get('lines', []):
                        kpis['total_revenue'] += float(line.get('credit_amount', 0.0))

            kpis['net_profit'] = kpis['total_revenue'] - kpis['total_expenses']

            # Training students
            registrations = fs_stream('trn_registrations')
            kpis['total_students'] = len({r.get('studentId') for r in registrations if r.get('studentId')})

            # Active projects
            projects = fs_stream('sol_projects')
            kpis['active_projects'] = sum(1 for p in projects if p.get('status') not in ('Completed', 'Cancelled'))

            # Expiring licenses
            today = datetime.now().date()
            end_window = today + timedelta(days=30)
            licenses = fs_stream('sol_software_licenses')
            for l in licenses:
                r_date_str = l.get('renewal_date', '')
                if r_date_str:
                    try:
                        r_date = datetime.strptime(r_date_str, '%Y-%m-%d').date()
                        if today <= r_date <= end_window:
                            kpis['expiring_licenses'] += 1
                    except ValueError:
                        pass

            # Pending leaves/advances/claims (approvals)
            try:
                pending_leaves = len(list(
                    fs_query('hrm_leaves').where('status', '==', 'Pending').stream()
                ))
                pending_advances = len(list(
                    fs_query('hrm_advances').where('status', '==', 'Pending').stream()
                ))
                pending_claims = len(list(
                    fs_query('hrm_expense_claims').where('status', '==', 'Pending').stream()
                ))
                kpis['pending_approvals'] += pending_leaves + pending_advances + pending_claims
            except Exception:
                pass

            # Investment
            try:
                loans = fs_stream('invst_loans')
                kpis['total_invested'] = sum(
                    float(l.get('principal_amount', 0.0)) for l in loans
                    if l.get('status') == 'Active'
                )
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error aggregating cross-module KPIs: {e}")

        return kpis

    @staticmethod
    def get_module_summaries():
        """Get list of summary items from each module for dashboard."""
        summaries = []

        try:
            for doc in fs_query('hrm_leaves').where('status', '==', 'Pending').limit(5).stream():
                d = doc.to_dict()
                summaries.append({
                    'module': 'HRM',
                    'type': 'Leave Request',
                    'label': f"{d.get('name', 'Unknown')} - {d.get('type', 'Leave')}",
                    'status': 'Pending',
                    'date': d.get('createdAt', ''),
                })
        except Exception:
            pass

        try:
            for doc in fs_query('hrm_expense_claims').where('status', '==', 'Pending').limit(5).stream():
                d = doc.to_dict()
                summaries.append({
                    'module': 'HRM',
                    'type': 'Expense Claim',
                    'label': f"{d.get('name', 'Unknown')} - {d.get('amount', '')}",
                    'status': 'Pending',
                    'date': d.get('createdAt', ''),
                })
        except Exception:
            pass

        try:
            for doc in fs_query('inv_requisitions').where('status', '==', 'Pending Approval').limit(5).stream():
                d = doc.to_dict()
                summaries.append({
                    'module': 'Inventory',
                    'type': 'Requisition',
                    'label': d.get('client_name', 'Unknown'),
                    'status': 'Pending Approval',
                    'date': d.get('created_at', ''),
                })
        except Exception:
            pass

        try:
            today_str = datetime.now().strftime('%Y-%m-%d')
            invoices = fs_stream('fin_invoices')
            for inv in invoices:
                if inv.get('status') != 'Paid' and inv.get('due_date', '') < today_str:
                    summaries.append({
                        'module': 'Billing',
                        'type': 'Overdue Invoice',
                        'label': f"{inv.get('client_name', 'Unknown')} - {inv.get('invoice_number', '')}",
                        'status': 'Overdue',
                        'date': inv.get('due_date', ''),
                    })
        except Exception:
            pass

        summaries.sort(key=lambda x: x.get('date', ''), reverse=True)
        return summaries[:20]

    @staticmethod
    def get_quick_actions(user):
        """Get available quick actions based on user role/permissions."""
        actions = []
        user_groups = set(user.groups.values_list('name', flat=True)) if user.is_authenticated else set()

        if 'hrm_access' in user_groups or user.is_superuser:
            actions.append({
                'label': 'Add Employee',
                'url': '/hrm/employees/',
                'icon': 'person-plus',
                'module': 'HRM',
            })
        if 'inventory_access' in user_groups or user.is_superuser:
            actions.append({
                'label': 'New Requisition',
                'url': '/inventory/requisitions/',
                'icon': 'cart-plus',
                'module': 'Inventory',
            })
        if 'billing_access' in user_groups or user.is_superuser:
            actions.append({
                'label': 'Create Invoice',
                'url': '/billing/invoices/',
                'icon': 'file-earmark-text',
                'module': 'Billing',
            })
        if 'training_access' in user_groups or user.is_superuser:
            actions.append({
                'label': 'New Course',
                'url': '/training/courses/',
                'icon': 'book',
                'module': 'Training',
            })
        if 'solutions_access' in user_groups or user.is_superuser:
            actions.append({
                'label': 'New Project',
                'url': '/solutions/projects/',
                'icon': 'diagram-3',
                'module': 'Solutions',
            })
        if 'investment_access' in user_groups or user.is_superuser:
            actions.append({
                'label': 'New Investor',
                'url': '/investment/investors/',
                'icon': 'bank',
                'module': 'Investment',
            })
        return actions
