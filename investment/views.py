from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from accounts.decorators import module_access
from datetime import datetime, date, timedelta
from collections import defaultdict
from config.logger import investment_logger

from investment.models import (
    Investor, Transaction, Loan, LoanSchedule,
    OutboundPlacement, FinancialInstrument, InstrumentPrice,
    PLLedger, NavHistory, InvestorHolding,
    FeeStructure, FeeAccrual,
)
from investment.services import (
    CodeGenerator, AmortizationService as amt,
    money_to_float, money_to_str,
)
from config.services.integration_service import IntegrationService


@module_access('investment')
def index(request):
    investors = Investor.objects.filter(is_active=True)
    loans = Loan.objects.filter(is_active=True)
    transactions = Transaction.objects.filter(is_active=True)
    outbound = OutboundPlacement.objects.filter(is_active=True)
    schedules = LoanSchedule.objects.filter(is_active=True)

    total_capital_managed = 0.0
    total_outbound = 0.0
    total_interest_due = 0.0

    for tx in transactions:
        if tx.status == 'Cleared':
            amt_val = float(tx.amount)
            if tx.transaction_type == 'Capital Influx':
                total_capital_managed += amt_val
            elif tx.transaction_type == 'Capital Withdrawal':
                total_capital_managed -= amt_val

    for loan in loans:
        if loan.status == 'Active':
            total_capital_managed += float(loan.outstanding_balance)

    for out in outbound:
        if out.status == 'Active':
            total_outbound += float(out.allocated_capital)

    for sch in schedules:
        if sch.payment_status == 'Unpaid':
            total_interest_due += float(sch.scheduled_interest)

    loan_map = {str(l.id): l for l in loans}
    investor_map = {str(i.id): i for i in investors}

    sorted_unpaid = list(schedules.filter(payment_status='Unpaid').order_by('due_date'))

    upcoming_payables = []
    for sch in sorted_unpaid[:5]:
        loan = loan_map.get(str(sch.loan_id) if sch.loan_id else '')
        investor_name = "Unknown Investor"
        if loan:
            inv = investor_map.get(str(loan.investor_id) if loan.investor_id else '')
            if inv:
                investor_name = inv.name
        upcoming_payables.append({
            'id': str(sch.id),
            'investor_name': investor_name,
            'due_date': sch.due_date.isoformat() if sch.due_date else '',
            'principal': float(sch.scheduled_principal),
            'interest': float(sch.scheduled_interest),
            'total': float(sch.scheduled_principal) + float(sch.scheduled_interest),
        })

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
            if tx.status == 'Cleared' and tx.value_date:
                d = tx.value_date
                if isinstance(d, str):
                    try:
                        d = datetime.strptime(d, '%Y-%m-%d').date()
                    except ValueError:
                        continue
                if d.year == y and d.month == m:
                    if tx.transaction_type == 'Capital Influx':
                        inflow += float(tx.amount)
                    elif tx.transaction_type in ('Capital Withdrawal', 'Interest Payout', 'Dividend Payout'):
                        outflow += float(tx.amount)
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
        'investors_count': investors.count(),
        'active_loans_count': loans.filter(status='Active').count(),
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
            }

            if doc_id:
                Investor.objects.filter(pk=doc_id).update(**data)
                messages.success(request, "Investor profile updated successfully!")
            else:
                raw_password = request.POST.get('password', '')
                if raw_password:
                    data['password_hash'] = make_password(raw_password)
                Investor.objects.create(**data)
                messages.success(request, "Investor profile registered successfully!")

        elif action == 'upload_kyc' and doc_id:
            kyc_file = request.FILES.get('kyc_document')
            if kyc_file:
                try:
                    investor = Investor.objects.get(pk=doc_id)
                    investor.kyc_document = kyc_file
                    investor.save()
                    messages.success(request, "KYC document uploaded successfully!")
                except Exception as e:
                    investment_logger.error(f"KYC upload error [{doc_id}]: {e}")
                    messages.error(request, "Failed to upload KYC document.")
            else:
                messages.error(request, "No file selected for upload.")

        elif action == 'delete_investor' and doc_id:
            Investor.objects.filter(pk=doc_id).delete()
            messages.success(request, "Investor profile deleted successfully!")

        return redirect('investment:investor_list')

    investors = Investor.objects.filter(is_active=True)
    transactions = Transaction.objects.filter(is_active=True)
    loans = Loan.objects.filter(is_active=True)

    tx_by_investor = defaultdict(list)
    for tx in transactions:
        inv_id = str(tx.investor_id) if tx.investor_id else None
        if inv_id:
            tx_by_investor[inv_id].append({
                'id': str(tx.id),
                'transaction_type': tx.transaction_type,
                'amount': float(tx.amount),
                'payment_method': tx.payment_method,
                'value_date': tx.value_date.isoformat() if tx.value_date else '',
                'status': tx.status,
                'notes': tx.notes or '',
            })

    loans_by_investor = defaultdict(list)
    for loan in loans:
        inv_id = str(loan.investor_id) if loan.investor_id else None
        if inv_id:
            loans_by_investor[inv_id].append({
                'id': str(loan.id),
                'principal_amount': float(loan.principal_amount),
                'outstanding_balance': float(loan.outstanding_balance),
                'interest_rate': float(loan.interest_rate),
                'tenure_months': loan.tenure_months,
                'disbursement_date': loan.disbursement_date.isoformat() if loan.disbursement_date else '',
                'status': loan.status,
            })

    for inv in investors:
        inv_id = str(inv.id)
        inv.transactions_list = tx_by_investor.get(inv_id, [])
        inv.loans_list = loans_by_investor.get(inv_id, [])

    return render(request, 'investment/investors.html', {'investors': investors})


@module_access('investment')
def inbound_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_inbound':
            investor_id = request.POST.get('investor_id')
            try:
                investor_obj = Investor.objects.get(pk=investor_id)
                investor_name = investor_obj.name
            except Investor.DoesNotExist:
                investor_name = 'Unknown'

            data = {
                'investor_id': investor_id,
                'investor_name': investor_name,
                'transaction_type': 'Capital Influx',
                'amount': money_to_float(request.POST.get('amount', 0.0)),
                'payment_method': request.POST.get('payment_method', 'Bank Wire'),
                'status': request.POST.get('status', 'Cleared'),
                'notes': request.POST.get('notes', ''),
            }
            value_date_str = request.POST.get('value_date', date.today().isoformat())
            try:
                data['value_date'] = date.fromisoformat(value_date_str)
            except ValueError:
                data['value_date'] = date.today()

            if doc_id:
                Transaction.objects.filter(pk=doc_id).update(**data)
                messages.success(request, "Inbound investment transaction updated successfully.")
            else:
                Transaction.objects.create(**data)
                messages.success(request, "Inbound investment transaction logged successfully.")

        elif action == 'delete_inbound' and doc_id:
            Transaction.objects.filter(pk=doc_id).delete()
            messages.success(request, "Inbound investment transaction deleted successfully.")

        return redirect('investment:inbound_list')

    transactions = Transaction.objects.filter(is_active=True, transaction_type='Capital Influx')
    investors = Investor.objects.filter(is_active=True)
    return render(request, 'investment/inbound.html', {'transactions': transactions, 'investors': investors})


@module_access('investment')
def loans_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_loan':
            investor_id = request.POST.get('investor_id')
            principal = money_to_float(request.POST.get('principal_amount', 0.0))
            rate_percent = money_to_float(request.POST.get('interest_rate', 0.0))
            tenure = int(request.POST.get('tenure_months', 1))
            disb_date_str = request.POST.get('disbursement_date')

            try:
                investor_obj = Investor.objects.get(pk=investor_id)
                investor_name = investor_obj.name
            except Investor.DoesNotExist:
                investor_name = 'Unknown'

            loan_obj = Loan.objects.create(
                investor_id=investor_id,
                investor_name=investor_name,
                principal_amount=principal,
                outstanding_balance=principal,
                interest_rate=rate_percent,
                tenure_months=tenure,
                disbursement_date=date.fromisoformat(disb_date_str) if disb_date_str else date.today(),
                status='Active',
            )
            loan_id = str(loan_obj.pk)

            disb_date = date.fromisoformat(disb_date_str) if disb_date_str else date.today()
            schedule = amt.generate_schedule(principal, rate_percent, tenure, disb_date, loan_id)

            for s in schedule:
                due = s['due_date']
                LoanSchedule.objects.create(
                    loan=loan_obj,
                    installment_number=s['installment_number'],
                    due_date=date.fromisoformat(due) if isinstance(due, str) else due,
                    scheduled_principal=s['scheduled_principal'],
                    scheduled_interest=s['scheduled_interest'],
                    paid_amount=s['paid_amount'],
                    payment_status=s['payment_status'],
                )

            try:
                IntegrationService.investment_loan_to_journal_entry(loan_obj, request.user)
            except Exception as e:
                investment_logger.error(f"Error auto-creating journal entry for loan: {e}")

            messages.success(request, "Investor loan and amortization schedule registered successfully.")

        elif action == 'delete_loan' and doc_id:
            LoanSchedule.objects.filter(loan_id=doc_id).delete()
            Loan.objects.filter(pk=doc_id).delete()
            messages.success(request, "Investor loan and amortization schedule deleted successfully.")

        return redirect('investment:loans_list')

    loans = Loan.objects.filter(is_active=True).select_related('investor')
    investors = Investor.objects.filter(is_active=True)
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
                'allocated_capital': money_to_float(request.POST.get('allocated_capital', 0.0)),
                'current_valuation': money_to_float(request.POST.get('current_valuation', 0.0)),
                'roi_expected_annual': money_to_float(request.POST.get('roi_expected_annual', 0.0)),
                'status': request.POST.get('status', 'Active'),
            }
            placement_date_str = request.POST.get('placement_date')
            if placement_date_str:
                try:
                    data['placement_date'] = date.fromisoformat(placement_date_str)
                except ValueError:
                    pass

            if doc_id:
                OutboundPlacement.objects.filter(pk=doc_id).update(**data)
                messages.success(request, "Outbound investment record updated successfully.")
            else:
                OutboundPlacement.objects.create(**data)
                messages.success(request, "Outbound investment record logged successfully.")

        elif action == 'delete_outbound' and doc_id:
            OutboundPlacement.objects.filter(pk=doc_id).delete()
            messages.success(request, "Outbound investment record deleted successfully.")

        return redirect('investment:outbound_list')

    outbound = OutboundPlacement.objects.filter(is_active=True)
    return render(request, 'investment/outbound.html', {'outbound': outbound})


@module_access('investment')
def instruments_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_instrument':
            data = {
                'instrument_code': request.POST.get('instrument_code'),
                'instrument_type': request.POST.get('type', 'Common Stock'),
                'face_value': money_to_float(request.POST.get('face_value', 0.0)),
                'coupon_rate': money_to_float(request.POST.get('coupon_rate', 0.0)) if request.POST.get('coupon_rate') else 0.0,
                'total_units_issued': int(request.POST.get('total_units_issued', 0)),
                'units_outstanding': int(request.POST.get('units_outstanding', 0)),
            }
            issue_date_str = request.POST.get('issue_date')
            if issue_date_str:
                try:
                    data['issue_date'] = date.fromisoformat(issue_date_str)
                except ValueError:
                    pass

            if doc_id:
                FinancialInstrument.objects.filter(pk=doc_id).update(**data)
                messages.success(request, "Financial instrument updated successfully.")
            else:
                FinancialInstrument.objects.create(**data)
                messages.success(request, "Financial instrument registered successfully.")

        elif action == 'delete_instrument' and doc_id:
            FinancialInstrument.objects.filter(pk=doc_id).delete()
            messages.success(request, "Financial instrument deleted successfully.")

        elif action == 'add_price':
            instrument_id = request.POST.get('instrument_id')
            price_date_str = request.POST.get('price_date')
            price_value = money_to_float(request.POST.get('price', 0.0))
            if not instrument_id or not price_date_str or price_value <= 0:
                messages.error(request, "Invalid price data.")
                return redirect('investment:instruments_list')
            try:
                inst = FinancialInstrument.objects.get(pk=instrument_id)
                InstrumentPrice.objects.create(
                    instrument=inst,
                    price_date=date.fromisoformat(price_date_str),
                    price=price_value,
                )
                messages.success(request, f"Price point {money_to_str(price_value)} recorded for {price_date_str}.")
            except (FinancialInstrument.DoesNotExist, ValueError):
                messages.error(request, "Invalid instrument or date.")

        elif action == 'delete_price' and doc_id:
            InstrumentPrice.objects.filter(pk=doc_id).delete()
            messages.success(request, "Price record deleted.")

        return redirect('investment:instruments_list')

    instruments = FinancialInstrument.objects.filter(is_active=True)
    all_prices = InstrumentPrice.objects.filter(is_active=True).order_by('instrument_id', 'price_date')
    prices_by_instrument = defaultdict(list)
    for p in all_prices:
        inv_id = str(p.instrument_id) if p.instrument_id else ''
        prices_by_instrument[inv_id].append({
            'id': str(p.id),
            'price_date': p.price_date.isoformat() if p.price_date else '',
            'price': float(p.price),
        })
    for inst in instruments:
        inst_prices = prices_by_instrument.get(str(inst.id), [])
        inst.last_price = inst_prices[-1]['price'] if inst_prices else None
    context = {
        'instruments': instruments,
        'prices_by_instrument': dict(prices_by_instrument),
    }
    return render(request, 'investment/instruments.html', context)


@module_access('investment')
def pl_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_pl_entry':
            month = request.POST.get('month')
            revenue = money_to_float(request.POST.get('revenue', 0.0))
            opex = money_to_float(request.POST.get('opex', 0.0))

            schedules = LoanSchedule.objects.filter(is_active=True, due_date__startswith=month)
            interest_expense = amt.compute_interest_expense(month, [
                {'scheduled_interest': str(s.scheduled_interest), 'due_date': s.due_date.isoformat() if s.due_date else ''}
                for s in schedules
            ])
            net_profit = revenue - opex - interest_expense

            data = {
                'month': month,
                'revenue': revenue,
                'opex': opex,
                'interest_expense': interest_expense,
                'net_profit': net_profit,
            }

            if doc_id:
                PLLedger.objects.filter(pk=doc_id).update(**data)
                messages.success(request, "Profit/Loss entry updated successfully.")
            else:
                PLLedger.objects.create(**data)
                messages.success(request, "Profit/Loss entry registered successfully.")

        elif action == 'delete_pl' and doc_id:
            PLLedger.objects.filter(pk=doc_id).delete()
            messages.success(request, "Profit/Loss entry deleted successfully.")

        return redirect('investment:pl_list')

    pl_entries = PLLedger.objects.filter(is_active=True).order_by('-month')
    return render(request, 'investment/pl_management.html', {'pl_entries': pl_entries})


@module_access('investment')
def payables_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        sch_id = request.POST.get('schedule_id')

        if action == 'clear_payment' and sch_id:
            try:
                sch = LoanSchedule.objects.get(pk=sch_id)
            except LoanSchedule.DoesNotExist:
                messages.error(request, "Schedule not found.")
                return redirect('investment:payables_list')

            principal = float(sch.scheduled_principal)
            interest = float(sch.scheduled_interest)
            total = principal + interest

            sch.payment_status = 'Paid'
            sch.paid_amount = total
            sch.actual_payment_date = date.today()
            sch.save()

            loan = sch.loan
            if loan:
                curr_bal = float(loan.outstanding_balance)
                new_bal = max(0.0, curr_bal - principal)
                loan.outstanding_balance = new_bal
                loan.status = 'Fully Paid' if new_bal <= 0.01 else 'Active'
                loan.save()

                inv_name = loan.investor.name if loan.investor else 'Unknown'
                Transaction.objects.create(
                    investor=loan.investor,
                    investor_name=inv_name,
                    transaction_type='Interest Payout',
                    amount=total,
                    payment_method='Bank Wire',
                    value_date=date.today(),
                    status='Cleared',
                    notes=f"Repayment installment #{sch.installment_number} for loan {str(loan.id)}.",
                )

                messages.success(request, "Loan installment payment cleared and payout logged successfully.")

        elif action == 'partial_payment' and sch_id:
            payment_amount = money_to_float(request.POST.get('amount', 0.0))
            if payment_amount <= 0:
                messages.error(request, "Invalid payment amount.")
                return redirect('investment:payables_list')

            try:
                sch = LoanSchedule.objects.get(pk=sch_id)
            except LoanSchedule.DoesNotExist:
                messages.error(request, "Schedule not found.")
                return redirect('investment:payables_list')

            scheduled_principal = float(sch.scheduled_principal)
            scheduled_interest = float(sch.scheduled_interest)
            total_due = scheduled_principal + scheduled_interest
            prev_paid = float(sch.paid_amount)
            new_paid = prev_paid + payment_amount
            capped = min(new_paid, total_due)

            if total_due > 0:
                principal_portion = payment_amount * (scheduled_principal / total_due)
            else:
                principal_portion = 0.0

            sch.paid_amount = capped
            if capped >= total_due - 0.01:
                sch.payment_status = 'Paid'
                sch.actual_payment_date = date.today()
            sch.save()

            loan = sch.loan
            if loan:
                curr_bal = float(loan.outstanding_balance)
                new_bal = max(0.0, curr_bal - principal_portion)
                loan.outstanding_balance = new_bal
                loan.status = 'Fully Paid' if new_bal <= 0.01 else 'Active'
                loan.save()

                inv_name = loan.investor.name if loan.investor else 'Unknown'
                Transaction.objects.create(
                    investor=loan.investor,
                    investor_name=inv_name,
                    transaction_type='Interest Payout',
                    amount=payment_amount,
                    payment_method='Bank Wire',
                    value_date=date.today(),
                    status='Cleared',
                    notes=f"Partial repayment installment #{sch.installment_number} for loan {str(loan.id)}.",
                )

            msg = "Full payment" if capped >= total_due - 0.01 else "Partial payment"
            messages.success(request, f"{msg} of {money_to_str(payment_amount)} recorded successfully.")

        return redirect('investment:payables_list')

    schedules = LoanSchedule.objects.filter(is_active=True).select_related('loan__investor').order_by('due_date')
    joined_schedules = []
    for s in schedules:
        inv_name = s.loan.investor.name if s.loan and s.loan.investor else "Unknown Investor"
        joined_schedules.append({
            'id': str(s.id),
            'installment_number': s.installment_number,
            'due_date': s.due_date.isoformat() if s.due_date else '',
            'scheduled_principal': float(s.scheduled_principal),
            'scheduled_interest': float(s.scheduled_interest),
            'total_due': float(s.scheduled_principal) + float(s.scheduled_interest),
            'paid_amount': float(s.paid_amount),
            'payment_status': s.payment_status,
            'actual_payment_date': s.actual_payment_date.isoformat() if s.actual_payment_date else '--',
            'investor_name': inv_name,
            'loan_id': str(s.loan_id) if s.loan_id else '',
        })

    return render(request, 'investment/payables.html', {'schedules': joined_schedules})


@module_access('investment')
def nav_dashboard(request):
    nav_history = NavHistory.objects.filter(is_active=True).order_by('nav_date')
    holdings = InvestorHolding.objects.filter(is_active=True).select_related('investor')
    fee_accruals = FeeAccrual.objects.filter(is_active=True).order_by('-accrual_date')

    from investment.services import NavService
    current_nav = NavService.get_current_nav()

    context = {
        'nav_history': nav_history,
        'current_nav': current_nav,
        'holdings': holdings,
        'fee_accruals': fee_accruals,
        'total_units': sum(float(h.units_held) for h in holdings),
        'total_invested': sum(float(h.total_invested) for h in holdings),
    }
    return render(request, 'investment/nav.html', context)


@module_access('investment')
def investor_holdings_list(request):
    investors_map = {str(i.id): i for i in Investor.objects.filter(is_active=True)}
    holdings = InvestorHolding.objects.filter(is_active=True).select_related('investor')

    joined = []
    for h in holdings:
        inv = h.investor
        inv_name = inv.name if inv else 'Unknown'
        invested = float(h.total_invested)
        pl = float(h.unrealized_pl)
        return_pct = round((pl / invested) * 100, 2) if invested > 0 else 0.0
        joined.append({
            'id': str(h.id),
            'investor_id': str(h.investor_id) if h.investor_id else '',
            'investor_name': inv_name,
            'units_held': h.units_held,
            'avg_cost_per_unit': h.avg_cost_per_unit,
            'total_invested': h.total_invested,
            'current_value': h.current_value,
            'unrealized_pl': h.unrealized_pl,
            'return_pct': f'{return_pct:.2f}',
        })

    return render(request, 'investment/holdings.html', {'holdings': joined})


@module_access('investment')
def fee_management(request):
    fee_structs = FeeStructure.objects.filter(is_active=True)
    fee_accruals = FeeAccrual.objects.filter(is_active=True).order_by('-accrual_date')

    current_struct = fee_structs.first()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_fee_structure':
            data = {
                'management_fee_annual_pct': request.POST.get('management_fee_annual_pct', '2.00'),
                'performance_fee_pct': request.POST.get('performance_fee_pct', '20.00'),
                'hurdle_rate_pct': request.POST.get('hurdle_rate_pct', '5.00'),
                'high_water_mark': money_to_float(request.POST.get('high_water_mark', '0.0000')),
                'fee_frequency': request.POST.get('fee_frequency', 'monthly'),
                'is_active': True,
            }
            if current_struct:
                FeeStructure.objects.filter(pk=current_struct.pk).update(**data)
                messages.success(request, 'Fee structure updated.')
            else:
                FeeStructure.objects.create(**data)
                messages.success(request, 'Fee structure created.')
            return redirect('investment:fee_management')

        elif action == 'settle_fee':
            fee_id = request.POST.get('fee_id')
            if fee_id:
                FeeAccrual.objects.filter(pk=fee_id).update(
                    is_settled=True,
                    settled_date=date.today(),
                )
                messages.success(request, 'Fee marked as settled.')
            return redirect('investment:fee_management')

    total_accrued_management = sum(
        float(f.amount)
        for f in fee_accruals if f.fee_type == 'management' and not f.is_settled
    )
    total_accrued_performance = sum(
        float(f.amount)
        for f in fee_accruals if f.fee_type == 'performance' and not f.is_settled
    )

    context = {
        'fee_structure': current_struct,
        'fee_accruals': fee_accruals,
        'total_accrued_management': total_accrued_management,
        'total_accrued_performance': total_accrued_performance,
    }
    return render(request, 'investment/fees.html', context)
