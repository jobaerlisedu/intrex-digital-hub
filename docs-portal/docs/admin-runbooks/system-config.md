# System Configuration Guide

This runbook documents the global environment settings, security flags, and backend integrations required to configure the Intrex ERP application.

---

## 1. Environment Variables Configuration

The application loads its configuration settings dynamically from the `.env` file in the root workspace directory. Ensure these variables are set correctly for your target deployment environment.

| Environment Variable | Recommended Value (Prod) | Default Fallback (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `DJANGO_SECRET_KEY` | *Generated 50-character key* | *Insecure local key* | Security salt for cryptographic signatures and session tokens. |
| `DJANGO_DEBUG` | `False` | `True` | Toggles detailed traceback pages. Must be `False` in production. |
| `DJANGO_ALLOWED_HOSTS` | `erp.intrex.digital` | `*` or `localhost` | Comma-separated list of host/domain names that this Django site can serve. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://erp.intrex.digital` | `http://localhost:8000` | Comma-separated list of trusted origins for safe cross-site requests. |
| `DB_ENGINE` | `django.db.backends.mysql` | `django.db.backends.mysql` | Django ORM database engine for MySQL. |
| `DB_NAME` | `intrex_erp` | `intrex_erp_dev` | Name of the MySQL database. |
| `DB_USER` | `erp_user` | `root` | MySQL database user. |
| `DB_PASSWORD` | *Secure password* | *None* | MySQL database password. |
| `DB_HOST` | `localhost` | `127.0.0.1` | MySQL server hostname or IP address. |
| `DB_PORT` | `3306` | `3306` | MySQL server port. |

---

## 2. Database Configuration

The application implements a hybrid data layer:

### A. Local Relational Engine (SQLite3)
Manages django sessions, user groups, and compliance logs.
*   **Engine**: `django.db.backends.sqlite3`
*   **Path**: `BASE_DIR / 'db.sqlite3'`
*   **Configuration Location**: `config/settings.py` -> `DATABASES` settings block.

### B. Core ERP Engine (MySQL via Django ORM)
Manages ERP transactional and master business entities.
*   **Initialization**: Configured inside `config/settings.py` -> `DATABASES` settings block.
*   **Connection Logic**:
    1. Reads the `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` variables from the `.env` file.
    2. Falls back to the default SQLite configuration if MySQL environment variables are not set.
    3. Django ORM handles connection pooling and query execution automatically.

---

## 3. Security & CSRF Origins Validation

To protect against Cross-Site Request Forgery (CSRF) attacks, Django validates HTTP Origin request headers.

To simplify deployments, the application automatically computes safe origins using the following mechanisms:
1. **Host-to-Origin Parsing**: The application loops through all hostnames configured in `DJANGO_ALLOWED_HOSTS` and prepends both `https://` and `http://` variants to the CSRF trust list.
2. **Render Cloud Platform Detection**: If the environment variable `RENDER_EXTERNAL_URL` is set, the system automatically appends the target deployment URL to allow immediate operations on Render subdomains.
3. **Hardcoded Secure Fallbacks**: The URLs `https://erp-intrex-digital.onrender.com` and its `http` counterpart are registered by default to guarantee standard sandbox deployments pass origin validation checks.

---

## 4. Production Deployment Checklist

Before deploying the platform instance to production:
1. Set `DJANGO_DEBUG=False`.
2. Generate a secure `DJANGO_SECRET_KEY` and store it inside environment variables (never hardcode in settings files).
3. Specify exact, restricted hostnames in `DJANGO_ALLOWED_HOSTS`.
4. Verify that SQLite files are placed on a persistent disk volume (if using container services like Docker or Render) so that audit logs and user accounts are not wiped on service redeployments.