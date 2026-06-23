# Intrex Digital Hub & ERP System

Welcome to the **Intrex Digital Hub & ERP System** codebase. This repository contains the public-facing platform for Intrex Digital Hub (offering digital services, training programs, and certificate verification) along with a fully integrated, modular Enterprise Resource Planning (ERP) subsystem.

---

## 🚀 System Architecture & Tech Stack

- **Backend Framework:** Django 4.2 (Python 3.9+)
- **Primary Database (Business Operations):** Google Firebase Firestore (NoSQL, real-time sync for ERP modules)
- **Secondary Database (User Auth):** Local SQLite3 (`db.sqlite3` for Django session data, user profiles, and permission groups)
- **Frontend Technologies:** HTML5, CSS3 (Custom Glassmorphism and CSS variables), Vanilla JavaScript, AJAX, Isotope Masonry, GSAP, Swiper, AOS, GLightbox, and FontAwesome.

---

## 📂 File Structure

Below is the directory mapping of the project codebase:

```text
intrex_digital_hub/
├── accounts/                  # User accounts, custom permission groups, and decorators (@module_access)
├── billing/                   # Billing & invoicing ERP module
├── config/                    # Django root project configuration (settings.py, urls.py, wsgi.py)
│   └── firebase.py            # Firebase Firestore client initialization
├── frontend/                  # Public website views & controllers
├── hrm/                       # HR Management ERP module (Firestore CRUD controllers and views)
├── inventory/                 # Inventory & stock tracking ERP module
├── investment/                # Investment & finance tracking ERP module
├── solutions/                 # Solutions delivery ERP module
├── static/                    # Global static assets
│   ├── css/                   # Stylesheets for public site and ERP dashboard
│   ├── images/                # Visual assets, branding icons, and dynamic banners
│   ├── js/                    # Client-side scripts (custom.js, calculations, calendar rendering)
│   └── vendors/               # External libraries (AOS, Swiper, GLightbox, GSAP)
├── templates/                 # Django HTML Templates
│   ├── accounts/              # User management templates
│   ├── billing/               # Billing and invoice generation templates
│   ├── erp/                   # Shared ERP common layouts, sidebar navigation, and 403 Forbidden pages
│   ├── erp_base.html          # Main layout extending to all ERP modules
│   ├── frontend/              # Landing page, training catalog, contact, and verify-certificate views
│   ├── frontend.html          # Main layout extending to all public landing pages
│   ├── hrm/                   # HR Management templates
│   │   ├── overview.html      # HR Admin dashboard (Stats grid & recent activity)
│   │   ├── employee_database.html # Multi-step wizard employee database CRUD
│   │   ├── recruitment.html   # Recruitment pipeline (Candidates, shortlists, selections)
│   │   ├── attendance.html    # Attendance logging & corrected logs list
│   │   ├── leave.html         # Leave calendar (JS calendar), holidays, weekend settings
│   │   ├── payroll.html       # Salary advances, pay periods, and payslip preview
│   │   └── reports.html       # Attendance, Leave & Payroll reports preview + CSV Export
│   └── registration/          # Login and session registration templates
├── create_admin.py            # Helper script to bootstrap/reset local admin user
├── firebase-credentials.json  # Google Cloud Firebase service account key (gitignore in production)
├── manage.py                  # Django administrative task manager
├── requirements.txt           # Python application dependencies
└── README.md                  # System documentation
```

---

## 🛠️ Main Modules & Features

### 1. Public-Facing Website (`frontend`)
- **Landing Page:** Interactive, modern home page featuring animations, client testimonial swipers, and service portfolios.
- **Contact Hub:** Embedded inquiry submitter with AJAX-driven verification.
- **Training Catalog:** Lists available software engineering, marketing, and design courses.
- **Certificate Verification:** Online portal allowing students/employers to verify issued course credentials.

### 2. ERP System Core (`config`, `accounts`)
- **Unified Sidebar Layout:** Responsive sidebar providing quick access to permitted modules.
- **Access Control Decorator (`@module_access`):** Granular permission-based access control protecting views at the routing level. ERP superusers/staff bypass restriction checks automatically.

### 3. HR Management ERP (`hrm`)
- **Overview Dashboard:** Visual summary of headcount, active staff, leave percentages, and vacancy openings.
- **Employee Database:** Advanced 4-step wizard to register employees (Basic details, Banking/Salary structure calculations, Personal info, Biological/Emergency contact details) with inline profile updating.
- **Recruitment Pipeline:** Complete candidate pipeline tracking from Application -> Shortlist -> Interview -> Offer/Selection.
- **Attendance Registry:** Registers employee daily entry/exit points and displays missing log logs for correction.
- **Leave Calendar & Policies:** Interactive JS leave planner calendar, public holiday lists, and weekend policy trackers.
- **Payroll & Pay Slips:** Period-based pay calculations, deduction trackers for pending advances, and dynamic payslip previews.
- **Analytical Reports:** Generates summaries for attendance records, estimated payroll, and leave histories with instant client-side CSV downloads.

---

## 🔧 Setup & Installation

### 1. Clone the project and configure environment
Set up your local configuration variables in a `.env` file at the project root (or as environment variables in your hosting provider's dashboard):
```env
DJANGO_SECRET_KEY=your_secret_key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=*

# For local development:
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json

# For cloud production environments (e.g., Render, Heroku) where gitignores prevent credential files:
# Add an environment variable named FIREBASE_CREDENTIALS_JSON containing the full stringified JSON content of your Firebase service account key file.
# FIREBASE_CREDENTIALS_JSON='{"type": "service_account", "project_id": "...", ...}'
```

### 2. Activate virtual environment
```bash
source venv/bin/activate
```

### 3. Run migrations (SQLite3 Auth Database)
```bash
python manage.py migrate
```

### 4. Create an administrator
Bootstrap the database with a default developer administrator:
```bash
python create_admin.py
# Default credentials: username "admin", password "admin123"
```

### 5. Launch the Server
```bash
python manage.py runserver
```
The website will be available at `http://127.0.0.1:8000/` and the ERP system dashboard at `http://127.0.0.1:8000/hrm/`.
