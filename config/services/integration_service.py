import logging
from datetime import datetime, date
from .event_bus import event_bus
from billing.models import ChartOfAccount, JournalEntry, JournalEntryLine, VendorBill
from inventory.models import PurchaseOrder

logger = logging.getLogger(__name__)


class IntegrationService:

    @staticmethod
    def grn_to_vendor_bill(grn_data, po_data, user):
        try:
            total_amount = sum(
                float(item.get('quantity_accepted', 0)) * float(item.get('unit_price', 0))
                for item in grn_data.get('items', [])
            )

            po_code = ''
            grn_code = ''
            vendor_name = 'Unknown Vendor'
            if hasattr(po_data, 'po_code'):
                po_code = po_data.po_code
                vendor_name = po_data.vendor.name if po_data.vendor else 'Unknown Vendor'
                grn_code = grn_data.get('grn_code', '')
                vendor_id = str(po_data.vendor_id) if po_data.vendor_id else ''
            else:
                po_code = po_data.get('po_code', '')
                vendor_name = po_data.get('vendor_name', 'Unknown Vendor')
                vendor_id = po_data.get('vendor_id', '')
                grn_code = grn_data.get('grn_code', '')

            bill_count = VendorBill.objects.count()
            bill_number = f"BILL-{datetime.now().year}-{bill_count + 1001}"

            bill = VendorBill.objects.create(
                bill_number=bill_number,
                vendor_name=vendor_name,
                issue_date=grn_data.get('received_date', str(date.today())),
                grand_total=total_amount,
                status='Pending',
                notes=f'Auto-generated from GRN {grn_code} for PO {po_code}',
            )

            logger.info(f"AP Bill {bill_number} auto-created from GRN")

            event_bus.publish('vendor_bill.created', {
                'bill_number': bill_number,
                'vendor_name': vendor_name,
                'amount': total_amount,
                'grn_code': grn_code,
            }, source='integration_service.grn_to_vendor_bill')

            return bill_number
        except Exception as e:
            logger.error(f"Failed to create AP Bill from GRN: {e}")
            return None

    @staticmethod
    def training_payment_to_journal_entry(payment_data, user):
        try:
            amount = float(payment_data.get('amount', 0))
            student_name = payment_data.get('student_name', 'Unknown')
            course_name = payment_data.get('course_name', 'Unknown')
            entry_code = f"JE-TRN-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            cash_acct = ChartOfAccount.objects.filter(account_code='11100').first()
            ar_acct = ChartOfAccount.objects.filter(account_code='11200').first()

            lines = []
            if cash_acct:
                lines.append({'account_id': str(cash_acct.pk), 'debit_amount': amount, 'credit_amount': 0.0})
            if ar_acct:
                lines.append({'account_id': str(ar_acct.pk), 'debit_amount': 0.0, 'credit_amount': amount})

            if not lines:
                logger.warning("No COA accounts found for training payment journal entry")
                return None

            je = JournalEntry.objects.create(
                entry_code=entry_code,
                posting_date=payment_data.get('payment_date', str(date.today())),
                reference_document=f"TRN-{payment_data.get('student_id', '')}",
                narration=f'Training fee payment - {student_name} ({course_name})',
                status='Posted',
                created_by_name='System',
                approved_by_name=user.username if user else 'System',
            )
            for line_data in lines:
                account = ChartOfAccount.objects.filter(pk=line_data['account_id']).first()
                JournalEntryLine.objects.create(
                    journal_entry=je, account=account,
                    debit_amount=line_data['debit_amount'], credit_amount=line_data['credit_amount'],
                )
            logger.info(f"Journal entry {entry_code} auto-created for training payment")

            event_bus.publish('journal_entry.created', {
                'entry_code': entry_code,
                'reference': f"TRN-{payment_data.get('student_id', '')}",
                'amount': amount,
                'narration': je.narration,
            }, source='integration_service.training_payment_to_journal_entry')

            return entry_code
        except Exception as e:
            logger.error(f"Failed to create journal entry from training payment: {e}")
            return None

    @staticmethod
    def investment_loan_to_journal_entry(loan_data, user):
        try:
            amount = float(loan_data.get('principal_amount', 0))
            investor_name = loan_data.get('investor_name', 'Unknown')
            entry_code = f"JE-INVST-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            loan_acct = ChartOfAccount.objects.filter(account_code__startswith='2').first()
            cash_acct = ChartOfAccount.objects.filter(account_code='11100').first()

            lines = []
            if cash_acct:
                lines.append({'account_id': str(cash_acct.pk), 'debit_amount': amount, 'credit_amount': 0.0})
            if loan_acct:
                lines.append({'account_id': str(loan_acct.pk), 'debit_amount': 0.0, 'credit_amount': amount})

            if not lines:
                logger.warning("No COA accounts found for investment loan journal entry")
                return None

            je = JournalEntry.objects.create(
                entry_code=entry_code,
                posting_date=loan_data.get('disbursement_date', str(date.today())),
                reference_document=f"LOAN-{loan_data.get('loan_id', '')}",
                narration=f'Loan disbursement - {investor_name}',
                status='Posted',
                created_by_name='System',
                approved_by_name=user.username if user else 'System',
            )
            for line_data in lines:
                account = ChartOfAccount.objects.filter(pk=line_data['account_id']).first()
                JournalEntryLine.objects.create(
                    journal_entry=je, account=account,
                    debit_amount=line_data['debit_amount'], credit_amount=line_data['credit_amount'],
                )
            logger.info(f"Journal entry {entry_code} auto-created for loan disbursement")

            event_bus.publish('journal_entry.created', {
                'entry_code': entry_code,
                'reference': f"LOAN-{loan_data.get('loan_id', '')}",
                'amount': amount,
                'narration': je.narration,
            }, source='integration_service.investment_loan_to_journal_entry')

            return entry_code
        except Exception as e:
            logger.error(f"Failed to create journal entry from loan disbursement: {e}")
            return None

    @staticmethod
    def project_requisition_to_po(requisition_data, user):
        try:
            po_count = PurchaseOrder.objects.count()
            po_code = f"PO-{datetime.now().year}-{po_count + 1001}"

            qty = float(requisition_data.get('quantity', 1))
            est_cost = float(requisition_data.get('estimated_cost', 0))
            unit_price = est_cost / qty if qty > 0 else 0

            items = [{
                'product_name': requisition_data.get('item_name', 'Unknown'),
                'quantity_ordered': qty,
                'quantity_received': 0,
                'unit_price': unit_price,
                'line_total': est_cost,
            }]

            po = PurchaseOrder.objects.create(
                po_code=po_code,
                status='Draft',
                grand_total=est_cost,
                items=items,
            )

            logger.info(f"Purchase Order {po_code} auto-created from project requisition")

            event_bus.publish('purchase_order.created', {
                'po_code': po_code,
                'project_id': requisition_data.get('project_id', ''),
                'amount': est_cost,
            }, source='integration_service.project_requisition_to_po')

            return po_code
        except Exception as e:
            logger.error(f"Failed to create PO from project requisition: {e}")
            return None

    @staticmethod
    def employee_to_user_registry(employee_data):
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
        if not person:
            logger.warning(f"Cannot create Person for employee {name}: no email provided")
            return None

        if not person.auth_user and email:
            try:
                from django.contrib.auth.models import User
                import secrets

                raw_username = employee_data.get('username', '').strip()
                if not raw_username:
                    raw_username = email.split('@')[0]
                base_username = raw_username
                suffix = 1
                while User.objects.filter(username=raw_username).exists():
                    raw_username = f"{base_username}{suffix}"
                    suffix += 1

                raw_password = employee_data.get('password', '').strip()
                if not raw_password:
                    raw_password = secrets.token_urlsafe(12)

                user = User.objects.create_user(
                    username=raw_username,
                    email=email,
                    password=raw_password,
                    first_name=employee_data.get('first_name', ''),
                    last_name=employee_data.get('last_name', ''),
                )
                person.auth_user = user
                person.save()

                if employee_data.get('password', '').strip():
                    logger.info(f"Auth user {raw_username} created for employee {name} with provided password")
                else:
                    logger.info(f"Auth user {raw_username} created for employee {name}")
            except Exception as e:
                logger.error(f"Failed to create auth user for employee {name}: {e}")

        if person.auth_user:
            from django.contrib.auth.models import Group, User
            import secrets
            updated = False

            new_username = employee_data.get('username', '').strip()
            new_password = employee_data.get('password', '').strip()

            if new_username and new_username != person.auth_user.username:
                base = new_username
                suffix = 1
                while User.objects.filter(username=new_username).exclude(pk=person.auth_user.pk).exists():
                    new_username = f"{base}{suffix}"
                    suffix += 1
                person.auth_user.username = new_username
                updated = True
            if new_password:
                person.auth_user.set_password(new_password)
                updated = True

            hrm_group = Group.objects.filter(name='hrm_access').first()
            if hrm_group and hrm_group in person.auth_user.groups.all():
                person.auth_user.groups.remove(hrm_group)
                updated = True
                logger.info(f"Removed hrm_access from employee user {person.auth_user.username}")

            if updated:
                person.auth_user.save()

        return person

    @staticmethod
    def student_to_person_registry(student_data):
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
        return person

    @staticmethod
    def investor_to_person_registry(investor_data):
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
        return person
