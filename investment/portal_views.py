"""
Investor Portal Views

Self-service portal for investors: dashboard, statements, profile.
Uses session-based auth with password verification for non-staff users.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.http import HttpResponse, JsonResponse
from datetime import date, datetime
from collections import defaultdict

from investment.models import (
    Investor, Transaction, NavHistory,
    InvestorHolding, FeeAccrual,
)
from investment.services import (
    money_to_float,
    money_to_str,
)


def portal_login(request):
    """Portal login by investor_code + password with rate limiting."""
    if request.method == 'POST':
        code = request.POST.get('investor_code', '').strip()
        password = request.POST.get('password', '')
        if not code or not password:
            messages.error(request, 'Investor code and password are required.')
            return redirect('investment:portal_login')

        attempts = request.session.get('portal_login_attempts', 0)
        block_until = request.session.get('portal_login_blocked_until')
        if block_until:
            try:
                blocked_dt = datetime.fromisoformat(block_until)
                if datetime.now() < blocked_dt:
                    messages.error(request, 'Too many login attempts. Please try again later.')
                    return redirect('investment:portal_login')
                else:
                    request.session.pop('portal_login_attempts', None)
                    request.session.pop('portal_login_blocked_until', None)
            except (ValueError, TypeError):
                pass

        try:
            match = Investor.objects.get(investor_code=code, is_active=True)
        except Investor.DoesNotExist:
            match = None

        if match:
            stored_hash = getattr(match, 'password_hash', '')
            if stored_hash and check_password(password, stored_hash):
                request.session.pop('portal_login_attempts', None)
                request.session.pop('portal_login_blocked_until', None)
                request.session['portal_investor_id'] = str(match.id)
                request.session['portal_investor_name'] = match.name
                return redirect('investment:portal_dashboard')

        request.session['portal_login_attempts'] = attempts + 1
        if attempts + 1 >= 5:
            from datetime import timedelta
            request.session['portal_login_blocked_until'] = (datetime.now() + timedelta(minutes=15)).isoformat()
            messages.error(request, 'Too many login attempts. Blocked for 15 minutes.')
        else:
            messages.error(request, f'Invalid investor code or password. {4 - attempts} attempt(s) remaining.')
        return redirect('investment:portal_login')
    return render(request, 'investment/portal/login.html')


def portal_logout(request):
    request.session.flush()
    return redirect('investment:portal_login')


def _get_portal_investor(request):
    inv_id = request.session.get('portal_investor_id')
    if not inv_id:
        return None
    try:
        return Investor.objects.get(pk=inv_id)
    except Investor.DoesNotExist:
        return None


def portal_dashboard(request):
    inv = _get_portal_investor(request)
    if not inv:
        return redirect('investment:portal_login')

    inv_id = str(inv.id)
    holdings = InvestorHolding.objects.filter(investor=inv, is_active=True)
    transactions = Transaction.objects.filter(investor=inv, status='Cleared', is_active=True).order_by('-value_date')

    nav_records = NavHistory.objects.filter(is_active=True).order_by('nav_date')
    current_nav = nav_records.last()

    total_invested = sum(float(h.total_invested) for h in holdings)
    total_value = sum(float(h.current_value) for h in holdings)
    total_pl = sum(float(h.unrealized_pl) for h in holdings)
    return_pct = round((total_pl / total_invested) * 100, 2) if total_invested > 0 else 0.0

    import json

    def serialize(obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return str(obj)

    nav_history_list = []
    for n in nav_records:
        d = {}
        for f in n._meta.fields:
            val = getattr(n, f.attname)
            d[f.attname] = serialize(val) if isinstance(val, (date, datetime)) else val
        nav_history_list.append(d)

    context = {
        'investor': inv,
        'holdings': holdings,
        'recent_transactions': transactions[:10],
        'total_invested': total_invested,
        'total_value': total_value,
        'total_pl': total_pl,
        'return_pct': return_pct,
        'current_nav': current_nav,
        'nav_history_json': json.dumps(nav_history_list, default=str),
    }
    return render(request, 'investment/portal/dashboard.html', context)


def portal_statements(request):
    inv = _get_portal_investor(request)
    if not inv:
        return redirect('investment:portal_login')

    transactions = Transaction.objects.filter(investor=inv, status='Cleared', is_active=True)
    fee_accruals = FeeAccrual.objects.filter(is_active=True)

    periods = set()
    for t in transactions:
        if t.value_date:
            periods.add(t.value_date.strftime('%Y-%m'))
    for f in fee_accruals:
        if f.accrual_date:
            periods.add(f.accrual_date.strftime('%Y-%m'))

    context = {
        'investor': inv,
        'periods': sorted(periods, reverse=True),
    }
    return render(request, 'investment/portal/statements.html', context)


def portal_profile(request):
    inv = _get_portal_investor(request)
    if not inv:
        return redirect('investment:portal_login')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            inv.email = request.POST.get('email', inv.email or '')
            inv.phone = request.POST.get('phone', inv.phone or '')
            inv.bank_account_name = request.POST.get('bank_account_name', inv.bank_account_name or '')
            inv.bank_account_number = request.POST.get('bank_account_number', inv.bank_account_number or '')
            inv.bank_routing_code = request.POST.get('bank_routing_code', inv.bank_routing_code or '')
            inv.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('investment:portal_profile')

        elif action == 'upload_kyc':
            kyc_file = request.FILES.get('kyc_document')
            if kyc_file:
                try:
                    inv.kyc_document = kyc_file
                    inv.kyc_status = 'Pending'
                    inv.save()
                    messages.success(request, 'KYC document uploaded successfully.')
                except Exception as e:
                    messages.error(request, f'Upload failed: {e}')
            else:
                messages.error(request, 'No file selected.')
            return redirect('investment:portal_profile')

    context = {'investor': inv}
    return render(request, 'investment/portal/profile.html', context)


def statement_download(request, investor_id, period):
    from investment.pdf_service import PdfStatementService
    inv = _get_portal_investor(request)
    if not inv or str(inv.id) != investor_id:
        return redirect('investment:portal_login')

    try:
        pdf_bytes = PdfStatementService.generate_investor_statement(investor_id, period)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="statement_{investor_id}_{period}.pdf"'
        return response
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('investment:portal_statements')
