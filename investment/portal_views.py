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

from investment.services import (
    FirestoreService as fs,
    COLL_INVESTORS,
    COLL_TRANSACTIONS,
    COLL_LOANS,
    COLL_LOAN_SCHEDULES,
    COLL_NAV_HISTORY,
    COLL_INVESTOR_HOLDINGS,
    COLL_FEE_ACCRUALS,
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

        # Session-based rate limiting: max 5 attempts per 15 minutes
        attempts = request.session.get('portal_login_attempts', 0)
        block_until = request.session.get('portal_login_blocked_until')
        if block_until:
            from datetime import datetime
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

        investors = fs.get_collection(COLL_INVESTORS, [('investor_code', '==', code)])
        match = investors[0] if investors else None
        if match:
            stored_hash = match.get('password_hash', '')
            if stored_hash and check_password(password, stored_hash):
                request.session.pop('portal_login_attempts', None)
                request.session.pop('portal_login_blocked_until', None)
                request.session['portal_investor_id'] = match['id']
                request.session['portal_investor_name'] = match.get('name', 'Investor')
                return redirect('investment:portal_dashboard')

        request.session['portal_login_attempts'] = attempts + 1
        if attempts + 1 >= 5:
            from datetime import datetime, timedelta
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
    """Get the currently logged-in portal investor from session."""
    inv_id = request.session.get('portal_investor_id')
    if not inv_id:
        return None
    return fs.get_document(COLL_INVESTORS, inv_id)


def portal_dashboard(request):
    """Investor dashboard: holdings, value, recent transactions, NAV."""
    inv = _get_portal_investor(request)
    if not inv:
        return redirect('investment:portal_login')

    inv_id = inv['id']
    holdings = fs.get_collection(COLL_INVESTOR_HOLDINGS, [('investor_id', '==', inv_id)])
    transactions = fs.get_collection(COLL_TRANSACTIONS, [('investor_id', '==', inv_id), ('status', '==', 'Cleared')])
    transactions.sort(key=lambda t: t.get('value_date', ''), reverse=True)

    nav_history = fs.get_collection(COLL_NAV_HISTORY)
    nav_history.sort(key=lambda r: r.get('nav_date', ''))
    current_nav = nav_history[-1] if nav_history else None

    total_invested = sum(money_to_float(h.get('total_invested', '0.00')) for h in holdings)
    total_value = sum(money_to_float(h.get('current_value', '0.00')) for h in holdings)
    total_pl = sum(money_to_float(h.get('unrealized_pl', '0.00')) for h in holdings)
    return_pct = round((total_pl / total_invested) * 100, 2) if total_invested > 0 else 0.0

    import json
    context = {
        'investor': inv,
        'holdings': holdings,
        'recent_transactions': transactions[:10],
        'total_invested': total_invested,
        'total_value': total_value,
        'total_pl': total_pl,
        'return_pct': return_pct,
        'current_nav': current_nav,
        'nav_history_json': json.dumps(nav_history, default=str),
    }
    return render(request, 'investment/portal/dashboard.html', context)


def portal_statements(request):
    """Statement selection and download page."""
    inv = _get_portal_investor(request)
    if not inv:
        return redirect('investment:portal_login')

    transactions = fs.get_collection(COLL_TRANSACTIONS, [('investor_id', '==', inv['id']), ('status', '==', 'Cleared')])
    fee_accruals = fs.get_collection(COLL_FEE_ACCRUALS)

    periods = set()
    for t in transactions:
        vd = t.get('value_date', '')
        if vd and len(vd) >= 7:
            periods.add(vd[:7])
    for f in fee_accruals:
        ad = f.get('accrual_date', '')
        if ad and len(ad) >= 7:
            periods.add(ad[:7])

    context = {
        'investor': inv,
        'periods': sorted(periods, reverse=True),
    }
    return render(request, 'investment/portal/statements.html', context)


def portal_profile(request):
    """Investor profile: view/update contact info, upload KYC."""
    inv = _get_portal_investor(request)
    if not inv:
        return redirect('investment:portal_login')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            update_data = {
                'email': request.POST.get('email', inv.get('email', '')),
                'phone': request.POST.get('phone', inv.get('phone', '')),
                'bank_account_name': request.POST.get('bank_account_name', inv.get('bank_account_name', '')),
                'bank_account_number': request.POST.get('bank_account_number', inv.get('bank_account_number', '')),
                'bank_routing_code': request.POST.get('bank_routing_code', inv.get('bank_routing_code', '')),
            }
            fs.update_document(COLL_INVESTORS, inv['id'], update_data)
            messages.success(request, 'Profile updated successfully.')
            return redirect('investment:portal_profile')

        elif action == 'upload_kyc':
            kyc_file = request.FILES.get('kyc_document')
            if kyc_file:
                from config.firebase import bucket
                from datetime import timedelta
                try:
                    blob = bucket.blob(f'kyc/{inv["id"]}/{kyc_file.name}')
                    blob.upload_from_file(kyc_file)
                    signed_url = blob.generate_signed_url(expiration=timedelta(hours=1))
                    fs.update_document(COLL_INVESTORS, inv['id'], {
                        'kyc_document_url': signed_url,
                        'kyc_status': 'Pending',
                    })
                    messages.success(request, 'KYC document uploaded successfully.')
                except Exception as e:
                    messages.error(request, f'Upload failed: {e}')
            else:
                messages.error(request, 'No file selected.')
            return redirect('investment:portal_profile')

        inv = fs.get_document(COLL_INVESTORS, inv['id'])

    context = {'investor': inv}
    return render(request, 'investment/portal/profile.html', context)


def statement_download(request, investor_id, period):
    """Download a PDF statement for an investor."""
    from investment.pdf_service import PdfStatementService
    inv = _get_portal_investor(request)
    if not inv or inv['id'] != investor_id:
        return redirect('investment:portal_login')

    try:
        pdf_bytes = PdfStatementService.generate_investor_statement(investor_id, period)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="statement_{investor_id}_{period}.pdf"'
        return response
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('investment:portal_statements')
