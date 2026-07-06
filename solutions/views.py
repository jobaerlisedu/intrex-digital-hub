from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from config.firebase import db
from accounts.decorators import module_access
from datetime import datetime, timedelta
import json
from config.services.integration_service import IntegrationService
from config.workflow_integration import ensure_workflow, try_transition, PROJECT_TRIGGER_MAP

def serialize_doc(doc):
    d = doc.to_dict()
    d['id'] = doc.id
    return d

@login_required
@module_access('solutions')
def index(request):
    proj_docs = db.collection('sol_projects').stream()
    projects = [serialize_doc(p) for p in proj_docs]

    task_docs = db.collection('sol_tasks').stream()
    tasks = [serialize_doc(t) for t in task_docs]

    req_docs = db.collection('sol_project_requisitions').stream()
    requisitions = [serialize_doc(r) for r in req_docs]

    license_docs = db.collection('sol_software_licenses').stream()
    licenses = [serialize_doc(l) for l in license_docs]

    meeting_docs = db.collection('sol_meetings').stream()
    meetings = [serialize_doc(m) for m in meeting_docs]

    # Metrics Calculations
    active_projects = [p for p in projects if p.get('status') not in ['Completed', 'Cancelled']]
    active_count = len(active_projects)

    # Average Task completion rate
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.get('status') == 'Completed'])
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0

    # Project Budget vs Actual spends
    total_budget = sum(float(p.get('total_budget', 0.0)) for p in projects)
    actual_spend = sum(float(r.get('estimated_cost', 0.0)) for r in requisitions if r.get('status') in ['Approved', 'Procured'])

    # Expiring licenses within 30 days
    today = datetime.now().date()
    end_window = today + timedelta(days=30)
    expiring_licenses = []
    for l in licenses:
        r_date_str = l.get('renewal_date', '')
        if r_date_str:
            try:
                r_date = datetime.strptime(r_date_str, '%Y-%m-%d').date()
                if today <= r_date <= end_window:
                    # Attach project info
                    p_info = next((p for p in projects if p['id'] == l.get('project_id')), {})
                    l['project_name'] = p_info.get('name', 'Unknown')
                    expiring_licenses.append(l)
            except ValueError:
                pass

    # Upcoming meetings (today or later)
    upcoming_meetings = []
    for m in meetings:
        m_date_str = m.get('meeting_date', '')
        if m_date_str:
            try:
                m_date = datetime.strptime(m_date_str, '%Y-%m-%d').date()
                if m_date >= today:
                    p_info = next((p for p in projects if p['id'] == m.get('project_id')), {})
                    m['project_name'] = p_info.get('name', 'Unknown')
                    upcoming_meetings.append(m)
            except ValueError:
                pass

    upcoming_meetings.sort(key=lambda x: x.get('meeting_date', ''))

    context = {
        'active_count': active_count,
        'completion_rate': completion_rate,
        'total_budget': total_budget,
        'actual_spend': actual_spend,
        'expiring_licenses': expiring_licenses,
        'upcoming_meetings': upcoming_meetings[:5]
    }
    return render(request, 'solutions/dashboard.html', context)


@login_required
@module_access('solutions')
def projects_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_project':
            total_budget = float(request.POST.get('total_budget', 0.0))
            data = {
                'project_code': request.POST.get('project_code'),
                'name': request.POST.get('name'),
                'category': request.POST.get('category'),
                'client_name': request.POST.get('client_name'),
                'total_budget': total_budget,
                'start_date': request.POST.get('start_date'),
                'end_date': request.POST.get('end_date'),
                'status': request.POST.get('status', 'Not Started'),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            if doc_id:
                db.collection('sol_projects').document(doc_id).update(data)
                ensure_workflow('solutions', 'project', doc_id, entity_label=data.get('name'), request=request)
                trigger = PROJECT_TRIGGER_MAP.get(data.get('status'))
                if trigger:
                    try_transition('solutions', 'project', doc_id, trigger, request=request)
                messages.success(request, f"Project {data['project_code']} updated successfully.")
            else:
                data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                p_ref = db.collection('sol_projects').add(data)
                new_proj_id = p_ref[1].id

                # Auto-scoping of default project phases to populate the scoping view!
                phases_defaults = [
                    {'name': 'Phase 1: Kickoff & Scoping Requirements', 'weight': 0.20},
                    {'name': 'Phase 2: Deployment, Development & Execution', 'weight': 0.60},
                    {'name': 'Phase 3: Integration Quality Checks & Delivery', 'weight': 0.20}
                ]
                for p_def in phases_defaults:
                    db.collection('sol_project_phases').add({
                        'project_id': new_proj_id,
                        'phase_name': p_def['name'],
                        'budget_allocation': total_budget * p_def['weight'],
                        'start_date': data['start_date'],
                        'end_date': data['end_date'],
                        'status': 'Pending'
                    })

                ensure_workflow('solutions', 'project', new_proj_id, entity_label=data.get('name'), request=request)
                messages.success(request, f"New Project {data['project_code']} created with default scopes.")

        elif action == 'delete_project' and doc_id:
            db.collection('sol_projects').document(doc_id).delete()
            messages.success(request, "Project record deleted successfully.")

        return redirect('solutions:projects_list')

    # GET
    proj_docs = db.collection('sol_projects').stream()
    projects = [serialize_doc(p) for p in proj_docs]
    projects.sort(key=lambda x: x.get('project_code', ''))

    # Fetch phases to map inside views
    phase_docs = db.collection('sol_project_phases').stream()
    phases = [serialize_doc(ph) for ph in phase_docs]

    for p in projects:
        p['phases'] = [ph for ph in phases if ph.get('project_id') == p['id']]

    projects_json = json.dumps(projects)

    return render(request, 'solutions/projects.html', {
        'projects': projects,
        'projects_json': projects_json
    })


@login_required
@module_access('solutions')
def kanban_board(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_task':
            data = {
                'phase_id': request.POST.get('phase_id'),
                'task_name': request.POST.get('task_name'),
                'assigned_to': request.POST.get('assigned_to', 'Unassigned'),
                'priority': request.POST.get('priority', 'Medium'),
                'status': request.POST.get('status', 'Todo'),
                'due_date': request.POST.get('due_date'),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            if doc_id:
                db.collection('sol_tasks').document(doc_id).update(data)
                messages.success(request, "Kanban Task updated.")
            else:
                db.collection('sol_tasks').add(data)
                messages.success(request, "New Kanban Task registered.")

        elif action == 'change_status' and doc_id:
            new_status = request.POST.get('status')
            db.collection('sol_tasks').document(doc_id).update({'status': new_status})
            messages.success(request, "Task status updated.")
            return redirect('solutions:kanban_board')

        elif action == 'delete_task' and doc_id:
            db.collection('sol_tasks').document(doc_id).delete()
            messages.success(request, "Task deleted.")

        return redirect('solutions:kanban_board')

    # GET
    proj_docs = db.collection('sol_projects').stream()
    projects = [serialize_doc(p) for p in proj_docs]

    phase_docs = db.collection('sol_project_phases').stream()
    phases = [serialize_doc(ph) for ph in phase_docs]
    phase_map = {ph['id']: ph for ph in phases}

    task_docs = db.collection('sol_tasks').stream()
    tasks = [serialize_doc(t) for t in task_docs]

    # Attach project details to tasks via phase
    for t in tasks:
        ph_id = t.get('phase_id')
        if ph_id in phase_map:
            t['phase_name'] = phase_map[ph_id].get('phase_name', 'Unknown Phase')
            p_id = phase_map[ph_id].get('project_id')
            p_info = next((p for p in projects if p['id'] == p_id), {})
            t['project_name'] = p_info.get('name', 'Unknown Project')
            t['project_code'] = p_info.get('project_code', '')

    # Fetch active employees to populate Task Owner dropdown
    emp_docs = db.collection('hrm_employees').where('status', '==', 'Active').stream()
    employees = [serialize_doc(emp) for emp in emp_docs]
    if not employees:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [serialize_doc(emp) for emp in emp_docs]
    employees.sort(key=lambda x: x.get('name', ''))

    tasks_json = json.dumps(tasks)

    return render(request, 'solutions/kanban.html', {
        'tasks': tasks,
        'phases': phases,
        'projects': projects,
        'employees': employees,
        'tasks_json': tasks_json
    })


@login_required
@module_access('solutions')
def project_sourcing(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_requisition':
            project_id = request.POST.get('project_id')
            phase_id = request.POST.get('phase_id')
            qty = float(request.POST.get('quantity', 1.0))
            est_cost = float(request.POST.get('estimated_cost', 0.0))

            # Budget Validation Rule
            phase_snap = db.collection('sol_project_phases').document(phase_id).get()
            if not phase_snap.exists:
                messages.error(request, "Project phase validation failed.")
                return redirect('solutions:project_sourcing')

            phase_data = phase_snap.to_dict()
            budget_limit = float(phase_data.get('budget_allocation', 0.0))

            # Calculate accumulated cost of all requisitions for this phase
            req_docs = db.collection('sol_project_requisitions').where('phase_id', '==', phase_id).stream()
            existing_cost = sum(float(r.to_dict().get('estimated_cost', 0.0)) for r in req_docs if r.id != doc_id)

            if existing_cost + est_cost > budget_limit:
                messages.error(request, f"Budget Protection Alert: Requisition violates Phase Budget limit (Allocation: ${budget_limit:.2f}, Cumulative: ${existing_cost + est_cost:.2f})!")
                return redirect('solutions:project_sourcing')

            data = {
                'project_id': project_id,
                'phase_id': phase_id,
                'item_name': request.POST.get('item_name'),
                'quantity': qty,
                'estimated_cost': est_cost,
                'status': 'Draft',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            if doc_id:
                db.collection('sol_project_requisitions').document(doc_id).update(data)
                messages.success(request, "Project Requisition updated.")
            else:
                db.collection('sol_project_requisitions').add(data)
                messages.success(request, "Project Requisition logged.")

        elif action == 'dispatch_to_inventory' and doc_id:
            req_ref = db.collection('sol_project_requisitions').document(doc_id)
            req_data = req_ref.get().to_dict()

            project_info = db.collection('sol_projects').document(req_data['project_id']).get().to_dict()

            # Create document in downstream inventory_requisitions collection
            inv_req_ref = db.collection('inv_requisitions').add({
                'item_name': req_data['item_name'],
                'category': 'Project Sourcing',
                'quantity': req_data['quantity'],
                'client_name': project_info.get('client_name', 'Bespoke Client'),
                'status': 'Pending Approval',
                'requested_by': request.user.username,
                'requisition_date': datetime.now().strftime('%Y-%m-%d'),
                'notes': f"Auto-dispatched project procurement requisition for Project {project_info.get('project_code')}"
            })

            req_ref.update({
                'status': 'Approved',
                'requisition_ref': inv_req_ref[1].id
            })

            # Auto-create draft Purchase Order from project requisition
            try:
                req_data['id'] = doc_id
                req_data['project_name'] = project_info.get('name', '')
                IntegrationService.project_requisition_to_po(req_data, request.user)
            except Exception as e:
                print(f"Error auto-creating PO from project requisition: {e}")

            messages.success(request, f"Requisition dispatched to central procurement system. Downstream ID: {inv_req_ref[1].id}")

        elif action == 'delete_requisition' and doc_id:
            db.collection('sol_project_requisitions').document(doc_id).delete()
            messages.success(request, "Requisition removed.")

        return redirect('solutions:project_sourcing')

    # GET
    proj_docs = db.collection('sol_projects').stream()
    projects = [serialize_doc(p) for p in proj_docs]

    phase_docs = db.collection('sol_project_phases').stream()
    phases = [serialize_doc(ph) for ph in phase_docs]

    req_docs = db.collection('sol_project_requisitions').stream()
    requisitions = [serialize_doc(r) for r in req_docs]

    p_map = {p['id']: p for p in projects}
    ph_map = {ph['id']: ph for ph in phases}

    for r in requisitions:
        p_id = r.get('project_id')
        ph_id = r.get('phase_id')
        r['project_code'] = p_map.get(p_id, {}).get('project_code', '')
        r['project_name'] = p_map.get(p_id, {}).get('name', 'Unknown')
        r['phase_name'] = ph_map.get(ph_id, {}).get('phase_name', 'Unknown')

    requisitions_json = json.dumps(requisitions)
    phases_json = json.dumps(phases)

    return render(request, 'solutions/sourcing.html', {
        'requisitions': requisitions,
        'projects': projects,
        'phases': phases,
        'requisitions_json': requisitions_json,
        'phases_json': phases_json
    })


@login_required
@module_access('solutions')
def licensing_assets(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_license':
            data = {
                'project_id': request.POST.get('project_id'),
                'license_name': request.POST.get('license_name'),
                'license_key': request.POST.get('license_key'),
                'subscription_tier': request.POST.get('subscription_tier'),
                'renewal_date': request.POST.get('renewal_date'),
                'cost': float(request.POST.get('cost', 0.0)),
                'status': request.POST.get('status', 'Active'),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            if doc_id:
                db.collection('sol_software_licenses').document(doc_id).update(data)
                messages.success(request, "Software license details updated.")
            else:
                db.collection('sol_software_licenses').add(data)
                messages.success(request, "Software license registered.")

        elif action == 'delete_license' and doc_id:
            db.collection('sol_software_licenses').document(doc_id).delete()
            messages.success(request, "License record removed.")

        return redirect('solutions:licensing_assets')

    # GET
    proj_docs = db.collection('sol_projects').stream()
    projects = [serialize_doc(p) for p in proj_docs]

    license_docs = db.collection('sol_software_licenses').stream()
    licenses = [serialize_doc(l) for l in license_docs]

    p_map = {p['id']: p for p in projects}
    for l in licenses:
        p_id = l.get('project_id')
        l['project_code'] = p_map.get(p_id, {}).get('project_code', '')
        l['project_name'] = p_map.get(p_id, {}).get('name', 'Unknown')

    licenses_json = json.dumps(licenses)

    return render(request, 'solutions/licensing.html', {
        'licenses': licenses,
        'projects': projects,
        'licenses_json': licenses_json
    })


@login_required
@module_access('solutions')
def client_stakeholders(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_stakeholder':
            contact_name = request.POST.get('contact_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')

            from config.contacts_helper import get_or_create_contact
            contact_id = get_or_create_contact(name=contact_name, email=email, phone=phone, role='client')

            data = {
                'project_id': request.POST.get('project_id'),
                'contact_name': contact_name,
                'email': email,
                'phone': phone,
                'role': request.POST.get('role', 'Primary Client Contact'),
                'contact_id': contact_id
            }

            if doc_id:
                db.collection('sol_project_stakeholders').document(doc_id).update(data)
                messages.success(request, "Stakeholder contact updated.")
            else:
                db.collection('sol_project_stakeholders').add(data)
                messages.success(request, "New Stakeholder contact registered.")

        elif action == 'delete_stakeholder' and doc_id:
            db.collection('sol_project_stakeholders').document(doc_id).delete()
            messages.success(request, "Stakeholder contact removed.")

        return redirect('solutions:client_stakeholders')

    # GET
    proj_docs = db.collection('sol_projects').stream()
    projects = [serialize_doc(p) for p in proj_docs]

    stakeholder_docs = db.collection('sol_project_stakeholders').stream()
    stakeholders = [serialize_doc(s) for s in stakeholder_docs]

    p_map = {p['id']: p for p in projects}
    for s in stakeholders:
        p_id = s.get('project_id')
        s['project_code'] = p_map.get(p_id, {}).get('project_code', '')
        s['project_name'] = p_map.get(p_id, {}).get('name', 'Unknown')

    stakeholders_json = json.dumps(stakeholders)

    return render(request, 'solutions/stakeholders.html', {
        'stakeholders': stakeholders,
        'projects': projects,
        'stakeholders_json': stakeholders_json
    })


@login_required
@module_access('solutions')
def global_contacts(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'delete_contact' and doc_id:
            db.collection('sys_contacts').document(doc_id).delete()
            messages.success(request, "Global Contact record deleted successfully.")
        return redirect('solutions:global_contacts')

    # GET
    contact_docs = db.collection('sys_contacts').stream()
    contacts = [serialize_doc(c) for c in contact_docs]
    contacts.sort(key=lambda x: x.get('legal_name', '').lower())

    contacts_json = json.dumps(contacts)

    return render(request, 'solutions/global_contacts.html', {
        'contacts': contacts,
        'contacts_json': contacts_json
    })


@login_required
@module_access('solutions')
def meeting_scheduler(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_meeting':
            data = {
                'project_id': request.POST.get('project_id'),
                'title': request.POST.get('title'),
                'meeting_date': request.POST.get('meeting_date'),
                'start_time': request.POST.get('start_time'),
                'video_link': request.POST.get('video_link', ''),
                'agenda': request.POST.get('agenda', '')
            }

            if doc_id:
                db.collection('sol_meetings').document(doc_id).update(data)
                messages.success(request, "Meeting details updated.")
            else:
                db.collection('sol_meetings').add(data)
                messages.success(request, "New meeting scheduled.")

        elif action == 'delete_meeting' and doc_id:
            db.collection('sol_meetings').document(doc_id).delete()
            messages.success(request, "Meeting scheduled cancelled.")

        return redirect('solutions:meeting_scheduler')

    # GET
    proj_docs = db.collection('sol_projects').stream()
    projects = [serialize_doc(p) for p in proj_docs]

    meeting_docs = db.collection('sol_meetings').stream()
    meetings = [serialize_doc(m) for m in meeting_docs]

    p_map = {p['id']: p for p in projects}
    for m in meetings:
        p_id = m.get('project_id')
        m['project_code'] = p_map.get(p_id, {}).get('project_code', '')
        m['project_name'] = p_map.get(p_id, {}).get('name', 'Unknown')

    meetings_json = json.dumps(meetings)

    return render(request, 'solutions/meetings.html', {
        'meetings': meetings,
        'projects': projects,
        'meetings_json': meetings_json
    })
