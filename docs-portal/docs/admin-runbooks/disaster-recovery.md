# Disaster Recovery & Backup Runbook

This runbook outlines the disaster recovery procedures for the Intrex ERP/CRM platform. It details backup and restoration operations for both the local SQLite database (User Access, Sessions, & Audits) and the MySQL database (ERP Business Ledger & Master Data).

---

## 1. Disaster Recovery Parameters

To meet business continuity compliance, system administrators must operate under the following parameters:
*   **Recovery Point Objective (RPO)**: 24 hours (maximum acceptable data loss).
*   **Recovery Time Objective (RTO)**: 1 hour (maximum acceptable downtime to restore services).

---

## 2. Local SQLite Backup & Restore (Auth, Sessions & Audits)

The file `db.sqlite3` is located in the root of the workspace directory. Because the system can write logs continuously, simple file copying can cause database write locks or corruption.

### A. SQLite Backup Procedure (Cron-ready)
Use SQLite's online backup tool to copy the database safely without stopping the Django web service:
```bash
sqlite3 db.sqlite3 ".backup '/var/backups/erp/sqlite/db_backup_$(date +%F_%H%M%S).sqlite3'"
```

### B. SQLite Restore Procedure
1. Stop the Django application server:
   ```bash
   pkill -f "manage.py runserver"
   ```
2. Rename the active compromised/corrupt database:
   ```bash
   mv db.sqlite3 db.sqlite3.corrupted
   ```
3. Copy the target backup file into place:
   ```bash
   cp /var/backups/erp/sqlite/db_backup_2026-06-27_120000.sqlite3 db.sqlite3
   ```
4. Restart the web service:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

---

## 3. MySQL Backup & Restore (ERP Core Data)

All business modules (HRM, Inventory, Investment, Billing, Solutions, Training) write to MySQL via Django ORM.

### A. MySQL Dump Procedure
Exports are dispatched using `mysqldump`:
```bash
mysqldump -u erp_user -p intrex_erp > /var/backups/erp/mysql/intrex_erp_$(date +%F).sql
```
*To automate this, schedule it via a cron job.*

### B. MySQL Import (Restoration) Procedure
> [!IMPORTANT]
> MySQL imports will overwrite existing tables. Ensure you have a backup of the current state before restoring.

To import the database state:
```bash
mysql -u erp_user -p intrex_erp < /var/backups/erp/mysql/intrex_erp_2026-06-27.sql
```

---

## 4. Disaster Recovery Scenarios

### Scenario A: SQLite Database Corruption
*   **Symptom**: Django prints `sqlite3.DatabaseError: database disk image is malformed` or cryptographic log chain audits fail (`COMPROMISED`).
*   **Resolution**: 
    1. Immediately stop the Django server.
    2. Run the SQLite Restore Procedure using the latest clean daily backup.
    3. Run a manual cryptographic integrity check via the Admin Dashboard.

### Scenario B: MySQL Database Corruption
*   **Symptom**: Page loads return MySQL connectivity errors, or table data is missing.
*   **Resolution**:
    1. Check the MySQL server status.
    2. If data was accidentally deleted, restore from the latest verified MySQL dump file using `mysql` CLI.

### Scenario C: Database Credential Compromise
*   **Symptom**: Unauthorized access detected in MySQL audit trails.
*   **Resolution**:
    1. Log in to the MySQL server.
    2. Revoke the compromised user credentials and create new ones.
    3. Update the `.env` file with the new database credentials and restart Django.

---

## 5. Automated Backup Script

Save the script below to `/usr/local/bin/erp-backup.sh` and set up a root cron job (`crontab -e`) to execute daily at 02:00:
`0 2 * * * /usr/local/bin/erp-backup.sh`

```bash
#!/bin/bash
# Backup Configuration
BACKUP_DIR="/var/backups/erp"
SQLITE_BACKUP_DIR="$BACKUP_DIR/sqlite"
MYSQL_BACKUP_DIR="$BACKUP_DIR/mysql"
DATE=$(date +%F_%H%M%S)

mkdir -p "$SQLITE_BACKUP_DIR" "$MYSQL_BACKUP_DIR"

# 1. SQLite Online Backup
sqlite3 /home/hsjb/Documents/Website/erp-intrex-digital/db.sqlite3 ".backup '$SQLITE_BACKUP_DIR/db_$DATE.sqlite3'"

# 2. MySQL Dump
mysqldump -u erp_user -p'intrex_erp_password' intrex_erp > "$MYSQL_BACKUP_DIR/intrex_erp_$DATE.sql"

# 3. Clean up local backups older than 14 days
find "$SQLITE_BACKUP_DIR" -type f -name "*.sqlite3" -mtime +14 -delete
find "$MYSQL_BACKUP_DIR" -type f -name "*.sql" -mtime +14 -delete

echo "Intrex ERP backup completed on $DATE"
```