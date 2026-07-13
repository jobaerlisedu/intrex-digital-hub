from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from config.logger import get_logger
from training.models import Course, Certificate, Registration, Inquiry

frontend_logger = get_logger('frontend')

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
    { "id": "CCNA & MTCNA", "title": "CCNA & MTCNA", "code": "CCMTC", "target": "Cisco & MikroTik Combo", "description": "Dual-certification program covering both Cisco and MikroTik systems, building solid foundational skills in routing and switching.", "duration": "3.0 Months", "fee": 15000, "status": "Active", "icon": "bi-link-45deg" },
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

@ensure_csrf_cookie
def training(request):
    courses = list(Course.objects.filter(is_active=True, status='Active').values(
        'pk', 'title', 'code', 'target', 'description', 'duration', 'fee', 'status', 'icon',
    ))
    for c in courses:
        c['id'] = str(c.pop('pk'))
        c['fee'] = float(c['fee'])
    courses.sort(key=lambda x: x.get('title', ''))
    if not courses:
        courses = FALLBACK_COURSES
    return render(request, 'frontend/training.html', {'courses': courses})

def verify_certificate(request):
    cert_id = request.GET.get('id', '').strip()
    context = {}
    if cert_id:
        full_cert_id = cert_id
        if not cert_id.upper().startswith('INTREX-CERT-'):
            full_cert_id = f"INTREX-CERT-{cert_id.upper()}"
        else:
            full_cert_id = f"INTREX-CERT-{cert_id[12:].upper()}"

        cert = Certificate.objects.filter(certificate_id=full_cert_id).first()
        if cert:
            import datetime as dt
            formatted_date = ''
            if cert.issue_date:
                try:
                    formatted_date = cert.issue_date.strftime('%B %d, %Y')
                except Exception:
                    formatted_date = str(cert.issue_date)
            import urllib.parse
            origin = request.build_absolute_uri('/')[:-1]
            verify_url = f"{origin}/verify-certificate/?id={cert.certificate_id}"
            verify_url_encoded = urllib.parse.quote(verify_url)
            context = {
                'certificate': {
                    'certificateId': cert.certificate_id,
                    'studentName': cert.student_name,
                    'courseName': cert.course_name,
                    'issueDate': str(cert.issue_date) if cert.issue_date else '',
                    'grade': cert.grade or '',
                    'status': cert.status,
                },
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
    return render(request, 'frontend/verify-certificate.html', context)

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

    if not (full_name and email and phone and course):
        return JsonResponse({'status': 'error', 'message': 'Missing required fields.'}, status=400)

    try:
        reg = Registration.objects.create(
            full_name=full_name,
            email=email,
            phone=phone,
            education=education,
            schedule=schedule,
            message=message,
            is_job_holder=is_job_holder,
            company_name=company_name,
            designation=designation,
        )
        return JsonResponse({'status': 'success', 'key': str(reg.pk)})
    except Exception as e:
        frontend_logger.error(f"Registration write error: {e}")
        return JsonResponse({'status': 'error', 'message': 'Database insertion failed.'}, status=500)

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
            reg = Registration.objects.create(
                full_name=name,
                email=email,
                phone=phone,
                course=subject,
                schedule='Inquiry',
                message=message,
                is_job_holder=False,
            )
            return JsonResponse({'status': 'success', 'key': str(reg.pk)})
        else:
            inq_count = Inquiry.objects.count()
            inq_key = f"INQ-{inq_count + 100001}"
            Inquiry.objects.create(
                inquiry_key=inq_key,
                name=name,
                email=email,
                phone=phone,
                subject=subject,
                message=message,
                source=source,
                status='New',
            )
            return JsonResponse({'status': 'success', 'key': inq_key})
    except Exception as e:
        frontend_logger.error(f"Inquiry write error: {e}")
        return JsonResponse({'status': 'error', 'message': 'Database insertion failed.'}, status=500)

@ensure_csrf_cookie
def contact(request):
    return render(request, 'frontend/contact.html')
