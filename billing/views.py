from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.decorators import module_access
from datetime import datetime, date
from django.db import models
from config.workflow_integration import ensure_workflow, try_transition, INVOICE_TRIGGER_MAP
from config.logger import hrm_logger
from .models import (
    ChartOfAccount, JournalEntry, JournalEntryLine, Invoice,
    InvoiceLine, VendorBill, VendorBillLine, Payment, TaxCode, AuditTrail,
)


def log_audit(action_type, performed_by_name, before=None, after=None):
    AuditTrail.objects.create(
        action_type=action_type,
        performed_by_name=performed_by_name,
        payload_before=before or {},
        payload_after=after or {},
    )


def create_automated_journal(entry_code, posting_date, ref_doc, narration, lines, user):
    je = JournalEntry.objects.create(
        entry_code=entry_code,
        posting_date=posting_date,
        reference_document=ref_doc,
        narration=narration,
        status='Posted',
        created_by_name='System',
        approved_by_name=user.username if user else 'System',
    )
    for line in lines:
        account = ChartOfAccount.objects.filter(pk=line['account_id']).first()
        JournalEntryLine.objects.create(
            journal_entry=je,
            account=account,
            debit_amount=line.get('debit_amount', 0),
            credit_amount=line.get('credit_amount', 0),
        )


def _resolve(doc_id, model_class):
    if not doc_id:
        return None
    try:
        return model_class.objects.get(pk=doc_id)
    except (model_class.DoesNotExist, ValueError):
        pass
    return model_class.objects.filter(pk=doc_id).first()


def _account_map():
    return {str(a.pk): f"{a.account_code} - {a.name}" for a in ChartOfAccount.objects.filter(is_active=True)}


@login_required
@module_access('billing')
def index(request):
    accounts = list(ChartOfAccount.objects.filter(is_active=True).values('pk', 'name', 'account_code', 'account_type'))
    journals = JournalEntry.objects.filter(is_active=True).prefetch_related('lines__account')
    invoices = Invoice.objects.filter(is_active=True)
    bills = VendorBill.objects.filter(is_active=True)

    cash_accounts = [str(a['pk']) for a in accounts if 'cash' in a['name'].lower() or 'bank' in a['name'].lower()]
    cash_balance = 0.0
    for j in journals:
        if j.status == 'Posted':
            for line in j.lines.all():
                acc_id = str(line.account_id)
                if acc_id in cash_accounts:
                    cash_balance += float(line.debit_amount) - float(line.credit_amount)

    today_str = str(date.today())
    receivables_overdue = sum(
        float(i.grand_total) for i in invoices
        if i.status != 'Paid' and str(i.due_date) < today_str
    )
    payables_due = sum(float(b.grand_total) for b in bills if b.status != 'Paid')

    revenue_ids = [str(a['pk']) for a in accounts if a['account_type'] == 'Revenue']
    expense_ids = [str(a['pk']) for a in accounts if a['account_type'] == 'Expense']
    total_revenue = 0.0
    total_expense = 0.0
    for j in journals:
        if j.status == 'Posted':
            for line in j.lines.all():
                acc_id = str(line.account_id)
                if acc_id in revenue_ids:
                    total_revenue += float(line.credit_amount) - float(line.debit_amount)
                elif acc_id in expense_ids:
                    total_expense += float(line.debit_amount) - float(line.credit_amount)

    net_profit = total_revenue - total_expense
    net_profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0
    unposted_journals = [j for j in journals if j.status == 'Draft']

    context = {
        'cash_balance': cash_balance,
        'receivables_overdue': receivables_overdue,
        'payables_due': payables_due,
        'net_profit': net_profit,
        'net_profit_margin': net_profit_margin,
        'unposted_journals': unposted_journals,
        'recent_invoices': invoices.order_by('-created_at')[:5],
        'recent_bills': bills.order_by('-created_at')[:5],
    }
    return render(request, 'billing/dashboard.html', context)


@login_required
@module_access('billing')
def chart_of_accounts(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'add_account':
            data = {
                'account_code': request.POST.get('account_code'),
                'name': request.POST.get('name'),
                'account_type': request.POST.get('account_type'),
                'currency': request.POST.get('currency', 'BDT'),
                'is_active': request.POST.get('is_active') == 'True',
            }
            if doc_id:
                old = _resolve(doc_id, ChartOfAccount)
                ChartOfAccount.objects.filter(pk=old.pk if old else doc_id).update(**data)
                log_audit('UPDATE_ACCOUNT', request.user.username, {'old': str(old) if old else ''}, data)
                messages.success(request, "Account updated successfully.")
            else:
                obj = ChartOfAccount.objects.create(**data)
                log_audit('CREATE_ACCOUNT', request.user.username, {}, data)
                messages.success(request, "Account created successfully.")
        elif action == 'delete_account' and doc_id:
            acc = _resolve(doc_id, ChartOfAccount)
            if acc:
                acc.is_active = False
                acc.save(update_fields=['is_active'])
                log_audit('DELETE_ACCOUNT', request.user.username, {'code': acc.account_code}, {})
                messages.success(request, "Account deleted successfully.")
        return redirect('billing:chart_of_accounts')

    accounts = list(ChartOfAccount.objects.filter(is_active=True).order_by('account_code').values(
        'pk', 'account_code', 'name', 'account_type', 'currency', 'is_active',
    ))
    for a in accounts:
        a['id'] = a.pop('pk') or ''
    import json
    return render(request, 'billing/chart_of_accounts.html', {
        'accounts': accounts,
        'accounts_json': json.dumps(accounts),
    })


@login_required
@module_access('billing')
def general_journal(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_journal':
            acc_ids = request.POST.getlist('line_account[]')
            debits = request.POST.getlist('line_debit[]')
            credits = request.POST.getlist('line_credit[]')

            lines_data = []
            total_debit = 0.0
            total_credit = 0.0
            for acc, deb, cred in zip(acc_ids, debits, credits):
                if acc:
                    d_val = float(deb or 0.0)
                    c_val = float(cred or 0.0)
                    lines_data.append({'account_id': acc, 'debit_amount': d_val, 'credit_amount': c_val})
                    total_debit += d_val
                    total_credit += c_val

            if abs(total_debit - total_credit) > 0.001:
                messages.error(request, f"Unbalanced Journal: Debits BDT {total_debit} != Credits BDT {total_credit}")
                return redirect('billing:general_journal')

            if doc_id:
                je = _resolve(doc_id, JournalEntry)
                if je:
                    je.posting_date = request.POST.get('posting_date')
                    je.reference_document = request.POST.get('reference_document', '')
                    je.narration = request.POST.get('narration', '')
                    je.save(update_fields=['posting_date', 'reference_document', 'narration'])
                    je.lines.all().delete()
                    for ld in lines_data:
                        acc = ChartOfAccount.objects.filter(pk=ld['account_id']).first()
                        JournalEntryLine.objects.create(journal_entry=je, account=acc, debit_amount=ld['debit_amount'], credit_amount=ld['credit_amount'])
                log_audit('UPDATE_JOURNAL', request.user.username, {}, {})
                messages.success(request, "Journal entry draft updated successfully.")
            else:
                count = JournalEntry.objects.count()
                entry_code = f"JE-{datetime.now().year}-{count + 1001}"
                je = JournalEntry.objects.create(
                    entry_code=entry_code,
                    posting_date=request.POST.get('posting_date'),
                    reference_document=request.POST.get('reference_document', ''),
                    narration=request.POST.get('narration', ''),
                    status='Draft',
                    created_by_name=request.user.username,
                )
                for ld in lines_data:
                    acc = ChartOfAccount.objects.filter(pk=ld['account_id']).first()
                    JournalEntryLine.objects.create(journal_entry=je, account=acc, debit_amount=ld['debit_amount'], credit_amount=ld['credit_amount'])
                log_audit('CREATE_JOURNAL', request.user.username, {}, {'entry_code': entry_code})
                messages.success(request, "Journal entry draft created successfully.")

        elif action == 'post_journal' and doc_id:
            je = _resolve(doc_id, JournalEntry)
            if je:
                total_debit = sum(float(l.debit_amount) for l in je.lines.all())
                total_credit = sum(float(l.credit_amount) for l in je.lines.all())
                if abs(total_debit - total_credit) > 0.001:
                    messages.error(request, "Cannot approve: Journal is unbalanced.")
                else:
                    je.status = 'Posted'
                    je.approved_by_name = request.user.username
                    je.save(update_fields=['status', 'approved_by_name'])
                    log_audit('POST_JOURNAL', request.user.username, {}, {'status': 'Posted'})
                    messages.success(request, "Journal entry approved and posted successfully.")

        elif action == 'void_journal' and doc_id:
            je = _resolve(doc_id, JournalEntry)
            if je:
                je.status = 'Voided'
                je.save(update_fields=['status'])
                log_audit('VOID_JOURNAL', request.user.username, {}, {'status': 'Voided'})
                messages.success(request, "Journal entry voided successfully.")

        elif action == 'delete_journal' and doc_id:
            je = _resolve(doc_id, JournalEntry)
            if je:
                if je.status == 'Posted':
                    messages.error(request, "Posted journals cannot be deleted!")
                else:
                    je.is_active = False
                    je.save(update_fields=['is_active'])
                    log_audit('DELETE_JOURNAL', request.user.username, {'entry_code': je.entry_code}, {})
                    messages.success(request, "Journal entry deleted successfully.")
        return redirect('billing:general_journal')

    accounts = list(ChartOfAccount.objects.filter(is_active=True).order_by('account_code').values(
        'pk', 'account_code', 'name',
    ))
    for a in accounts:
        a['id'] = str(a.pop('pk'))
    acc_map = {a['id']: f"{a['account_code']} - {a['name']}" for a in accounts}

    journals = JournalEntry.objects.filter(is_active=True).prefetch_related('lines__account').order_by('-created_at')
    journal_list = []
    for j in journals:
        lines = []
        for line in j.lines.all():
            lines.append({
                'account_id': str(line.account_id) if line.account else '',
                'account_name': acc_map.get(str(line.account_id), 'Unknown'),
                'debit_amount': float(line.debit_amount),
                'credit_amount': float(line.credit_amount),
            })
        journal_list.append({
            'id': j.pk or str(j.pk),
            'entry_code': j.entry_code,
            'posting_date': str(j.posting_date),
            'reference_document': j.reference_document or '',
            'narration': j.narration or '',
            'status': j.status,
            'created_by': j.created_by_name or '',
            'approved_by': j.approved_by_name or '',
            'lines': lines,
            'created_at': j.created_at.isoformat() if j.created_at else '',
        })

    import json
    return render(request, 'billing/general_journal.html', {
        'journals': journal_list,
        'accounts': accounts,
        'journals_json': json.dumps(journal_list),
        'accounts_json': json.dumps(accounts),
    })


@login_required
@module_access('billing')
def ar_invoices(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_invoice':
            subtotal = float(request.POST.get('subtotal', 0.0))
            tax_rate = float(request.POST.get('tax_rate', 0.0))
            tax_amount = subtotal * (tax_rate / 100)
            grand_total = subtotal + tax_amount

            if doc_id:
                inv = _resolve(doc_id, Invoice)
                if inv:
                    inv.client_name = request.POST.get('client_name')
                    inv.invoice_number = request.POST.get('invoice_number')
                    inv.issue_date = request.POST.get('issue_date')
                    inv.due_date = request.POST.get('due_date')
                    inv.subtotal = subtotal
                    inv.tax_amount = tax_amount
                    inv.grand_total = grand_total
                    inv.status = request.POST.get('status', 'Pending')
                    inv.save()
                    ensure_workflow('billing', 'invoice', str(inv.pk), request=request)
                log_audit('UPDATE_INVOICE', request.user.username, {}, {})
                messages.success(request, "Invoice updated successfully.")
            else:
                inv = Invoice.objects.create(
                    invoice_number=request.POST.get('invoice_number'),
                    client_name=request.POST.get('client_name'),
                    issue_date=request.POST.get('issue_date'),
                    due_date=request.POST.get('due_date'),
                    subtotal=subtotal,
                    tax_amount=tax_amount,
                    grand_total=grand_total,
                    status=request.POST.get('status', 'Pending'),
                )
                log_audit('CREATE_INVOICE', request.user.username, {}, {'invoice_number': inv.invoice_number})

                ar_account = ChartOfAccount.objects.filter(account_code='11200').first()
                sales_account = ChartOfAccount.objects.filter(account_code='41000').first()
                if ar_account and sales_account:
                    lines = [
                        {'account_id': str(ar_account.pk), 'debit_amount': grand_total, 'credit_amount': 0.0},
                        {'account_id': str(sales_account.pk), 'debit_amount': 0.0, 'credit_amount': grand_total},
                    ]
                    create_automated_journal(
                        entry_code=f"AUTO-INV-{inv.invoice_number}",
                        posting_date=str(inv.issue_date),
                        ref_doc=inv.invoice_number,
                        narration=f"Auto sales journal for Invoice {inv.invoice_number}",
                        lines=lines,
                        user=request.user,
                    )
                ensure_workflow('billing', 'invoice', str(inv.pk), request=request)
                messages.success(request, "Invoice created with automated journal entries.")

        elif action == 'record_payment' and doc_id:
            inv = _resolve(doc_id, Invoice)
            if inv:
                pay_amount = float(request.POST.get('amount', 0.0))
                grand_total = float(inv.grand_total)

                pmt = Payment.objects.create(
                    receipt_code=f"REC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    invoice=inv,
                    payment_date=request.POST.get('payment_date'),
                    amount=pay_amount,
                    payment_method=request.POST.get('payment_method', 'Cash'),
                    bank_reference=request.POST.get('bank_reference', ''),
                )
                new_status = 'Paid' if pay_amount >= grand_total else 'Partially Paid'
                inv.status = new_status
                inv.save(update_fields=['status'])
                log_audit('RECORD_AR_PAYMENT', request.user.username, {}, {'status': new_status})
                ensure_workflow('billing', 'invoice', str(inv.pk), request=request)
                trigger = INVOICE_TRIGGER_MAP.get(new_status)
                if trigger:
                    try_transition('billing', 'invoice', str(inv.pk), trigger, request=request)

                cash_account = ChartOfAccount.objects.filter(account_code='11100').first()
                ar_account = ChartOfAccount.objects.filter(account_code='11200').first()
                if cash_account and ar_account:
                    lines = [
                        {'account_id': str(cash_account.pk), 'debit_amount': pay_amount, 'credit_amount': 0.0},
                        {'account_id': str(ar_account.pk), 'debit_amount': 0.0, 'credit_amount': pay_amount},
                    ]
                    create_automated_journal(
                        entry_code=f"AUTO-REC-{inv.invoice_number}",
                        posting_date=request.POST.get('payment_date'),
                        ref_doc=inv.invoice_number,
                        narration=f"Auto payment clearing for Invoice {inv.invoice_number}",
                        lines=lines,
                        user=request.user,
                    )
                messages.success(request, "Payment logged and automated journal entries posted.")

        elif action == 'delete_invoice' and doc_id:
            inv = _resolve(doc_id, Invoice)
            if inv:
                inv.is_active = False
                inv.save(update_fields=['is_active'])
                log_audit('DELETE_INVOICE', request.user.username, {'invoice_number': inv.invoice_number}, {})
                messages.success(request, "Invoice deleted successfully.")
        return redirect('billing:ar_invoices')

    invoices = list(Invoice.objects.filter(is_active=True).order_by('-created_at').values(
        'pk', 'invoice_number', 'client_name', 'issue_date', 'due_date',
        'subtotal', 'tax_amount', 'grand_total', 'status',
    ))
    for i in invoices:
        i['id'] = i.pop('pk') or ''
        for f in ('issue_date', 'due_date'):
            i[f] = str(i[f]) if i[f] else ''

    import json
    taxes = list(TaxCode.objects.filter(is_active=True).values('pk', 'tax_code', 'name', 'rate_percentage'))
    for t in taxes:
        t['id'] = t.pop('pk') or ''

    return render(request, 'billing/ar_invoices.html', {
        'invoices': invoices,
        'invoices_json': json.dumps(invoices),
        'taxes': taxes,
    })


@login_required
@module_access('billing')
def ap_bills(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_bill':
            grand_total = float(request.POST.get('grand_total', 0.0))
            if doc_id:
                bill = _resolve(doc_id, VendorBill)
                if bill:
                    bill.bill_number = request.POST.get('bill_number')
                    bill.vendor_name = request.POST.get('vendor_name')
                    bill.issue_date = request.POST.get('issue_date')
                    bill.due_date = request.POST.get('due_date')
                    bill.grand_total = grand_total
                    bill.status = request.POST.get('status', 'Pending')
                    bill.save()
                log_audit('UPDATE_BILL', request.user.username, {}, {})
                messages.success(request, "Vendor bill updated successfully.")
            else:
                bill = VendorBill.objects.create(
                    bill_number=request.POST.get('bill_number'),
                    vendor_name=request.POST.get('vendor_name'),
                    issue_date=request.POST.get('issue_date'),
                    due_date=request.POST.get('due_date'),
                    grand_total=grand_total,
                    status=request.POST.get('status', 'Pending'),
                )
                log_audit('CREATE_BILL', request.user.username, {}, {'bill_number': bill.bill_number})

                ap_account = ChartOfAccount.objects.filter(account_code='21100').first()
                exp_account = ChartOfAccount.objects.filter(account_code='51000').first()
                if ap_account and exp_account:
                    lines = [
                        {'account_id': str(exp_account.pk), 'debit_amount': grand_total, 'credit_amount': 0.0},
                        {'account_id': str(ap_account.pk), 'debit_amount': 0.0, 'credit_amount': grand_total},
                    ]
                    create_automated_journal(
                        entry_code=f"AUTO-BILL-{bill.bill_number}",
                        posting_date=str(bill.issue_date),
                        ref_doc=bill.bill_number,
                        narration=f"Auto expense posting for Vendor Bill {bill.bill_number}",
                        lines=lines,
                        user=request.user,
                    )
                messages.success(request, "Vendor bill created with automated journal entries.")

        elif action == 'pay_bill' and doc_id:
            bill = _resolve(doc_id, VendorBill)
            if bill:
                pay_amount = float(bill.grand_total)
                bill.status = 'Paid'
                bill.save(update_fields=['status'])
                log_audit('PAY_VENDOR_BILL', request.user.username, {}, {'status': 'Paid'})

                ap_account = ChartOfAccount.objects.filter(account_code='21100').first()
                cash_account = ChartOfAccount.objects.filter(account_code='11100').first()
                if ap_account and cash_account:
                    lines = [
                        {'account_id': str(ap_account.pk), 'debit_amount': pay_amount, 'credit_amount': 0.0},
                        {'account_id': str(cash_account.pk), 'debit_amount': 0.0, 'credit_amount': pay_amount},
                    ]
                    create_automated_journal(
                        entry_code=f"AUTO-PAY-{bill.bill_number}",
                        posting_date=str(date.today()),
                        ref_doc=bill.bill_number,
                        narration=f"Auto settlement for Bill {bill.bill_number}",
                        lines=lines,
                        user=request.user,
                    )
                messages.success(request, "Vendor bill paid and clearing entries posted.")

        elif action == 'delete_bill' and doc_id:
            bill = _resolve(doc_id, VendorBill)
            if bill:
                bill.is_active = False
                bill.save(update_fields=['is_active'])
                log_audit('DELETE_BILL', request.user.username, {'bill_number': bill.bill_number}, {})
                messages.success(request, "Vendor bill deleted successfully.")
        return redirect('billing:ap_bills')

    bills = list(VendorBill.objects.filter(is_active=True).order_by('-created_at').values(
        'pk', 'bill_number', 'vendor_name', 'issue_date', 'due_date', 'grand_total', 'status',
    ))
    for b in bills:
        b['id'] = b.pop('pk') or ''
        for f in ('issue_date', 'due_date'):
            b[f] = str(b[f]) if b[f] else ''

    import json
    return render(request, 'billing/ap_bills.html', {
        'vendor_bills': bills,
        'bills_json': json.dumps(bills),
    })


@login_required
@module_access('billing')
def tax_center(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'add_tax_code':
            data = {
                'tax_code': request.POST.get('tax_code'),
                'name': request.POST.get('name'),
                'rate_percentage': float(request.POST.get('rate_percentage', 0.0)),
                'tax_authority': request.POST.get('tax_authority', 'National Revenue Authority'),
            }
            if doc_id:
                tc = _resolve(doc_id, TaxCode)
                if tc:
                    TaxCode.objects.filter(pk=tc.pk).update(**data)
                log_audit('UPDATE_TAX_CODE', request.user.username, {}, data)
                messages.success(request, "Tax code updated.")
            else:
                obj = TaxCode.objects.create(**data)
                log_audit('CREATE_TAX_CODE', request.user.username, {}, data)
                messages.success(request, "Tax code created.")
        elif action == 'delete_tax_code' and doc_id:
            tc = _resolve(doc_id, TaxCode)
            if tc:
                tc.is_active = False
                tc.save(update_fields=['is_active'])
                log_audit('DELETE_TAX_CODE', request.user.username, {'code': tc.tax_code}, {})
                messages.success(request, "Tax code deleted.")
        return redirect('billing:tax_center')

    taxes = list(TaxCode.objects.filter(is_active=True).order_by('tax_code').values(
        'pk', 'tax_code', 'name', 'rate_percentage', 'tax_authority',
    ))
    for t in taxes:
        t['id'] = t.pop('pk') or ''

    total_tax_liability = Invoice.objects.filter(is_active=True).aggregate(total=models.Sum('tax_amount'))['total'] or 0

    import json
    return render(request, 'billing/tax_center.html', {
        'tax_codes': taxes,
        'taxes_json': json.dumps(taxes),
        'total_tax_liability': float(total_tax_liability),
    })


@login_required
@module_access('billing')
def financial_statements(request):
    accounts = list(ChartOfAccount.objects.filter(is_active=True).values('pk', 'account_code', 'name', 'account_type'))
    journals = JournalEntry.objects.filter(is_active=True, status='Posted').prefetch_related('lines__account')

    balances = {str(a['pk']): {'debit': 0.0, 'credit': 0.0} for a in accounts}
    for j in journals:
        for line in j.lines.all():
            acc_id = str(line.account_id)
            if acc_id in balances:
                balances[acc_id]['debit'] += float(line.debit_amount)
                balances[acc_id]['credit'] += float(line.credit_amount)

    trial_balance = []
    bs = {'assets': [], 'liabilities': [], 'equity': [], 'total_assets': 0.0, 'total_liabilities': 0.0, 'total_equity': 0.0}
    inc = {'revenues': [], 'expenses': [], 'total_revenue': 0.0, 'total_expense': 0.0, 'net_profit': 0.0}

    for a in accounts:
        acc_id = str(a['pk'])
        deb = balances[acc_id]['debit']
        cred = balances[acc_id]['credit']
        bal = deb - cred
        trial_balance.append({'account_code': a['account_code'], 'name': a['name'], 'type': a['account_type'], 'debit': deb, 'credit': cred})

        if a['account_type'] == 'Asset':
            bs['assets'].append({'name': a['name'], 'code': a['account_code'], 'balance': bal})
            bs['total_assets'] += bal
        elif a['account_type'] == 'Liability':
            bs['liabilities'].append({'name': a['name'], 'code': a['account_code'], 'balance': -bal})
            bs['total_liabilities'] += -bal
        elif a['account_type'] == 'Equity':
            bs['equity'].append({'name': a['name'], 'code': a['account_code'], 'balance': -bal})
            bs['total_equity'] += -bal
        elif a['account_type'] == 'Revenue':
            inc['revenues'].append({'name': a['name'], 'code': a['account_code'], 'balance': -bal})
            inc['total_revenue'] += -bal
        elif a['account_type'] == 'Expense':
            inc['expenses'].append({'name': a['name'], 'code': a['account_code'], 'balance': bal})
            inc['total_expense'] += bal

    net_profit = inc['total_revenue'] - inc['total_expense']
    inc['net_profit'] = net_profit
    bs['equity'].append({'name': 'Retained Earnings / Net Profit', 'code': '--', 'balance': net_profit})
    bs['total_equity'] += net_profit

    return render(request, 'billing/financial_statements.html', {
        'trial_balance': trial_balance,
        'balance_sheet': bs,
        'income_statement': inc,
    })


@login_required
@module_access('billing')
def audit_trail(request):
    trail = list(AuditTrail.objects.filter(is_active=True).order_by('-created_at').values(
        'action_type', 'performed_by_name', 'payload_before', 'payload_after', 'created_at',
    ))
    import json
    return render(request, 'billing/audit_trail.html', {
        'trail': trail,
        'trail_json': json.dumps(trail),
    })
