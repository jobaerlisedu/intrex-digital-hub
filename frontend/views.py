import datetime
import random
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from firebase_admin import firestore
from config.firebase import db

# Default fallback courses list matching training.js mock data
FALLBACK_COURSES = [
    { "id": "CompTIA A+", "title": "CompTIA A+", "code": "APLUS", "target": "CompTIA A+", "description": "Hardware, operating systems, troubleshooting, and basic networking skills required for entry-level IT support roles.", "duration": "2.5 Months", "fee": 8000, "status": "Active", "icon": "bi-pc-display" },
    { "id": "CompTIA Network+", "title": "CompTIA Network+", "code": "NET", "target": "CompTIA Network+", "description": "Core concepts of networking technologies, design, infrastructure management, troubleshooting, and network security.", "duration": "2.0 Months", "fee": 8000, "status": "Active", "icon": "bi-diagram-3" },
    { "id": "CompTIA Security+", "title": "CompTIA Security+", "code": "SEC", "target": "CompTIA Security+", "description": "Core cybersecurity principles, threat intelligence, vulnerability management, cryptography, and secure network design.", "duration": "2.5 Months", "fee": 12000, "status": "Active", "icon": "bi-shield-check" },
    { "id": "CompTIA Linux+", "title": "CompTIA Linux+", "code": "LIN", "target": "CompTIA Linux+", "description": "Linux administration, command line operations, scripting, storage management, and container virtualization security.", "duration": "2.0 Months", "fee": 10000, "status": "Active", "icon": "bi-terminal" },
    { "id": "CompTIA Server+", "title": "CompTIA Server+", "code": "SRV", "target": "CompTIA Server+", "description": "Server architecture, virtualization, server administration, backup and disaster recovery, and storage systems.", "duration": "2.0 Months", "fee": 10000, "status": "Active", "icon": "bi-server" },
    { "id": "CCNA", "title": "CCNA", "code": "CCNA", "target": "CCNA", "description": "Network fundamentals, IP connectivity, IP services, security fundamentals, automation, and programmability using Cisco gear.", "duration": "1.5 Months", "fee": 10000, "status": "Active", "icon": "bi-router" },
    { "id": "CCNP - Enterprise", "title": "CCNP - Enterprise", "code": "CCNPE", "target": "CCNP Enterprise", "description": "Advanced routing and switching, wireless networks, enterprise network design, and software-defined networking (SDN).", "duration": "3.0 Months", "fee": 18000, "status": "Active", "icon": "bi-hdd-network" },
    { "id": "CCNP - Security", "title": "CCNP - Security", "code": "CCNPS", "target": "CCNP Security", "description": "Implementing and operating Cisco security technologies, covering firewalls, VPNs, web security, and endpoint protection.", "duration": "3.0 Months", "fee": 18000, "status": "Active", "icon": "bi-shield-lock" },
    { "id": "MTCNA", "title": "MTCNA", "code": "MTCNA", "target": "MikroTik Associate", "description": "MikroTik Certified Network Associate. RouterOS basics, routing, switching, firewall, NAT, DHCP, wireless, and bandwidth management.", "duration": "1.5 Months", "fee": 6000, "status": "Active", "icon": "bi-broadcast" },
    { "id": "MTCRE", "title": "MTCRE", "code": "MTCRE", "target": "MikroTik Routing Engineer", "description": "MikroTik Certified Routing Engineer. Advanced static and dynamic routing (OSPF), VPNs, point-to-point tunnels, and addressing.", "duration": "1.5 Months", "fee": 7000, "status": "Active", "icon": "bi-globe" },
    { "id": "MTCSE", "title": "MTCSE", "code": "MTCSE", "target": "MikroTik Security Engineer", "description": "MikroTik Certified Security Engineer. Network security mechanisms, threat mitigation, secure tunnels, and RouterOS hardening.", "duration": "1.5 Months", "fee": 8000, "status": "Active", "icon": "bi-shield-shaded" },
    { "id": "RHCSA", "title": "RHCSA", "code": "RHCSA", "target": "Red Hat Admin", "description": "Red Hat Certified System Administrator. Deploying, configuring, and maintaining Red Hat Enterprise Linux (RHEL) systems.", "duration": "2.0 Months", "fee": 8000, "status": "Active", "icon": "bi-cpu" },
    { "id": "RHCE", "title": "RHCE", "code": "RHCE", "target": "Red Hat Automation", "description": "Red Hat Certified Engineer. Automation of RHEL tasks using Ansible, system deployment automation, and configuration management.", "duration": "2.0 Months", "fee": 10000, "status": "Active", "icon": "bi-gear" },
    { "id": "FCP NSE4", "title": "FCP NSE4", "code": "NSE4", "target": "Fortinet Network Security", "description": "Fortinet Certified Professional in Network Security. FortiGate firewall setup, security policies, VPNs, and system monitoring.", "duration": "2.0 Months", "fee": 12000, "status": "Active", "icon": "bi-bricks" },
    { "id": "FCP NSE5", "title": "FCP NSE5", "code": "NSE5", "target": "Fortinet Security Analyst", "description": "Fortinet Certified Professional in Security Analyst. FortiAnalyzer and FortiManager deployment, threat detection, and log parsing.", "duration": "2.0 Months", "fee": 12000, "status": "Active", "icon": "bi-graph-up-arrow" },
    { "id": "CCNA & MTCNA", "title": "CCNA & MTCNA", "code": "CCMTC", "target": "Cisco & MikroTik Combo", "description": "Dual-certification program covering both Cisco and MikroTik systems, building solid foundational skills in routing and switching.", "duration": "3.0 Months", "fee": 15000, "status": "Active", "icon": "bi-link-45deg" }
]

def index(request):
    return render(request, 'frontend/index.html')

def about_background(request):
    return render(request, 'frontend/about/background.html')

def about_team(request):
    return render(request, 'frontend/about/team.html')

def service_network(request):
    return render(request, 'frontend/services/service-network.html')

def service_cloud(request):
    return render(request, 'frontend/services/service-cloud.html')

def service_hosting(request):
    return render(request, 'frontend/services/service-hosting.html')

def service_managed_it(request):
    return render(request, 'frontend/services/service-managed-it.html')

def service_business_suite(request):
    return render(request, 'frontend/services/service-business-suite.html')

def training(request):
    courses = []
    try:
        docs = db.collection('learn_courses').stream()
        for doc in docs:
            c = doc.to_dict()
            c['id'] = doc.id
            if c.get('status') == 'Active':
                courses.append(c)
        courses.sort(key=lambda x: x.get('title', ''))
    except Exception as e:
        print(f"Error fetching courses from Firestore: {e}")
        
    # If no courses fetched, use fallback list
    if not courses:
        courses = [c for c in FALLBACK_COURSES if c.get('status') == 'Active']
        
    return render(request, 'frontend/training.html', {'courses': courses})

def verify_certificate(request):
    cert_id = request.GET.get('id', '').strip()
    context = {}
    if cert_id:
        # standard prefix formatting
        full_cert_id = cert_id
        if not cert_id.upper().startswith('INTREX-CERT-'):
            full_cert_id = f"INTREX-CERT-{cert_id.upper()}"
        else:
            # ensure standard casing
            full_cert_id = f"INTREX-CERT-{cert_id[12:].upper()}"
            
        try:
            doc_ref = db.collection('learn_certificates').document(full_cert_id)
            doc_snap = doc_ref.get()
            if doc_snap.exists:
                cert_data = doc_snap.to_dict()
                
                # Format issue date nicely (e.g. "June 01, 2026")
                issue_date_str = cert_data.get('issueDate', '')
                formatted_date = issue_date_str
                try:
                    dt = datetime.datetime.strptime(issue_date_str, '%Y-%m-%d')
                    formatted_date = dt.strftime('%B %d, %Y')
                except Exception:
                    pass
                
                import urllib.parse
                origin = request.build_absolute_uri('/')[:-1]
                verify_url = f"{origin}/verify-certificate/?id={cert_data.get('certificateId', '')}"
                verify_url_encoded = urllib.parse.quote(verify_url)
                
                context = {
                    'certificate': cert_data,
                    'formatted_date': formatted_date,
                    'verify_url': verify_url,
                    'verify_url_encoded': verify_url_encoded,
                    'success': True,
                    'searched': True,
                    'cert_id_input': cert_id,
                }
            else:
                context = {
                    'success': False,
                    'searched': True,
                    'cert_id_input': cert_id,
                }
        except Exception as e:
            print(f"Error checking certificate in Firestore: {e}")
            context = {
                'success': False,
                'searched': True,
                'error': str(e),
                'cert_id_input': cert_id,
            }
    return render(request, 'frontend/verify-certificate.html', context)

# API endpoint for online registrations
@csrf_exempt
def register_course(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
        
    full_name = request.POST.get('fullName', '').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
    course = request.POST.get('course', '').strip()
    education = request.POST.get('education', '').strip()
    schedule = request.POST.get('schedule', '').strip()
    message = request.POST.get('message', '').strip()
    is_job_holder = request.POST.get('isJobHolder') == 'true'
    company_name = request.POST.get('companyName', '').strip()
    designation = request.POST.get('designation', '').strip()
    
    if not (full_name and email and phone and course and schedule):
        return JsonResponse({'status': 'error', 'message': 'Missing required fields.'}, status=400)
        
    try:
        # Generate unique REG key
        attempts = 0
        reg_key = ""
        while attempts < 10:
            attempts += 1
            candidate = f"REG-{random.randint(100000, 999999)}"
            doc_snap = db.collection('learn_online_registrations').document(candidate).get()
            if not doc_snap.exists:
                reg_key = candidate
                break
        if not reg_key:
            reg_key = f"REG-{random.randint(100000, 999999)}"
            
        db.collection('learn_online_registrations').document(reg_key).set({
            'registrationKey': reg_key,
            'fullName': full_name,
            'email': email,
            'phone': phone,
            'course': course,
            'education': education,
            'schedule': schedule,
            'message': message,
            'isJobHolder': is_job_holder,
            'companyName': company_name,
            'designation': designation,
            'createdAt': firestore.SERVER_TIMESTAMP
        })
        return JsonResponse({'status': 'success', 'key': reg_key})
    except Exception as e:
        print(f"Firestore registration write error: {e}")
        return JsonResponse({'status': 'error', 'message': 'Database insertion failed.'}, status=500)

# API endpoint for online inquiries
@csrf_exempt
def inquire_course(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
        
    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
    subject = request.POST.get('subject', '').strip()
    message = request.POST.get('message', '').strip()
    source = request.POST.get('source', 'training-page').strip()
    
    if not (name and email and message):
        return JsonResponse({'status': 'error', 'message': 'Missing required inquiry fields.'}, status=400)
        
    try:
        if source == 'training-page':
            # Save to learn_online_registrations instead
            attempts = 0
            reg_key = ""
            while attempts < 10:
                attempts += 1
                candidate = f"REG-{random.randint(100000, 999999)}"
                doc_snap = db.collection('learn_online_registrations').document(candidate).get()
                if not doc_snap.exists:
                    reg_key = candidate
                    break
            if not reg_key:
                reg_key = f"REG-{random.randint(100000, 999999)}"
                
            db.collection('learn_online_registrations').document(reg_key).set({
                'registrationKey': reg_key,
                'fullName': name,
                'email': email,
                'phone': phone,
                'course': subject,
                'education': '',
                'schedule': 'Inquiry',
                'message': message,
                'isJobHolder': False,
                'companyName': '',
                'designation': '',
                'createdAt': firestore.SERVER_TIMESTAMP
            })
            return JsonResponse({'status': 'success', 'key': reg_key})
        else:
            # Generate unique INQ key
            attempts = 0
            inq_key = ""
            while attempts < 10:
                attempts += 1
                candidate = f"INQ-{random.randint(100000, 999999)}"
                doc_snap = db.collection('learn_online_inquiries').document(candidate).get()
                if not doc_snap.exists:
                    inq_key = candidate
                    break
            if not inq_key:
                inq_key = f"INQ-{random.randint(100000, 999999)}"
                
            db.collection('learn_online_inquiries').document(inq_key).set({
                'inquiryKey': inq_key,
                'name': name,
                'email': email,
                'phone': phone,
                'subject': subject,
                'message': message,
                'source': source,
                'status': 'New',
                'createdAt': firestore.SERVER_TIMESTAMP
            })
            return JsonResponse({'status': 'success', 'key': inq_key})
    except Exception as e:
        print(f"Firestore inquiry write error: {e}")
        return JsonResponse({'status': 'error', 'message': 'Database insertion failed.'}, status=500)

def contact(request):
    return render(request, 'frontend/contact.html')
