from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.decorators import module_access
from datetime import datetime, date
import json
from config.workflow_integration import ensure_workflow, try_transition, REQUISITION_TRIGGER_MAP, PO_TRIGGER_MAP
from config.logger import inventory_logger
from .models import (
    Product, Vendor, Requisition, RFQ, Quotation, PurchaseOrder,
    GoodsReceipt, InventoryLedger, Delivery,
)


def _resolve(doc_id, model_class):
    if not doc_id:
        return None
    try:
        return model_class.objects.get(pk=doc_id)
    except (model_class.DoesNotExist, ValueError):
        pass
    return model_class.objects.filter(pk=doc_id).first()


@login_required
@module_access('inventory')
def index(request):
    products = list(Product.objects.filter(is_active=True).values('item_name', 'quantity', 'unit_price'))
    pos = list(PurchaseOrder.objects.filter(is_active=True).values('status'))
    reqs = list(Requisition.objects.filter(is_active=True).values('status'))
    deliveries = list(Delivery.objects.filter(is_active=True).values('delivery_status'))

    low_stock = [p for p in products if float(p['quantity']) <= 10]
    active_pos = [po for po in pos if po['status'] not in ['Fulfilled', 'Cancelled']]
    pending_reqs = [req for req in reqs if req['status'] in ['Pending Approval', 'Approved']]
    pending_dels = [d for d in deliveries if d['delivery_status'] != 'Delivered']
    total_valuation = sum(float(p.get('quantity', 0)) * float(p.get('unit_price', 0.0)) for p in products)

    context = {
        'products': products,
        'low_stock': low_stock,
        'low_stock_count': len(low_stock),
        'active_pos': active_pos,
        'active_po_count': len(active_pos),
        'pending_reqs': pending_reqs,
        'pending_req_count': len(pending_reqs),
        'pending_dels': pending_dels,
        'pending_del_count': len(pending_dels),
        'total_valuation': total_valuation,
    }
    return render(request, 'inventory/dashboard.html', context)


@login_required
@module_access('inventory')
def requisitions_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_requisition':
            item_names = request.POST.getlist('item_name[]')
            item_qtys = request.POST.getlist('item_qty[]')
            item_uoms = request.POST.getlist('item_uom[]')
            items = []
            for name, qty, uom in zip(item_names, item_qtys, item_uoms):
                if name.strip():
                    items.append({
                        'product_name': name.strip(),
                        'requested_quantity': float(qty or 0.0),
                        'unit_of_measure': uom.strip()
                    })

            data = {
                'client_name': request.POST.get('client_name'),
                'expected_delivery_date': request.POST.get('expected_delivery_date'),
                'priority': request.POST.get('priority', 'Medium'),
                'status': request.POST.get('status', 'Pending Approval'),
                'notes': request.POST.get('notes', ''),
                'items': items,
            }

            if doc_id:
                req = _resolve(doc_id, Requisition)
                if req:
                    for k, v in data.items():
                        setattr(req, k, v)
                    req.save()
                    ensure_workflow('inventory', 'requisition', str(req.pk), request=request)
                    trigger = REQUISITION_TRIGGER_MAP.get(data.get('status'))
                    if trigger:
                        try_transition('inventory', 'requisition', str(req.pk), trigger, request=request)
                messages.success(request, "Requisition updated successfully.")
            else:
                count = Requisition.objects.count()
                data['requisition_code'] = f"REQ-{datetime.now().year}-{count + 1001}"
                obj = Requisition.objects.create(**data)
                ensure_workflow('inventory', 'requisition', str(obj.pk), request=request)
                messages.success(request, "Requisition submitted successfully.")

        elif action == 'approve_requisition' and doc_id:
            req = _resolve(doc_id, Requisition)
            if req:
                req.status = 'Approved'
                req.save(update_fields=['status'])
                ensure_workflow('inventory', 'requisition', str(req.pk), request=request)
                try_transition('inventory', 'requisition', str(req.pk), 'approve', request=request)
                messages.success(request, "Requisition approved successfully.")

        elif action == 'reject_requisition' and doc_id:
            req = _resolve(doc_id, Requisition)
            if req:
                req.status = 'Rejected'
                req.save(update_fields=['status'])
                ensure_workflow('inventory', 'requisition', str(req.pk), request=request)
                try_transition('inventory', 'requisition', str(req.pk), 'reject', request=request)
                messages.success(request, "Requisition rejected successfully.")

        elif action == 'delete_requisition' and doc_id:
            req = _resolve(doc_id, Requisition)
            if req:
                req.is_active = False
                req.save(update_fields=['is_active'])
                messages.success(request, "Requisition deleted successfully.")

        return redirect('inventory:requisitions_list')

    requisitions = list(Requisition.objects.filter(is_active=True).order_by('-created_at').values(
        'pk', 'requisition_code', 'client_name', 'expected_delivery_date',
        'priority', 'status', 'notes', 'items', 'created_at',
    ))
    for r in requisitions:
        r['id'] = r.pop('pk') or ''
        if r.get('expected_delivery_date'):
            r['expected_delivery_date'] = str(r['expected_delivery_date'])
        if r.get('created_at'):
            r['created_at'] = r['created_at'].isoformat() if hasattr(r['created_at'], 'isoformat') else str(r['created_at'])

    requisitions_json = json.dumps(requisitions)
    return render(request, 'inventory/requisitions.html', {
        'requisitions': requisitions,
        'requisitions_json': requisitions_json
    })


@login_required
@module_access('inventory')
def vendors_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_vendor':
            data = {
                'name': request.POST.get('name'),
                'contact_name': request.POST.get('contact_name'),
                'email': request.POST.get('email'),
                'phone': request.POST.get('phone'),
                'address': request.POST.get('address'),
                'payment_terms': request.POST.get('payment_terms', 'Net 30'),
                'performance_rating': float(request.POST.get('performance_rating', 5.0)),
                'supplied_categories': [c.strip() for c in request.POST.get('supplied_categories', '').split(',') if c.strip()],
                'is_active': request.POST.get('is_active') == 'True',
            }

            if doc_id:
                v = _resolve(doc_id, Vendor)
                if v:
                    for k, val in data.items():
                        setattr(v, k, val)
                    v.save()
                messages.success(request, "Vendor details updated successfully.")
            else:
                count = Vendor.objects.count()
                data['vendor_code'] = f"VND-{count + 1001}"
                obj = Vendor.objects.create(**data)
                messages.success(request, "Vendor details registered successfully.")

        elif action == 'delete_vendor' and doc_id:
            v = _resolve(doc_id, Vendor)
            if v:
                v.is_active = False
                v.save(update_fields=['is_active'])
                messages.success(request, "Vendor details deleted successfully.")

        return redirect('inventory:vendors_list')

    vendors = list(Vendor.objects.filter(is_active=True).values(
        'pk', 'vendor_code', 'name', 'contact_name', 'email', 'phone',
        'address', 'payment_terms', 'performance_rating', 'supplied_categories',
    ))
    for v in vendors:
        v['id'] = v.pop('pk') or ''
        v['performance_rating'] = float(v['performance_rating'])

    vendors_json = json.dumps(vendors)
    return render(request, 'inventory/vendors.html', {
        'vendors': vendors,
        'vendors_json': vendors_json
    })


@login_required
@module_access('inventory')
def rfq_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_rfq':
            req_id = request.POST.get('requisition_id')
            req_obj = _resolve(req_id, Requisition)

            data = {
                'requisition': req_obj,
                'deadline': request.POST.get('deadline'),
                'status': 'Sent',
                'notes': request.POST.get('notes', ''),
                'items': req_obj.items if req_obj else [],
            }
            count = RFQ.objects.count()
            data['rfq_code'] = f"RFQ-{datetime.now().year}-{count + 1001}"
            obj = RFQ.objects.create(**data)
            if req_obj:
                req_obj.status = 'Procuring'
                req_obj.save(update_fields=['status'])
                ensure_workflow('inventory', 'requisition', str(req_obj.pk), request=request)
                try_transition('inventory', 'requisition', str(req_obj.pk), 'start_procurement', request=request)
            messages.success(request, "Request for Quotation (RFQ) created successfully.")

        elif action == 'add_quotation':
            rfq_id = request.POST.get('rfq_id')
            vendor_id = request.POST.get('vendor_id')
            rfq_obj = _resolve(rfq_id, RFQ)
            vendor_obj = _resolve(vendor_id, Vendor)

            unit_prices = {}
            grand_total = 0.0
            for idx, item in enumerate(rfq_obj.items if rfq_obj else []):
                price = float(request.POST.get(f'price_{idx}', 0.0))
                qty = float(item.get('requested_quantity', 1.0))
                unit_prices[item.get('product_name')] = price
                grand_total += (price * qty)

            del_charge = float(request.POST.get('delivery_charges', 0.0))
            grand_total += del_charge

            data = {
                'rfq': rfq_obj,
                'vendor': vendor_obj,
                'quotation_reference': request.POST.get('quotation_reference'),
                'lead_time_days': int(request.POST.get('lead_time_days', 5)),
                'delivery_charges': del_charge,
                'warranty_terms': request.POST.get('warranty_terms', ''),
                'unit_prices': unit_prices,
                'grand_total': grand_total,
                'status': 'Under Review',
            }
            obj = Quotation.objects.create(**data)
            messages.success(request, "Vendor quotation added successfully.")

        elif action == 'accept_quotation' and doc_id:
            quote_obj = _resolve(doc_id, Quotation)
            if not quote_obj:
                messages.error(request, "Quotation not found.")
                return redirect('inventory:rfq_list')

            rfq_obj = quote_obj.rfq

            other_quotes = Quotation.objects.filter(rfq=rfq_obj).exclude(pk=quote_obj.pk)
            for oq in other_quotes:
                oq.status = 'Rejected'
                oq.save(update_fields=['status'])

            quote_obj.status = 'Accepted'
            quote_obj.save(update_fields=['status'])

            if rfq_obj:
                rfq_obj.status = 'Selected'
                rfq_obj.save(update_fields=['status'])

                po_items = []
                for item in rfq_obj.items:
                    p_name = item.get('product_name')
                    u_price = quote_obj.unit_prices.get(p_name, 0.0)
                    po_items.append({
                        'product_name': p_name,
                        'quantity_ordered': item.get('requested_quantity'),
                        'quantity_received': 0.0,
                        'unit_price': u_price,
                        'line_total': item.get('requested_quantity') * u_price
                    })

                po_count = PurchaseOrder.objects.count()
                po_data = {
                    'po_code': f"PO-{datetime.now().year}-{po_count + 1001}",
                    'vendor': quote_obj.vendor,
                    'requisition': rfq_obj.requisition,
                    'quotation': quote_obj,
                    'payment_terms': 'Net 30',
                    'shipping_address': 'Main Central Warehouse, Section B',
                    'status': 'Draft',
                    'grand_total': quote_obj.grand_total,
                    'items': po_items,
                }
                po_obj = PurchaseOrder.objects.create(**po_data)
                ensure_workflow('inventory', 'purchase_order', str(po_obj.pk), request=request)

            messages.success(request, "Quotation accepted; purchase order created successfully.")

        elif action == 'delete_rfq' and doc_id:
            rfq_obj = _resolve(doc_id, RFQ)
            if rfq_obj:
                Quotation.objects.filter(rfq=rfq_obj).update(is_active=False)
                rfq_obj.is_active = False
                rfq_obj.save(update_fields=['is_active'])
            messages.success(request, "Request for Quotation deleted successfully.")

        return redirect('inventory:rfq_list')

    rfqs = RFQ.objects.filter(is_active=True).order_by('-created_at')
    requisitions = Requisition.objects.filter(is_active=True, status='Approved')
    vendors = Vendor.objects.filter(is_active=True)
    quotations = Quotation.objects.filter(is_active=True)

    rfq_list_data = []
    for r in rfqs:
        rfq_dict = {
            'id': r.pk or str(r.pk),
            'rfq_code': r.rfq_code,
            'requisition_id': str(r.requisition_id) if r.requisition_id else '',
            'requisition_code': r.requisition.requisition_code if r.requisition else '',
            'deadline': str(r.deadline) if r.deadline else '',
            'status': r.status,
            'notes': r.notes or '',
            'items': r.items,
            'created_at': r.created_at.isoformat() if r.created_at else '',
            'quotes': [],
        }
        for q in quotations:
            if q.rfq_id == r.pk:
                quote_dict = {
                    'id': q.pk or str(q.pk),
                    'quotation_reference': q.quotation_reference or '',
                    'vendor_id': str(q.vendor_id) if q.vendor_id else '',
                    'vendor_name': q.vendor.name if q.vendor else '',
                    'lead_time_days': q.lead_time_days,
                    'delivery_charges': float(q.delivery_charges),
                    'warranty_terms': q.warranty_terms or '',
                    'unit_prices': q.unit_prices,
                    'grand_total': float(q.grand_total),
                    'status': q.status,
                    'created_at': q.created_at.isoformat() if q.created_at else '',
                }
                rfq_dict['quotes'].append(quote_dict)
        rfq_list_data.append(rfq_dict)

    req_list = []
    for req in requisitions:
        req_list.append({
            'id': req.pk or str(req.pk),
            'requisition_code': req.requisition_code,
            'client_name': req.client_name or '',
            'items': req.items,
            'status': req.status,
        })

    rfqs_json = json.dumps(rfq_list_data)
    requisitions_json = json.dumps(req_list)

    return render(request, 'inventory/rfq.html', {
        'rfqs': rfq_list_data,
        'requisitions': req_list,
        'vendors': vendors,
        'rfqs_json': rfqs_json,
        'requisitions_json': requisitions_json
    })


@login_required
@module_access('inventory')
def po_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'approve_po' and doc_id:
            po = _resolve(doc_id, PurchaseOrder)
            if po:
                po.status = 'Approved'
                po.save(update_fields=['status'])
                ensure_workflow('inventory', 'purchase_order', str(po.pk), request=request)
                try_transition('inventory', 'purchase_order', str(po.pk), 'approve', request=request)
                messages.success(request, "Purchase Order approved successfully.")

        elif action == 'cancel_po' and doc_id:
            po = _resolve(doc_id, PurchaseOrder)
            if po:
                po.status = 'Cancelled'
                po.save(update_fields=['status'])
                ensure_workflow('inventory', 'purchase_order', str(po.pk), request=request)
                try_transition('inventory', 'purchase_order', str(po.pk), 'cancel', request=request)
                messages.success(request, "Purchase Order cancelled successfully.")

        elif action == 'delete_po' and doc_id:
            po = _resolve(doc_id, PurchaseOrder)
            if po:
                po.is_active = False
                po.save(update_fields=['is_active'])
                messages.success(request, "Purchase Order deleted successfully.")

        return redirect('inventory:po_list')

    pos = PurchaseOrder.objects.filter(is_active=True).order_by('-created_at').select_related('vendor', 'requisition')
    po_list_data = []
    for po in pos:
        po_list_data.append({
            'id': po.pk or str(po.pk),
            'po_code': po.po_code,
            'vendor_id': str(po.vendor_id) if po.vendor_id else '',
            'vendor_name': po.vendor.name if po.vendor else '',
            'requisition_id': str(po.requisition_id) if po.requisition_id else '',
            'requisition_code': po.requisition.requisition_code if po.requisition else '',
            'quotation_id': str(po.quotation_id) if po.quotation_id else '',
            'payment_terms': po.payment_terms,
            'shipping_address': po.shipping_address or '',
            'status': po.status,
            'grand_total': float(po.grand_total),
            'items': po.items,
            'created_at': po.created_at.isoformat() if po.created_at else '',
        })

    pos_json = json.dumps(po_list_data)
    return render(request, 'inventory/po.html', {
        'purchase_orders': po_list_data,
        'pos_json': pos_json
    })


@login_required
@module_access('inventory')
def grn_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_grn':
            po_id = request.POST.get('po_id')
            po_obj = _resolve(po_id, PurchaseOrder)

            received_qtys = request.POST.getlist('received_qty[]')
            rejected_qtys = request.POST.getlist('rejected_qty[]')
            reasons = request.POST.getlist('rejection_reason[]')
            locations = request.POST.getlist('storage_location[]')

            grn_items = []
            updated_po_items = []
            has_partial = False

            for idx, item in enumerate(po_obj.items if po_obj else []):
                rec_qty = float(received_qtys[idx] or 0.0)
                rej_qty = float(rejected_qtys[idx] or 0.0)
                reason = reasons[idx]
                loc = locations[idx]

                grn_items.append({
                    'product_name': item.get('product_name'),
                    'quantity_accepted': rec_qty,
                    'quantity_rejected': rej_qty,
                    'rejection_reason': reason,
                    'storage_location': loc,
                })

                total_rec = float(item.get('quantity_received', 0.0)) + rec_qty
                item['quantity_received'] = total_rec
                updated_po_items.append(item)

                if total_rec < float(item.get('quantity_ordered', 0.0)):
                    has_partial = True

                existing = Product.objects.filter(item_name=item.get('product_name')).first()
                if existing:
                    existing.quantity = float(existing.quantity) + rec_qty
                    existing.unit_price = item.get('unit_price')
                    existing.storage_location = loc
                    existing.save(update_fields=['quantity', 'unit_price', 'storage_location'])
                else:
                    sku_count = Product.objects.count()
                    Product.objects.create(
                        item_name=item.get('product_name'),
                        sku=f"SKU-{sku_count + 1001}",
                        category='General Sourcing',
                        quantity=rec_qty,
                        unit_price=item.get('unit_price'),
                        storage_location=loc,
                    )

                InventoryLedger.objects.create(
                    product_name=item.get('product_name'),
                    quantity_change=rec_qty,
                    unit_cost=item.get('unit_price', 0),
                    transaction_type='PO_Receipt',
                )

            grn_count = GoodsReceipt.objects.count()
            grn_code = f"GRN-{datetime.now().year}-{grn_count + 1001}"
            grn_obj = GoodsReceipt.objects.create(
                grn_code=grn_code,
                purchase_order=po_obj,
                received_by=request.user.username,
                delivery_note_ref=request.POST.get('delivery_note_ref'),
                received_date=request.POST.get('received_date'),
                items=grn_items,
                status='Inspected',
            )
            po_status = 'Fulfilled' if not has_partial else 'Partially Received'
            if po_obj:
                po_obj.items = updated_po_items
                po_obj.status = po_status
                po_obj.save()
                ensure_workflow('inventory', 'purchase_order', str(po_obj.pk), request=request)
                trigger = PO_TRIGGER_MAP.get(po_status)
                if trigger:
                    try_transition('inventory', 'purchase_order', str(po_obj.pk), trigger, request=request)

                req_obj = po_obj.requisition
                if req_obj and po_status == 'Fulfilled':
                    req_obj.status = 'Partially Received'
                    req_obj.save(update_fields=['status'])
                    ensure_workflow('inventory', 'requisition', str(req_obj.pk), request=request)
                    try_transition('inventory', 'requisition', str(req_obj.pk), 'partial_receipt', request=request)

            try:
                from config.services.integration_service import IntegrationService
                IntegrationService.grn_to_vendor_bill(grn_items, po_obj, request.user)
            except Exception as e:
                inventory_logger.error(f"Error auto-creating AP Bill from GRN: {e}")

            messages.success(request, "Goods Receipt Note (GRN) created and stock updated successfully.")

        elif action == 'delete_grn' and doc_id:
            grn = _resolve(doc_id, GoodsReceipt)
            if grn:
                grn.is_active = False
                grn.save(update_fields=['is_active'])
            messages.success(request, "Goods Receipt Note deleted successfully.")

        return redirect('inventory:grn_list')

    grns = GoodsReceipt.objects.filter(is_active=True).order_by('-created_at').select_related('purchase_order')
    grn_list_data = []
    for g in grns:
        grn_list_data.append({
            'id': g.pk or str(g.pk),
            'grn_code': g.grn_code,
            'po_id': str(g.purchase_order_id) if g.purchase_order_id else '',
            'po_code': g.purchase_order.po_code if g.purchase_order else '',
            'received_by': g.received_by or '',
            'delivery_note_ref': g.delivery_note_ref or '',
            'received_date': str(g.received_date) if g.received_date else '',
            'items': g.items,
            'status': g.status,
            'created_at': g.created_at.isoformat() if g.created_at else '',
        })

    purchase_orders = PurchaseOrder.objects.filter(is_active=True, status__in=['Approved', 'Partially Received'])
    po_list_data = []
    for po in purchase_orders:
        po_list_data.append({
            'id': po.pk or str(po.pk),
            'po_code': po.po_code,
            'vendor_name': po.vendor.name if po.vendor else '',
            'status': po.status,
            'items': po.items,
        })

    po_json = json.dumps(po_list_data)
    grns_json = json.dumps(grn_list_data)

    return render(request, 'inventory/grn.html', {
        'goods_receipts': grn_list_data,
        'purchase_orders': po_list_data,
        'pos_json': po_json,
        'grns_json': grns_json
    })


@login_required
@module_access('inventory')
def stock_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_product':
            data = {
                'item_name': request.POST.get('item_name'),
                'sku': request.POST.get('sku'),
                'category': request.POST.get('category'),
                'quantity': float(request.POST.get('quantity', 0.0)),
                'unit_price': float(request.POST.get('unit_price', 0.0)),
                'storage_location': request.POST.get('storage_location', 'Aisle A'),
            }

            if doc_id:
                prod = _resolve(doc_id, Product)
                if prod:
                    old_qty = float(prod.quantity)
                    diff = data['quantity'] - old_qty
                    if diff != 0:
                        InventoryLedger.objects.create(
                            product_name=data['item_name'],
                            quantity_change=diff,
                            unit_cost=data['unit_price'],
                            transaction_type='Stock_Adjustment',
                        )
                    for k, v in data.items():
                        setattr(prod, k, v)
                    prod.save()
                messages.success(request, "Product details updated successfully.")
            else:
                InventoryLedger.objects.create(
                    product_name=data['item_name'],
                    quantity_change=data['quantity'],
                    unit_cost=data['unit_price'],
                    transaction_type='Stock_Adjustment',
                )
                obj = Product.objects.create(**data)
                messages.success(request, "Product registered successfully.")

        elif action == 'delete_product' and doc_id:
            prod = _resolve(doc_id, Product)
            if prod:
                prod.is_active = False
                prod.save(update_fields=['is_active'])
                messages.success(request, "Product deleted successfully.")

        return redirect('inventory:stock_list')

    products = list(Product.objects.filter(is_active=True).values(
        'pk', 'item_name', 'sku', 'category', 'quantity', 'unit_price', 'storage_location',
    ))
    for p in products:
        p['id'] = p.pop('pk') or ''
        p['total_value'] = float(p.get('quantity', 0.0)) * float(p.get('unit_price', 0.0))
        p['quantity'] = float(p['quantity'])
        p['unit_price'] = float(p['unit_price'])

    ledger = list(InventoryLedger.objects.filter(is_active=True).order_by('-created_at').values(
        'product_name', 'quantity_change', 'unit_cost', 'transaction_type', 'created_at',
    ))
    for l in ledger:
        l['quantity_change'] = float(l['quantity_change'])
        l['unit_cost'] = float(l['unit_cost'])
        if l.get('created_at'):
            l['created_at'] = l['created_at'].isoformat() if hasattr(l['created_at'], 'isoformat') else str(l['created_at'])

    products_json = json.dumps(products)
    return render(request, 'inventory/stock.html', {
        'products': products,
        'products_json': products_json,
        'ledger': ledger
    })


@login_required
@module_access('inventory')
def delivery_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_delivery':
            req_id = request.POST.get('requisition_id')
            req_obj = _resolve(req_id, Requisition)

            data = {
                'requisition': req_obj,
                'client_name': req_obj.client_name if req_obj else '',
                'dispatched_by': request.user.username,
                'handover_person_name': request.POST.get('handover_person_name'),
                'handover_contact': request.POST.get('handover_contact'),
                'dispatch_date': request.POST.get('dispatch_date'),
                'delivery_status': request.POST.get('delivery_status', 'Dispatched'),
                'proof_of_delivery': request.POST.get('proof_of_delivery', ''),
            }

            if doc_id:
                del_obj = _resolve(doc_id, Delivery)
                if del_obj:
                    old_status = del_obj.delivery_status
                    del_obj.delivery_status = data['delivery_status']
                    del_obj.proof_of_delivery = data['proof_of_delivery']
                    del_obj.save(update_fields=['delivery_status', 'proof_of_delivery'])

                    if data['delivery_status'] == 'Delivered' and old_status != 'Delivered' and req_obj:
                        for item in req_obj.items:
                            p_name = item.get('product_name')
                            p_qty = float(item.get('requested_quantity', 0.0))

                            existing = Product.objects.filter(item_name=p_name).first()
                            if existing:
                                existing.quantity = max(0.0, float(existing.quantity) - p_qty)
                                existing.save(update_fields=['quantity'])

                            InventoryLedger.objects.create(
                                product_name=p_name,
                                quantity_change=-p_qty,
                                unit_cost=0,
                                transaction_type='Client_Handover',
                            )

                        req_obj.status = 'Completed'
                        req_obj.save(update_fields=['status'])
                        ensure_workflow('inventory', 'requisition', str(req_obj.pk), request=request)
                        try_transition('inventory', 'requisition', str(req_obj.pk), 'complete', request=request)

                messages.success(request, "Delivery challan status updated successfully.")
            else:
                challan_count = Delivery.objects.count()
                data['challan_code'] = f"CHL-{datetime.now().year}-{challan_count + 1001}"
                obj = Delivery.objects.create(**data)
                if req_obj:
                    req_obj.status = 'Dispatched'
                    req_obj.save(update_fields=['status'])
                    ensure_workflow('inventory', 'requisition', str(req_obj.pk), request=request)
                    try_transition('inventory', 'requisition', str(req_obj.pk), 'dispatch', request=request)
                messages.success(request, "Delivery challan created and status set to Dispatched successfully.")

        elif action == 'delete_delivery' and doc_id:
            del_obj = _resolve(doc_id, Delivery)
            if del_obj:
                del_obj.is_active = False
                del_obj.save(update_fields=['is_active'])
                messages.success(request, "Delivery challan deleted successfully.")

        return redirect('inventory:delivery_list')

    deliveries = Delivery.objects.filter(is_active=True).order_by('-created_at').select_related('requisition')
    del_list_data = []
    for d in deliveries:
        del_list_data.append({
            'id': d.pk or str(d.pk),
            'challan_code': d.challan_code,
            'requisition_id': str(d.requisition_id) if d.requisition_id else '',
            'requisition_code': d.requisition.requisition_code if d.requisition else '',
            'client_name': d.client_name or '',
            'dispatched_by': d.dispatched_by or '',
            'handover_person_name': d.handover_person_name or '',
            'handover_contact': d.handover_contact or '',
            'dispatch_date': str(d.dispatch_date) if d.dispatch_date else '',
            'delivery_status': d.delivery_status,
            'proof_of_delivery': d.proof_of_delivery or '',
            'created_at': d.created_at.isoformat() if d.created_at else '',
        })

    reqs = Requisition.objects.filter(is_active=True, status__in=['Approved', 'Partially Received', 'Dispatched'])
    req_list_data = []
    for req in reqs:
        req_list_data.append({
            'id': req.pk or str(req.pk),
            'requisition_code': req.requisition_code,
            'client_name': req.client_name or '',
            'items': req.items,
            'status': req.status,
        })

    deliveries_json = json.dumps(del_list_data)
    return render(request, 'inventory/deliveries.html', {
        'deliveries': del_list_data,
        'requisitions': req_list_data,
        'deliveries_json': deliveries_json
    })
