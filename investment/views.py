from django.shortcuts import render, redirect
from django.contrib import messages
from accounts.decorators import module_access
from datetime import datetime, date, timedelta
from collections import defaultdict
from config.logger import investment_logger
from config.firebase import bucket

from investment.services import (
    FirestoreService as fs,
    CodeGenerator,
    AmortizationService as amt,
    audit_create,
    audit_update,
    COLL_INVESTORS,
    COLL_TRANSACTIONS,
    COLL_LOANS,
    COLL_LOAN_SCHEDULES,
    COLL_OUTBOUND,
    COLL_INSTRUMENTS,
    COLL_INSTRUMENT_PRICES,
    COLL_PL_LEDGER,
)
from config.services.integration_service import IntegrationService


@module_access('investment')
def index(request):
    investors = fs.get_collection(COLL_INVESTORS)
    loans = fs.get_collection(COLL_LOANS)
    transactions = fs.get_collection(COLL_TRANSACTIONS)
    outbound = fs.get_collection(COLL_OUTBOUND)
    schedules = fs.get_collection(COLL_LOAN_SCHEDULES)

    total_capital_managed = 0.0
    total_outbound = 0.0
    total_interest_due = 0.0

    for tx in transactions:
        if tx.get('status') == 'Cleared':
            ttype = tx.get('transaction_type')
            amt_val = float(tx.get('amount', 0.0))
            if ttype == 'Capital Influx':
                total_capital_managed += amt_val
            elif ttype == 'Capital Withdrawal':
                total_capital_managed -= amt_val

    for loan in loans:
        if loan.get('status') == 'Active':
            total_capital_managed += float(loan.get('outstanding_balance', 0.0))

    for out in outbound:
        if out.get('status') == 'Active':
            total_outbound += float(out.get('allocated_capital', 0.0))

    for sch in schedules:
        if sch.get('payment_status') == 'Unpaid':
            total_interest_due += float(sch.get('scheduled_interest', 0.0))

    loan_map = {l['id']: l for l in loans}
    investor_map = {i['id']: i for i in investors}

    sorted_unpaid = sorted(
        [s for s in schedules if s.get('payment_status') == 'Unpaid'],
        key=lambda x: x.get('due_date', '')
    )

    upcoming_payables = []
    for sch in sorted_unpaid[:5]:
        loan = loan_map.get(sch.get('loan_id', ''))
        investor_name = "Unknown Investor"
        if loan:
            inv = investor_map.get(loan.get('investor_id', ''))
            if inv:
                investor_name = inv.get('name', 'Unknown Investor')
        upcoming_payables.append({
            'id': sch['id'],
            'investor_name': investor_name,
            'due_date': sch.get('due_date', ''),
            'principal': float(sch.get('scheduled_principal', 0.0)),
            'interest': float(sch.get('scheduled_interest', 0.0)),
            'total': float(sch.get('scheduled_principal', 0.0)) + float(sch.get('scheduled_interest', 0.0)),
        })

    # Rolling 12-month chart
    today = date.today()
    chart_labels = []
    inflow_data = []
    outflow_data = []

    for offset in range(11, -1, -1):
        m = today.month - offset
        y = today.year
        while m < 1:
            m += 12
            y -= 1
        while m > 12:
            m -= 12
            y += 1
        label = datetime(y, m, 1).strftime('%b')
        chart_labels.append(f"{label} {str(y)[-2:] if offset != 0 else ''}")
        inflow = 0.0
        outflow = 0.0
        for tx in transactions:
            if tx.get('status') == 'Cleared' and tx.get('value_date'):
                try:
                    d = datetime.strptime(tx['value_date'], '%Y-%m-%d')
                    if d.year == y and d.month == m:
                        if tx.get('transaction_type') == 'Capital Influx':
                            inflow += float(tx.get('amount', 0.0))
                        elif tx.get('transaction_type') in ('Capital Withdrawal', 'Interest Payout', 'Dividend Payout'):
                            outflow += float(tx.get('amount', 0.0))
                except (ValueError, TypeError):
                    continue
        inflow_data.append(inflow)
        outflow_data.append(outflow)

    context = {
        'total_capital_managed': total_capital_managed,
        'total_outbound': total_outbound,
        'total_interest_due': total_interest_due,
        'upcoming_payables': upcoming_payables,
        'chart_months': chart_labels,
        'inflow_data': inflow_data,
        'outflow_data': outflow_data,
        'investors_count': len(investors),
        'active_loans_count': len([l for l in loans if l.get('status') == 'Active']),
    }
    return render(request, 'investment/index.html', context)


@module_access('investment')
def investor_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_investor':
            code = CodeGenerator.investor_code()
            if not code:
                messages.error(request, "Failed to generate investor code. Try again.")
                return redirect('investment:investor_list')

            email = request.POST.get('email', '')
            name = request.POST.get('name', '')
            phone = request.POST.get('phone', '')

            from config.contacts_helper import get_or_create_contact
            contact_id = get_or_create_contact(name=name, email=email, phone=phone, role='investor')

            data = {
                'investor_code': code,
                'name': name,
                'category': request.POST.get('category', 'Individual'),
                'kyc_status': request.POST.get('kyc_status', 'Pending'),
                'tax_id': request.POST.get('tax_id', ''),
                'email': email,
                'phone': phone,
                'bank_account_name': request.POST.get('bank_account_name', ''),
                'bank_account_number': request.POST.get('bank_account_number', ''),
                'bank_routing_code': request.POST.get('bank_routing_code', ''),
                'contact_id': contact_id,
                **audit_create(request.user),
            }

            if doc_id:
                fs.update_document(COLL_INVESTORS, doc_id, data)
                messages.success(request, "Investor profile updated successfully!")
            else:
                fs.create_document(COLL_INVESTORS, data)
                messages.success(request, "Investor profile registered successfully!")

        elif action == 'upload_kyc' and doc_id:
            kyc_file = request.FILES.get('kyc_document')
            if kyc_file:
                try:
                    blob = bucket.blob(f'kyc/{doc_id}/{kyc_file.name}')
                    blob.upload_from_file(kyc_file)
                    blob.make_public()
                    fs.update_document(COLL_INVESTORS, doc_id, {
                        'kyc_document_url': blob.public_url,
                    })
                    messages.success(request, "KYC document uploaded successfully!")
                except Exception as e:
                    investment_logger.error(f"KYC upload error [{doc_id}]: {e}")
                    messages.error(request, "Failed to upload KYC document.")
            else:
                messages.error(request, "No file selected for upload.")

        elif action == 'delete_investor' and doc_id:
            fs.delete_document(COLL_INVESTORS, doc_id)
            messages.success(request, "Investor profile deleted successfully!")

        return redirect('investment:investor_list')

    investors = fs.get_collection(COLL_INVESTORS)
    transactions = fs.get_collection(COLL_TRANSACTIONS)
    loans = fs.get_collection(COLL_LOANS)

    tx_by_investor = defaultdict(list)
    for tx in transactions:
        inv_id = tx.get('investor_id')
        if inv_id:
            tx_by_investor[inv_id].append({
                'id': tx.get('id'),
                'transaction_type': tx.get('transaction_type'),
                'amount': float(tx.get('amount', 0.0)),
                'payment_method': tx.get('payment_method'),
                'value_date': tx.get('value_date'),
                'status': tx.get('status'),
                'notes': tx.get('notes', ''),
            })

    loans_by_investor = defaultdict(list)
    for loan in loans:
        inv_id = loan.get('investor_id')
        if inv_id:
            loans_by_investor[inv_id].append({
                'id': loan.get('id'),
                'principal_amount': float(loan.get('principal_amount', 0.0)),
                'outstanding_balance': float(loan.get('outstanding_balance', 0.0)),
                'interest_rate': float(loan.get('interest_rate', 0.0)),
                'tenure_months': int(loan.get('tenure_months', 0)),
                'disbursement_date': loan.get('disbursement_date'),
                'status': loan.get('status'),
            })

    for inv in investors:
        inv_id = inv['id']
        inv['transactions'] = tx_by_investor.get(inv_id, [])
        inv['loans'] = loans_by_investor.get(inv_id, [])

    return render(request, 'investment/investors.html', {'investors': investors})


@module_access('investment')
def inbound_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_inbound':
            investor_id = request.POST.get('investor_id')
            investor_doc = fs.get_document(COLL_INVESTORS, investor_id)
            investor_name = investor_doc.get('name', 'Unknown') if investor_doc else 'Unknown'

            data = {
                'investor_id': investor_id,
                'investor_name': investor_name,
                'transaction_type': 'Capital Influx',
                'amount': float(request.POST.get('amount', 0.0)),
                'payment_method': request.POST.get('payment_method', 'Bank Wire'),
                'value_date': request.POST.get('value_date', date.today().isoformat()),
                'status': request.POST.get('status', 'Cleared'),
                'notes': request.POST.get('notes', ''),
                **audit_create(request.user),
            }

            if doc_id:
                fs.update_document(COLL_TRANSACTIONS, doc_id, data)
                messages.success(request, "Inbound investment transaction updated successfully.")
            else:
                fs.create_document(COLL_TRANSACTIONS, data)
                messages.success(request, "Inbound investment transaction logged successfully.")

        elif action == 'delete_inbound' and doc_id:
            fs.delete_document(COLL_TRANSACTIONS, doc_id)
            messages.success(request, "Inbound investment transaction deleted successfully.")

        return redirect('investment:inbound_list')

    transactions = [t for t in fs.get_collection(COLL_TRANSACTIONS) if t.get('transaction_type') == 'Capital Influx']
    investors = fs.get_collection(COLL_INVESTORS)
    return render(request, 'investment/inbound.html', {'transactions': transactions, 'investors': investors})


@module_access('investment')
def loans_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_loan':
            investor_id = request.POST.get('investor_id')
            principal = float(request.POST.get('principal_amount', 0.0))
            rate_percent = float(request.POST.get('interest_rate', 0.0))
            tenure = int(request.POST.get('tenure_months', 1))
            disb_date_str = request.POST.get('disbursement_date')

            investor_doc = fs.get_document(COLL_INVESTORS, investor_id)
            investor_name = investor_doc.get('name', 'Unknown') if investor_doc else 'Unknown'

            loan_data = {
                'investor_id': investor_id,
                'investor_name': investor_name,
                'principal_amount': principal,
                'outstanding_balance': principal,
                'interest_rate': rate_percent,
                'tenure_months': tenure,
                'disbursement_date': disb_date_str,
                'status': 'Active',
                **audit_create(request.user),
            }

            loan_id = fs.create_document(COLL_LOANS, loan_data)
            if not loan_id:
                messages.error(request, "Failed to create loan record.")
                return redirect('investment:loans_list')

            disb_date = datetime.strptime(disb_date_str, '%Y-%m-%d').date()
            schedule = amt.generate_schedule(principal, rate_percent, tenure, disb_date, loan_id)

            ops = [('set', COLL_LOAN_SCHEDULES, None, s) for s in schedule]
            fs.batch_write(ops)

            loan_data['id'] = loan_id
            loan_data['loan_id'] = loan_id
            try:
                IntegrationService.investment_loan_to_journal_entry(loan_data, request.user)
            except Exception as e:
                investment_logger.error(f"Error auto-creating journal entry for loan: {e}")

            messages.success(request, "Investor loan and amortization schedule registered successfully.")

        elif action == 'delete_loan' and doc_id:
            fs.delete_document(COLL_LOANS, doc_id)
            schedules = fs.query_collection(COLL_LOAN_SCHEDULES, 'loan_id', '==', doc_id)
            ops = [('delete', COLL_LOAN_SCHEDULES, s['id'], None) for s in schedules]
            if ops:
                fs.batch_write(ops)
            messages.success(request, "Investor loan and amortization schedule deleted successfully.")

        return redirect('investment:loans_list')

    loans = fs.get_collection(COLL_LOANS)
    investors = fs.get_collection(COLL_INVESTORS)
    return render(request, 'investment/loans.html', {'loans': loans, 'investors': investors})


@module_access('investment')
def outbound_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_outbound':
            data = {
                'project_name': request.POST.get('project_name'),
                'entity_type': request.POST.get('entity_type', 'Subsidiary'),
                'allocated_capital': float(request.POST.get('allocated_capital', 0.0)),
                'current_valuation': float(request.POST.get('current_valuation', 0.0)),
                'roi_expected_annual': float(request.POST.get('roi_expected_annual', 0.0)),
                'placement_date': request.POST.get('placement_date'),
                'status': request.POST.get('status', 'Active'),
                **audit_create(request.user),
            }

            if doc_id:
                fs.update_document(COLL_OUTBOUND, doc_id, data)
                messages.success(request, "Outbound investment record updated successfully.")
            else:
                fs.create_document(COLL_OUTBOUND, data)
                messages.success(request, "Outbound investment record logged successfully.")

        elif action == 'delete_outbound' and doc_id:
            fs.delete_document(COLL_OUTBOUND, doc_id)
            messages.success(request, "Outbound investment record deleted successfully.")

        return redirect('investment:outbound_list')

    outbound = fs.get_collection(COLL_OUTBOUND)
    return render(request, 'investment/outbound.html', {'outbound': outbound})


@module_access('investment')
def instruments_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_instrument':
            data = {
                'instrument_code': request.POST.get('instrument_code'),
                'type': request.POST.get('type', 'Common Stock'),
                'face_value': float(request.POST.get('face_value', 0.0)),
                'coupon_rate': float(request.POST.get('coupon_rate', 0.0)) if request.POST.get('coupon_rate') else 0.0,
                'total_units_issued': int(request.POST.get('total_units_issued', 0)),
                'units_outstanding': int(request.POST.get('units_outstanding', 0)),
                'issue_date': request.POST.get('issue_date'),
                **audit_create(request.user),
            }

            if doc_id:
                fs.update_document(COLL_INSTRUMENTS, doc_id, data)
                messages.success(request, "Financial instrument updated successfully.")
            else:
                fs.create_document(COLL_INSTRUMENTS, data)
                messages.success(request, "Financial instrument registered successfully.")

        elif action == 'delete_instrument' and doc_id:
            fs.delete_document(COLL_INSTRUMENTS, doc_id)
            messages.success(request, "Financial instrument deleted successfully.")

        return redirect('investment:instruments_list')

    instruments = fs.get_collection(COLL_INSTRUMENTS)
    return render(request, 'investment/instruments.html', {'instruments': instruments})


@module_access('investment')
def pl_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_pl_entry':
            month = request.POST.get('month')
            revenue = float(request.POST.get('revenue', 0.0))
            opex = float(request.POST.get('opex', 0.0))

            schedules = fs.get_collection(COLL_LOAN_SCHEDULES)
            interest_expense = amt.compute_interest_expense(month, schedules)
            net_profit = revenue - opex - interest_expense

            data = {
                'month': month,
                'revenue': revenue,
                'opex': opex,
                'interest_expense': interest_expense,
                'net_profit': net_profit,
                **audit_create(request.user),
            }

            if doc_id:
                fs.update_document(COLL_PL_LEDGER, doc_id, data)
                messages.success(request, "Profit/Loss entry updated successfully.")
            else:
                fs.create_document(COLL_PL_LEDGER, data)
                messages.success(request, "Profit/Loss entry registered successfully.")

        elif action == 'delete_pl' and doc_id:
            fs.delete_document(COLL_PL_LEDGER, doc_id)
            messages.success(request, "Profit/Loss entry deleted successfully.")

        return redirect('investment:pl_list')

    pl_entries = sorted(fs.get_collection(COLL_PL_LEDGER), key=lambda x: x.get('month', ''), reverse=True)
    return render(request, 'investment/pl_management.html', {'pl_entries': pl_entries})


@module_access('investment')
def payables_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        sch_id = request.POST.get('schedule_id')

        if action == 'clear_payment' and sch_id:
            sch = fs.get_document(COLL_LOAN_SCHEDULES, sch_id)
            if not sch:
                messages.error(request, "Schedule not found.")
                return redirect('investment:payables_list')

            principal = float(sch.get('scheduled_principal', 0.0))
            interest = float(sch.get('scheduled_interest', 0.0))
            total = principal + interest

            fs.update_document(COLL_LOAN_SCHEDULES, sch_id, {
                'payment_status': 'Paid',
                'paid_amount': total,
                'actual_payment_date': date.today().isoformat(),
            })

            loan_id = sch.get('loan_id')
            loan = fs.get_document(COLL_LOANS, loan_id)
            if loan:
                curr_bal = float(loan.get('outstanding_balance', 0.0))
                new_bal = max(0.0, curr_bal - principal)
                loan_status = 'Fully Paid' if new_bal <= 0.01 else 'Active'
                fs.update_document(COLL_LOANS, loan_id, {
                    'outstanding_balance': new_bal,
                    'status': loan_status,
                })

                inv_id = loan.get('investor_id')
                inv = fs.get_document(COLL_INVESTORS, inv_id)
                inv_name = inv.get('name', 'Unknown') if inv else 'Unknown'

                fs.create_document(COLL_TRANSACTIONS, {
                    'investor_id': inv_id,
                    'investor_name': inv_name,
                    'transaction_type': 'Interest Payout',
                    'amount': total,
                    'payment_method': 'Bank Wire',
                    'value_date': date.today().isoformat(),
                    'status': 'Cleared',
                    'notes': f"Repayment installment #{sch.get('installment_number')} for loan {loan_id}.",
                })

                messages.success(request, "Loan installment payment cleared and payout logged successfully.")

        elif action == 'partial_payment' and sch_id:
            payment_amount = float(request.POST.get('amount', 0.0))
            if payment_amount <= 0:
                messages.error(request, "Invalid payment amount.")
                return redirect('investment:payables_list')

            sch = fs.get_document(COLL_LOAN_SCHEDULES, sch_id)
            if not sch:
                messages.error(request, "Schedule not found.")
                return redirect('investment:payables_list')

            scheduled_principal = float(sch.get('scheduled_principal', 0.0))
            scheduled_interest = float(sch.get('scheduled_interest', 0.0))
            total_due = scheduled_principal + scheduled_interest
            prev_paid = float(sch.get('paid_amount', 0.0))
            new_paid = prev_paid + payment_amount
            capped = min(new_paid, total_due)

            if total_due > 0:
                principal_portion = payment_amount * (scheduled_principal / total_due)
            else:
                principal_portion = 0.0

            update_data = {
                'paid_amount': round(capped, 2),
            }
            if capped >= total_due - 0.01:
                update_data['payment_status'] = 'Paid'
                update_data['actual_payment_date'] = date.today().isoformat()

            fs.update_document(COLL_LOAN_SCHEDULES, sch_id, update_data)

            loan_id = sch.get('loan_id')
            loan = fs.get_document(COLL_LOANS, loan_id)
            if loan:
                curr_bal = float(loan.get('outstanding_balance', 0.0))
                new_bal = max(0.0, curr_bal - principal_portion)
                loan_status = 'Fully Paid' if new_bal <= 0.01 else 'Active'
                fs.update_document(COLL_LOANS, loan_id, {
                    'outstanding_balance': round(new_bal, 2),
                    'status': loan_status,
                })

                inv_id = loan.get('investor_id')
                inv = fs.get_document(COLL_INVESTORS, inv_id)
                inv_name = inv.get('name', 'Unknown') if inv else 'Unknown'

                fs.create_document(COLL_TRANSACTIONS, {
                    'investor_id': inv_id,
                    'investor_name': inv_name,
                    'transaction_type': 'Interest Payout',
                    'amount': round(payment_amount, 2),
                    'payment_method': 'Bank Wire',
                    'value_date': date.today().isoformat(),
                    'status': 'Cleared',
                    'notes': f"Partial repayment installment #{sch.get('installment_number')} for loan {loan_id}.",
                })

            msg = "Full payment" if capped >= total_due - 0.01 else "Partial payment"
            messages.success(request, f"{msg} of BDT {payment_amount:.2f} recorded successfully.")

        return redirect('investment:payables_list')

    schedules = fs.get_collection(COLL_LOAN_SCHEDULES)
    loans = fs.get_collection(COLL_LOANS)
    investors = fs.get_collection(COLL_INVESTORS)

    loan_map = {l['id']: l for l in loans}
    investor_map = {i['id']: i for i in investors}

    joined_schedules = []
    for s in schedules:
        loan = loan_map.get(s.get('loan_id', ''))
        investor_name = "Unknown Investor"
        if loan:
            inv = investor_map.get(loan.get('investor_id', ''))
            if inv:
                investor_name = inv.get('name', 'Unknown Investor')
        joined_schedules.append({
            'id': s['id'],
            'installment_number': s.get('installment_number'),
            'due_date': s.get('due_date'),
            'scheduled_principal': float(s.get('scheduled_principal', 0.0)),
            'scheduled_interest': float(s.get('scheduled_interest', 0.0)),
            'total_due': float(s.get('scheduled_principal', 0.0)) + float(s.get('scheduled_interest', 0.0)),
            'paid_amount': float(s.get('paid_amount', 0.0)),
            'payment_status': s.get('payment_status'),
            'actual_payment_date': s.get('actual_payment_date', '--'),
            'investor_name': investor_name,
            'loan_id': s.get('loan_id'),
        })

    joined_schedules.sort(key=lambda x: x.get('due_date', ''))
    return render(request, 'investment/payables.html', {'schedules': joined_schedules})
