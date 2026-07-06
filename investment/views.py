from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from config.firebase import db
from google.cloud import firestore
from django.contrib.auth.decorators import login_required
from accounts.decorators import module_access
from datetime import datetime, timedelta
from config.services.integration_service import IntegrationService

# Helper to retrieve all data in a collection
def get_collection_data(collection_name):
    try:
        docs = db.collection(collection_name).stream()
        results = []
        for doc in docs:
            item = doc.to_dict()
            item['id'] = doc.id
            results.append(item)
        return results
    except Exception as e:
        print(f"Error fetching collection {collection_name}: {e}")
        return []

@module_access('investment')
def index(request):
    investors = get_collection_data('invst_investors')
    loans = get_collection_data('invst_loans')
    transactions = get_collection_data('invst_transactions')
    outbound = get_collection_data('invst_outbound_placements')
    schedules = get_collection_data('invst_loan_schedules')

    # Calculate KPIs
    total_capital_managed = 0.0
    total_outbound = 0.0
    total_interest_due = 0.0

    # Inbound capital from influx transactions minus withdrawals
    for tx in transactions:
        if tx.get('status') == 'Cleared':
            if tx.get('transaction_type') == 'Capital Influx':
                total_capital_managed += float(tx.get('amount', 0.0))
            elif tx.get('transaction_type') == 'Capital Withdrawal':
                total_capital_managed -= float(tx.get('amount', 0.0))

    # Add outstanding principal from active loans to managed capital
    for loan in loans:
        if loan.get('status') == 'Active':
            total_capital_managed += float(loan.get('outstanding_balance', 0.0))

    # Outbound capital placed
    for out in outbound:
        if out.get('status') == 'Active':
            total_outbound += float(out.get('allocated_capital', 0.0))

    # Unpaid interest due
    for sch in schedules:
        if sch.get('payment_status') == 'Unpaid':
            total_interest_due += float(sch.get('scheduled_interest', 0.0))

    # Next 5 upcoming payables
    upcoming_payables = []
    # Join schedules with loans & investors
    loan_map = {l['id']: l for l in loans}
    investor_map = {i['id']: i for i in investors}

    sorted_schedules = sorted(
        [s for s in schedules if s.get('payment_status') == 'Unpaid'],
        key=lambda x: x.get('due_date', '')
    )

    for sch in sorted_schedules[:5]:
        loan = loan_map.get(sch.get('loan_id', ''))
        investor_name = "Unknown Investor"
        if loan:
            investor = investor_map.get(loan.get('investor_id', ''))
            if investor:
                investor_name = investor.get('name', 'Unknown Investor')
        
        upcoming_payables.append({
            'id': sch['id'],
            'investor_name': investor_name,
            'due_date': sch.get('due_date', ''),
            'principal': float(sch.get('scheduled_principal', 0.0)),
            'interest': float(sch.get('scheduled_interest', 0.0)),
            'total': float(sch.get('scheduled_principal', 0.0)) + float(sch.get('scheduled_interest', 0.0))
        })

    # Prepare chart data (monthly capital influx in 2026)
    chart_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    inflow_data = [0.0] * 12
    outflow_data = [0.0] * 12

    for tx in transactions:
        if tx.get('status') == 'Cleared' and tx.get('value_date'):
            try:
                date_obj = datetime.strptime(tx.get('value_date'), '%Y-%m-%d')
                if date_obj.year == 2026:
                    idx = date_obj.month - 1
                    if tx.get('transaction_type') == 'Capital Influx':
                        inflow_data[idx] += float(tx.get('amount', 0.0))
                    elif tx.get('transaction_type') in ['Capital Withdrawal', 'Interest Payout', 'Dividend Payout']:
                        outflow_data[idx] += float(tx.get('amount', 0.0))
            except Exception:
                continue

    context = {
        'total_capital_managed': total_capital_managed,
        'total_outbound': total_outbound,
        'total_interest_due': total_interest_due,
        'upcoming_payables': upcoming_payables,
        'chart_months': chart_months,
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
            # Generate unique code
            existing = get_collection_data('invst_investors')
            code = f"INV-{len(existing) + 1:04d}"

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
                'created_at': firestore.SERVER_TIMESTAMP
            }

            if doc_id:
                if 'created_at' in data:
                    del data['created_at']
                db.collection('invst_investors').document(doc_id).update(data)
                messages.success(request, "Investor profile updated successfully!")
            else:
                db.collection('invst_investors').add(data)
                messages.success(request, "Investor profile registered successfully!")

        elif action == 'delete_investor' and doc_id:
            db.collection('invst_investors').document(doc_id).delete()
            messages.success(request, "Investor profile deleted successfully!")

        return redirect('investment:investor_list')

    investors = get_collection_data('invst_investors')
    transactions = get_collection_data('invst_transactions')
    loans = get_collection_data('invst_loans')

    from collections import defaultdict
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
                'notes': tx.get('notes', '')
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
                'status': loan.get('status')
            })

    for inv in investors:
        inv_id = inv['id']
        inv['transactions'] = tx_by_investor.get(inv_id, [])
        inv['loans'] = loans_by_investor.get(inv_id, [])
        if 'created_at' in inv:
            del inv['created_at']

    return render(request, 'investment/investors.html', {'investors': investors})

@module_access('investment')
def inbound_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_inbound':
            investor_id = request.POST.get('investor_id')
            # Resolve investor name
            investor_doc = db.collection('invst_investors').document(investor_id).get()
            investor_name = investor_doc.to_dict().get('name', 'Unknown') if investor_doc.exists else 'Unknown'

            data = {
                'investor_id': investor_id,
                'investor_name': investor_name,
                'transaction_type': 'Capital Influx',
                'amount': float(request.POST.get('amount', 0.0)),
                'payment_method': request.POST.get('payment_method', 'Bank Wire'),
                'value_date': request.POST.get('value_date', datetime.today().strftime('%Y-%m-%d')),
                'status': request.POST.get('status', 'Cleared'),
                'notes': request.POST.get('notes', ''),
                'created_at': firestore.SERVER_TIMESTAMP
            }

            if doc_id:
                if 'created_at' in data:
                    del data['created_at']
                db.collection('invst_transactions').document(doc_id).update(data)
                messages.success(request, "Inbound investment transaction updated successfully.")
            else:
                db.collection('invst_transactions').add(data)
                messages.success(request, "Inbound investment transaction logged successfully.")

        elif action == 'delete_inbound' and doc_id:
            db.collection('invst_transactions').document(doc_id).delete()
            messages.success(request, "Inbound investment transaction deleted successfully.")

        return redirect('investment:inbound_list')

    transactions = [t for t in get_collection_data('invst_transactions') if t.get('transaction_type') == 'Capital Influx']
    investors = get_collection_data('invst_investors')
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

            investor_doc = db.collection('invst_investors').document(investor_id).get()
            investor_name = investor_doc.to_dict().get('name', 'Unknown') if investor_doc.exists else 'Unknown'

            # PMT Equal Installments Amortization Formula
            r = (rate_percent / 100) / 12
            n = tenure
            if r > 0:
                pmt = principal * (r * (1 + r)**n) / ((1 + r)**n - 1)
            else:
                pmt = principal / n

            loan_data = {
                'investor_id': investor_id,
                'investor_name': investor_name,
                'principal_amount': principal,
                'outstanding_balance': principal,
                'interest_rate': rate_percent,
                'tenure_months': tenure,
                'disbursement_date': disb_date_str,
                'status': 'Active',
                'created_at': firestore.SERVER_TIMESTAMP
            }

            # Save loan to database and get ID
            _, loan_ref = db.collection('invst_loans').add(loan_data)
            loan_id = loan_ref.id

            # Generate and write amortization schedule entries to database
            disb_date = datetime.strptime(disb_date_str, '%Y-%m-%d')
            remaining_balance = principal
            batch = db.batch()

            for i in range(1, n + 1):
                interest_portion = remaining_balance * r
                principal_portion = pmt - interest_portion

                if i == n:
                    principal_portion = remaining_balance
                    pmt = principal_portion + interest_portion

                remaining_balance -= principal_portion
                due_date = (disb_date + timedelta(days=30 * i)).strftime('%Y-%m-%d')

                sch_ref = db.collection('invst_loan_schedules').document()
                batch.set(sch_ref, {
                    'loan_id': loan_id,
                    'installment_number': i,
                    'due_date': due_date,
                    'scheduled_principal': round(principal_portion, 2),
                    'scheduled_interest': round(interest_portion, 2),
                    'paid_amount': 0.0,
                    'payment_status': 'Unpaid'
                })

            batch.commit()

            # Auto-create journal entry for loan disbursement
            loan_data['id'] = loan_id
            loan_data['loan_id'] = loan_id
            try:
                IntegrationService.investment_loan_to_journal_entry(loan_data, request.user)
            except Exception as e:
                print(f"Error auto-creating journal entry for loan: {e}")

            messages.success(request, "Investor loan and amortization schedule registered successfully.")

        elif action == 'delete_loan' and doc_id:
            # Delete loan
            db.collection('invst_loans').document(doc_id).delete()
            # Clean up related schedules
            schedules = db.collection('invst_loan_schedules').where('loan_id', '==', doc_id).stream()
            batch = db.batch()
            for s in schedules:
                batch.delete(s.reference)
            batch.commit()
            messages.success(request, "Investor loan and amortization schedule deleted successfully.")

        return redirect('investment:loans_list')

    loans = get_collection_data('invst_loans')
    investors = get_collection_data('invst_investors')
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
                'status': request.POST.get('status', 'Active')
            }

            if doc_id:
                db.collection('invst_outbound_placements').document(doc_id).update(data)
                messages.success(request, "Outbound investment record updated successfully.")
            else:
                db.collection('invst_outbound_placements').add(data)
                messages.success(request, "Outbound investment record logged successfully.")

        elif action == 'delete_outbound' and doc_id:
            db.collection('invst_outbound_placements').document(doc_id).delete()
            messages.success(request, "Outbound investment record deleted successfully.")

        return redirect('investment:outbound_list')

    outbound = get_collection_data('invst_outbound_placements')
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
                'issue_date': request.POST.get('issue_date')
            }

            if doc_id:
                db.collection('invst_financial_instruments').document(doc_id).update(data)
                messages.success(request, "Financial instrument updated successfully.")
            else:
                db.collection('invst_financial_instruments').add(data)
                messages.success(request, "Financial instrument registered successfully.")

        elif action == 'delete_instrument' and doc_id:
            db.collection('invst_financial_instruments').document(doc_id).delete()
            messages.success(request, "Financial instrument deleted successfully.")

        return redirect('investment:instruments_list')

    instruments = get_collection_data('invst_financial_instruments')
    return render(request, 'investment/instruments.html', {'instruments': instruments})

@module_access('investment')
def pl_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_pl_entry':
            month = request.POST.get('month') # Format 'YYYY-MM'
            revenue = float(request.POST.get('revenue', 0.0))
            opex = float(request.POST.get('opex', 0.0))

            # Fetch schedules to calculate interest paid this month
            schedules = get_collection_data('invst_loan_schedules')
            interest_expense = 0.0
            for s in schedules:
                if s.get('due_date') and s.get('due_date')[:7] == month:
                    interest_expense += float(s.get('scheduled_interest', 0.0))

            net_profit = revenue - opex - interest_expense

            data = {
                'month': month,
                'revenue': revenue,
                'opex': opex,
                'interest_expense': interest_expense,
                'net_profit': net_profit,
                'created_at': firestore.SERVER_TIMESTAMP
            }

            if doc_id:
                if 'created_at' in data:
                    del data['created_at']
                db.collection('invst_pl_ledger').document(doc_id).update(data)
                messages.success(request, "Profit/Loss entry updated successfully.")
            else:
                db.collection('invst_pl_ledger').add(data)
                messages.success(request, "Profit/Loss entry registered successfully.")

        elif action == 'delete_pl' and doc_id:
            db.collection('invst_pl_ledger').document(doc_id).delete()
            messages.success(request, "Profit/Loss entry deleted successfully.")

        return redirect('investment:pl_list')

    pl_entries = sorted(get_collection_data('invst_pl_ledger'), key=lambda x: x.get('month', ''), reverse=True)
    return render(request, 'investment/pl_management.html', {'pl_entries': pl_entries})

@module_access('investment')
def payables_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        sch_id = request.POST.get('schedule_id')

        if action == 'clear_payment' and sch_id:
            sch_doc = db.collection('invst_loan_schedules').document(sch_id).get()
            if sch_doc.exists:
                sch_data = sch_doc.to_dict()
                principal = float(sch_data.get('scheduled_principal', 0.0))
                interest = float(sch_data.get('scheduled_interest', 0.0))
                total = principal + interest

                # 1. Update Schedule status
                db.collection('invst_loan_schedules').document(sch_id).update({
                    'payment_status': 'Paid',
                    'paid_amount': total,
                    'actual_payment_date': datetime.today().strftime('%Y-%m-%d')
                })

                # 2. Update Outstanding Balance on the related Loan
                loan_id = sch_data.get('loan_id')
                loan_ref = db.collection('invst_loans').document(loan_id)
                loan_doc = loan_ref.get()
                if loan_doc.exists:
                    curr_bal = float(loan_doc.to_dict().get('outstanding_balance', 0.0))
                    new_bal = max(0.0, curr_bal - principal)
                    status = 'Fully Paid' if new_bal <= 0.01 else 'Active'
                    loan_ref.update({
                        'outstanding_balance': new_bal,
                        'status': status
                    })

                    # Get investor profile to log payouts
                    inv_id = loan_doc.to_dict().get('investor_id')
                    inv_doc = db.collection('invst_investors').document(inv_id).get()
                    inv_name = inv_doc.to_dict().get('name', 'Unknown') if inv_doc.exists else 'Unknown'

                    # 3. Log Payout Transaction (Cash outflow)
                    db.collection('invst_transactions').add({
                        'investor_id': inv_id,
                        'investor_name': inv_name,
                        'transaction_type': 'Interest Payout',
                        'amount': total,
                        'payment_method': 'Bank Wire',
                        'value_date': datetime.today().strftime('%Y-%m-%d'),
                        'status': 'Cleared',
                        'notes': f"Repayment installment #{sch_data.get('installment_number')} for loan {loan_id}.",
                        'created_at': firestore.SERVER_TIMESTAMP
                    })
                    messages.success(request, "Loan installment payment cleared and payout logged successfully.")

        return redirect('investment:payables_list')

    schedules = get_collection_data('invst_loan_schedules')
    loans = get_collection_data('invst_loans')
    investors = get_collection_data('invst_investors')

    loan_map = {l['id']: l for l in loans}
    investor_map = {i['id']: i for i in investors}

    # Join schedules details
    joined_schedules = []
    for s in schedules:
        loan = loan_map.get(s.get('loan_id', ''))
        investor_name = "Unknown Investor"
        if loan:
            investor = investor_map.get(loan.get('investor_id', ''))
            if investor:
                investor_name = investor.get('name', 'Unknown Investor')
        
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
            'loan_id': s.get('loan_id')
        })

    # Sort upcoming first
    joined_schedules = sorted(joined_schedules, key=lambda x: x.get('due_date', ''))

    return render(request, 'investment/payables.html', {'schedules': joined_schedules})
