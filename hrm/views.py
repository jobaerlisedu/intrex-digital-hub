from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from config.firebase import db
from google.cloud import firestore
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from accounts.decorators import module_access
from config.services.integration_service import IntegrationService
from config.workflow_integration import ensure_workflow, try_transition, LEAVE_TRIGGER_MAP
from config.logger import hrm_logger
import random

# Helper to get Firestore collection data or fallback to sample lists (no cache)
def get_collection_data(collection_name, default_data):
    try:
        docs = db.collection(collection_name).order_by('createdAt', direction=firestore.Query.DESCENDING).stream()
        results = []
        for doc in docs:
            item = doc.to_dict()
            item['id'] = doc.id
            results.append(item)
        if not results:
            return default_data
        return results
    except Exception as e:
        hrm_logger.error(f"Error fetching {collection_name}: {e}")
        return default_data

# Cached helper for slow-changing reference data (departments, positions, etc.)
# Cache timeout: 60 seconds. Call cache.clear() or cache.delete(key) after writes.
def get_cached_collection(collection_name, default_data=None, timeout=60):
    if default_data is None:
        default_data = []
    cache_key = f'firestore_{collection_name}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    data = get_collection_data(collection_name, default_data)
    cache.set(cache_key, data, timeout)
    return data

def invalidate_cache(collection_name):
    """Call this after any write to a cached collection."""
    cache.delete(f'firestore_{collection_name}')

@module_access('hrm')
def index(request):
    # HR Overview / Dashboard
    try:
        employees = list(db.collection('hrm_employees').stream())
        positions = list(db.collection('org_positions').stream())

        total_emp = len(employees)
        active_emp = len([e for e in employees if (e.to_dict() or {}).get('status') == 'Active'])
        leave_emp = len([e for e in employees if (e.to_dict() or {}).get('status') == 'On Leave'])
        open_positions = len(positions)
        
        # Calculate pending approvals
        pending_leaves = len(list(db.collection('hrm_leaves').where('status', '==', 'Pending').stream()))
        pending_advances = len(list(db.collection('hrm_advances').where('status', '==', 'Pending').stream()))
        pending_claims = len(list(db.collection('hrm_expense_claims').where('status', '==', 'Pending').stream()))
        pending_approvals = pending_leaves + pending_advances + pending_claims

        # Calculate absenteeism rate
        from datetime import datetime
        today_str = datetime.now().strftime('%Y-%m-%d')
        today_att = [a.to_dict() or {} for a in db.collection('hrm_attendance').where('date', '==', today_str).stream()]
        absent_count = sum(1 for a in today_att if a.get('status') == 'Absent')
        total_att = len(today_att)
        absenteeism_rate = round((absent_count / total_att * 100), 1) if total_att > 0 else 0.0
        
        recent_activities = [
            f"Employee database check completed.",
            f"Dashboard metrics refreshed.",
        ]
        if pending_approvals > 0:
            recent_activities.append(f"There are {pending_approvals} requests pending manager approval.")
    except Exception as e:
        hrm_logger.error(f"Error loading dashboard: {e}")
        total_emp, active_emp, leave_emp, open_positions = 0, 0, 0, 0
        pending_approvals = 0
        absenteeism_rate = 0.0
        recent_activities = []

    context = {
        'total_employees': total_emp,
        'active_employees': active_emp,
        'employees_on_leave': leave_emp,
        'open_positions': open_positions,
        'pending_approvals': pending_approvals,
        'absenteeism_rate': absenteeism_rate,
        'recent_activities': recent_activities
    }
    return render(request, 'hrm/overview.html', context)

@module_access('hrm')
def recruitment(request):

    # Handle form submissions
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # 1. Add Candidate
        if action == 'add_candidate':
            try:
                doc_id = request.POST.get('doc_id')
                from datetime import datetime
                today_str = datetime.now().strftime('%Y-%m-%d')
                date_applied = request.POST.get('date_applied') or today_str
                
                update_data = {
                    'name': request.POST.get('name'),
                    'position': request.POST.get('position'),
                    'status': request.POST.get('status', 'New'),
                    'notes': request.POST.get('notes', ''),
                    'date_applied': date_applied,
                }
                
                if doc_id:
                    db.collection('hrm_recruitment_candidates').document(doc_id).update(update_data)
                    messages.success(request, "Candidate profile updated successfully.")
                else:
                    cand_id = f"CAN-{random.randint(100, 999)}"
                    update_data['cand_id'] = cand_id
                    update_data['createdAt'] = firestore.SERVER_TIMESTAMP
                    db.collection('hrm_recruitment_candidates').add(update_data)
                    messages.success(request, "Candidate profile registered successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding candidate: {e}")
                
        # 2. Add to Shortlist
        elif action == 'add_shortlist':
            cand_doc_id = request.POST.get('candidate_id')
            rating = request.POST.get('rating')
            experience = request.POST.get('experience')
            
            if cand_doc_id:
                try:
                    cand_name, cand_position = None, None
                    cand_ref = db.collection('hrm_recruitment_candidates').document(cand_doc_id)
                    cand_doc = cand_ref.get()
                    if cand_doc.exists:
                        cand_name = cand_doc.to_dict().get('name')
                        cand_position = cand_doc.to_dict().get('position')
                        cand_ref.update({'status': 'Shortlisted'})
                            
                    if cand_name:
                        doc_id = request.POST.get('doc_id')
                        if doc_id:
                            update_data = {
                            'candidate_id': cand_doc_id,
                            'name': cand_name,
                            'position': cand_position,
                            'rating': rating,
                            'experience': experience,
                            'createdAt': firestore.SERVER_TIMESTAMP
                        }
                            if 'createdAt' in update_data:
                                del update_data['createdAt']
                            db.collection('hrm_recruitment_shortlists').document(doc_id).update(update_data)
                            messages.success(request, "Shortlist details updated successfully.")
                        else:
                            db.collection('hrm_recruitment_shortlists').add({
                            'candidate_id': cand_doc_id,
                            'name': cand_name,
                            'position': cand_position,
                            'rating': rating,
                            'experience': experience,
                            'createdAt': firestore.SERVER_TIMESTAMP
                        })
                            messages.success(request, "Candidate added to shortlist successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error adding shortlist candidate: {e}")
                    
        # 3. Schedule Interview
        elif action == 'add_interview':
            cand_doc_id = request.POST.get('candidate_id')
            interviewer = request.POST.get('interviewer')
            date_time = request.POST.get('date_time')
            status = request.POST.get('status', 'Scheduled')
            
            if cand_doc_id:
                try:
                    cand_name, cand_position = None, None
                    cand_ref = db.collection('hrm_recruitment_candidates').document(cand_doc_id)
                    cand_doc = cand_ref.get()
                    if cand_doc.exists:
                        cand_name = cand_doc.to_dict().get('name')
                        cand_position = cand_doc.to_dict().get('position')
                        cand_ref.update({'status': 'Interview'})
                            
                    if cand_name:
                        doc_id = request.POST.get('doc_id')
                        if doc_id:
                            update_data = {
                            'candidate_id': cand_doc_id,
                            'name': cand_name,
                            'position': cand_position,
                            'interviewer': interviewer,
                            'date_time': date_time,
                            'status': status,
                            'createdAt': firestore.SERVER_TIMESTAMP
                        }
                            if 'createdAt' in update_data:
                                del update_data['createdAt']
                            db.collection('hrm_recruitment_interviews').document(doc_id).update(update_data)
                            messages.success(request, "Interview schedule updated successfully.")
                        else:
                            db.collection('hrm_recruitment_interviews').add({
                            'candidate_id': cand_doc_id,
                            'name': cand_name,
                            'position': cand_position,
                            'interviewer': interviewer,
                            'date_time': date_time,
                            'status': status,
                            'createdAt': firestore.SERVER_TIMESTAMP
                        })
                            messages.success(request, "Interview scheduled successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error scheduling interview: {e}")
                    
        # 4. Make Selection
        elif action == 'add_selection':
            cand_doc_id = request.POST.get('candidate_id')
            offer_status = request.POST.get('offer_status')
            offer_date = request.POST.get('offer_date')
            
            if cand_doc_id:
                try:
                    cand_name, cand_position = None, None
                    cand_ref = db.collection('hrm_recruitment_candidates').document(cand_doc_id)
                    cand_doc = cand_ref.get()
                    if cand_doc.exists:
                        cand_name = cand_doc.to_dict().get('name')
                        cand_position = cand_doc.to_dict().get('position')
                        new_status = 'Selected' if offer_status in ['Offered', 'Accepted', 'Joined'] else 'Rejected'
                        cand_ref.update({'status': new_status})
                            
                    if cand_name:
                        doc_id = request.POST.get('doc_id')
                        if doc_id:
                            update_data = {
                            'candidate_id': cand_doc_id,
                            'name': cand_name,
                            'position': cand_position,
                            'offer_status': offer_status,
                            'offer_date': offer_date,
                            'createdAt': firestore.SERVER_TIMESTAMP
                        }
                            if 'createdAt' in update_data:
                                del update_data['createdAt']
                            db.collection('hrm_recruitment_selections').document(doc_id).update(update_data)
                            messages.success(request, "Selection details updated successfully.")
                        else:
                            db.collection('hrm_recruitment_selections').add({
                            'candidate_id': cand_doc_id,
                            'name': cand_name,
                            'position': cand_position,
                            'offer_status': offer_status,
                            'offer_date': offer_date,
                            'createdAt': firestore.SERVER_TIMESTAMP
                        })
                            messages.success(request, "Selection decision logged successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error saving selection: {e}")
                    
        # 5. Delete Actions
        elif action.startswith('delete_'):
            col_name = action.replace('delete_', 'hrm_recruitment_')
            if col_name == 'hrm_recruitment_candidate':
                col_name = 'hrm_recruitment_candidates'
            elif col_name == 'hrm_recruitment_shortlist':
                col_name = 'hrm_recruitment_shortlists'
            elif col_name == 'hrm_recruitment_interview':
                col_name = 'hrm_recruitment_interviews'
            elif col_name == 'hrm_recruitment_selection':
                col_name = 'hrm_recruitment_selections'
                
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection(col_name).document(doc_id).delete()
                    messages.success(request, "Record deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting doc from {col_name}: {e}")
                    
        # 6. Inline Update Status
        elif action == 'update_status':
            doc_id = request.POST.get('doc_id')
            new_status = request.POST.get('status')
            if doc_id and new_status:
                try:
                    db.collection('hrm_recruitment_candidates').document(doc_id).update({'status': new_status})
                    messages.success(request, f"Candidate status updated to {new_status}.")
                except Exception as e:
                    hrm_logger.error(f"Error updating status: {e}")
                    
        return redirect('hrm:recruitment')

    # Fetch data from collections
    # Transactional data fetched fresh; positions cached (rarely changes)
    candidates = get_collection_data('hrm_recruitment_candidates', [])
    shortlists = get_collection_data('hrm_recruitment_shortlists', [])
    interviews = get_collection_data('hrm_recruitment_interviews', [])
    selections = get_collection_data('hrm_recruitment_selections', [])
    positions_data = get_cached_collection('org_positions')
    departments = get_cached_collection('org_departments')
    sub_departments = get_cached_collection('org_departments_sub')

    positions = []
    for p in positions_data:
        title = p.get('title') or p.get('name')
        if title:
            positions.append({
                'title': title,
                'dept_name': p.get('dept_name', ''),
                'sub_dept_name': p.get('sub_dept_name', '')
            })

    return render(request, 'hrm/recruitment.html', {
        'candidates': candidates,
        'shortlists': shortlists,
        'interviews': interviews,
        'selections': selections,
        'positions': positions,
        'departments': departments,
        'sub_departments': sub_departments
    })

@module_access('hrm')
def department(request):
    # Default lists for fallback (only used when Firestore IDs start with 'sample-')
    default_departments = []
    default_sub_departments = []

    # Handle form submissions
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # 1. Add Department
        if action == 'add_department':
            try:
                doc_id = request.POST.get('doc_id')
                if doc_id:
                    update_data = {
                    'name': request.POST.get('name'),
                    'status': request.POST.get('status', 'Active'),
                    'module_linking': request.POST.getlist('module_linking'),
                    'notes': request.POST.get('notes', ''),
                    'createdAt': firestore.SERVER_TIMESTAMP
                }
                    if 'createdAt' in update_data:
                        del update_data['createdAt']
                    db.collection('org_departments').document(doc_id).update(update_data)
                    messages.success(request, "Department updated successfully.")
                else:
                    db.collection('org_departments').add({
                    'name': request.POST.get('name'),
                    'status': request.POST.get('status', 'Active'),
                    'module_linking': request.POST.getlist('module_linking'),
                    'notes': request.POST.get('notes', ''),
                    'createdAt': firestore.SERVER_TIMESTAMP
                })
                    messages.success(request, "Department added successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding department: {e}")
                
        # 2. Add Sub Department
        elif action == 'add_sub_department':
            parent_id = request.POST.get('parent_id')
            name = request.POST.get('name')
            status = request.POST.get('status', 'Active')
            notes = request.POST.get('notes', '')
            
            if parent_id:
                try:
                    parent_name = None
                    if parent_id.startswith('sample-'):
                        for d in default_departments:
                            if d['id'] == parent_id:
                                parent_name = d['name']
                                break
                    else:
                        dept_doc = db.collection('org_departments').document(parent_id).get()
                        if dept_doc.exists:
                            parent_name = dept_doc.to_dict().get('name')
                            
                    if parent_name:
                        doc_id = request.POST.get('doc_id')
                        if doc_id:
                            update_data = {
                            'name': name,
                            'parent_id': parent_id,
                            'parent_name': parent_name,
                            'status': status,
                            'notes': notes,
                            'createdAt': firestore.SERVER_TIMESTAMP
                        }
                            if 'createdAt' in update_data:
                                del update_data['createdAt']
                            db.collection('org_departments_sub').document(doc_id).update(update_data)
                            messages.success(request, "Sub-department updated successfully.")
                        else:
                            db.collection('org_departments_sub').add({
                            'name': name,
                            'parent_id': parent_id,
                            'parent_name': parent_name,
                            'status': status,
                            'notes': notes,
                            'createdAt': firestore.SERVER_TIMESTAMP
                        })
                            messages.success(request, "Sub-department added successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error adding sub department: {e}")
                    
        elif action == 'add_position':
            dept_id = request.POST.get('dept_id')
            sub_dept_id = request.POST.get('sub_dept_id', '')
            title = request.POST.get('title')
            status = request.POST.get('status', 'Active')
            
            if dept_id:
                try:
                    dept_name = None
                    sub_dept_name = "None"
                    
                    # Resolve department
                    if dept_id.startswith('sample-'):
                        for d in default_departments:
                            if d['id'] == dept_id:
                                dept_name = d['name']
                                break
                    else:
                        dept_doc = db.collection('org_departments').document(dept_id).get()
                        if dept_doc.exists:
                            dept_name = dept_doc.to_dict().get('name')
                            
                    # Resolve sub department
                    if sub_dept_id:
                        if sub_dept_id.startswith('sample-'):
                            for sd in default_sub_departments:
                                if sd['id'] == sub_dept_id:
                                    sub_dept_name = sd['name']
                                    break
                        else:
                            sub_dept_doc = db.collection('org_departments_sub').document(sub_dept_id).get()
                            if sub_dept_doc.exists:
                                sub_dept_name = sub_dept_doc.to_dict().get('name')
                    else:
                        sub_dept_id = ""
                        sub_dept_name = "None"
                            
                    if dept_name:
                        doc_id = request.POST.get('doc_id')
                        if doc_id:
                            update_data = {
                                'title': title,
                                'dept_id': dept_id,
                                'dept_name': dept_name,
                                'sub_dept_id': sub_dept_id,
                                'sub_dept_name': sub_dept_name,
                                'status': status,
                                'createdAt': firestore.SERVER_TIMESTAMP
                            }
                            if 'createdAt' in update_data:
                                del update_data['createdAt']
                            db.collection('org_positions').document(doc_id).update(update_data)
                            messages.success(request, "Job position updated successfully.")
                        else:
                            db.collection('org_positions').add({
                                'title': title,
                                'dept_id': dept_id,
                                'dept_name': dept_name,
                                'sub_dept_id': sub_dept_id,
                                'sub_dept_name': sub_dept_name,
                                'status': status,
                                'createdAt': firestore.SERVER_TIMESTAMP
                            })
                            messages.success(request, "Job position added successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error adding position: {e}")
                    
        # 4. Delete Action
        elif action.startswith('delete_'):
            col_name = action.replace('delete_', 'org_')
            if col_name == 'org_department':
                col_name = 'org_departments'
            elif col_name == 'org_sub_department':
                col_name = 'org_departments_sub'
            elif col_name == 'org_position':
                col_name = 'org_positions'
                
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection(col_name).document(doc_id).delete()
                    messages.success(request, "Record deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting doc from {col_name}: {e}")
                    
        # Invalidate caches so next load reflects the write
        invalidate_cache('org_departments')
        invalidate_cache('org_departments_sub')
        invalidate_cache('org_positions')
        return redirect('hrm:department')

    # Fetch lists — use cache for slow-changing reference data
    departments = get_cached_collection('org_departments')
    # Normalize module_linking to always be a list of strings
    for d in departments:
        linking = d.get('module_linking', [])
        if isinstance(linking, str):
            d['module_linking'] = [linking] if linking else []
        elif not isinstance(linking, list):
            d['module_linking'] = []

    sub_departments = get_cached_collection('org_departments_sub')
    positions = get_cached_collection('org_positions')

    return render(request, 'hrm/departments.html', {
        'departments': departments,
        'sub_departments': sub_departments,
        'positions': positions
    })

@module_access('hrm')
def employee_database(request):
    # Default data mirroring department defaults for dropdowns

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'delete_employee':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection('hrm_employees').document(doc_id).delete()
                    messages.success(request, "Employee record deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting employee: {e}")
            return redirect('hrm:employee_database')

        # Full 4-step form submission
        try:
            doc_id = request.POST.get('doc_id')

            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            full_name = f"{first_name} {last_name}".strip()

            email = request.POST.get('email', '')
            phone = request.POST.get('phone', '')
            from config.contacts_helper import get_or_create_contact
            contact_id = get_or_create_contact(name=full_name, email=email, phone=phone, role='employee')

            # Salary calculations
            basic_salary = float(request.POST.get('basic_salary') or 0)
            house_rent = round(basic_salary * 0.50, 2)
            medical = round(basic_salary * 0.20, 2)
            conveyance = round(basic_salary * 0.20, 2)
            utility = round(basic_salary * 0.10, 2)
            mobile_bill = float(request.POST.get('mobile_bill') or 1000)
            gross_salary = round(basic_salary + house_rent + medical + conveyance + utility + mobile_bill, 2)

            # Additional Roles
            additional_depts = request.POST.getlist('additional_dept')
            additional_subdepts = request.POST.getlist('additional_subdept')
            additional_positions = request.POST.getlist('additional_position')
            additional_roles = []
            for d, sd, p in zip(additional_depts, additional_subdepts, additional_positions):
                if d and p:
                    additional_roles.append({
                        'department': d,
                        'sub_department': sd or '',
                        'position': p
                    })

            data = {
                'name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
                'alt_phone': request.POST.get('alt_phone', ''),
                'national_id': request.POST.get('national_id', ''),
                'city': request.POST.get('city', ''),
                'zip': request.POST.get('zip', ''),
                # Bank
                'account_holder': request.POST.get('account_holder', ''),
                'account_number': request.POST.get('account_number', ''),
                'branch_name': request.POST.get('branch_name', ''),
                'bank_name': request.POST.get('bank_name', ''),
                # Salary
                'basic_salary': basic_salary,
                'house_rent': house_rent,
                'medical_allowance': medical,
                'conveyance_allowance': conveyance,
                'utility': utility,
                'mobile_bill': mobile_bill,
                'gross_salary': gross_salary,
                # Personal Info
                'department': request.POST.get('department', ''),
                'sub_department': request.POST.get('sub_department', ''),
                'position': request.POST.get('position', ''),
                'additional_roles': additional_roles,
                'employee_type': request.POST.get('employee_type', 'Permanent'),
                'joining_date': request.POST.get('joining_date', ''),
                'status': request.POST.get('employment_status', 'Active'),
                'exit_date': request.POST.get('exit_date', ''),
                'exit_type': request.POST.get('exit_type', ''),
                'exit_reason': request.POST.get('exit_reason', ''),
                # Biological
                'dob': request.POST.get('dob', ''),
                'gender': request.POST.get('gender', ''),
                'marital_status': request.POST.get('marital_status', ''),
                'religion': request.POST.get('religion', ''),
                # Emergency
                'ec_primary_name': request.POST.get('ec_primary_name', ''),
                'ec_primary_relation': request.POST.get('ec_primary_relation', ''),
                'ec_primary_mobile': request.POST.get('ec_primary_mobile', ''),
                'ec_secondary_name': request.POST.get('ec_secondary_name', ''),
                'ec_secondary_relation': request.POST.get('ec_secondary_relation', ''),
                'ec_secondary_mobile': request.POST.get('ec_secondary_mobile', ''),
                'contact_id': contact_id
            }

            if doc_id:
                # Update existing employee
                db.collection('hrm_employees').document(doc_id).update(data)
                data['id'] = doc_id
                messages.success(request, "Employee profile updated successfully.")
            else:
                # Generate new emp_id and add employee
                existing = db.collection('hrm_employees').stream()
                count = sum(1 for _ in existing) + 1
                data['emp_id'] = f"EMP-{count:04d}"
                data['createdAt'] = firestore.SERVER_TIMESTAMP
                _, new_ref = db.collection('hrm_employees').add(data)
                data['id'] = new_ref.id
                messages.success(request, "Employee profile registered successfully.")

            # Sync employee to unified registry and auto-provision auth user
            try:
                IntegrationService.employee_to_user_registry(data)
            except Exception as e:
                hrm_logger.error(f"Error syncing employee to registry: {e}")
        except Exception as e:
            hrm_logger.error(f"Error saving employee: {e}")
        return redirect('hrm:employee_database')

    # Fetch employees list
    try:
        docs = db.collection('hrm_employees').stream()
        employees = []
        for doc in docs:
            emp = doc.to_dict()
            emp['id'] = doc.id
            employees.append(emp)
    except Exception as e:
        hrm_logger.error(f"Error fetching employees: {e}")
        employees = []

    # Use cached reference data for dropdowns
    departments = get_cached_collection('org_departments')
    sub_departments = get_cached_collection('org_departments_sub')
    positions = get_cached_collection('org_positions')

    return render(request, 'hrm/employee_database.html', {
        'employees': employees,
        'departments': departments,
        'sub_departments': sub_departments,
        'positions': positions
    })

@module_access('hrm')
def attendance(request):

    if request.method == 'POST':
        att_action = request.POST.get('att_action')

        if att_action == 'delete':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection('hrm_attendance').document(doc_id).delete()
                    messages.success(request, "Attendance record deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting attendance: {e}")

        elif att_action == 'resolve_missing':
            try:
                data = {
                    'name': request.POST.get('missing_name'),
                    'date': request.POST.get('missing_date'),
                    'status': request.POST.get('corrected_status', 'Present'),
                    'check_in': '',
                    'check_out': '',
                    'resolved': True,
                    'createdAt': firestore.SERVER_TIMESTAMP
                }
                db.collection('hrm_attendance').add(data)
                messages.success(request, "Missing attendance resolved successfully.")
            except Exception as e:
                hrm_logger.error(f"Error resolving missing attendance: {e}")

        else:  # record
            try:
                att_data = {
                    'name': request.POST.get('name'),
                    'date': request.POST.get('date'),
                    'check_in': request.POST.get('check_in', ''),
                    'check_out': request.POST.get('check_out', ''),
                    'status': request.POST.get('status', 'Present'),
                    'createdAt': firestore.SERVER_TIMESTAMP
                }
                db.collection('hrm_attendance').add(att_data)
                messages.success(request, "Attendance record logged successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding attendance log: {e}")

        return redirect('hrm:attendance')

    logs = get_collection_data('hrm_attendance', [])

    # Fetch employees for dropdown
    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': d.to_dict().get('name', '')} for d in emp_docs if d.to_dict().get('name')]
    except Exception:
        employees = []

    # Missing logs = employees with Absent status (placeholder)
    missing_logs = [l for l in logs if l.get('status') == 'Absent']

    return render(request, 'hrm/attendance.html', {
        'logs': logs,
        'employees': employees,
        'missing_logs': missing_logs
    })

@module_access('hrm')
def leave(request):

    if request.method == 'POST':
        lv_action = request.POST.get('lv_action')

        if lv_action == 'add_holiday':
            try:
                doc_id = request.POST.get('doc_id')
                if doc_id:
                    update_data = {
                    'holiday_name': request.POST.get('holiday_name'),
                    'from_date': request.POST.get('from_date'),
                    'to_date': request.POST.get('to_date'),
                    'type': request.POST.get('holiday_type', 'Public'),
                    'createdAt': firestore.SERVER_TIMESTAMP
                }
                    if 'createdAt' in update_data:
                        del update_data['createdAt']
                    db.collection('hrm_holidays').document(doc_id).update(update_data)
                    messages.success(request, "Holiday updated successfully.")
                else:
                    db.collection('hrm_holidays').add({
                    'holiday_name': request.POST.get('holiday_name'),
                    'from_date': request.POST.get('from_date'),
                    'to_date': request.POST.get('to_date'),
                    'type': request.POST.get('holiday_type', 'Public'),
                    'createdAt': firestore.SERVER_TIMESTAMP
                })
                    messages.success(request, "Holiday added successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding holiday: {e}")

        elif lv_action == 'delete_holiday':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection('hrm_holidays').document(doc_id).delete()
                    messages.success(request, "Holiday deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting holiday: {e}")

        elif lv_action == 'apply_leave':
            try:
                from_date = request.POST.get('from_date', '')
                to_date = request.POST.get('to_date', '')
                # Calculate duration
                try:
                    from datetime import date as dt
                    fd = dt.fromisoformat(from_date)
                    td = dt.fromisoformat(to_date)
                    days = (td - fd).days + 1
                    duration = f"{days} Day{'s' if days != 1 else ''}"
                except Exception:
                    duration = request.POST.get('duration', '')
                doc_id = request.POST.get('doc_id')
                if doc_id:
                    update_data = {
                    'name': request.POST.get('emp_name'),
                    'type': request.POST.get('leave_type'),
                    'from_date': from_date,
                    'to_date': to_date,
                    'duration': duration,
                    'reason': request.POST.get('reason', ''),
                    'status': 'Pending',
                    'createdAt': firestore.SERVER_TIMESTAMP
                }
                    if 'createdAt' in update_data:
                        del update_data['createdAt']
                    db.collection('hrm_leaves').document(doc_id).update(update_data)
                    emp_name = request.POST.get('emp_name', '')
                    ensure_workflow('hrm', 'leave', doc_id, entity_label=emp_name, request=request)
                    messages.success(request, "Leave request updated successfully.")
                else:
                    _, new_ref = db.collection('hrm_leaves').add({
                    'name': request.POST.get('emp_name'),
                    'type': request.POST.get('leave_type'),
                    'from_date': from_date,
                    'to_date': to_date,
                    'duration': duration,
                    'reason': request.POST.get('reason', ''),
                    'status': 'Pending',
                    'createdAt': firestore.SERVER_TIMESTAMP
                })
                    doc_id = new_ref.id
                    emp_name = request.POST.get('emp_name', '')
                    ensure_workflow('hrm', 'leave', doc_id, entity_label=emp_name, request=request)
                    messages.success(request, "Leave request submitted successfully.")
            except Exception as e:
                hrm_logger.error(f"Error applying leave: {e}")

        elif lv_action in ('Approved', 'Rejected'):
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection('hrm_leaves').document(doc_id).update({'status': lv_action})
                    ensure_workflow('hrm', 'leave', doc_id, request=request)
                    trigger = LEAVE_TRIGGER_MAP.get(lv_action)
                    if trigger:
                        try_transition('hrm', 'leave', doc_id, trigger, request=request)
                    messages.success(request, f"Leave request status updated to {lv_action}.")
                except Exception as e:
                    hrm_logger.error(f"Error updating leave: {e}")

        elif lv_action == 'delete_leave':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection('hrm_leaves').document(doc_id).delete()
                    messages.success(request, "Leave request deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting leave: {e}")

        elif lv_action == 'save_weekend':
            weekend_days = request.POST.getlist('weekend_days')
            try:
                db.collection('hrm_settings').document('weekend').set({'days': weekend_days})
                messages.success(request, "Weekend settings saved successfully.")
            except Exception as e:
                hrm_logger.error(f"Error saving weekend: {e}")

        return redirect('hrm:leave')

    # Fetch data — real-time for transactional records
    holidays = get_collection_data('hrm_holidays', [])
    leaves = get_collection_data('hrm_leaves', [])

    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': d.to_dict().get('name', '')} for d in emp_docs if d.to_dict().get('name')]
    except Exception:
        employees = []

    try:
        ws_doc = db.collection('hrm_settings').document('weekend').get()
        weekend_days = ws_doc.to_dict().get('days', ['Saturday', 'Sunday']) if ws_doc.exists else ['Saturday', 'Sunday']
    except Exception:
        weekend_days = ['Saturday', 'Sunday']

    try:
        from .models import LeaveBalance, Employee
        emp_balances = []
        for emp in employees:
            emp_obj = Employee.objects.filter(name=emp['name']).first()
            if emp_obj:
                balances = LeaveBalance.objects.filter(employee=emp_obj, is_active=True)
                emp_balances.append({
                    'name': emp['name'],
                    'balances': [
                        {'leave_type': b.leave_type, 'entitled': b.entitled, 'used': b.used, 'pending': b.pending, 'available': b.available}
                        for b in balances
                    ]
                })
    except Exception:
        emp_balances = []

    return render(request, 'hrm/leave.html', {
        'holidays': holidays,
        'leaves': leaves,
        'employees': employees,
        'weekend_days': weekend_days,
        'all_days': ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
        'emp_balances': emp_balances,
    })

@module_access('hrm')
def payroll(request):

    if request.method == 'POST':
        pr_action = request.POST.get('pr_action')

        if pr_action == 'add_advance':
            try:
                doc_id = request.POST.get('doc_id')
                if doc_id:
                    update_data = {
                    'employee': request.POST.get('employee'),
                    'amount': float(request.POST.get('amount', 0)),
                    'deduct_month': request.POST.get('deduct_month'),
                    'reason': request.POST.get('reason', ''),
                    'status': 'Pending',
                    'createdAt': firestore.SERVER_TIMESTAMP
                }
                    if 'createdAt' in update_data:
                        del update_data['createdAt']
                    db.collection('hrm_advances').document(doc_id).update(update_data)
                    messages.success(request, "Advance salary request updated successfully.")
                else:
                    db.collection('hrm_advances').add({
                    'employee': request.POST.get('employee'),
                    'amount': float(request.POST.get('amount', 0)),
                    'deduct_month': request.POST.get('deduct_month'),
                    'reason': request.POST.get('reason', ''),
                    'status': 'Pending',
                    'createdAt': firestore.SERVER_TIMESTAMP
                })
                    messages.success(request, "Advance salary request filed successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding advance salary: {e}")

        elif pr_action == 'delete_advance':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection('hrm_advances').document(doc_id).delete()
                    messages.success(request, "Advance salary request deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting advance: {e}")

        elif pr_action == 'generate_salary':
            month = request.POST.get('month')
            year = request.POST.get('year')
            period = f"{month} {year}"
            
            months_map = {
                'January': '01', 'February': '02', 'March': '03', 'April': '04',
                'May': '05', 'June': '06', 'July': '07', 'August': '08',
                'September': '09', 'October': '10', 'November': '11', 'December': '12'
            }
            month_num = months_map.get(month, '01')
            target_period = f"{year}-{month_num}"
            
            try:
                # Calculate real totals from the employees collection
                emp_docs = list(db.collection('hrm_employees').stream())
                active_employees = [e.to_dict() for e in emp_docs if e.to_dict().get('status') == 'Active']
                employee_count = len(active_employees)
                
                total_net_pay = 0.0
                for emp in active_employees:
                    emp_name = emp.get('name')
                    basic_salary = float(emp.get('basic_salary', 0))
                    gross_salary = float(emp.get('gross_salary', 0))
                    
                    # Count absent days
                    absent_count = 0
                    att_docs = db.collection('hrm_attendance').where('name', '==', emp_name).stream()
                    for doc in att_docs:
                        data = doc.to_dict()
                        if data.get('date', '').startswith(target_period) and data.get('status') == 'Absent':
                            absent_count += 1
                    
                    daily_rate = basic_salary / 30.0 if basic_salary > 0 else 0.0
                    absent_deduction = round(daily_rate * absent_count, 2)
                    
                    # Find advances
                    advance_deduction = 0.0
                    adv_docs = db.collection('hrm_advances').where('employee', '==', emp_name).where('deduct_month', '==', target_period).stream()
                    for doc in adv_docs:
                        advance_deduction += float(doc.to_dict().get('amount', 0))
                        
                    # Tax deduction (5% of basic salary)
                    tax_deduction = round(basic_salary * 0.05, 2)
                    
                    net_pay = round(gross_salary - absent_deduction - advance_deduction - tax_deduction, 2)
                    if net_pay < 0:
                        net_pay = 0.0
                        
                    total_net_pay += net_pay
                
                total_net_pay = round(total_net_pay, 2)

                doc_id = request.POST.get('doc_id')
                payload = {
                    'period': period,
                    'employee_count': employee_count,
                    'total_net_pay': total_net_pay,
                    'status': 'Generated',
                }
                if doc_id:
                    db.collection('hrm_payrolls').document(doc_id).update(payload)
                    messages.success(request, "Payroll sheet updated/recalculated successfully.")
                else:
                    payload['createdAt'] = firestore.SERVER_TIMESTAMP
                    db.collection('hrm_payrolls').add(payload)
                    messages.success(request, "Payroll sheet generated successfully.")
            except Exception as e:
                hrm_logger.error(f"Error generating payroll: {e}")

        elif pr_action == 'delete_payroll':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection('hrm_payrolls').document(doc_id).delete()
                    messages.success(request, "Payroll sheet deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting payroll: {e}")

        elif pr_action == 'disburse_payroll':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    from datetime import datetime
                    pr_ref = db.collection('hrm_payrolls').document(doc_id)
                    pr_data = pr_ref.get().to_dict()
                    if pr_data and pr_data.get('status') != 'Disbursed':
                        pr_ref.update({'status': 'Disbursed'})
                        
                        total_net_pay = float(pr_data.get('total_net_pay', 0.0))
                        period = pr_data.get('period', '')
                        
                        coa_exp = list(db.collection('fin_chart_of_accounts').where('account_code', '==', '51000').stream())
                        coa_cash = list(db.collection('fin_chart_of_accounts').where('account_code', '==', '11100').stream())
                        
                        exp_id = coa_exp[0].id if coa_exp else '51000_fallback'
                        cash_id = coa_cash[0].id if coa_cash else '11100_fallback'
                        
                        lines = [
                            {'account_id': exp_id, 'debit_amount': total_net_pay, 'credit_amount': 0.0},
                            {'account_id': cash_id, 'debit_amount': 0.0, 'credit_amount': total_net_pay}
                        ]
                        
                        je_data = {
                            'entry_code': f"AUTO-PAYROLL-{datetime.now().strftime('%Y%m%d')}",
                            'posting_date': datetime.now().strftime('%Y-%m-%d'),
                            'reference_document': f"Payroll {period}",
                            'narration': f"Automated posting of net pay for period {period}",
                            'status': 'Posted',
                            'created_by': 'System',
                            'approved_by': request.user.username if request.user else 'System',
                            'lines': lines,
                            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        db.collection('fin_journal_entries').add(je_data)
                        messages.success(request, "Payroll disbursed and journal entries posted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error disbursing payroll: {e}")

        return redirect('hrm:payroll')

    # Fetch data — transactional, always fresh
    advances = get_collection_data('hrm_advances', [])
    payrolls = get_collection_data('hrm_payrolls', [])

    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': d.to_dict().get('name', '')} for d in emp_docs if d.to_dict().get('name')]
    except Exception:
        employees = []

    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    from datetime import datetime
    current_year = datetime.now().year
    years = [current_year - 1, current_year, current_year + 1]

    return render(request, 'hrm/payroll.html', {
        'advances': advances,
        'payrolls': payrolls,
        'employees': employees,
        'months': months,
        'years': years
    })

@login_required
@module_access('hrm')
def get_payslip(request):
    emp_name = request.GET.get('employee')
    month_name = request.GET.get('month')
    year = request.GET.get('year')
    
    if not emp_name or not month_name or not year:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
        
    months_map = {
        'January': '01', 'February': '02', 'March': '03', 'April': '04',
        'May': '05', 'June': '06', 'July': '07', 'August': '08',
        'September': '09', 'October': '10', 'November': '11', 'December': '12'
    }
    month_num = months_map.get(month_name)
    if not month_num:
        return JsonResponse({'error': 'Invalid month'}, status=400)
        
    target_period = f"{year}-{month_num}"
    
    try:
        # 1. Fetch employee
        emp_query = list(db.collection('hrm_employees').where('name', '==', emp_name).stream())
        if not emp_query:
            return JsonResponse({'error': 'Employee not found'}, status=404)
        emp_data = emp_query[0].to_dict()
        
        basic_salary = float(emp_data.get('basic_salary', 0))
        house_rent = float(emp_data.get('house_rent', 0))
        medical_allowance = float(emp_data.get('medical_allowance', 0))
        gross_salary = float(emp_data.get('gross_salary', 0))
        
        # 2. Count absent days from hrm_attendance
        absent_count = 0
        att_docs = db.collection('hrm_attendance').where('name', '==', emp_name).stream()
        for doc in att_docs:
            data = doc.to_dict()
            att_date = data.get('date', '')
            status = data.get('status', '')
            if att_date.startswith(target_period) and status == 'Absent':
                absent_count += 1
                
        # Calculate absent deduction: (basic_salary / 30) * absent_count
        daily_rate = basic_salary / 30.0 if basic_salary > 0 else 0.0
        absent_deduction = round(daily_rate * absent_count, 2)
        
        # 3. Fetch advances for this month
        advance_deduction = 0.0
        adv_docs = db.collection('hrm_advances').where('employee', '==', emp_name).where('deduct_month', '==', target_period).stream()
        for doc in adv_docs:
            data = doc.to_dict()
            advance_deduction += float(data.get('amount', 0))
            
        # Tax deduction (5% of basic salary)
        tax_deduction = round(basic_salary * 0.05, 2)
        
        # Net Pay calculation
        net_pay = round(gross_salary - absent_deduction - advance_deduction - tax_deduction, 2)
        if net_pay < 0:
            net_pay = 0.0
            
        return JsonResponse({
            'employee': emp_name,
            'period': f"{month_name} {year}",
            'basic_salary': basic_salary,
            'house_rent': house_rent,
            'medical_allowance': medical_allowance,
            'absent_days': absent_count,
            'absent_deduction': absent_deduction,
            'advance_deduction': advance_deduction,
            'tax_deduction': tax_deduction,
            'net_pay': net_pay
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@module_access('hrm')
def reports(request):
    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': d.to_dict().get('name', '')} for d in emp_docs if d.to_dict().get('name')]
    except Exception:
        employees = []

    context = {
        'employees': employees,
        'report_data': None,
        'report_type': None
    }

    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        employee_filter = request.POST.get('employee_filter')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        context['report_type'] = report_type

        try:
            if report_type == 'Attendance Summary':
                att_docs = db.collection('hrm_attendance').stream()
                att_records = [d.to_dict() for d in att_docs]

                summary = {}
                for r in att_records:
                    # Field stored during attendance recording is 'name', not 'employee'
                    emp_name = r.get('name', '')
                    if not emp_name: continue
                    if employee_filter != 'All Employees' and emp_name != employee_filter: continue

                    r_date = r.get('date', '')
                    if start_date and r_date < start_date: continue
                    if end_date and r_date > end_date: continue

                    if emp_name not in summary:
                        summary[emp_name] = {'Present': 0, 'Absent': 0, 'Late': 0, 'Half Day': 0}

                    status = r.get('status', '')
                    if status in summary[emp_name]:
                        summary[emp_name][status] += 1

                rows = [[name, data['Present'], data['Absent'], data['Late'], data['Half Day']] for name, data in summary.items()]

                context['report_data'] = {
                    'headers': ['Employee', 'Total Present', 'Total Absent', 'Total Late', 'Total Half Day'],
                    'rows': rows
                }

            elif report_type == 'Payroll Summary':
                emp_data = {}
                for e in db.collection('hrm_employees').stream():
                    dt = e.to_dict()
                    name = dt.get('name')
                    if name:
                        # Fallback to a default 0 if basic_salary not found
                        emp_data[name] = float(dt.get('basic_salary', 0))

                adv_docs = db.collection('hrm_advances').stream()
                advances = {}
                for doc in adv_docs:
                    d = doc.to_dict()
                    if d.get('status') == 'Deducted': continue
                    emp_name = d.get('employee')
                    advances[emp_name] = advances.get(emp_name, 0) + float(d.get('amount', 0))

                rows = []
                for name, b_pay in emp_data.items():
                    if employee_filter != 'All Employees' and name != employee_filter: continue
                    adv = advances.get(name, 0)
                    net = b_pay - adv
                    rows.append([name, f"${b_pay:,.2f}", f"${adv:,.2f}", f"${net:,.2f}"])

                context['report_data'] = {
                    'headers': ['Employee', 'Basic Pay', 'Pending Advances', 'Estimated Net Pay'],
                    'rows': rows
                }

            elif report_type == 'Leave History':
                leave_docs = db.collection('hrm_leaves').stream()
                rows = []
                for doc in leave_docs:
                    d = doc.to_dict()
                    emp_name = d.get('name', '')
                    if not emp_name: continue
                    if employee_filter != 'All Employees' and emp_name != employee_filter: continue

                    l_from = d.get('from_date', '')
                    l_to = d.get('to_date', '')
                    
                    if start_date and l_to < start_date: continue
                    if end_date and l_from > end_date: continue

                    rows.append([
                        emp_name, 
                        d.get('type', ''), 
                        d.get('duration', ''), 
                        d.get('status', 'Pending')
                    ])

                context['report_data'] = {
                    'headers': ['Employee', 'Leave Type', 'Duration', 'Status'],
                    'rows': rows
                }

        except Exception as e:
            hrm_logger.error(f"Error generating report: {e}")

    return render(request, 'hrm/reports.html', context)


@login_required
@module_access('hrm')
def onboarding_offboarding(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_task':
            try:
                db.collection('hrm_onboarding_tasks').add({
                    'employee': request.POST.get('employee'),
                    'task_name': request.POST.get('task_name'),
                    'due_date': request.POST.get('due_date'),
                    'status': 'Pending',
                    'createdAt': firestore.SERVER_TIMESTAMP
                })
                messages.success(request, "Onboarding task added successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding onboarding task: {e}")

        elif action == 'complete_task':
            if doc_id:
                try:
                    db.collection('hrm_onboarding_tasks').document(doc_id).update({'status': 'Completed'})
                    messages.success(request, "Onboarding task marked as completed.")
                except Exception as e:
                    hrm_logger.error(f"Error completing onboarding task: {e}")

        elif action == 'delete_task':
            if doc_id:
                try:
                    db.collection('hrm_onboarding_tasks').document(doc_id).delete()
                    messages.success(request, "Onboarding task deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting onboarding task: {e}")

        elif action == 'trigger_exit':
            try:
                emp_name = request.POST.get('employee')
                db.collection('hrm_exit_clearance').add({
                    'employee': emp_name,
                    'exit_date': request.POST.get('exit_date'),
                    'reason': request.POST.get('reason'),
                    'it_clearance': 'Pending',
                    'finance_clearance': 'Pending',
                    'hr_clearance': 'Pending',
                    'status': 'In Progress',
                    'createdAt': firestore.SERVER_TIMESTAMP
                })
                emp_query = list(db.collection('hrm_employees').where('name', '==', emp_name).stream())
                if emp_query:
                    emp_query[0].reference.update({'status': 'Resigned'})
                messages.success(request, "Exit clearance workflow triggered successfully.")
            except Exception as e:
                hrm_logger.error(f"Error triggering exit: {e}")

        elif action == 'update_clearance':
            if doc_id:
                try:
                    field = request.POST.get('clearance_field')
                    status = request.POST.get('clearance_status')
                    db.collection('hrm_exit_clearance').document(doc_id).update({field: status})
                    
                    doc_snap = db.collection('hrm_exit_clearance').document(doc_id).get().to_dict()
                    if doc_snap and doc_snap.get('it_clearance') == 'Cleared' and doc_snap.get('finance_clearance') == 'Cleared' and doc_snap.get('hr_clearance') == 'Cleared':
                        db.collection('hrm_exit_clearance').document(doc_id).update({'status': 'Cleared'})
                        emp_name = doc_snap.get('employee')
                        emp_query = list(db.collection('hrm_employees').where('name', '==', emp_name).stream())
                        if emp_query:
                            emp_query[0].reference.update({'status': 'Inactive'})
                    messages.success(request, "Exit clearance status updated successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error updating clearance: {e}")

        return redirect('hrm:onboarding_offboarding')

    tasks = get_collection_data('hrm_onboarding_tasks', [])
    exits = get_collection_data('hrm_exit_clearance', [])
    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': (d.to_dict() or {}).get('name', '')} for d in emp_docs if (d.to_dict() or {}).get('name')]
    except Exception:
        employees = []

    return render(request, 'hrm/onboarding_offboarding.html', {
        'tasks': tasks,
        'exits': exits,
        'employees': employees
    })


@login_required
@module_access('hrm')
def roster_management(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'assign_shift':
            try:
                db.collection('hrm_employee_shifts').add({
                    'employee': request.POST.get('employee'),
                    'shift_name': request.POST.get('shift_name'),
                    'start_date': request.POST.get('start_date'),
                    'end_date': request.POST.get('end_date'),
                    'createdAt': firestore.SERVER_TIMESTAMP
                })
                messages.success(request, "Employee shift roster assigned successfully.")
            except Exception as e:
                hrm_logger.error(f"Error assigning shift: {e}")

        elif action == 'delete_shift':
            if doc_id:
                try:
                    db.collection('hrm_employee_shifts').document(doc_id).delete()
                    messages.success(request, "Shift assignment deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting shift: {e}")

        return redirect('hrm:roster_management')

    shifts = get_collection_data('hrm_employee_shifts', [])
    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': (d.to_dict() or {}).get('name', '')} for d in emp_docs if (d.to_dict() or {}).get('name')]
    except Exception:
        employees = []

    return render(request, 'hrm/roster_management.html', {
        'shifts': shifts,
        'employees': employees
    })


@login_required
@module_access('hrm')
def expense_claims(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'file_claim':
            try:
                db.collection('hrm_expense_claims').add({
                    'employee': request.POST.get('employee'),
                    'category': request.POST.get('category'),
                    'amount': float(request.POST.get('amount', 0)),
                    'description': request.POST.get('description', ''),
                    'status': 'Pending',
                    'createdAt': firestore.SERVER_TIMESTAMP
                })
                messages.success(request, "Expense claim filed successfully.")
            except Exception as e:
                hrm_logger.error(f"Error filing expense claim: {e}")

        elif action == 'approve_claim':
            if doc_id:
                try:
                    db.collection('hrm_expense_claims').document(doc_id).update({'status': 'Approved'})
                    messages.success(request, "Expense claim approved successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error approving claim: {e}")

        elif action == 'reject_claim':
            if doc_id:
                try:
                    db.collection('hrm_expense_claims').document(doc_id).update({'status': 'Rejected'})
                    messages.success(request, "Expense claim rejected.")
                except Exception as e:
                    hrm_logger.error(f"Error rejecting claim: {e}")

        elif action == 'delete_claim':
            if doc_id:
                try:
                    db.collection('hrm_expense_claims').document(doc_id).delete()
                    messages.success(request, "Expense claim deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting claim: {e}")

        return redirect('hrm:expense_claims')

    claims = get_collection_data('hrm_expense_claims', [])
    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': (d.to_dict() or {}).get('name', '')} for d in emp_docs if (d.to_dict() or {}).get('name')]
    except Exception:
        employees = []

    return render(request, 'hrm/expense_claims.html', {
        'claims': claims,
        'employees': employees
    })


@login_required
@module_access('hrm')
def document_asset_vault(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_document':
            try:
                db.collection('hrm_documents').add({
                    'employee': request.POST.get('employee'),
                    'document_type': request.POST.get('document_type'),
                    'document_number': request.POST.get('document_number', ''),
                    'expiry_date': request.POST.get('expiry_date'),
                    'createdAt': firestore.SERVER_TIMESTAMP
                })
                messages.success(request, "Employee document added to vault successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding document: {e}")

        elif action == 'delete_document':
            if doc_id:
                try:
                    db.collection('hrm_documents').document(doc_id).delete()
                    messages.success(request, "Employee document deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting document: {e}")

        elif action == 'assign_asset':
            try:
                db.collection('hrm_assets').add({
                    'employee': request.POST.get('employee'),
                    'asset_name': request.POST.get('asset_name'),
                    'asset_tag': request.POST.get('asset_tag', ''),
                    'serial_number': request.POST.get('serial_number', ''),
                    'status': 'Assigned',
                    'createdAt': firestore.SERVER_TIMESTAMP
                })
                messages.success(request, "Asset assigned to employee successfully.")
            except Exception as e:
                hrm_logger.error(f"Error assigning asset: {e}")

        elif action == 'return_asset':
            if doc_id:
                try:
                    db.collection('hrm_assets').document(doc_id).update({'status': 'Returned'})
                    messages.success(request, "Asset marked as returned successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error returning asset: {e}")

        elif action == 'delete_asset':
            if doc_id:
                try:
                    db.collection('hrm_assets').document(doc_id).delete()
                    messages.success(request, "Asset record deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting asset: {e}")

        return redirect('hrm:document_asset_vault')

    documents = get_collection_data('hrm_documents', [])
    assets = get_collection_data('hrm_assets', [])
    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': (d.to_dict() or {}).get('name', '')} for d in emp_docs if (d.to_dict() or {}).get('name')]
    except Exception:
        employees = []

    return render(request, 'hrm/document_asset_vault.html', {
        'documents': documents,
        'assets': assets,
        'employees': employees
    })


@login_required
@module_access('hrm')
def performance(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        # ── Review Cycles ────────────────────────────────────────────
        if action == 'add_review_cycle':
            try:
                doc_id = request.POST.get('doc_id')
                data = {
                    'name': request.POST.get('name'),
                    'start_date': request.POST.get('start_date'),
                    'end_date': request.POST.get('end_date'),
                    'review_type': request.POST.get('review_type', 'Half-Yearly'),
                    'status': request.POST.get('status', 'Draft'),
                    'createdAt': firestore.SERVER_TIMESTAMP,
                }
                if doc_id:
                    del data['createdAt']
                    db.collection('hrm_review_cycles').document(doc_id).update(data)
                    messages.success(request, "Review cycle updated successfully.")
                else:
                    db.collection('hrm_review_cycles').add(data)
                    messages.success(request, "Review cycle created successfully.")
            except Exception as e:
                hrm_logger.error(f"Error saving review cycle: {e}")

        elif action == 'delete_review_cycle':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection('hrm_review_cycles').document(doc_id).delete()
                    messages.success(request, "Review cycle deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting review cycle: {e}")

        # ── KPI Library ──────────────────────────────────────────────
        elif action == 'add_kpi':
            try:
                doc_id = request.POST.get('doc_id')
                data = {
                    'name': request.POST.get('name'),
                    'description': request.POST.get('description', ''),
                    'unit': request.POST.get('unit', ''),
                    'target_value': request.POST.get('target_value'),
                    'default_weight': request.POST.get('default_weight', 1.0),
                    'createdAt': firestore.SERVER_TIMESTAMP,
                }
                if doc_id:
                    del data['createdAt']
                    db.collection('hrm_kpis').document(doc_id).update(data)
                    messages.success(request, "KPI updated successfully.")
                else:
                    db.collection('hrm_kpis').add(data)
                    messages.success(request, "KPI created successfully.")
            except Exception as e:
                hrm_logger.error(f"Error saving KPI: {e}")

        elif action == 'delete_kpi':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection('hrm_kpis').document(doc_id).delete()
                    messages.success(request, "KPI deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting KPI: {e}")

        # ── Performance Reviews ──────────────────────────────────────
        elif action == 'add_review':
            try:
                doc_id = request.POST.get('doc_id')
                data = {
                    'employee': request.POST.get('employee'),
                    'reviewer': request.POST.get('reviewer'),
                    'review_cycle': request.POST.get('review_cycle'),
                    'overall_score': request.POST.get('overall_score'),
                    'strengths': request.POST.get('strengths', ''),
                    'improvements': request.POST.get('improvements', ''),
                    'goals': request.POST.get('goals', ''),
                    'status': request.POST.get('status', 'Self-Assessment'),
                    'createdAt': firestore.SERVER_TIMESTAMP,
                }
                if doc_id:
                    del data['createdAt']
                    db.collection('hrm_performance_reviews').document(doc_id).update(data)
                    messages.success(request, "Performance review updated successfully.")
                else:
                    db.collection('hrm_performance_reviews').add(data)
                    messages.success(request, "Performance review created successfully.")
            except Exception as e:
                hrm_logger.error(f"Error saving review: {e}")

        elif action == 'delete_review':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection('hrm_performance_reviews').document(doc_id).delete()
                    messages.success(request, "Performance review deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting review: {e}")

        # ── Performance Improvement Plans ────────────────────────────
        elif action == 'add_pip':
            try:
                doc_id = request.POST.get('doc_id')
                data = {
                    'employee': request.POST.get('employee'),
                    'issue_description': request.POST.get('issue_description', ''),
                    'improvement_goals': request.POST.get('improvement_goals', ''),
                    'start_date': request.POST.get('start_date'),
                    'end_date': request.POST.get('end_date'),
                    'status': request.POST.get('status', 'Open'),
                    'createdAt': firestore.SERVER_TIMESTAMP,
                }
                if doc_id:
                    del data['createdAt']
                    db.collection('hrm_pips').document(doc_id).update(data)
                    messages.success(request, "PIP updated successfully.")
                else:
                    db.collection('hrm_pips').add(data)
                    messages.success(request, "PIP created successfully.")
            except Exception as e:
                hrm_logger.error(f"Error saving PIP: {e}")

        elif action == 'delete_pip':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection('hrm_pips').document(doc_id).delete()
                    messages.success(request, "PIP deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting PIP: {e}")

        return redirect('hrm:performance')

    review_cycles = get_collection_data('hrm_review_cycles', [])
    kpis = get_collection_data('hrm_kpis', [])
    reviews = get_collection_data('hrm_performance_reviews', [])
    pips = get_collection_data('hrm_pips', [])

    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': (d.to_dict() or {}).get('name', '')} for d in emp_docs if (d.to_dict() or {}).get('name')]
    except Exception:
        employees = []

    return render(request, 'hrm/performance.html', {
        'review_cycles': review_cycles,
        'kpis': kpis,
        'reviews': reviews,
        'pips': pips,
        'employees': employees,
    })


# ── Notification Center (Admin) ───────────────────────────────────────

@login_required
@module_access('hrm')
def notification_center(request):
    from hrm.models import Notification, NotificationPreference
    from django.contrib.auth.models import User

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'mark_read':
            nid = request.POST.get('notification_id')
            if nid:
                Notification.objects.filter(id=nid, recipient=request.user).update(is_read=True)
                messages.success(request, "Notification marked as read.")
        elif action == 'mark_all_read':
            Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
            messages.success(request, "All notifications marked as read.")
        elif action == 'update_prefs':
            pref, _ = NotificationPreference.objects.get_or_create(user=request.user)
            pref.notify_in_app = request.POST.get('notify_in_app') == 'on'
            pref.notify_email = request.POST.get('notify_email') == 'on'
            pref.save()
            messages.success(request, "Notification preferences updated.")
        return redirect('hrm:notification_center')

    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:100]

    unread_count = notifications.filter(is_read=False).count()

    pref, _ = NotificationPreference.objects.get_or_create(user=request.user)

    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'prefs': pref,
    }
    return render(request, 'hrm/notifications.html', context)


# ── Succession Planning (Admin) ───────────────────────────────────────

@login_required
@module_access('hrm')
def succession_planning(request):
    from hrm.models import KeyPosition, SuccessorCandidate, SuccessionPlan
    from registry.models import Person

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_key_position':
            try:
                pos_id = request.POST.get('position', '')
                dept_id = request.POST.get('department', '')
                from hrm.models import Position as PosModel, Department as DeptModel
                pos = PosModel.objects.filter(title=pos_id).first() if pos_id else None
                dept = DeptModel.objects.filter(name=dept_id).first() if dept_id else None
                KeyPosition.objects.create(
                    position_title=request.POST.get('position_title'),
                    position=pos,
                    department=dept,
                    risk_of_vacancy=request.POST.get('risk_of_vacancy', 'Medium'),
                    readiness_gap=request.POST.get('readiness_gap', ''),
                    status=request.POST.get('status', 'Active'),
                    created_by=request.user,
                )
                messages.success(request, "Key position added successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding key position: {e}")
                messages.error(request, "Failed to add key position.")

        elif action == 'update_key_position':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    kp = KeyPosition.objects.get(id=doc_id)
                    pos_id = request.POST.get('position', '')
                    dept_id = request.POST.get('department', '')
                    from hrm.models import Position as PosModel, Department as DeptModel
                    kp.position_title = request.POST.get('position_title')
                    kp.position = PosModel.objects.filter(title=pos_id).first() if pos_id else None
                    kp.department = DeptModel.objects.filter(name=dept_id).first() if dept_id else None
                    kp.risk_of_vacancy = request.POST.get('risk_of_vacancy', 'Medium')
                    kp.readiness_gap = request.POST.get('readiness_gap', '')
                    kp.status = request.POST.get('status', 'Active')
                    kp.updated_by = request.user
                    kp.save()
                    messages.success(request, "Key position updated successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error updating key position: {e}")

        elif action == 'add_successor':
            try:
                emp_name = request.POST.get('employee', '')
                from hrm.models import Employee as EmpModel
                from django.db.models import Q as Q_
                emp = None
                if emp_name:
                    emp = EmpModel.objects.filter(
                        Q_(first_name__icontains=emp_name) | Q_(last_name__icontains=emp_name) | Q_(emp_id=emp_name)
                    ).first()
                SuccessorCandidate.objects.create(
                    key_position_id=request.POST.get('key_position'),
                    employee=emp,
                    readiness=request.POST.get('readiness', 'Developing'),
                    strengths=request.POST.get('strengths', ''),
                    development_needs=request.POST.get('development_needs', ''),
                    is_primary=request.POST.get('is_primary') == 'on',
                    created_by=request.user,
                )
                messages.success(request, "Successor candidate added successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding successor: {e}")

        elif action == 'update_successor':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    sc = SuccessorCandidate.objects.get(id=doc_id)
                    sc.readiness = request.POST.get('readiness', 'Developing')
                    sc.strengths = request.POST.get('strengths', '')
                    sc.development_needs = request.POST.get('development_needs', '')
                    sc.is_primary = request.POST.get('is_primary') == 'on'
                    sc.updated_by = request.user
                    sc.save()
                    messages.success(request, "Successor candidate updated.")
                except Exception as e:
                    hrm_logger.error(f"Error updating successor: {e}")

        elif action == 'delete_successor':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    SuccessorCandidate.objects.filter(id=doc_id).update(is_active=False)
                    messages.success(request, "Successor candidate removed.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting successor: {e}")

        elif action == 'create_plan':
            try:
                dept_id = request.POST.get('department', '')
                from hrm.models import Department as DeptModel
                dept = DeptModel.objects.filter(name=dept_id).first() if dept_id else None
                SuccessionPlan.objects.create(
                    title=request.POST.get('title'),
                    department=dept,
                    description=request.POST.get('description', ''),
                    review_date=request.POST.get('review_date') or None,
                    status=request.POST.get('status', 'Draft'),
                    created_by=request.user,
                )
                messages.success(request, "Succession plan created successfully.")
            except Exception as e:
                hrm_logger.error(f"Error creating succession plan: {e}")

        elif action == 'delete_position':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    KeyPosition.objects.filter(id=doc_id).update(is_active=False)
                    messages.success(request, "Key position removed.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting key position: {e}")

        return redirect('hrm:succession_planning')

    key_positions = KeyPosition.objects.filter(is_active=True).select_related('position')
    successors = SuccessorCandidate.objects.filter(is_active=True).select_related('key_position', 'employee')
    plans = SuccessionPlan.objects.filter(is_active=True)

    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': (d.to_dict() or {}).get('name', ''), 'id': d.id} for d in emp_docs if (d.to_dict() or {}).get('name')]
    except Exception:
        employees = []

    positions = get_cached_collection('org_positions')
    departments = get_cached_collection('org_departments')

    context = {
        'key_positions': key_positions,
        'successors': successors,
        'plans': plans,
        'employees': employees,
        'positions': positions,
        'departments': departments,
    }
    return render(request, 'hrm/succession.html', context)


# ── Unread Count (AJAX) ───────────────────────────────────────────────

@login_required
def get_unread_notification_count(request):
    from hrm.models import Notification
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'count': count})


# ── Phase 5: Skills Inventory ──────────────────────────────────────

@login_required
@module_access('hrm')
def skills_inventory(request):
    from hrm.models import (
        Employee as SQLEmployee, EmployeeEducation, EmployeeExperience,
        EmployeeSkill, Competency, CompetencyRating,
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'add_education':
                emp = SQLEmployee.objects.get(id=request.POST.get('employee'))
                EmployeeEducation.objects.create(
                    employee=emp, degree=request.POST['degree'],
                    institution=request.POST['institution'],
                    field_of_study=request.POST.get('field_of_study', ''),
                    start_year=int(request.POST['start_year']) if request.POST.get('start_year') else None,
                    end_year=int(request.POST['end_year']) if request.POST.get('end_year') else None,
                    grade=request.POST.get('grade', ''),
                )
                messages.success(request, "Education record added.")
            elif action == 'add_experience':
                emp = SQLEmployee.objects.get(id=request.POST.get('employee'))
                EmployeeExperience.objects.create(
                    employee=emp, company=request.POST['company'],
                    job_title=request.POST['job_title'],
                    start_date=request.POST['start_date'],
                    end_date=request.POST.get('end_date') or None,
                    is_current=request.POST.get('is_current') == 'on',
                    description=request.POST.get('description', ''),
                )
                messages.success(request, "Experience record added.")
            elif action == 'add_skill':
                emp = SQLEmployee.objects.get(id=request.POST.get('employee'))
                EmployeeSkill.objects.create(
                    employee=emp, skill_name=request.POST['skill_name'],
                    proficiency=request.POST['proficiency'],
                    years_of_experience=request.POST.get('years_of_experience') or None,
                )
                messages.success(request, "Skill added.")
            elif action == 'add_competency_rating':
                emp = SQLEmployee.objects.get(id=request.POST.get('employee'))
                comp = Competency.objects.get(id=request.POST.get('competency'))
                CompetencyRating.objects.create(
                    employee=emp, competency=comp,
                    rating=int(request.POST['rating']),
                    assessed_by=request.user,
                )
                messages.success(request, "Competency rating saved.")
        except Exception as e:
            hrm_logger.error(f"Skills inventory error: {e}")
            messages.error(request, f"Error: {e}")
        return redirect('hrm:skills_inventory')

    employees = SQLEmployee.objects.filter(is_active=True)
    education = EmployeeEducation.objects.filter(is_active=True).select_related('employee')
    experiences = EmployeeExperience.objects.filter(is_active=True).select_related('employee')
    skills = EmployeeSkill.objects.filter(is_active=True).select_related('employee')
    competencies = Competency.objects.filter(is_active=True)
    competency_ratings = CompetencyRating.objects.filter(is_active=True).select_related('employee', 'competency', 'assessed_by')

    context = {
        'employees': employees, 'education': education, 'experiences': experiences,
        'skills': skills, 'competencies': competencies, 'competency_ratings': competency_ratings,
    }
    return render(request, 'hrm/skills_inventory.html', context)


# ── Phase 5: 360 Feedback ──────────────────────────────────────────

@login_required
@module_access('hrm')
def feedback_360(request):
    from hrm.models import (
        Employee as SQLEmployee, ReviewCycle,
        FeedbackQuestion, FeedbackRequest, FeedbackResponse,
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'add_question':
                FeedbackQuestion.objects.create(
                    category=request.POST['category'],
                    question_text=request.POST['question_text'],
                    is_required=request.POST.get('is_required') == 'on',
                    order=int(request.POST.get('order', 0)),
                )
                messages.success(request, "Feedback question added.")
            elif action == 'send_request':
                reviewer_id = request.POST.get('reviewer')
                reviewee_id = request.POST.get('reviewee')
                cycle_id = request.POST.get('review_cycle')
                FeedbackRequest.objects.create(
                    reviewer_id=reviewer_id, reviewee_id=reviewee_id,
                    review_cycle_id=cycle_id,
                    relationship=request.POST.get('relationship', 'Peer'),
                    due_date=request.POST.get('due_date'),
                )
                messages.success(request, "Feedback request sent.")
        except Exception as e:
            hrm_logger.error(f"360 feedback error: {e}")
            messages.error(request, f"Error: {e}")
        return redirect('hrm:feedback_360')

    questions = FeedbackQuestion.objects.filter(is_active=True)
    requests = FeedbackRequest.objects.filter(is_active=True).select_related('reviewer', 'reviewee', 'review_cycle')
    responses = FeedbackResponse.objects.select_related('request', 'question')
    employees = SQLEmployee.objects.filter(is_active=True)
    cycles = ReviewCycle.objects.filter(is_active=True)

    context = {
        'questions': questions, 'requests': requests, 'responses': responses,
        'employees': employees, 'cycles': cycles,
    }
    return render(request, 'hrm/feedback_360.html', context)


# ── Phase 5: Engagement Surveys ────────────────────────────────────

@login_required
@module_access('hrm')
def engagement_surveys(request):
    from hrm.models import (
        Employee as SQLEmployee,
        EngagementSurvey, SurveyQuestion, SurveyResponse,
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'create_survey':
                survey = EngagementSurvey.objects.create(
                    title=request.POST['title'],
                    description=request.POST.get('description', ''),
                    is_anonymous=request.POST.get('is_anonymous') == 'on',
                )
                messages.success(request, f"Survey '{survey.title}' created.")
            elif action == 'add_question':
                survey = EngagementSurvey.objects.get(id=request.POST.get('survey_id'))
                SurveyQuestion.objects.create(
                    survey=survey,
                    question_text=request.POST['question_text'],
                    question_type=request.POST.get('question_type', 'text'),
                    is_required=request.POST.get('is_required') == 'on',
                    order=int(request.POST.get('order', 0)),
                )
                messages.success(request, "Survey question added.")
        except Exception as e:
            hrm_logger.error(f"Survey error: {e}")
            messages.error(request, f"Error: {e}")
        return redirect('hrm:engagement_surveys')

    surveys = EngagementSurvey.objects.filter(is_active=True)
    survey_questions = SurveyQuestion.objects.filter(is_active=True).select_related('survey')
    survey_responses = SurveyResponse.objects.select_related('survey', 'question', 'employee')

    context = {
        'surveys': surveys, 'survey_questions': survey_questions,
        'survey_responses': survey_responses,
    }
    return render(request, 'hrm/engagement_surveys.html', context)


# ── Phase 5: Compliance Calendar ────────────────────────────────────

@login_required
@module_access('hrm')
def compliance_calendar(request):
    from hrm.models import Employee as SQLEmployee, ComplianceReminder
    from hrm.services import sync_document_compliance_reminders, check_compliance_overdue_reminders

    # Auto-sync documents and check overdue on page load
    sync_document_compliance_reminders()
    check_compliance_overdue_reminders()

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'add_reminder':
                ComplianceReminder.objects.create(
                    employee_id=request.POST.get('employee'),
                    reminder_type=request.POST['reminder_type'],
                    title=request.POST['title'],
                    description=request.POST.get('description', ''),
                    due_date=request.POST['due_date'],
                )
                messages.success(request, "Compliance reminder added.")
            elif action == 'complete_reminder':
                reminder = ComplianceReminder.objects.get(id=request.POST.get('reminder_id'))
                reminder.mark_completed()
                messages.success(request, f"Reminder '{reminder.title}' marked complete.")
            elif action == 'dismiss_reminder':
                ComplianceReminder.objects.filter(id=request.POST.get('reminder_id')).update(is_active=False)
                messages.success(request, "Reminder dismissed.")
        except Exception as e:
            hrm_logger.error(f"Compliance calendar error: {e}")
            messages.error(request, f"Error: {e}")
        return redirect('hrm:compliance_calendar')

    reminders = ComplianceReminder.objects.filter(is_active=True).select_related('employee')
    employees = SQLEmployee.objects.filter(is_active=True)
    upcoming = reminders.filter(status__in=['Pending', 'Overdue']).order_by('due_date')

    context = {'reminders': reminders, 'employees': employees, 'upcoming': upcoming}
    return render(request, 'hrm/compliance_calendar.html', context)


# ── Phase 5: Talent Review & 9-Box ──────────────────────────────────

@login_required
@module_access('hrm')
def talent_review(request):
    from hrm.models import Employee as SQLEmployee, TalentReviewMeeting, NineBoxCell

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'start_meeting':
                TalentReviewMeeting.objects.create(
                    title=request.POST['title'],
                    meeting_date=request.POST['meeting_date'] or None,
                    notes=request.POST.get('notes', ''),
                )
                messages.success(request, "Talent review meeting created.")
            elif action == 'add_cell':
                meeting = TalentReviewMeeting.objects.get(id=request.POST.get('meeting_id'))
                NineBoxCell.objects.create(
                    talent_review=meeting,
                    employee_id=request.POST.get('employee'),
                    performance=request.POST['performance'],
                    potential=request.POST['potential'],
                    notes=request.POST.get('notes', ''),
                )
                messages.success(request, "9-Box cell added.")
            elif action == 'complete_meeting':
                TalentReviewMeeting.objects.filter(id=request.POST.get('meeting_id')).update(status='Completed')
                messages.success(request, "Meeting marked as completed.")
        except Exception as e:
            hrm_logger.error(f"Talent review error: {e}")
            messages.error(request, f"Error: {e}")
        return redirect('hrm:talent_review')

    meetings = TalentReviewMeeting.objects.filter(is_active=True)
    cells = NineBoxCell.objects.filter(is_active=True).select_related('employee', 'talent_review')
    employees = SQLEmployee.objects.filter(is_active=True)

    context = {
        'meetings': meetings, 'cells': cells, 'employees': employees,
    }
    return render(request, 'hrm/talent_review.html', context)


# ── Configuration UI ───────────────────────────────────────────────

@login_required
@module_access('hrm')
def hrm_settings(request):
    from hrm.models import HRMSetting, LeavePolicy, RatingTemplate, RatingScale

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'update_setting':
                key = request.POST.get('key')
                value = request.POST.get('value', '')
                obj, _ = HRMSetting.objects.update_or_create(
                    key=key,
                    defaults={'value': value},
                )
                messages.success(request, f"Setting '{key}' updated.")
            elif action == 'add_setting':
                HRMSetting.objects.create(
                    key=request.POST.get('key'),
                    value=request.POST.get('value', ''),
                )
                messages.success(request, "Setting created.")
            elif action == 'delete_setting':
                HRMSetting.objects.filter(id=request.POST.get('setting_id')).update(is_active=False)
                messages.success(request, "Setting removed.")
            elif action == 'add_leave_policy':
                LeavePolicy.objects.create(
                    employee_type=request.POST['employee_type'],
                    leave_type=request.POST['leave_type'],
                    entitled_days=request.POST['entitled_days'],
                    carry_forward_days=request.POST.get('carry_forward_days', 0),
                )
                messages.success(request, "Leave policy added.")
            elif action == 'delete_leave_policy':
                LeavePolicy.objects.filter(id=request.POST.get('policy_id')).update(is_active=False)
                messages.success(request, "Leave policy removed.")
            elif action == 'add_rating_template':
                RatingTemplate.objects.create(
                    name=request.POST['name'],
                    description=request.POST.get('description', ''),
                )
                messages.success(request, "Rating template created.")
            elif action == 'add_rating_scale':
                template = RatingTemplate.objects.get(id=request.POST.get('template_id'))
                RatingScale.objects.create(
                    template=template,
                    label=request.POST['label'],
                    value=request.POST['value'],
                    definition=request.POST.get('definition', ''),
                    order=int(request.POST.get('order', 0)),
                )
                messages.success(request, "Rating scale value added.")
        except Exception as e:
            hrm_logger.error(f"Settings error: {e}")
            messages.error(request, f"Error: {e}")
        return redirect('hrm:hrm_settings')

    settings = HRMSetting.objects.filter(is_active=True)
    leave_policies = LeavePolicy.objects.filter(is_active=True)
    templates = RatingTemplate.objects.filter(is_active=True).prefetch_related('scales')

    context = {
        'settings': settings,
        'leave_policies': leave_policies,
        'templates': templates,
    }
    return render(request, 'hrm/hrm_settings.html', context)

