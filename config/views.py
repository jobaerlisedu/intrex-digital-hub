from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from config.firebase import db

@login_required
def erp_dashboard(request):
    # 1. HRM Stats
    hrm_stats = {'total_employees': 0, 'active_employees': 0, 'open_positions': 0}
    try:
        employees = [doc.to_dict() for doc in db.collection('employees').stream()]
        hrm_stats['total_employees'] = len(employees)
        hrm_stats['active_employees'] = sum(1 for e in employees if e.get('status') == 'Active')
        
        positions = [doc.to_dict() for doc in db.collection('hrm_positions').stream()]
        hrm_stats['open_positions'] = len(positions)
    except Exception as e:
        print(f"Error fetching HRM stats: {e}")

    # 2. Inventory Stats
    inventory_stats = {'total_products': 0, 'total_stock': 0, 'total_value': 0.0}
    try:
        products = [doc.to_dict() for doc in db.collection('products').stream()]
        inventory_stats['total_products'] = len(products)
        inventory_stats['total_stock'] = sum(int(p.get('quantity', 0)) for p in products)
        inventory_stats['total_value'] = sum(int(p.get('quantity', 0)) * float(p.get('unit_price', 0.0)) for p in products)
    except Exception as e:
        print(f"Error fetching Inventory stats: {e}")

    # 3. Investment Stats
    investment_stats = {'total_assets': 0, 'total_invested': 0.0, 'current_value': 0.0, 'overall_roi': 0.0}
    try:
        portfolios = [doc.to_dict() for doc in db.collection('portfolios').stream()]
        investment_stats['total_assets'] = len(portfolios)
        investment_stats['total_invested'] = sum(float(p.get('invested_amount', 0.0)) for p in portfolios)
        investment_stats['current_value'] = sum(float(p.get('current_value', 0.0)) for p in portfolios)
        
        if investment_stats['total_invested'] > 0:
            investment_stats['overall_roi'] = round(
                ((investment_stats['current_value'] - investment_stats['total_invested']) / investment_stats['total_invested']) * 100, 
                2
            )
    except Exception as e:
        print(f"Error fetching Investment stats: {e}")

    # 4. Billing Stats
    billing_stats = {'total_invoices': 0, 'paid_amount': 0.0, 'pending_amount': 0.0}
    try:
        invoices = [doc.to_dict() for doc in db.collection('invoices').stream()]
        billing_stats['total_invoices'] = len(invoices)
        billing_stats['paid_amount'] = sum(float(i.get('amount', 0.0)) for i in invoices if i.get('status') == 'Paid')
        billing_stats['pending_amount'] = sum(float(i.get('amount', 0.0)) for i in invoices if i.get('status') == 'Pending')
    except Exception as e:
        print(f"Error fetching Billing stats: {e}")

    # 5. Solutions Stats
    solutions_stats = {'total_tickets': 0, 'open_tickets': 0, 'resolved_tickets': 0}
    try:
        tickets = [doc.to_dict() for doc in db.collection('service_tickets').stream()]
        solutions_stats['total_tickets'] = len(tickets)
        solutions_stats['open_tickets'] = sum(1 for t in tickets if t.get('status') == 'Open')
        solutions_stats['resolved_tickets'] = sum(1 for t in tickets if t.get('status') in ['Resolved', 'Closed'])
    except Exception as e:
        print(f"Error fetching Solutions stats: {e}")

    # 6. Training Stats
    training_stats = {'total_courses': 0, 'total_students': 0, 'active_batches': 0}
    try:
        courses = [doc.to_dict() for doc in db.collection('learn_courses').stream()]
        training_stats['total_courses'] = len(courses)
        
        registrations = [doc.to_dict() for doc in db.collection('learn_registrations').stream()]
        training_stats['total_students'] = len({r.get('studentId') for r in registrations if r.get('studentId')})
        
        batches = [doc.to_dict() for doc in db.collection('learn_batches').stream()]
        training_stats['active_batches'] = sum(1 for b in batches if b.get('status') == 'Active')
    except Exception as e:
        print(f"Error fetching Training stats: {e}")

    # Top-level aggregate stats
    aggregate_stats = {
        'total_employees': hrm_stats['total_employees'],
        'total_students': training_stats['total_students'],
        'total_stock_items': inventory_stats['total_stock'],
        'total_invoiced': billing_stats['paid_amount'] + billing_stats['pending_amount']
    }

    # Fetch audit logs (recent 5 system audit logs)
    audit_logs = []
    try:
        logs_stream = db.collection('learn_tbl_audit_logs').order_by('createdAt', direction='DESCENDING').limit(5).stream()
        for doc in logs_stream:
            log_data = doc.to_dict()
            log_data['id'] = doc.id
            audit_logs.append(log_data)
    except Exception:
        # Fallback to unordered if index is not built yet
        try:
            logs_stream = db.collection('learn_tbl_audit_logs').limit(5).stream()
            for doc in logs_stream:
                log_data = doc.to_dict()
                log_data['id'] = doc.id
                audit_logs.append(log_data)
        except Exception as e:
            print(f"Error fetching audit logs: {e}")

    context = {
        'hrm': hrm_stats,
        'inventory': inventory_stats,
        'investment': investment_stats,
        'billing': billing_stats,
        'solutions': solutions_stats,
        'training': training_stats,
        'aggregate': aggregate_stats,
        'audit_logs': audit_logs,
    }
    return render(request, 'erp/dashboard.html', context)
