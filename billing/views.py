from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from config.firebase import db
from accounts.decorators import module_access
from datetime import datetime
import json

# Helper to serialize Firestore docs
def serialize_doc(doc):
    d = doc.to_dict()
    d['id'] = doc.id
    return d

def log_audit(action_type, performed_by, before=None, after=None):
    db.collection('financial_audit_trail').add({
        'action_type': action_type,
        'performed_by': performed_by,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'payload_before': before or {},
        'payload_after': after or {}
    })

# Automated double-entry helper
def create_automated_journal(entry_code, posting_date, ref_doc, narration, lines, user):
    je_data = {
        'entry_code': entry_code,
        'posting_date': posting_date,
        'reference_document': ref_doc,
        'narration': narration,
        'status': 'Posted', # Auto-generated entries from AR/AP subledgers are pre-verified & posted
        'created_by': 'System',
        'approved_by': user.username,
        'lines': lines,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    db.collection('journal_entries').add(je_data)

@login_required
@module_access('billing')
def index(request):
    # Dashboard view
    coa_docs = db.collection('chart_of_accounts').stream()
    accounts = [serialize_doc(a) for a in coa_docs]

    je_docs = db.collection('journal_entries').stream()
    journals = [serialize_doc(j) for j in je_docs]

    inv_docs = db.collection('invoices').stream()
    invoices = [serialize_doc(i) for i in inv_docs]

    bill_docs = db.collection('vendor_bills').stream()
    bills = [serialize_doc(b) for b in bill_docs]

    # Calculate Cash Balance from posted journal lines
    cash_accounts = [a['id'] for a in accounts if 'cash' in a['name'].lower() or 'bank' in a['name'].lower()]
    cash_balance = 0.0
    for j in journals:
        if j.get('status') == 'Posted':
            for line in j.get('lines', []):
                if line.get('account_id') in cash_accounts:
                    cash_balance += float(line.get('debit_amount', 0.0)) - float(line.get('credit_amount', 0.0))

    # Calculate Receivables Overdue
    today_str = datetime.now().strftime('%Y-%m-%d')
    receivables_overdue = sum(
        float(i.get('grand_total', 0.0)) for i in invoices 
        if i.get('status') != 'Paid' and i.get('due_date', '') < today_str
    )

    # Calculate Payables Due
    payables_due = sum(
        float(b.get('grand_total', 0.0)) for b in bills 
        if b.get('status') != 'Paid'
    )

    # Calculate Net Profit (Posted Revenues - Posted Expenses)
    revenue_accounts = [a['id'] for a in accounts if a.get('account_type') == 'Revenue']
    expense_accounts = [a['id'] for a in accounts if a.get('account_type') == 'Expense']
    
    total_revenue = 0.0
    total_expense = 0.0
    for j in journals:
        if j.get('status') == 'Posted':
            for line in j.get('lines', []):
                acc_id = line.get('account_id')
                if acc_id in revenue_accounts:
                    # Revenue increases with credit
                    total_revenue += float(line.get('credit_amount', 0.0)) - float(line.get('debit_amount', 0.0))
                elif acc_id in expense_accounts:
                    # Expense increases with debit
                    total_expense += float(line.get('debit_amount', 0.0)) - float(line.get('credit_amount', 0.0))

    net_profit = total_revenue - total_expense
    net_profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

    # Maker-Checker: unposted journals list
    unposted_journals = [j for j in journals if j.get('status') == 'Draft']

    context = {
        'cash_balance': cash_balance,
        'receivables_overdue': receivables_overdue,
        'payables_due': payables_due,
        'net_profit': net_profit,
        'net_profit_margin': net_profit_margin,
        'unposted_journals': unposted_journals,
        'recent_invoices': invoices[:5],
        'recent_bills': bills[:5],
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
                'is_active': request.POST.get('is_active') == 'True'
            }

            if doc_id:
                old_snap = db.collection('chart_of_accounts').document(doc_id).get().to_dict()
                db.collection('chart_of_accounts').document(doc_id).update(data)
                log_audit('UPDATE_ACCOUNT', request.user.username, old_snap, data)
            else:
                db.collection('chart_of_accounts').add(data)
                log_audit('CREATE_ACCOUNT', request.user.username, {}, data)

        elif action == 'delete_account' and doc_id:
            old_snap = db.collection('chart_of_accounts').document(doc_id).get().to_dict()
            db.collection('chart_of_accounts').document(doc_id).delete()
            log_audit('DELETE_ACCOUNT', request.user.username, old_snap, {})

        return redirect('billing:chart_of_accounts')

    coa_docs = db.collection('chart_of_accounts').stream()
    accounts = [serialize_doc(a) for a in coa_docs]
    # Sort by account code
    accounts.sort(key=lambda x: x.get('account_code', ''))
    accounts_json = json.dumps(accounts)

    return render(request, 'billing/chart_of_accounts.html', {
        'accounts': accounts,
        'accounts_json': accounts_json
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

            lines = []
            total_debit = 0.0
            total_credit = 0.0

            for acc, deb, cred in zip(acc_ids, debits, credits):
                if acc:
                    d_val = float(deb or 0.0)
                    c_val = float(cred or 0.0)
                    lines.append({
                        'account_id': acc,
                        'debit_amount': d_val,
                        'credit_amount': c_val
                    })
                    total_debit += d_val
                    total_credit += c_val

            # Enforce double-entry integrity
            if abs(total_debit - total_credit) > 0.001:
                messages.error(request, f"Unbalanced Journal: Sum of Debits (BDT {total_debit}) must equal Credits (BDT {total_credit})!")
                return redirect('billing:general_journal')

            data = {
                'posting_date': request.POST.get('posting_date'),
                'reference_document': request.POST.get('reference_document', ''),
                'narration': request.POST.get('narration', ''),
                'status': 'Draft', # Maker-Checker: Default is Draft
                'created_by': request.user.username,
                'lines': lines,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            if doc_id:
                old_snap = db.collection('journal_entries').document(doc_id).get().to_dict()
                db.collection('journal_entries').document(doc_id).update(data)
                log_audit('UPDATE_JOURNAL', request.user.username, old_snap, data)
            else:
                count = len(list(db.collection('journal_entries').stream()))
                data['entry_code'] = f"JE-{datetime.now().year}-{count + 1001}"
                data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                db.collection('journal_entries').add(data)
                log_audit('CREATE_JOURNAL', request.user.username, {}, data)

        elif action == 'post_journal' and doc_id:
            je_ref = db.collection('journal_entries').document(doc_id)
            je_data = je_ref.get().to_dict()
            
            # Recheck balance logic before approval
            total_debit = sum(float(l.get('debit_amount', 0.0)) for l in je_data.get('lines', []))
            total_credit = sum(float(l.get('credit_amount', 0.0)) for l in je_data.get('lines', []))
            if abs(total_debit - total_credit) > 0.001:
                messages.error(request, "Cannot approve: Journal is unbalanced.")
                return redirect('billing:general_journal')

            je_ref.update({
                'status': 'Posted',
                'approved_by': request.user.username
            })
            log_audit('POST_JOURNAL', request.user.username, je_data, {'status': 'Posted', 'approved_by': request.user.username})

        elif action == 'void_journal' and doc_id:
            je_ref = db.collection('journal_entries').document(doc_id)
            je_data = je_ref.get().to_dict()
            je_ref.update({'status': 'Voided'})
            log_audit('VOID_JOURNAL', request.user.username, je_data, {'status': 'Voided'})

        elif action == 'delete_journal' and doc_id:
            old_snap = db.collection('journal_entries').document(doc_id).get().to_dict()
            # Strict protection: Posted journals cannot be deleted
            if old_snap.get('status') == 'Posted':
                messages.error(request, "Compliance protection: Posted general journals cannot be deleted!")
            else:
                db.collection('journal_entries').document(doc_id).delete()
                log_audit('DELETE_JOURNAL', request.user.username, old_snap, {})

        return redirect('billing:general_journal')

    # GET context
    coa_docs = db.collection('chart_of_accounts').where('is_active', '==', True).stream()
    accounts = [serialize_doc(a) for a in coa_docs]
    accounts.sort(key=lambda x: x.get('account_code', ''))

    je_docs = db.collection('journal_entries').stream()
    journals = [serialize_doc(j) for j in je_docs]
    journals.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    # Attach account names for UI listing clarity
    acc_map = {a['id']: f"{a['account_code']} - {a['name']}" for a in accounts}
    for j in journals:
        for line in j.get('lines', []):
            line['account_name'] = acc_map.get(line.get('account_id'), 'Unknown Account')

    journals_json = json.dumps(journals)
    accounts_json = json.dumps(accounts)

    return render(request, 'billing/general_journal.html', {
        'journals': journals,
        'accounts': accounts,
        'journals_json': journals_json,
        'accounts_json': accounts_json
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

            data = {
                'client_name': request.POST.get('client_name'),
                'invoice_number': request.POST.get('invoice_number'),
                'issue_date': request.POST.get('issue_date'),
                'due_date': request.POST.get('due_date'),
                'subtotal': subtotal,
                'tax_amount': tax_amount,
                'grand_total': grand_total,
                'status': request.POST.get('status', 'Pending'),
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            if doc_id:
                old_snap = db.collection('invoices').document(doc_id).get().to_dict()
                db.collection('invoices').document(doc_id).update(data)
                log_audit('UPDATE_INVOICE', request.user.username, old_snap, data)
            else:
                db.collection('invoices').add(data)
                log_audit('CREATE_INVOICE', request.user.username, {}, data)

                # Automated Double-entry: Debit AR asset and Credit Sales revenue
                coa_ar = list(db.collection('chart_of_accounts').where('account_code', '==', '11200').stream())
                coa_sales = list(db.collection('chart_of_accounts').where('account_code', '==', '41000').stream())
                if coa_ar and coa_sales:
                    ar_acc_id = coa_ar[0].id
                    sales_acc_id = coa_sales[0].id
                    lines = [
                        {'account_id': ar_acc_id, 'debit_amount': grand_total, 'credit_amount': 0.0},
                        {'account_id': sales_acc_id, 'debit_amount': 0.0, 'credit_amount': grand_total}
                    ]
                    create_automated_journal(
                        entry_code=f"AUTO-INV-{data['invoice_number']}",
                        posting_date=data['issue_date'],
                        ref_doc=data['invoice_number'],
                        narration=f"Auto sales journal posting for Invoice {data['invoice_number']}",
                        lines=lines,
                        user=request.user
                    )

        elif action == 'record_payment' and doc_id:
            inv_ref = db.collection('invoices').document(doc_id)
            inv_data = inv_ref.get().to_dict()

            pay_amount = float(request.POST.get('amount', 0.0))
            grand_total = float(inv_data.get('grand_total', 0.0))

            # Record settlement
            db.collection('payments').add({
                'receipt_code': f"REC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'invoice_id': doc_id,
                'payment_date': request.POST.get('payment_date'),
                'amount': pay_amount,
                'payment_method': request.POST.get('payment_method'),
                'bank_reference': request.POST.get('bank_reference', ''),
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

            # Check status shifts
            new_status = 'Paid' if pay_amount >= grand_total else 'Partially Paid'
            inv_ref.update({'status': new_status})
            log_audit('RECORD_AR_PAYMENT', request.user.username, inv_data, {'status': new_status})

            # Automated Double-entry: Debit Cash/Bank Asset and Credit AR Asset
            coa_cash = list(db.collection('chart_of_accounts').where('account_code', '==', '11100').stream())
            coa_ar = list(db.collection('chart_of_accounts').where('account_code', '==', '11200').stream())
            if coa_cash and coa_ar:
                cash_id = coa_cash[0].id
                ar_id = coa_ar[0].id
                lines = [
                    {'account_id': cash_id, 'debit_amount': pay_amount, 'credit_amount': 0.0},
                    {'account_id': ar_id, 'debit_amount': 0.0, 'credit_amount': pay_amount}
                ]
                create_automated_journal(
                    entry_code=f"AUTO-REC-{inv_data['invoice_number']}",
                    posting_date=request.POST.get('payment_date'),
                    ref_doc=inv_data['invoice_number'],
                    narration=f"Auto payment clearing sales posting for Invoice {inv_data['invoice_number']}",
                    lines=lines,
                    user=request.user
                )

        elif action == 'delete_invoice' and doc_id:
            old_snap = db.collection('invoices').document(doc_id).get().to_dict()
            db.collection('invoices').document(doc_id).delete()
            log_audit('DELETE_INVOICE', request.user.username, old_snap, {})

        return redirect('billing:ar_invoices')

    # GET context
    inv_docs = db.collection('invoices').stream()
    invoices = [serialize_doc(i) for i in inv_docs]
    invoices.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    invoices_json = json.dumps(invoices)

    tax_docs = db.collection('tax_codes').stream()
    taxes = [serialize_doc(t) for t in tax_docs]

    return render(request, 'billing/ar_invoices.html', {
        'invoices': invoices,
        'invoices_json': invoices_json,
        'taxes': taxes
    })


@login_required
@module_access('billing')
def ap_bills(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_bill':
            grand_total = float(request.POST.get('grand_total', 0.0))
            data = {
                'bill_number': request.POST.get('bill_number'),
                'vendor_name': request.POST.get('vendor_name'),
                'issue_date': request.POST.get('issue_date'),
                'due_date': request.POST.get('due_date'),
                'grand_total': grand_total,
                'status': request.POST.get('status', 'Pending'),
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            if doc_id:
                old_snap = db.collection('vendor_bills').document(doc_id).get().to_dict()
                db.collection('vendor_bills').document(doc_id).update(data)
                log_audit('UPDATE_BILL', request.user.username, old_snap, data)
            else:
                db.collection('vendor_bills').add(data)
                log_audit('CREATE_BILL', request.user.username, {}, data)

                # Automated Double-entry: Debit Expense and Credit Accounts Payable Liability
                coa_ap = list(db.collection('chart_of_accounts').where('account_code', '==', '21100').stream())
                coa_exp = list(db.collection('chart_of_accounts').where('account_code', '==', '51000').stream())
                if coa_ap and coa_exp:
                    ap_id = coa_ap[0].id
                    exp_id = coa_exp[0].id
                    lines = [
                        {'account_id': exp_id, 'debit_amount': grand_total, 'credit_amount': 0.0},
                        {'account_id': ap_id, 'debit_amount': 0.0, 'credit_amount': grand_total}
                    ]
                    create_automated_journal(
                        entry_code=f"AUTO-BILL-{data['bill_number']}",
                        posting_date=data['issue_date'],
                        ref_doc=data['bill_number'],
                        narration=f"Auto expense posting for Vendor Bill {data['bill_number']}",
                        lines=lines,
                        user=request.user
                    )

        elif action == 'pay_bill' and doc_id:
            bill_ref = db.collection('vendor_bills').document(doc_id)
            bill_data = bill_ref.get().to_dict()
            
            pay_amount = float(bill_data.get('grand_total', 0.0))

            bill_ref.update({'status': 'Paid'})
            log_audit('PAY_VENDOR_BILL', request.user.username, bill_data, {'status': 'Paid'})

            # Automated Double-entry: Debit Accounts Payable Liability and Credit Cash Asset
            coa_ap = list(db.collection('chart_of_accounts').where('account_code', '==', '21100').stream())
            coa_cash = list(db.collection('chart_of_accounts').where('account_code', '==', '11100').stream())
            if coa_ap and coa_cash:
                ap_id = coa_ap[0].id
                cash_id = coa_cash[0].id
                lines = [
                    {'account_id': ap_id, 'debit_amount': pay_amount, 'credit_amount': 0.0},
                    {'account_id': cash_id, 'debit_amount': 0.0, 'credit_amount': pay_amount}
                ]
                create_automated_journal(
                    entry_code=f"AUTO-PAY-{bill_data['bill_number']}",
                    posting_date=datetime.now().strftime('%Y-%m-%d'),
                    ref_doc=bill_data['bill_number'],
                    narration=f"Auto settlement clearing entry for Bill {bill_data['bill_number']}",
                    lines=lines,
                    user=request.user
                )

        elif action == 'delete_bill' and doc_id:
            old_snap = db.collection('vendor_bills').document(doc_id).get().to_dict()
            db.collection('vendor_bills').document(doc_id).delete()
            log_audit('DELETE_BILL', request.user.username, old_snap, {})

        return redirect('billing:ap_bills')

    # GET context
    bill_docs = db.collection('vendor_bills').stream()
    bills = [serialize_doc(b) for b in bill_docs]
    bills.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    bills_json = json.dumps(bills)

    return render(request, 'billing/ap_bills.html', {
        'vendor_bills': bills,
        'bills_json': bills_json
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
                'tax_authority': request.POST.get('tax_authority', 'National Revenue Authority')
            }

            if doc_id:
                old_snap = db.collection('tax_codes').document(doc_id).get().to_dict()
                db.collection('tax_codes').document(doc_id).update(data)
                log_audit('UPDATE_TAX_CODE', request.user.username, old_snap, data)
            else:
                db.collection('tax_codes').add(data)
                log_audit('CREATE_TAX_CODE', request.user.username, {}, data)

        elif action == 'delete_tax_code' and doc_id:
            old_snap = db.collection('tax_codes').document(doc_id).get().to_dict()
            db.collection('tax_codes').document(doc_id).delete()
            log_audit('DELETE_TAX_CODE', request.user.username, old_snap, {})

        return redirect('billing:tax_center')

    tax_docs = db.collection('tax_codes').stream()
    taxes = [serialize_doc(t) for t in tax_docs]
    taxes_json = json.dumps(taxes)

    # Aggregates liability: Sum tax amounts from all invoices
    inv_docs = db.collection('invoices').stream()
    total_tax_liability = sum(float(i.get('tax_amount', 0.0)) for i in inv_docs)

    return render(request, 'billing/tax_center.html', {
        'tax_codes': taxes,
        'taxes_json': taxes_json,
        'total_tax_liability': total_tax_liability
    })


@login_required
@module_access('billing')
def financial_statements(request):
    # Generates Real-time Trial Balance, Balance Sheet and Income Statement (P&L)
    coa_docs = db.collection('chart_of_accounts').stream()
    accounts = [serialize_doc(a) for a in coa_docs]

    je_docs = db.collection('journal_entries').where('status', '==', 'Posted').stream()
    journals = [serialize_doc(j) for j in je_docs]

    # Map transaction balances per account ID
    balances = {a['id']: {'debit': 0.0, 'credit': 0.0} for a in accounts}
    for j in journals:
        for line in j.get('lines', []):
            acc_id = line.get('account_id')
            if acc_id in balances:
                balances[acc_id]['debit'] += float(line.get('debit_amount', 0.0))
                balances[acc_id]['credit'] += float(line.get('credit_amount', 0.0))

    # Compile structures
    trial_balance = []
    balance_sheet = {'assets': [], 'liabilities': [], 'equity': [], 'total_assets': 0.0, 'total_liabilities': 0.0, 'total_equity': 0.0}
    income_statement = {'revenues': [], 'expenses': [], 'total_revenue': 0.0, 'total_expense': 0.0, 'net_profit': 0.0}

    for a in accounts:
        acc_id = a['id']
        deb = balances[acc_id]['debit']
        cred = balances[acc_id]['credit']
        bal = deb - cred # Default asset sign

        # Trial Balance
        trial_balance.append({
            'account_code': a.get('account_code'),
            'name': a.get('name'),
            'type': a.get('account_type'),
            'debit': deb,
            'credit': cred
        })

        # Balance Sheet categorizations
        if a.get('account_type') == 'Asset':
            balance_sheet['assets'].append({'name': a['name'], 'code': a['account_code'], 'balance': bal})
            balance_sheet['total_assets'] += bal
        elif a.get('account_type') == 'Liability':
            # Liability is negative of asset bal
            balance_sheet['liabilities'].append({'name': a['name'], 'code': a['account_code'], 'balance': -bal})
            balance_sheet['total_liabilities'] += -bal
        elif a.get('account_type') == 'Equity':
            balance_sheet['equity'].append({'name': a['name'], 'code': a['account_code'], 'balance': -bal})
            balance_sheet['total_equity'] += -bal

        # Income statement categorizations
        elif a.get('account_type') == 'Revenue':
            income_statement['revenues'].append({'name': a['name'], 'code': a['account_code'], 'balance': -bal})
            income_statement['total_revenue'] += -bal
        elif a.get('account_type') == 'Expense':
            income_statement['expenses'].append({'name': a['name'], 'code': a['account_code'], 'balance': bal})
            income_statement['total_expense'] += bal

    # Factor Net Profit into Balance Sheet Equity
    net_profit = income_statement['total_revenue'] - income_statement['total_expense']
    income_statement['net_profit'] = net_profit
    balance_sheet['equity'].append({'name': 'Retained Earnings / Net Profit', 'code': '--', 'balance': net_profit})
    balance_sheet['total_equity'] += net_profit

    return render(request, 'billing/financial_statements.html', {
        'trial_balance': trial_balance,
        'balance_sheet': balance_sheet,
        'income_statement': income_statement
    })


@login_required
@module_access('billing')
def audit_trail(request):
    audit_docs = db.collection('financial_audit_trail').stream()
    trail = [serialize_doc(t) for t in audit_docs]
    # Sort descending by timestamp
    trail.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    trail_json = json.dumps(trail)

    return render(request, 'billing/audit_trail.html', {
        'trail': trail,
        'trail_json': trail_json
    })
