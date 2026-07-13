from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.decorators import module_access
from datetime import datetime, timedelta, date
import json
from config.workflow_integration import ensure_workflow, try_transition, PROJECT_TRIGGER_MAP
from config.logger import solutions_logger
from .models import (
    Project, ProjectPhase, Task, ProjectRequisition,
    SoftwareLicense, ProjectStakeholder, Meeting,
)
from hrm.models import Employee
from registry.models import Person


def _resolve(doc_id, model_class):
    if not doc_id:
        return None
    try:
        return model_class.objects.get(pk=doc_id)
    except (model_class.DoesNotExist, ValueError):
        pass
    return model_class.objects.filter(pk=doc_id).first()


def _get_or_create_person(name, email, phone, role):
    if not email:
        return None
    email = email.lower().strip()
    person = Person.objects.filter(email=email).first()
    if person:
        roles = person.roles or []
        if role not in roles:
            roles.append(role)
            person.roles = roles
        if not person.legal_name and name:
            person.legal_name = name
        if not person.phone and phone:
            person.phone = phone
        person.save()
        return str(person.pk)
    person = Person.objects.create(
        display_name=name.strip(),
        legal_name=name.strip(),
        email=email,
        phone=phone.strip(),
        person_type='client',
        roles=[role],
    )
    return str(person.pk)


@login_required
@module_access('solutions')
def index(request):
    projects = list(Project.objects.filter(is_active=True).values('status', 'total_budget'))
    tasks = list(Task.objects.filter(is_active=True).values('status'))
    requisitions = list(ProjectRequisition.objects.filter(is_active=True).values('estimated_cost', 'status'))
    licenses = list(SoftwareLicense.objects.filter(is_active=True).values('renewal_date', 'project_id'))
    meetings = list(Meeting.objects.filter(is_active=True).values('meeting_date', 'project_id'))

    active_projects = [p for p in projects if p['status'] not in ['Completed', 'Cancelled']]
    active_count = len(active_projects)
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t['status'] == 'Completed'])
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
    total_budget = sum(float(p.get('total_budget', 0.0)) for p in projects)
    actual_spend = sum(float(r.get('estimated_cost', 0.0)) for r in requisitions if r['status'] in ['Approved', 'Procured'])

    project_map = {str(p['id']): p for p in Project.objects.filter(is_active=True).values('pk', 'name')}
    for l in project_map:
        project_map[l] = {'id': l, 'name': project_map[l]['name']}
    project_map = {str(p.pk): p.name for p in Project.objects.filter(is_active=True).only('pk', 'name')}

    today = date.today()
    end_window = today + timedelta(days=30)
    expiring_licenses = []
    for l in licenses:
        r_date = l.get('renewal_date')
        if r_date:
            if today <= r_date <= end_window:
                l['project_name'] = project_map.get(str(l['project_id']), 'Unknown') if l['project_id'] else 'Unknown'
                expiring_licenses.append(l)

    upcoming_meetings = []
    for m in meetings:
        m_date = m.get('meeting_date')
        if m_date and m_date >= today:
            m['project_name'] = project_map.get(str(m['project_id']), 'Unknown') if m['project_id'] else 'Unknown'
            upcoming_meetings.append(m)
    upcoming_meetings.sort(key=lambda x: x.get('meeting_date') or date.min)

    context = {
        'active_count': active_count,
        'completion_rate': completion_rate,
        'total_budget': total_budget,
        'actual_spend': actual_spend,
        'expiring_licenses': expiring_licenses,
        'upcoming_meetings': upcoming_meetings[:5],
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
            }

            if doc_id:
                proj = _resolve(doc_id, Project)
                if proj:
                    for k, v in data.items():
                        setattr(proj, k, v)
                    proj.save()
                    ensure_workflow('solutions', 'project', str(proj.pk), entity_label=data.get('name'), request=request)
                    trigger = PROJECT_TRIGGER_MAP.get(data.get('status'))
                    if trigger:
                        try_transition('solutions', 'project', str(proj.pk), trigger, request=request)
                messages.success(request, f"Project {data['project_code']} updated successfully.")
            else:
                obj = Project.objects.create(**data)
                phases_defaults = [
                    {'name': 'Phase 1: Kickoff & Scoping Requirements', 'weight': 0.20},
                    {'name': 'Phase 2: Deployment, Development & Execution', 'weight': 0.60},
                    {'name': 'Phase 3: Integration Quality Checks & Delivery', 'weight': 0.20},
                ]
                for p_def in phases_defaults:
                    ProjectPhase.objects.create(
                        project=obj,
                        phase_name=p_def['name'],
                        budget_allocation=total_budget * p_def['weight'],
                        start_date=data.get('start_date'),
                        end_date=data.get('end_date'),
                        status='Pending',
                    )

                ensure_workflow('solutions', 'project', str(obj.pk), entity_label=data.get('name'), request=request)
                messages.success(request, f"New Project {data['project_code']} created with default scopes.")

        elif action == 'delete_project' and doc_id:
            proj = _resolve(doc_id, Project)
            if proj:
                proj.is_active = False
                proj.save(update_fields=['is_active'])
                messages.success(request, "Project record deleted successfully.")

        return redirect('solutions:projects_list')

    projects = Project.objects.filter(is_active=True).order_by('project_code').prefetch_related('phases')
    proj_list_data = []
    for p in projects:
        phases_list = []
        for ph in p.phases.all():
            phases_list.append({
                'id': ph.pk or str(ph.pk),
                'phase_name': ph.phase_name,
                'budget_allocation': float(ph.budget_allocation),
                'start_date': str(ph.start_date) if ph.start_date else '',
                'end_date': str(ph.end_date) if ph.end_date else '',
                'status': ph.status,
                'project_id': str(p.pk),
            })
        proj_list_data.append({
            'id': p.pk or str(p.pk),
            'project_code': p.project_code,
            'name': p.name,
            'category': p.category or '',
            'client_name': p.client_name or '',
            'total_budget': float(p.total_budget),
            'start_date': str(p.start_date) if p.start_date else '',
            'end_date': str(p.end_date) if p.end_date else '',
            'status': p.status,
            'created_at': p.created_at.isoformat() if p.created_at else '',
            'phases': phases_list,
        })

    projects_json = json.dumps(proj_list_data)
    return render(request, 'solutions/projects.html', {
        'projects': proj_list_data,
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
            }

            if doc_id:
                task = _resolve(doc_id, Task)
                if task:
                    for k, v in data.items():
                        setattr(task, k, v)
                    task.save()
                messages.success(request, "Kanban Task updated.")
            else:
                obj = Task.objects.create(**data)
                messages.success(request, "New Kanban Task registered.")

        elif action == 'change_status' and doc_id:
            task = _resolve(doc_id, Task)
            if task:
                task.status = request.POST.get('status')
                task.save(update_fields=['status'])
                messages.success(request, "Task status updated.")
            return redirect('solutions:kanban_board')

        elif action == 'delete_task' and doc_id:
            task = _resolve(doc_id, Task)
            if task:
                task.is_active = False
                task.save(update_fields=['is_active'])
                messages.success(request, "Task deleted.")

        return redirect('solutions:kanban_board')

    phases = list(ProjectPhase.objects.filter(is_active=True).select_related('project').values(
        'pk', 'phase_name', 'project_id', 'status',
    ))
    for ph in phases:
        ph['id'] = str(ph.pop('pk'))

    phase_map = {ph['id']: ph for ph in phases}

    projects = Project.objects.filter(is_active=True)
    project_map = {str(p.pk): p for p in projects}

    tasks = Task.objects.filter(is_active=True).select_related('phase__project')
    task_list = []
    for t in tasks:
        ph = t.phase
        task_list.append({
            'id': t.pk or str(t.pk),
            'phase_id': str(ph.pk) if ph else '',
            'phase_name': ph.phase_name if ph else 'Unknown Phase',
            'project_id': str(ph.project_id) if ph and ph.project_id else '',
            'project_name': ph.project.name if ph and ph.project else 'Unknown Project',
            'project_code': ph.project.project_code if ph and ph.project else '',
            'task_name': t.task_name,
            'assigned_to': t.assigned_to,
            'priority': t.priority,
            'status': t.status,
            'due_date': str(t.due_date) if t.due_date else '',
        })

    employees = list(Employee.objects.filter(status='Active').values('first_name', 'last_name'))
    if not employees:
        employees = list(Employee.objects.all().values('first_name', 'last_name'))
    emp_list = []
    for e in employees:
        emp_list.append({'name': f"{e['first_name']} {e['last_name']}".strip()})
    emp_list.sort(key=lambda x: x['name'])

    phases_json = json.dumps(phases)
    tasks_json = json.dumps(task_list)

    return render(request, 'solutions/kanban.html', {
        'tasks': task_list,
        'phases': phases,
        'projects': projects,
        'employees': emp_list,
        'phases_json': phases_json,
        'tasks_json': tasks_json,
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

            phase_obj = _resolve(phase_id, ProjectPhase)
            if not phase_obj:
                messages.error(request, "Project phase validation failed.")
                return redirect('solutions:project_sourcing')

            budget_limit = float(phase_obj.budget_allocation)

            existing_cost = sum(
                float(r.estimated_cost)
                for r in ProjectRequisition.objects.filter(phase=phase_obj).exclude(pk=doc_id if doc_id else None)
            )

            if existing_cost + est_cost > budget_limit:
                messages.error(request, f"Budget Protection Alert: Requisition violates Phase Budget limit (Allocation: ${budget_limit:.2f}, Cumulative: ${existing_cost + est_cost:.2f})!")
                return redirect('solutions:project_sourcing')

            data = {
                'project': _resolve(project_id, Project) if project_id else None,
                'phase': phase_obj,
                'item_name': request.POST.get('item_name'),
                'quantity': qty,
                'estimated_cost': est_cost,
                'status': 'Draft',
            }

            if doc_id:
                req_obj = _resolve(doc_id, ProjectRequisition)
                if req_obj:
                    for k, v in data.items():
                        setattr(req_obj, k, v)
                    req_obj.save()
                messages.success(request, "Project Requisition updated.")
            else:
                obj = ProjectRequisition.objects.create(**data)
                messages.success(request, "Project Requisition logged.")

        elif action == 'dispatch_to_inventory' and doc_id:
            req_obj = _resolve(doc_id, ProjectRequisition)
            if not req_obj:
                messages.error(request, "Requisition not found.")
                return redirect('solutions:project_sourcing')

            project_info = req_obj.project

            from inventory.models import Requisition as InvRequisition
            inv_count = InvRequisition.objects.count()
            inv_req = InvRequisition.objects.create(
                requisition_code=f"REQ-{datetime.now().year}-{inv_count + 1001}",
                item_name=req_obj.item_name,
                category='Project Sourcing',
                quantity=float(req_obj.quantity),
                client_name=project_info.client_name if project_info else 'Bespoke Client',
                status='Pending Approval',
                requested_by=request.user.username,
                requisition_date=str(date.today()),
                notes=f"Auto-dispatched project procurement requisition for Project {project_info.project_code if project_info else ''}",
            )
            req_obj.status = 'Approved'
            req_obj.requisition_ref = str(inv_req.pk)
            req_obj.save()

            try:
                req_data = {
                    'id': str(req_obj.pk),
                    'project_id': str(project_info.pk) if project_info else '',
                    'phase_id': str(req_obj.phase_id) if req_obj.phase_id else '',
                    'item_name': req_obj.item_name,
                    'quantity': float(req_obj.quantity),
                    'estimated_cost': float(req_obj.estimated_cost),
                    'status': req_obj.status,
                    'project_name': project_info.name if project_info else '',
                    'requisition_ref': str(inv_req.pk),
                }
                from config.services.integration_service import IntegrationService
                IntegrationService.project_requisition_to_po(req_data, request.user)
            except Exception as e:
                solutions_logger.error(f"Error auto-creating PO from project requisition: {e}")

            messages.success(request, f"Requisition dispatched to central procurement system. Downstream ID: {inv_req.pk}")

        elif action == 'delete_requisition' and doc_id:
            req_obj = _resolve(doc_id, ProjectRequisition)
            if req_obj:
                req_obj.is_active = False
                req_obj.save(update_fields=['is_active'])
            messages.success(request, "Requisition removed.")

        return redirect('solutions:project_sourcing')

    projects = Project.objects.filter(is_active=True)
    phases = ProjectPhase.objects.filter(is_active=True).select_related('project')
    requisitions = ProjectRequisition.objects.filter(is_active=True).select_related('project', 'phase')

    req_list = []
    for r in requisitions:
        req_list.append({
            'id': r.pk or str(r.pk),
            'project_id': str(r.project_id) if r.project_id else '',
            'phase_id': str(r.phase_id) if r.phase_id else '',
            'item_name': r.item_name,
            'quantity': float(r.quantity),
            'estimated_cost': float(r.estimated_cost),
            'status': r.status,
            'requisition_ref': r.requisition_ref or '',
            'project_code': r.project.project_code if r.project else '',
            'project_name': r.project.name if r.project else 'Unknown',
            'phase_name': r.phase.phase_name if r.phase else 'Unknown',
            'created_at': r.created_at.isoformat() if r.created_at else '',
        })

    phases_list = []
    for ph in phases:
        phases_list.append({
            'id': ph.pk or str(ph.pk),
            'phase_name': ph.phase_name,
            'project_id': str(ph.project_id) if ph.project_id else '',
            'budget_allocation': float(ph.budget_allocation),
            'status': ph.status,
        })

    requisitions_json = json.dumps(req_list)
    phases_json = json.dumps(phases_list)

    return render(request, 'solutions/sourcing.html', {
        'requisitions': req_list,
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
            }

            if doc_id:
                lic = _resolve(doc_id, SoftwareLicense)
                if lic:
                    for k, v in data.items():
                        setattr(lic, k, v)
                    lic.save()
                messages.success(request, "Software license details updated.")
            else:
                obj = SoftwareLicense.objects.create(**data)
                messages.success(request, "Software license registered.")

        elif action == 'delete_license' and doc_id:
            lic = _resolve(doc_id, SoftwareLicense)
            if lic:
                lic.is_active = False
                lic.save(update_fields=['is_active'])
                messages.success(request, "License record removed.")

        return redirect('solutions:licensing_assets')

    projects = Project.objects.filter(is_active=True)
    project_map = {str(p.pk): p for p in projects}

    licenses = SoftwareLicense.objects.filter(is_active=True).select_related('project')
    lic_list = []
    for l in licenses:
        lic_list.append({
            'id': l.pk or str(l.pk),
            'project_id': str(l.project_id) if l.project_id else '',
            'license_name': l.license_name,
            'license_key': l.license_key or '',
            'subscription_tier': l.subscription_tier,
            'renewal_date': str(l.renewal_date) if l.renewal_date else '',
            'cost': float(l.cost),
            'status': l.status,
            'project_code': l.project.project_code if l.project else '',
            'project_name': l.project.name if l.project else 'Unknown',
        })

    licenses_json = json.dumps(lic_list)
    return render(request, 'solutions/licensing.html', {
        'licenses': lic_list,
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
            contact_id = _get_or_create_person(contact_name, email, phone, 'client')

            data = {
                'project_id': request.POST.get('project_id'),
                'contact_name': contact_name,
                'email': email,
                'phone': phone,
                'role': request.POST.get('role', 'Primary Client Contact'),
                'contact_id': contact_id or '',
            }

            if doc_id:
                sh = _resolve(doc_id, ProjectStakeholder)
                if sh:
                    for k, v in data.items():
                        setattr(sh, k, v)
                    sh.save()
                messages.success(request, "Stakeholder contact updated.")
            else:
                obj = ProjectStakeholder.objects.create(**data)
                messages.success(request, "New Stakeholder contact registered.")

        elif action == 'delete_stakeholder' and doc_id:
            sh = _resolve(doc_id, ProjectStakeholder)
            if sh:
                sh.is_active = False
                sh.save(update_fields=['is_active'])
                messages.success(request, "Stakeholder contact removed.")

        return redirect('solutions:client_stakeholders')

    projects = Project.objects.filter(is_active=True)
    project_map = {str(p.pk): p for p in projects}

    stakeholders = ProjectStakeholder.objects.filter(is_active=True).select_related('project')
    sh_list = []
    for s in stakeholders:
        sh_list.append({
            'id': s.pk or str(s.pk),
            'project_id': str(s.project_id) if s.project_id else '',
            'contact_name': s.contact_name,
            'email': s.email or '',
            'phone': s.phone or '',
            'role': s.role,
            'contact_id': s.contact_id or '',
            'project_code': s.project.project_code if s.project else '',
            'project_name': s.project.name if s.project else 'Unknown',
        })

    stakeholders_json = json.dumps(sh_list)
    return render(request, 'solutions/stakeholders.html', {
        'stakeholders': sh_list,
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
            person = _resolve(doc_id, Person)
            if person:
                person.is_active = False
                person.save(update_fields=['is_active'])
            messages.success(request, "Global Contact record deleted successfully.")
        return redirect('solutions:global_contacts')

    contacts = Person.objects.filter(is_active=True).order_by('legal_name').values(
        'pk', 'pk', 'display_name', 'legal_name', 'email', 'phone',
        'person_type', 'roles', 'created_at',
    )
    contact_list = []
    for c in contacts:
        contact_list.append({
            'id': c.get('pk') or str(c['pk']),
            'legal_name': c.get('legal_name') or c.get('display_name') or '',
            'email': c.get('email') or '',
            'phone': c.get('phone') or '',
            'person_type': c.get('person_type') or '',
            'roles': c.get('roles') or [],
            'created_at': c['created_at'].isoformat() if c.get('created_at') else '',
        })

    contacts_json = json.dumps(contact_list)
    return render(request, 'solutions/global_contacts.html', {
        'contacts': contact_list,
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
                'agenda': request.POST.get('agenda', ''),
            }

            if doc_id:
                mtg = _resolve(doc_id, Meeting)
                if mtg:
                    for k, v in data.items():
                        setattr(mtg, k, v)
                    mtg.save()
                messages.success(request, "Meeting details updated.")
            else:
                obj = Meeting.objects.create(**data)
                messages.success(request, "New meeting scheduled.")

        elif action == 'delete_meeting' and doc_id:
            mtg = _resolve(doc_id, Meeting)
            if mtg:
                mtg.is_active = False
                mtg.save(update_fields=['is_active'])
                messages.success(request, "Meeting scheduled cancelled.")

        return redirect('solutions:meeting_scheduler')

    projects = Project.objects.filter(is_active=True)
    meetings = Meeting.objects.filter(is_active=True).select_related('project')

    meeting_list = []
    for m in meetings:
        meeting_list.append({
            'id': m.pk or str(m.pk),
            'project_id': str(m.project_id) if m.project_id else '',
            'title': m.title,
            'meeting_date': str(m.meeting_date) if m.meeting_date else '',
            'start_time': str(m.start_time) if m.start_time else '',
            'video_link': m.video_link or '',
            'agenda': m.agenda or '',
            'project_code': m.project.project_code if m.project else '',
            'project_name': m.project.name if m.project else 'Unknown',
        })

    meetings_json = json.dumps(meeting_list)
    return render(request, 'solutions/meetings.html', {
        'meetings': meeting_list,
        'projects': projects,
        'meetings_json': meetings_json
    })
