from django.shortcuts import render, redirect
from django.http import JsonResponse
from config.firebase import db
from django.contrib.auth.decorators import login_required
from accounts.decorators import module_access
from datetime import datetime
import json

# Utility to serialize Firestore documents
def serialize_doc(doc):
    d = doc.to_dict()
    d['id'] = doc.id
    return d

@login_required
@module_access('inventory')
def index(request):
    # Dashboard view
    products_docs = db.collection('products').stream()
    products = [serialize_doc(p) for p in products_docs]

    po_docs = db.collection('purchase_orders').stream()
    pos = [serialize_doc(po) for po in po_docs]

    req_docs = db.collection('requisitions').stream()
    reqs = [serialize_doc(req) for req in req_docs]

    del_docs = db.collection('deliveries').stream()
    deliveries = [serialize_doc(d) for d in del_docs]

    # Calculations
    low_stock = [p for p in products if p.get('quantity', 0) <= 10]
    active_pos = [po for po in pos if po.get('status') not in ['Fulfilled', 'Cancelled']]
    pending_reqs = [req for req in reqs if req.get('status') in ['Pending Approval', 'Approved']]
    pending_dels = [d for d in deliveries if d.get('delivery_status') != 'Delivered']

    # Total inventory valuation
    total_valuation = sum(p.get('quantity', 0) * p.get('unit_price', 0.0) for p in products)

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
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            if doc_id:
                db.collection('requisitions').document(doc_id).update(data)
            else:
                # Generate unique requisition code
                count = len(list(db.collection('requisitions').stream()))
                data['requisition_code'] = f"REQ-{datetime.now().year}-{count + 1001}"
                data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                db.collection('requisitions').add(data)

        elif action == 'approve_requisition' and doc_id:
            db.collection('requisitions').document(doc_id).update({'status': 'Approved'})
        
        elif action == 'reject_requisition' and doc_id:
            db.collection('requisitions').document(doc_id).update({'status': 'Rejected'})

        elif action == 'delete_requisition' and doc_id:
            db.collection('requisitions').document(doc_id).delete()

        return redirect('inventory:requisitions_list')

    # GET request
    req_docs = db.collection('requisitions').stream()
    requisitions = []
    for doc in req_docs:
        r = serialize_doc(doc)
        requisitions.append(r)

    # Sort descending by creation date
    requisitions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
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
                'is_active': request.POST.get('is_active') == 'True'
            }

            if doc_id:
                db.collection('vendors').document(doc_id).update(data)
            else:
                count = len(list(db.collection('vendors').stream()))
                data['vendor_code'] = f"VND-{count + 1001}"
                db.collection('vendors').add(data)

        elif action == 'delete_vendor' and doc_id:
            db.collection('vendors').document(doc_id).delete()

        return redirect('inventory:vendors_list')

    vendor_docs = db.collection('vendors').stream()
    vendors = [serialize_doc(v) for v in vendor_docs]
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
            req_doc = db.collection('requisitions').document(req_id).get()
            req_data = req_doc.to_dict()

            data = {
                'requisition_id': req_id,
                'requisition_code': req_data.get('requisition_code'),
                'deadline': request.POST.get('deadline'),
                'status': 'Sent',
                'notes': request.POST.get('notes', ''),
                'items': req_data.get('items', []),
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            count = len(list(db.collection('rfqs').stream()))
            data['rfq_code'] = f"RFQ-{datetime.now().year}-{count + 1001}"
            db.collection('rfqs').add(data)

            # Update Requisition status
            db.collection('requisitions').document(req_id).update({'status': 'Procuring'})

        elif action == 'add_quotation':
            rfq_id = request.POST.get('rfq_id')
            vendor_id = request.POST.get('vendor_id')
            rfq_snap = db.collection('rfqs').document(rfq_id).get().to_dict()
            vendor_snap = db.collection('vendors').document(vendor_id).get().to_dict()

            # Read prices
            unit_prices = {}
            grand_total = 0.0
            for idx, item in enumerate(rfq_snap.get('items', [])):
                price = float(request.POST.get(f'price_{idx}', 0.0))
                qty = float(item.get('requested_quantity', 1.0))
                unit_prices[item.get('product_name')] = price
                grand_total += (price * qty)

            del_charge = float(request.POST.get('delivery_charges', 0.0))
            grand_total += del_charge

            data = {
                'rfq_id': rfq_id,
                'rfq_code': rfq_snap.get('rfq_code'),
                'vendor_id': vendor_id,
                'vendor_name': vendor_snap.get('name'),
                'quotation_reference': request.POST.get('quotation_reference'),
                'lead_time_days': int(request.POST.get('lead_time_days', 5)),
                'delivery_charges': del_charge,
                'warranty_terms': request.POST.get('warranty_terms', ''),
                'unit_prices': unit_prices,
                'grand_total': grand_total,
                'status': 'Under Review',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            db.collection('quotations').add(data)

        elif action == 'accept_quotation' and doc_id:
            # Get quotation
            quote_ref = db.collection('quotations').document(doc_id)
            quote = quote_ref.get().to_dict()
            rfq_id = quote.get('rfq_id')
            
            # Reject other quotations for this RFQ
            other_quotes = db.collection('quotations').where('rfq_id', '==', rfq_id).stream()
            for oq in other_quotes:
                if oq.id != doc_id:
                    db.collection('quotations').document(oq.id).update({'status': 'Rejected'})
            
            quote_ref.update({'status': 'Accepted'})
            db.collection('rfqs').document(rfq_id).update({'status': 'Selected'})

            # Automatically generate Purchase Order
            rfq_data = db.collection('rfqs').document(rfq_id).get().to_dict()
            po_items = []
            for item in rfq_data.get('items', []):
                p_name = item.get('product_name')
                u_price = quote.get('unit_prices', {}).get(p_name, 0.0)
                po_items.append({
                    'product_name': p_name,
                    'quantity_ordered': item.get('requested_quantity'),
                    'quantity_received': 0.0,
                    'unit_price': u_price,
                    'line_total': item.get('requested_quantity') * u_price
                })

            po_count = len(list(db.collection('purchase_orders').stream()))
            po_data = {
                'po_code': f"PO-{datetime.now().year}-{po_count + 1001}",
                'vendor_id': quote.get('vendor_id'),
                'vendor_name': quote.get('vendor_name'),
                'requisition_id': rfq_data.get('requisition_id'),
                'requisition_code': rfq_data.get('requisition_code'),
                'quotation_id': doc_id,
                'payment_terms': 'Net 30',
                'shipping_address': 'Main Central Warehouse, Section B',
                'status': 'Draft',
                'grand_total': quote.get('grand_total'),
                'items': po_items,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            db.collection('purchase_orders').add(po_data)

        elif action == 'delete_rfq' and doc_id:
            db.collection('rfqs').document(doc_id).delete()
            # Also clean up related quotes
            quotes = db.collection('quotations').where('rfq_id', '==', doc_id).stream()
            for q in quotes:
                db.collection('quotations').document(q.id).delete()

        return redirect('inventory:rfq_list')

    # GET context
    rfq_docs = db.collection('rfqs').stream()
    rfqs = [serialize_doc(r) for r in rfq_docs]

    req_docs = db.collection('requisitions').where('status', '==', 'Approved').stream()
    requisitions = [serialize_doc(req) for req in req_docs]

    vendor_docs = db.collection('vendors').where('is_active', '==', True).stream()
    vendors = [serialize_doc(v) for v in vendor_docs]

    quote_docs = db.collection('quotations').stream()
    quotations = [serialize_doc(q) for q in quote_docs]

    # Map quotations to RFQ lists
    for r in rfqs:
        r['quotes'] = [q for q in quotations if q.get('rfq_id') == r['id']]

    rfqs_json = json.dumps(rfqs)
    requisitions_json = json.dumps(requisitions)

    return render(request, 'inventory/rfq.html', {
        'rfqs': rfqs,
        'requisitions': requisitions,
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
            db.collection('purchase_orders').document(doc_id).update({'status': 'Approved'})
        
        elif action == 'cancel_po' and doc_id:
            db.collection('purchase_orders').document(doc_id).update({'status': 'Cancelled'})
            
        elif action == 'delete_po' and doc_id:
            db.collection('purchase_orders').document(doc_id).delete()

        return redirect('inventory:po_list')

    po_docs = db.collection('purchase_orders').stream()
    pos = [serialize_doc(po) for po in po_docs]
    pos.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    pos_json = json.dumps(pos)

    return render(request, 'inventory/po.html', {
        'purchase_orders': pos,
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
            po_ref = db.collection('purchase_orders').document(po_id)
            po_data = po_ref.get().to_dict()

            received_qtys = request.POST.getlist('received_qty[]')
            rejected_qtys = request.POST.getlist('rejected_qty[]')
            reasons = request.POST.getlist('rejection_reason[]')
            locations = request.POST.getlist('storage_location[]')

            grn_items = []
            updated_po_items = []
            has_partial = False

            # Add/adjust product stocks and log ledger entries
            for idx, item in enumerate(po_data.get('items', [])):
                rec_qty = float(received_qtys[idx] or 0.0)
                rej_qty = float(rejected_qtys[idx] or 0.0)
                reason = reasons[idx]
                loc = locations[idx]

                grn_items.append({
                    'product_name': item.get('product_name'),
                    'quantity_accepted': rec_qty,
                    'quantity_rejected': rej_qty,
                    'rejection_reason': reason,
                    'storage_location': loc
                })

                # Calculate cumulative received
                total_rec = item.get('quantity_received', 0.0) + rec_qty
                item['quantity_received'] = total_rec
                updated_po_items.append(item)

                if total_rec < item.get('quantity_ordered', 0.0):
                    has_partial = True

                # Adjust warehouse stocks
                prod_query = db.collection('products').where('item_name', '==', item.get('product_name')).stream()
                prod_docs = list(prod_query)
                
                if prod_docs:
                    # Update existing product stock
                    p_doc = prod_docs[0]
                    p_data = p_doc.to_dict()
                    new_qty = p_data.get('quantity', 0) + rec_qty
                    db.collection('products').document(p_doc.id).update({
                        'quantity': new_qty,
                        'unit_price': item.get('unit_price'),
                        'storage_location': loc
                    })
                else:
                    # Insert new product
                    sku_count = len(list(db.collection('products').stream()))
                    new_product = {
                        'item_name': item.get('product_name'),
                        'sku': f"SKU-{sku_count + 1001}",
                        'category': 'General Sourcing',
                        'quantity': rec_qty,
                        'unit_price': item.get('unit_price'),
                        'storage_location': loc
                    }
                    db.collection('products').add(new_product)

                # Record in Inventory Ledger
                db.collection('inventory_ledger').add({
                    'product_name': item.get('product_name'),
                    'quantity_change': rec_qty,
                    'unit_cost': item.get('unit_price'),
                    'transaction_type': 'PO_Receipt',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

            # Create GRN Document
            grn_count = len(list(db.collection('goods_receipts').stream()))
            grn_code = f"GRN-{datetime.now().year}-{grn_count + 1001}"
            grn_data = {
                'grn_code': grn_code,
                'po_id': po_id,
                'po_code': po_data.get('po_code'),
                'received_by': request.user.username,
                'delivery_note_ref': request.POST.get('delivery_note_ref'),
                'received_date': request.POST.get('received_date'),
                'items': grn_items,
                'status': 'Inspected',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            db.collection('goods_receipts').add(grn_data)

            # Update PO state
            po_status = 'Fulfilled' if not has_partial else 'Partially Received'
            po_ref.update({
                'items': updated_po_items,
                'status': po_status
            })

            # If PO fulfilled, update related requisition status
            req_id = po_data.get('requisition_id')
            if req_id and po_status == 'Fulfilled':
                db.collection('requisitions').document(req_id).update({'status': 'Partially Received'})

        elif action == 'delete_grn' and doc_id:
            db.collection('goods_receipts').document(doc_id).delete()

        return redirect('inventory:grn_list')

    # GET context
    grn_docs = db.collection('goods_receipts').stream()
    grns = [serialize_doc(g) for g in grn_docs]
    grns.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    po_docs = db.collection('purchase_orders').where('status', 'in', ['Approved', 'Partially Received']).stream()
    purchase_orders = [serialize_doc(po) for po in po_docs]
    po_json = json.dumps(purchase_orders)
    grns_json = json.dumps(grns)

    return render(request, 'inventory/grn.html', {
        'goods_receipts': grns,
        'purchase_orders': purchase_orders,
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
                'storage_location': request.POST.get('storage_location', 'Aisle A')
            }

            if doc_id:
                # Log adjustment ledger record before updating
                old_snap = db.collection('products').document(doc_id).get().to_dict()
                old_qty = old_snap.get('quantity', 0.0)
                diff = data['quantity'] - old_qty
                if diff != 0:
                    db.collection('inventory_ledger').add({
                        'product_name': data['item_name'],
                        'quantity_change': diff,
                        'unit_cost': data['unit_price'],
                        'transaction_type': 'Stock_Adjustment',
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                db.collection('products').document(doc_id).update(data)
            else:
                # Log initial ledger entry
                db.collection('inventory_ledger').add({
                    'product_name': data['item_name'],
                    'quantity_change': data['quantity'],
                    'unit_cost': data['unit_price'],
                    'transaction_type': 'Stock_Adjustment',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                db.collection('products').add(data)

        elif action == 'delete_product' and doc_id:
            db.collection('products').document(doc_id).delete()

        return redirect('inventory:stock_list')

    # GET context
    prod_docs = db.collection('products').stream()
    products = [serialize_doc(p) for p in prod_docs]
    for p in products:
        p['total_value'] = float(p.get('quantity', 0.0)) * float(p.get('unit_price', 0.0))
    products_json = json.dumps(products)

    ledger_docs = db.collection('inventory_ledger').stream()
    ledger = [serialize_doc(l) for l in ledger_docs]
    ledger.sort(key=lambda x: x.get('created_at', ''), reverse=True)

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
            req_ref = db.collection('requisitions').document(req_id)
            req_data = req_ref.get().to_dict()

            data = {
                'requisition_id': req_id,
                'requisition_code': req_data.get('requisition_code'),
                'client_name': req_data.get('client_name'),
                'dispatched_by': request.user.username,
                'handover_person_name': request.POST.get('handover_person_name'),
                'handover_contact': request.POST.get('handover_contact'),
                'dispatch_date': request.POST.get('dispatch_date'),
                'delivery_status': request.POST.get('delivery_status', 'Dispatched'),
                'proof_of_delivery': request.POST.get('proof_of_delivery', ''),
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            if doc_id:
                # Update status
                db.collection('deliveries').document(doc_id).update({
                    'delivery_status': data['delivery_status'],
                    'proof_of_delivery': data['proof_of_delivery']
                })
                
                # If delivered, decrement quantities from Products collection and log inventory ledger
                if data['delivery_status'] == 'Delivered':
                    # Check if already processed to avoid double decrementing
                    del_doc = db.collection('deliveries').document(doc_id).get().to_dict()
                    if del_doc.get('delivery_status') != 'Delivered':
                        for item in req_data.get('items', []):
                            p_name = item.get('product_name')
                            p_qty = float(item.get('requested_quantity', 0.0))

                            prod_query = db.collection('products').where('item_name', '==', p_name).stream()
                            prod_docs = list(prod_query)
                            if prod_docs:
                                p_doc = prod_docs[0]
                                old_qty = p_doc.to_dict().get('quantity', 0)
                                new_qty = max(0.0, old_qty - p_qty)
                                db.collection('products').document(p_doc.id).update({'quantity': new_qty})

                            # Write to ledger
                            db.collection('inventory_ledger').add({
                                'product_name': p_name,
                                'quantity_change': -p_qty,
                                'unit_cost': 0.0, # Handover has no cost input here
                                'transaction_type': 'Client_Handover',
                                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })

                        # Mark Requisition as Completed
                        req_ref.update({'status': 'Completed'})
            else:
                challan_count = len(list(db.collection('deliveries').stream()))
                data['challan_code'] = f"CHL-{datetime.now().year}-{challan_count + 1001}"
                db.collection('deliveries').add(data)

                # Update Requisition status
                req_ref.update({'status': 'Dispatched'})

        elif action == 'delete_delivery' and doc_id:
            db.collection('deliveries').document(doc_id).delete()

        return redirect('inventory:delivery_list')

    # GET context
    del_docs = db.collection('deliveries').stream()
    deliveries = [serialize_doc(d) for d in del_docs]
    deliveries.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    deliveries_json = json.dumps(deliveries)

    req_docs = db.collection('requisitions').where('status', 'in', ['Approved', 'Partially Received', 'Dispatched']).stream()
    requisitions = [serialize_doc(req) for req in req_docs]

    return render(request, 'inventory/deliveries.html', {
        'deliveries': deliveries,
        'requisitions': requisitions,
        'deliveries_json': deliveries_json
    })
