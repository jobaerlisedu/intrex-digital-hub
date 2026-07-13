import logging
from datetime import datetime, timedelta
from django.db.models import Sum, Q, Count
from decimal import Decimal

logger = logging.getLogger(__name__)


class KPIService:

    @staticmethod
    def get_cross_module_kpis():
        """Aggregate KPIs across all modules via Django ORM."""
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
            from hrm.models import Employee, Position, Leave, AdvanceSalary, ExpenseClaim
            from inventory.models import Product, Requisition
            from billing.models import Invoice, VendorBill, JournalEntry, JournalEntryLine
            from training.models import Registration
            from solutions.models import Project, SoftwareLicense
            from investment.models import Loan

            kpis['total_employees'] = Employee.objects.filter(is_active=True).count()
            kpis['open_positions'] = Position.objects.filter(is_active=True).count()
            kpis['pending_approvals'] += Leave.objects.filter(status='Pending').count()
            kpis['pending_approvals'] += AdvanceSalary.objects.filter(status='Pending').count()
            kpis['pending_approvals'] += ExpenseClaim.objects.filter(status='Pending').count()

            products = Product.objects.filter(is_active=True)
            kpis['total_products'] = products.count()
            kpis['low_stock_items'] = products.filter(quantity__lte=10).count()

            invoices = Invoice.objects.filter(is_active=True)
            inv_total = invoices.aggregate(s=Sum('grand_total'))['s'] or Decimal('0.00')
            kpis['total_revenue'] = float(inv_total)
            kpis['pending_invoices'] = invoices.exclude(status='Paid').count()

            bills = VendorBill.objects.filter(is_active=True)
            bill_total = bills.aggregate(s=Sum('grand_total'))['s'] or Decimal('0.00')
            kpis['total_expenses'] = float(bill_total)
            kpis['pending_bills'] = bills.exclude(status='Paid').count()

            journals = JournalEntry.objects.filter(status='Posted', is_active=True)
            credit_total = JournalEntryLine.objects.filter(
                journal_entry__in=journals
            ).aggregate(s=Sum('credit_amount'))['s'] or Decimal('0.00')
            kpis['total_revenue'] += float(credit_total)

            kpis['net_profit'] = kpis['total_revenue'] - kpis['total_expenses']

            kpis['total_students'] = Registration.objects.values('student').distinct().count()

            kpis['active_projects'] = Project.objects.filter(
                is_active=True
            ).exclude(status__in=['Completed', 'Cancelled']).count()

            today = datetime.now().date()
            end_window = today + timedelta(days=30)
            kpis['expiring_licenses'] = SoftwareLicense.objects.filter(
                is_active=True,
                renewal_date__gte=today,
                renewal_date__lte=end_window,
            ).count()

            active_loans = Loan.objects.filter(status='Active')
            total_inv = active_loans.aggregate(s=Sum('principal_amount'))['s'] or Decimal('0.00')
            kpis['total_invested'] = float(total_inv)

        except Exception as e:
            logger.error(f"Error aggregating cross-module KPIs: {e}")

        return kpis

    @staticmethod
    def get_module_summaries():
        """Get list of summary items from each module for dashboard."""
        summaries = []

        try:
            from hrm.models import Leave, ExpenseClaim
            from inventory.models import Requisition
            from billing.models import Invoice

            for l in Leave.objects.filter(status='Pending', is_active=True)[:5]:
                summaries.append({
                    'module': 'HRM',
                    'type': 'Leave Request',
                    'label': f"{l.employee} - {l.leave_type or 'Leave'}",
                    'status': 'Pending',
                    'date': str(l.created_at.date()) if l.created_at else '',
                })
        except Exception:
            pass

        try:
            from hrm.models import ExpenseClaim
            for e in ExpenseClaim.objects.filter(status='Pending', is_active=True)[:5]:
                summaries.append({
                    'module': 'HRM',
                    'type': 'Expense Claim',
                    'label': f"{e.employee} - {e.amount}",
                    'status': 'Pending',
                    'date': str(e.created_at.date()) if e.created_at else '',
                })
        except Exception:
            pass

        try:
            from inventory.models import Requisition
            for r in Requisition.objects.filter(status='Pending Approval', is_active=True)[:5]:
                summaries.append({
                    'module': 'Inventory',
                    'type': 'Requisition',
                    'label': r.client_name or 'Unknown',
                    'status': 'Pending Approval',
                    'date': str(r.created_at.date()) if r.created_at else '',
                })
        except Exception:
            pass

        try:
            from billing.models import Invoice
            today_str = datetime.now().strftime('%Y-%m-%d')
            for inv in Invoice.objects.filter(is_active=True).exclude(status='Paid')[:5]:
                if inv.due_date and str(inv.due_date) < today_str:
                    summaries.append({
                        'module': 'Billing',
                        'type': 'Overdue Invoice',
                        'label': f"{inv.client_name} - {inv.invoice_number}",
                        'status': 'Overdue',
                        'date': str(inv.due_date),
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
