from django.shortcuts import render, redirect
from django.http import JsonResponse
from config.firebase import db
from google.cloud import firestore
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from accounts.decorators import module_access
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
        print(f"Error fetching {collection_name}: {e}")
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
        employees = list(db.collection('employees').stream())
        positions = list(db.collection('hrm_positions').stream())

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
        print(f"Error loading dashboard: {e}")
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
                    db.collection('hrm_candidates').document(doc_id).update(update_data)
                else:
                    cand_id = f"CAN-{random.randint(100, 999)}"
                    update_data['cand_id'] = cand_id
                    update_data['createdAt'] = firestore.SERVER_TIMESTAMP
                    db.collection('hrm_candidates').add(update_data)
            except Exception as e:
                print(f"Error adding candidate: {e}")
                
        # 2. Add to Shortlist
        elif action == 'add_shortlist':
            cand_doc_id = request.POST.get('candidate_id')
            rating = request.POST.get('rating')
            experience = request.POST.get('experience')
            
            if cand_doc_id:
                try:
                    cand_name, cand_position = None, None
                    cand_ref = db.collection('hrm_candidates').document(cand_doc_id)
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
                            db.collection('hrm_shortlists').document(doc_id).update(update_data)
                        else:
                            db.collection('hrm_shortlists').add({
                            'candidate_id': cand_doc_id,
                            'name': cand_name,
                            'position': cand_position,
                            'rating': rating,
                            'experience': experience,
                            'createdAt': firestore.SERVER_TIMESTAMP
                        })
                except Exception as e:
                    print(f"Error adding shortlist candidate: {e}")
                    
        # 3. Schedule Interview
        elif action == 'add_interview':
            cand_doc_id = request.POST.get('candidate_id')
            interviewer = request.POST.get('interviewer')
            date_time = request.POST.get('date_time')
            status = request.POST.get('status', 'Scheduled')
            
            if cand_doc_id:
                try:
                    cand_name, cand_position = None, None
                    cand_ref = db.collection('hrm_candidates').document(cand_doc_id)
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
                            db.collection('hrm_interviews').document(doc_id).update(update_data)
                        else:
                            db.collection('hrm_interviews').add({
                            'candidate_id': cand_doc_id,
                            'name': cand_name,
                            'position': cand_position,
                            'interviewer': interviewer,
                            'date_time': date_time,
                            'status': status,
                            'createdAt': firestore.SERVER_TIMESTAMP
                        })
                except Exception as e:
                    print(f"Error scheduling interview: {e}")
                    
        # 4. Make Selection
        elif action == 'add_selection':
            cand_doc_id = request.POST.get('candidate_id')
            offer_status = request.POST.get('offer_status')
            offer_date = request.POST.get('offer_date')
            
            if cand_doc_id:
                try:
                    cand_name, cand_position = None, None
                    cand_ref = db.collection('hrm_candidates').document(cand_doc_id)
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
                            db.collection('hrm_selections').document(doc_id).update(update_data)
                        else:
                            db.collection('hrm_selections').add({
                            'candidate_id': cand_doc_id,
                            'name': cand_name,
                            'position': cand_position,
                            'offer_status': offer_status,
                            'offer_date': offer_date,
                            'createdAt': firestore.SERVER_TIMESTAMP
                        })
                except Exception as e:
                    print(f"Error saving selection: {e}")
                    
        # 5. Delete Actions
        elif action.startswith('delete_'):
            col_name = action.replace('delete_', 'hrm_')
            if col_name == 'hrm_candidate':
                col_name = 'hrm_candidates'
            elif col_name == 'hrm_shortlist':
                col_name = 'hrm_shortlists'
            elif col_name == 'hrm_interview':
                col_name = 'hrm_interviews'
            elif col_name == 'hrm_selection':
                col_name = 'hrm_selections'
                
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection(col_name).document(doc_id).delete()
                except Exception as e:
                    print(f"Error deleting doc from {col_name}: {e}")
                    
        # 6. Inline Update Status
        elif action == 'update_status':
            doc_id = request.POST.get('doc_id')
            new_status = request.POST.get('status')
            if doc_id and new_status:
                try:
                    db.collection('hrm_candidates').document(doc_id).update({'status': new_status})
                except Exception as e:
                    print(f"Error updating status: {e}")
                    
        return redirect('hrm:recruitment')

    # Fetch data from collections
    # Transactional data fetched fresh; positions cached (rarely changes)
    candidates = get_collection_data('hrm_candidates', [])
    shortlists = get_collection_data('hrm_shortlists', [])
    interviews = get_collection_data('hrm_interviews', [])
    selections = get_collection_data('hrm_selections', [])
    positions_data = get_cached_collection('hrm_positions')

    positions = [p.get('title') or p.get('name') for p in positions_data if (p.get('title') or p.get('name'))]

    return render(request, 'hrm/recruitment.html', {
        'candidates': candidates,
        'shortlists': shortlists,
        'interviews': interviews,
        'selections': selections,
        'positions': positions
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
                    db.collection('hrm_departments').document(doc_id).update(update_data)
                else:
                    db.collection('hrm_departments').add({
                    'name': request.POST.get('name'),
                    'status': request.POST.get('status', 'Active'),
                    'module_linking': request.POST.getlist('module_linking'),
                    'notes': request.POST.get('notes', ''),
                    'createdAt': firestore.SERVER_TIMESTAMP
                })
            except Exception as e:
                print(f"Error adding department: {e}")
                
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
                        dept_doc = db.collection('hrm_departments').document(parent_id).get()
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
                            db.collection('hrm_sub_departments').document(doc_id).update(update_data)
                        else:
                            db.collection('hrm_sub_departments').add({
                            'name': name,
                            'parent_id': parent_id,
                            'parent_name': parent_name,
                            'status': status,
                            'notes': notes,
                            'createdAt': firestore.SERVER_TIMESTAMP
                        })
                except Exception as e:
                    print(f"Error adding sub department: {e}")
                    
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
                        dept_doc = db.collection('hrm_departments').document(dept_id).get()
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
                            sub_dept_doc = db.collection('hrm_sub_departments').document(sub_dept_id).get()
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
                            db.collection('hrm_positions').document(doc_id).update(update_data)
                        else:
                            db.collection('hrm_positions').add({
                                'title': title,
                                'dept_id': dept_id,
                                'dept_name': dept_name,
                                'sub_dept_id': sub_dept_id,
                                'sub_dept_name': sub_dept_name,
                                'status': status,
                                'createdAt': firestore.SERVER_TIMESTAMP
                            })
                except Exception as e:
                    print(f"Error adding position: {e}")
                    
        # 4. Delete Action
        elif action.startswith('delete_'):
            col_name = action.replace('delete_', 'hrm_')
            if col_name == 'hrm_department':
                col_name = 'hrm_departments'
            elif col_name == 'hrm_sub_department':
                col_name = 'hrm_sub_departments'
            elif col_name == 'hrm_position':
                col_name = 'hrm_positions'
                
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection(col_name).document(doc_id).delete()
                except Exception as e:
                    print(f"Error deleting doc from {col_name}: {e}")
                    
        # Invalidate caches so next load reflects the write
        invalidate_cache('hrm_departments')
        invalidate_cache('hrm_sub_departments')
        invalidate_cache('hrm_positions')
        return redirect('hrm:department')

    # Fetch lists — use cache for slow-changing reference data
    departments = get_cached_collection('hrm_departments')
    # Normalize module_linking to always be a list of strings
    for d in departments:
        linking = d.get('module_linking', [])
        if isinstance(linking, str):
            d['module_linking'] = [linking] if linking else []
        elif not isinstance(linking, list):
            d['module_linking'] = []

    sub_departments = get_cached_collection('hrm_sub_departments')
    positions = get_cached_collection('hrm_positions')

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
                    db.collection('employees').document(doc_id).delete()
                except Exception as e:
                    print(f"Error deleting employee: {e}")
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
                db.collection('employees').document(doc_id).update(data)
            else:
                # Generate new emp_id and add employee
                existing = db.collection('employees').stream()
                count = sum(1 for _ in existing) + 1
                data['emp_id'] = f"EMP-{count:04d}"
                data['createdAt'] = firestore.SERVER_TIMESTAMP
                db.collection('employees').add(data)
        except Exception as e:
            print(f"Error saving employee: {e}")
        return redirect('hrm:employee_database')

    # Fetch employees list
    try:
        docs = db.collection('employees').stream()
        employees = []
        for doc in docs:
            emp = doc.to_dict()
            emp['id'] = doc.id
            employees.append(emp)
    except Exception as e:
        print(f"Error fetching employees: {e}")
        employees = []

    # Use cached reference data for dropdowns
    departments = get_cached_collection('hrm_departments')
    sub_departments = get_cached_collection('hrm_sub_departments')
    positions = get_cached_collection('hrm_positions')

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
                except Exception as e:
                    print(f"Error deleting attendance: {e}")

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
            except Exception as e:
                print(f"Error resolving missing attendance: {e}")

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
            except Exception as e:
                print(f"Error adding attendance log: {e}")

        return redirect('hrm:attendance')

    logs = get_collection_data('hrm_attendance', [])

    # Fetch employees for dropdown
    try:
        emp_docs = db.collection('employees').stream()
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
                else:
                    db.collection('hrm_holidays').add({
                    'holiday_name': request.POST.get('holiday_name'),
                    'from_date': request.POST.get('from_date'),
                    'to_date': request.POST.get('to_date'),
                    'type': request.POST.get('holiday_type', 'Public'),
                    'createdAt': firestore.SERVER_TIMESTAMP
                })
            except Exception as e:
                print(f"Error adding holiday: {e}")

        elif lv_action == 'delete_holiday':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection('hrm_holidays').document(doc_id).delete()
                except Exception as e:
                    print(f"Error deleting holiday: {e}")

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
                else:
                    db.collection('hrm_leaves').add({
                    'name': request.POST.get('emp_name'),
                    'type': request.POST.get('leave_type'),
                    'from_date': from_date,
                    'to_date': to_date,
                    'duration': duration,
                    'reason': request.POST.get('reason', ''),
                    'status': 'Pending',
                    'createdAt': firestore.SERVER_TIMESTAMP
                })
            except Exception as e:
                print(f"Error applying leave: {e}")

        elif lv_action in ('Approved', 'Rejected'):
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection('hrm_leaves').document(doc_id).update({'status': lv_action})
                except Exception as e:
                    print(f"Error updating leave: {e}")

        elif lv_action == 'delete_leave':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection('hrm_leaves').document(doc_id).delete()
                except Exception as e:
                    print(f"Error deleting leave: {e}")

        elif lv_action == 'save_weekend':
            weekend_days = request.POST.getlist('weekend_days')
            try:
                db.collection('hrm_settings').document('weekend').set({'days': weekend_days})
            except Exception as e:
                print(f"Error saving weekend: {e}")

        return redirect('hrm:leave')

    # Fetch data — real-time for transactional records
    holidays = get_collection_data('hrm_holidays', [])
    leaves = get_collection_data('hrm_leaves', [])

    try:
        emp_docs = db.collection('employees').stream()
        employees = [{'name': d.to_dict().get('name', '')} for d in emp_docs if d.to_dict().get('name')]
    except Exception:
        employees = []

    try:
        ws_doc = db.collection('hrm_settings').document('weekend').get()
        weekend_days = ws_doc.to_dict().get('days', ['Saturday', 'Sunday']) if ws_doc.exists else ['Saturday', 'Sunday']
    except Exception:
        weekend_days = ['Saturday', 'Sunday']

    return render(request, 'hrm/leave.html', {
        'holidays': holidays,
        'leaves': leaves,
        'employees': employees,
        'weekend_days': weekend_days,
        'all_days': ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
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
                else:
                    db.collection('hrm_advances').add({
                    'employee': request.POST.get('employee'),
                    'amount': float(request.POST.get('amount', 0)),
                    'deduct_month': request.POST.get('deduct_month'),
                    'reason': request.POST.get('reason', ''),
                    'status': 'Pending',
                    'createdAt': firestore.SERVER_TIMESTAMP
                })
            except Exception as e:
                print(f"Error adding advance salary: {e}")

        elif pr_action == 'delete_advance':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection('hrm_advances').document(doc_id).delete()
                except Exception as e:
                    print(f"Error deleting advance: {e}")

        elif pr_action == 'generate_salary':
            month = request.POST.get('month')
            year = request.POST.get('year')
            period = f"{month} {year}"
            try:
                # Calculate real totals from the employees collection
                emp_docs = list(db.collection('employees').stream())
                active_employees = [e.to_dict() for e in emp_docs if e.to_dict().get('status') == 'Active']
                employee_count = len(active_employees)
                total_net_pay = round(sum(float(e.get('gross_salary', 0)) for e in active_employees), 2)

                doc_id = request.POST.get('doc_id')
                payload = {
                    'period': period,
                    'employee_count': employee_count,
                    'total_net_pay': total_net_pay,
                    'status': 'Generated',
                }
                if doc_id:
                    db.collection('hrm_payrolls').document(doc_id).update(payload)
                else:
                    payload['createdAt'] = firestore.SERVER_TIMESTAMP
                    db.collection('hrm_payrolls').add(payload)
            except Exception as e:
                print(f"Error generating payroll: {e}")

        elif pr_action == 'delete_payroll':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    db.collection('hrm_payrolls').document(doc_id).delete()
                except Exception as e:
                    print(f"Error deleting payroll: {e}")

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
                        
                        coa_exp = list(db.collection('chart_of_accounts').where('account_code', '==', '51000').stream())
                        coa_cash = list(db.collection('chart_of_accounts').where('account_code', '==', '11100').stream())
                        
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
                        db.collection('journal_entries').add(je_data)
                except Exception as e:
                    print(f"Error disbursing payroll: {e}")

        return redirect('hrm:payroll')

    # Fetch data — transactional, always fresh
    advances = get_collection_data('hrm_advances', [])
    payrolls = get_collection_data('hrm_payrolls', [])

    try:
        emp_docs = db.collection('employees').stream()
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

@module_access('hrm')
def reports(request):
    try:
        emp_docs = db.collection('employees').stream()
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
                for e in db.collection('employees').stream():
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
            print(f"Error generating report: {e}")

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
            except Exception as e:
                print(f"Error adding onboarding task: {e}")

        elif action == 'complete_task':
            if doc_id:
                try:
                    db.collection('hrm_onboarding_tasks').document(doc_id).update({'status': 'Completed'})
                except Exception as e:
                    print(f"Error completing onboarding task: {e}")

        elif action == 'delete_task':
            if doc_id:
                try:
                    db.collection('hrm_onboarding_tasks').document(doc_id).delete()
                except Exception as e:
                    print(f"Error deleting onboarding task: {e}")

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
                emp_query = list(db.collection('employees').where('name', '==', emp_name).stream())
                if emp_query:
                    emp_query[0].reference.update({'status': 'Resigned'})
            except Exception as e:
                print(f"Error triggering exit: {e}")

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
                        emp_query = list(db.collection('employees').where('name', '==', emp_name).stream())
                        if emp_query:
                            emp_query[0].reference.update({'status': 'Inactive'})
                except Exception as e:
                    print(f"Error updating clearance: {e}")

        return redirect('hrm:onboarding_offboarding')

    tasks = get_collection_data('hrm_onboarding_tasks', [])
    exits = get_collection_data('hrm_exit_clearance', [])
    try:
        emp_docs = db.collection('employees').stream()
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
            except Exception as e:
                print(f"Error assigning shift: {e}")

        elif action == 'delete_shift':
            if doc_id:
                try:
                    db.collection('hrm_employee_shifts').document(doc_id).delete()
                except Exception as e:
                    print(f"Error deleting shift: {e}")

        return redirect('hrm:roster_management')

    shifts = get_collection_data('hrm_employee_shifts', [])
    try:
        emp_docs = db.collection('employees').stream()
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
            except Exception as e:
                print(f"Error filing expense claim: {e}")

        elif action == 'approve_claim':
            if doc_id:
                try:
                    db.collection('hrm_expense_claims').document(doc_id).update({'status': 'Approved'})
                except Exception as e:
                    print(f"Error approving claim: {e}")

        elif action == 'reject_claim':
            if doc_id:
                try:
                    db.collection('hrm_expense_claims').document(doc_id).update({'status': 'Rejected'})
                except Exception as e:
                    print(f"Error rejecting claim: {e}")

        elif action == 'delete_claim':
            if doc_id:
                try:
                    db.collection('hrm_expense_claims').document(doc_id).delete()
                except Exception as e:
                    print(f"Error deleting claim: {e}")

        return redirect('hrm:expense_claims')

    claims = get_collection_data('hrm_expense_claims', [])
    try:
        emp_docs = db.collection('employees').stream()
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
            except Exception as e:
                print(f"Error adding document: {e}")

        elif action == 'delete_document':
            if doc_id:
                try:
                    db.collection('hrm_documents').document(doc_id).delete()
                except Exception as e:
                    print(f"Error deleting document: {e}")

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
            except Exception as e:
                print(f"Error assigning asset: {e}")

        elif action == 'return_asset':
            if doc_id:
                try:
                    db.collection('hrm_assets').document(doc_id).update({'status': 'Returned'})
                except Exception as e:
                    print(f"Error returning asset: {e}")

        elif action == 'delete_asset':
            if doc_id:
                try:
                    db.collection('hrm_assets').document(doc_id).delete()
                except Exception as e:
                    print(f"Error deleting asset: {e}")

        return redirect('hrm:document_asset_vault')

    documents = get_collection_data('hrm_documents', [])
    assets = get_collection_data('hrm_assets', [])
    try:
        emp_docs = db.collection('employees').stream()
        employees = [{'name': (d.to_dict() or {}).get('name', '')} for d in emp_docs if (d.to_dict() or {}).get('name')]
    except Exception:
        employees = []

    return render(request, 'hrm/document_asset_vault.html', {
        'documents': documents,
        'assets': assets,
        'employees': employees
    })

