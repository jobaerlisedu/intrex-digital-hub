# Local Setup & Development Guide

This guide contains step-by-step instructions for developers to install, configure, and run the Intrex ERP/CRM platform locally.

---

## 1. Prerequisites

Before starting, ensure your local development machine has the following tools installed:
*   **Operating System**: Linux/macOS preferred (WSL supported on Windows).
*   **Python**: Version `3.8` up to `3.11`.
*   **Database**: SQLite3 (pre-installed with Python) and MySQL (for ERP business data).
*   **MySQL Client**: (Optional) For backup management and direct database access.

---

## 2. Step-by-Step Setup

### Step A: Clone the Repository
Clone the codebase and navigate to the project directory:
```bash
git clone <repository_url> erp-intrex-digital
cd erp-intrex-digital
```

### Step B: Create a Virtual Environment
Create and activate a Python virtual environment to isolate project packages:
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step C: Install Dependencies
Upgrade pip and install all required modules listed in `requirements.txt`:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step D: Configure Environment Variables
Create a `.env` file in the project root:
```bash
touch .env
```
Populate `.env` with the following variables:
```ini
DJANGO_SECRET_KEY=local_development_secret_key_change_me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
DB_ENGINE=django.db.backends.mysql
DB_NAME=intrex_erp_dev
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

### Step E: Configure MySQL Database
1. Ensure MySQL is installed and running on your machine.
2. Create a new MySQL database for the ERP platform:
   ```sql
   CREATE DATABASE intrex_erp_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. Create a MySQL user and grant privileges:
   ```sql
   CREATE USER 'erp_user'@'localhost' IDENTIFIED BY 'your_password';
   GRANT ALL PRIVILEGES ON intrex_erp_dev.* TO 'erp_user'@'localhost';
   FLUSH PRIVILEGES;
   ```
4. Update the `.env` file with the correct database credentials.
> [!WARNING]
> Never commit `.env` to version control. It is automatically ignored in the `.gitignore`.

---

## 3. Database Initialization

### Step A: Database Migrations
Run Django migrations to create the local SQLite schema (holds User accounts, active session records, and cryptographic audit logs):
```bash
python manage.py migrate
```

### Step B: Bootstrap Admin Operator
The system is configured to automatically check for and create a default admin operator on startup. Alternatively, you can run the bootstrap script manually to generate default credentials:
```bash
python create_admin.py
```
*   **Default Username**: `admin`
*   **Default Password**: `adminpass`

---

## 4. Run the Development Server

Start the Django local development server:
```bash
python manage.py runserver
```
Navigate to your web browser and open:
*   **Corporate Landing Page**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
*   **ERP Dashboard**: [http://127.0.0.1:8000/erp/](http://127.0.0.1:8000/erp/) (logs in using the admin account).

---

## 5. Verification & Testing

Verify that your local environment passes the automated unit test suite.

Run Django tests:
```bash
python manage.py test
```
The test runner will create a temporary local database, test view routings, check permission decorators, and verify Django ORM connection handles.