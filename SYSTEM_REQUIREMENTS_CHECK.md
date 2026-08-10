# System Requirements Check
## Automated Rule-Based Admission Decision System
**Project:** CUSTECH Admission System — Emmanuel Onucheojo Ocheme (22L1SE0086)  
**Stack:** Python · Flask · SQLAlchemy · MySQL · Bootstrap 5  
**Purpose:** Run every check below before starting development or deployment. Each section tells you exactly what to verify, what command to run, and what a passing result looks like.

---

## How to Use This File

Work through each section top to bottom. For every item:
- ✅ **PASS** — requirement is met, continue
- ❌ **FAIL** — requirement is not met, follow the fix note before proceeding
- ⚠️ **WARN** — minimum met but upgrade recommended

Paste this file to your AI coding assistant and ask it to run all checks automatically, then report back a status table.

---

## 1. Operating System

| Check | Requirement | Command |
|-------|-------------|---------|
| OS platform | Windows 10/11 · Ubuntu 20.04+ · macOS 12+ | `python -c "import platform; print(platform.platform())"` |
| OS architecture | 64-bit | `python -c "import platform; print(platform.architecture())"` |

**Passing values:**
- Windows: `Windows-10-...` or `Windows-11-...`
- Linux: `Linux-5.x` or higher (Ubuntu 20.04+)
- macOS: `macOS-12` or higher
- Architecture: `64bit`

---

## 2. Python

| Check | Minimum | Recommended | Command |
|-------|---------|-------------|---------|
| Python version | 3.8 | 3.11+ | `python --version` or `python3 --version` |
| pip available | Any | Latest | `pip --version` |
| venv support | Required | — | `python -m venv --help` |

**Passing values:**
```
Python 3.8.x or higher
pip 23.x or higher
```

**Fix if failing:**
- Download Python from https://python.org/downloads
- On Ubuntu: `sudo apt install python3 python3-pip python3-venv`
- On macOS: `brew install python3`

**Critical note:** The project uses a virtual environment. All packages must be installed inside it:
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

---

## 3. Core Python Packages

Run this block inside your activated virtual environment. Each package maps directly to a system module.

### 3.1 Web Framework & Extensions

| Package | Min Version | Maps To | Install Command |
|---------|-------------|---------|-----------------|
| `flask` | 2.0 | Core application framework, routing, Blueprints | `pip install flask>=2.0` |
| `flask-sqlalchemy` | 3.0 | ORM — all database models | `pip install flask-sqlalchemy>=3.0` |
| `flask-migrate` | 4.0 | Database schema migrations | `pip install flask-migrate>=4.0` |
| `flask-login` | 0.6 | Session management, role-based route protection | `pip install flask-login>=0.6` |
| `flask-wtf` | 1.1 | Form handling + CSRF protection on all forms | `pip install flask-wtf>=1.1` |
| `wtforms` | 3.0 | Form field validators | `pip install wtforms>=3.0` |

### 3.2 Database

| Package | Min Version | Maps To | Install Command |
|---------|-------------|---------|-----------------|
| `pymysql` | 1.0 | MySQL production database connector | `pip install pymysql>=1.0` |
| `cryptography` | 41.0 | Required by PyMySQL for SSL connections | `pip install cryptography>=41.0` |
| `alembic` | 1.12 | Installed with flask-migrate; handles migration files | *(auto-installed)* |

> SQLite is used during development — it ships with Python and needs no separate install.

### 3.3 Security

| Package | Min Version | Maps To | Install Command |
|---------|-------------|---------|-----------------|
| `bcrypt` | 4.0 | Password hashing for all user accounts | `pip install bcrypt>=4.0` |
| `flask-bcrypt` | 1.0 | Flask integration for bcrypt | `pip install flask-bcrypt>=1.0` |

### 3.4 Utilities & Export

| Package | Min Version | Maps To | Install Command |
|---------|-------------|---------|-----------------|
| `python-dotenv` | 1.0 | Loads `.env` config file at startup | `pip install python-dotenv>=1.0` |
| `openpyxl` | 3.1 | Excel export in reporting module | `pip install openpyxl>=3.1` |
| `reportlab` | 4.0 | PDF export (reports + admission letters) | `pip install reportlab>=4.0` |
| `requests` | 2.31 | HTTP calls to Mock JAMB CAPS API | `pip install requests>=2.31` |

### 3.5 Verify All Packages At Once

After activating your virtualenv and installing everything, run this single check:

```bash
python -c "
import flask, flask_sqlalchemy, flask_migrate, flask_login, flask_wtf
import wtforms, pymysql, bcrypt, dotenv, openpyxl, reportlab, requests
import alembic

packages = {
    'flask': flask.__version__,
    'flask_sqlalchemy': flask_sqlalchemy.__version__,
    'flask_migrate': flask_migrate.__version__,
    'flask_login': flask_login.__version__,
    'flask_wtf': flask_wtf.__version__,
    'wtforms': wtforms.__version__,
    'pymysql': pymysql.__version__,
    'bcrypt': bcrypt.__version__,
    'openpyxl': openpyxl.__version__,
    'reportlab': reportlab.Version,
    'requests': requests.__version__,
    'alembic': alembic.__version__,
}
for name, version in packages.items():
    print(f'  {name}: {version}')
print('All packages found.')
"
```

---

## 4. Database — MySQL (Production)

### 4.1 MySQL Server

| Check | Requirement | Command |
|-------|-------------|---------|
| MySQL version | 8.0 or later | `mysql --version` |
| Server running | Active | `mysqladmin -u root -p status` |
| Root or admin access | Required for setup | `mysql -u root -p -e "SELECT VERSION();"` |

**Passing output:**
```
mysql  Ver 8.0.x ...
Uptime: ...   Threads: ...   Questions: ...
```

**Fix if failing (Ubuntu):**
```bash
sudo apt install mysql-server
sudo systemctl start mysql
sudo mysql_secure_installation
```

**Fix if failing (Windows):**
- Download MySQL Installer from https://dev.mysql.com/downloads/installer/
- Install "MySQL Server 8.0" + "MySQL Workbench"

**Fix if failing (macOS):**
```bash
brew install mysql
brew services start mysql
```

### 4.2 Create the Project Database

Run these commands in the MySQL shell once the server is running:

```sql
CREATE DATABASE admission_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'admission_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON admission_db.* TO 'admission_user'@'localhost';
FLUSH PRIVILEGES;
```

**Verify:**
```sql
SHOW DATABASES;
-- Should list: admission_db
SELECT user, host FROM mysql.user WHERE user = 'admission_user';
-- Should return one row
```

### 4.3 SQLite (Development Only)

SQLite is built into Python 3.x. Verify:
```bash
python -c "import sqlite3; print(sqlite3.sqlite_version)"
# Expected: 3.x.x
```

---

## 5. Environment Configuration (`.env` File)

The project reads configuration from a `.env` file at the project root. The file must exist and contain all of the following variables before `flask run` or `python run.py` will work.

### 5.1 Required `.env` Variables

```env
# Flask core
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-this-in-production

# Database — use SQLite for development, MySQL for production
DATABASE_URL=sqlite:///admission.db
# DATABASE_URL=mysql+pymysql://admission_user:your_password@localhost/admission_db

# File uploads
UPLOAD_FOLDER=uploads

# Admission calculation constants (do not change without updating rule base)
JAMB_DIVISOR=8.0
POST_UTME_DIVISOR=4.0
MIN_UTME_SCORE=140
MIN_OLEVEL_CREDITS=5
MAX_OLEVEL_SITTINGS=2

# Mock JAMB CAPS API endpoint
JAMB_API_BASE_URL=http://localhost:5001/api/jamb
JAMB_API_KEY=mock-api-key-for-development

# Grade point mappings (O'Level grades to points)
GRADE_A1=8
GRADE_B2=7
GRADE_B3=6
GRADE_C4=5
GRADE_C5=4
GRADE_C6=3
GRADE_D7=2
GRADE_E8=1
GRADE_F9=0

# Quota allocations (must sum to 100)
MERIT_QUOTA=45
CATCHMENT_QUOTA=35
ELDS_QUOTA=20
```

### 5.2 Verify `.env` Is Loaded

```bash
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
required = [
    'SECRET_KEY', 'DATABASE_URL', 'UPLOAD_FOLDER',
    'JAMB_DIVISOR', 'POST_UTME_DIVISOR', 'MIN_UTME_SCORE',
    'MIN_OLEVEL_CREDITS', 'MAX_OLEVEL_SITTINGS',
    'JAMB_API_BASE_URL', 'MERIT_QUOTA', 'CATCHMENT_QUOTA', 'ELDS_QUOTA'
]
missing = [k for k in required if not os.getenv(k)]
if missing:
    print(f'MISSING: {missing}')
else:
    print('All required env vars present.')
"
```

---

## 6. Project Folder Structure

The project must match this exact layout before Flask can initialize correctly. Ask your AI assistant to verify every file and folder exists:

```
admission_system/
├── app/
│   ├── __init__.py              ← Application factory (required)
│   ├── forms.py                 ← WTForms classes
│   ├── models.py                ← SQLAlchemy models (12 entities)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── admin.py             ← Admin dashboard, programme management
│   │   ├── admission.py         ← Admission processing, inference engine calls
│   │   └── auth.py              ← Login, logout, session handling
│   ├── services/
│   │   ├── __init__.py
│   │   ├── candidate_processor.py  ← Rule-based inference engine (CORE)
│   │   └── merit_list.py           ← Ranked merit list generation
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   ├── templates/
│   │   ├── admin/
│   │   ├── auth/
│   │   ├── errors/
│   │   └── base.html
│   └── utils/
│       ├── __init__.py
│       ├── helpers.py
│       └── seed.py
├── instance/                    ← Flask instance folder (auto-created)
├── migrations/                  ← Auto-generated by flask db init
├── uploads/                     ← Must exist and be writable
├── config.py                    ← Application configuration classes
├── requirements.txt             ← All pip dependencies
├── run.py                       ← Application entry point
├── .env                         ← Environment variables (never commit this)
├── .env.example                 ← Template for .env
└── .gitignore
```

**Check that uploads/ exists and is writable:**
```bash
python -c "
import os
path = 'uploads'
os.makedirs(path, exist_ok=True)
test_file = os.path.join(path, '.write_test')
try:
    with open(test_file, 'w') as f:
        f.write('test')
    os.remove(test_file)
    print(f'{path}/ exists and is writable.')
except Exception as e:
    print(f'FAIL: {e}')
"
```

---

## 7. Database Models — Entity Verification

The `models.py` must define all 12 entities below. Ask your AI assistant to confirm each class exists in the file:

| Model Class | Table Name | Key Fields | Used By |
|-------------|------------|------------|---------|
| `AcademicSession` | `academic_sessions` | `name`, `is_active`, `start_date`, `end_date` | All admission records |
| `University` | `universities` | `name`, `jamb_divisor`, `post_utme_divisor`, `min_utme_score`, `min_olevel_credits` | System-wide config |
| `Faculty` | `faculties` | `name`, `university_id` | Programme grouping |
| `Programme` | `programmes` | `name`, `faculty_id`, `merit_slots`, `catchment_slots`, `elds_slots`, `utme_cutoff` | Rule-based evaluation |
| `Candidate` | `candidates` | `utme_score`, `state_of_origin`, `programme_id`, `application_category` | Inference engine input |
| `OLevelResult` | `olevel_results` | `candidate_id`, `subject`, `grade` | O'Level checks |
| `AdmissionRule` | `admission_rules` | `programme_id`, `required_subjects`, `min_credits` | Rule configuration |
| `AdmissionRecord` | `admission_records` | `candidate_id`, `status`, `quota_category`, `aggregate_score`, `approval_stage` | Decision output |
| `CatchmentState` | `catchment_states` | `state_name`, `university_id` | Quota classification |
| `ELDSState` | `elds_states` | `state_name` | Quota classification |
| `User` | `users` | `username`, `password_hash`, `role` | Authentication |
| `AuditLog` | `audit_logs` | `user_id`, `action`, `target`, `timestamp` | Audit trail |

**Verify models load without error:**
```bash
python -c "
from app import create_app
from app.models import (AcademicSession, University, Faculty, Programme,
    Candidate, OLevelResult, AdmissionRule, AdmissionRecord,
    CatchmentState, ELDSState, User, AuditLog)
print('All 12 models imported successfully.')
"
```

---

## 8. Flask Application Factory

The app must initialize correctly with all extensions registered.

**Check:**
```bash
python -c "
from app import create_app
app = create_app()
print('Extensions registered:')
print(f'  SQLAlchemy: {\"db\" in app.extensions}')
print(f'  Migrate: {\"migrate\" in app.extensions}')
print(f'  Login Manager: {\"login_manager\" in app.extensions}')
print(f'  CSRF: {\"csrf\" in app.extensions or \"flask_wtf\" in str(app.extensions)}')
print('Blueprints:')
for bp in app.blueprints:
    print(f'  {bp}')
"
```

**Expected output:**
```
Extensions registered:
  SQLAlchemy: True
  Migrate: True
  Login Manager: True
  CSRF: True
Blueprints:
  auth
  admin
  admission
```

---

## 9. Database Migration Setup

Run these commands in order. Each must succeed before running the next.

```bash
# Step 1 — initialize migrations folder (only once, first time)
flask db init
# Expected: "Creating directory .../migrations ... done"

# Step 2 — generate migration from models
flask db migrate -m "initial schema"
# Expected: "Generating .../migrations/versions/xxxx_initial_schema.py"

# Step 3 — apply migration to database
flask db upgrade
# Expected: "Running upgrade  -> xxxx, initial schema"
```

**Verify tables were created:**
```bash
python -c "
from app import create_app
from app.extensions import db
app = create_app()
with app.app_context():
    tables = db.engine.table_names()
    expected = ['academic_sessions','universities','faculties','programmes',
                'candidates','olevel_results','admission_rules',
                'admission_records','catchment_states','elds_states',
                'users','audit_logs']
    missing = [t for t in expected if t not in tables]
    if missing:
        print(f'MISSING TABLES: {missing}')
    else:
        print(f'All {len(expected)} tables created successfully.')
        for t in tables:
            print(f'  - {t}')
"
```

---

## 10. Flask CLI Commands

The project registers custom CLI commands. Verify each exists:

```bash
flask --help
# Should list: seed, generate-candidates, create-admin
```

**Test each command:**

```bash
# Seed initial data (university, faculties, catchment/ELDS states, admin user)
flask seed
# Expected: "Database seeded successfully."

# Generate test candidates (replace 10 with any number)
flask generate-candidates 10
# Expected: "Generated 10 test candidates."

# Create an admin user interactively
flask create-admin
# Expected: prompts for username and password, then "Admin user created."
```

**Default admin credentials (development only — change immediately in production):**
```
Username: admin
Password: admin123
```

---

## 11. Inference Engine Configuration

The inference engine in `app/services/candidate_processor.py` applies these exact values. Verify they match the `.env` and the `University` model defaults:

| Parameter | Value | Source |
|-----------|-------|--------|
| JAMB score divisor | `8.0` | `JAMB_DIVISOR` env var / University model |
| Post-UTME score divisor | `4.0` | `POST_UTME_DIVISOR` env var / University model |
| Minimum UTME score | `140` | `MIN_UTME_SCORE` env var / AdmissionRule |
| Minimum O'Level credits | `5` | `MIN_OLEVEL_CREDITS` env var / AdmissionRule |
| Maximum O'Level sittings | `2` | `MAX_OLEVEL_SITTINGS` env var / Candidate validator |
| Merit quota | `45%` | `MERIT_QUOTA` / Programme.merit_slots |
| Catchment quota | `35%` | `CATCHMENT_QUOTA` / Programme.catchment_slots |
| ELDS quota | `20%` | `ELDS_QUOTA` / Programme.elds_slots |

**O'Level grade point mapping (must match exactly):**

| Grade | Points |
|-------|--------|
| A1 | 8 |
| B2 | 7 |
| B3 | 6 |
| C4 | 5 |
| C5 | 4 |
| C6 | 3 |
| D7 | 2 |
| E8 | 1 |
| F9 | 0 |

**Aggregate score formula:**
```
Aggregate = (UTME_Score / 8.0) + (PostUTME_Score / 4.0)
# Example: UTME=240, PostUTME=60 → (240/8) + (60/4) = 30 + 15 = 45.0
```

**Quick engine sanity check:**
```bash
python -c "
from app import create_app
from app.services.candidate_processor import evaluate_candidate
app = create_app()
with app.app_context():
    print('candidate_processor imported successfully.')
    # If the function signature is importable the engine is wired correctly
"
```

---

## 12. Mock JAMB CAPS API

The mock server runs as a separate Flask process on port `5001`. Verify it can start:

```bash
# In a second terminal:
python -m app.utils.mock_jamb_server
# or
flask run-mock-jamb
# Expected: "Mock JAMB CAPS server running on http://localhost:5001"

# Test the endpoint from a third terminal:
curl -X POST http://localhost:5001/api/jamb/verify \
     -H "Content-Type: application/json" \
     -d '{"registration_number": "12345678AB"}'
# Expected JSON response:
# {"registration_number": "12345678AB", "utme_score": 245, "status": "verified"}
```

**If curl is not available, test with Python:**
```bash
python -c "
import requests
res = requests.post('http://localhost:5001/api/jamb/verify',
    json={'registration_number': '12345678AB'})
print(res.status_code)   # Expected: 200
print(res.json())        # Expected: {'registration_number':..., 'utme_score':..., 'status':'verified'}
"
```

---

## 13. Frontend Dependencies

All frontend assets are loaded via CDN — no npm or node install is needed. Verify your internet connection can reach these URLs:

| Asset | CDN URL | Used By |
|-------|---------|---------|
| Bootstrap 5 CSS | `https://cdn.jsdelivr.net/npm/bootstrap@5.x.x/dist/css/bootstrap.min.css` | All pages |
| Bootstrap 5 JS | `https://cdn.jsdelivr.net/npm/bootstrap@5.x.x/dist/js/bootstrap.bundle.min.js` | Modals, dropdowns |
| Bootstrap Icons | `https://cdn.jsdelivr.net/npm/bootstrap-icons@1.x/font/bootstrap-icons.css` | UI icons |

**Connectivity check:**
```bash
python -c "
import urllib.request
urls = [
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css',
]
for url in urls:
    try:
        urllib.request.urlopen(url, timeout=5)
        print(f'REACHABLE: {url}')
    except Exception as e:
        print(f'UNREACHABLE: {url} — {e}')
"
```

---

## 14. Web Browser

The system requires a modern browser for the admin interface and applicant portal.

| Browser | Minimum Version | Check |
|---------|----------------|-------|
| Google Chrome | 90+ | `chrome://version` in address bar |
| Mozilla Firefox | 88+ | `about:support` in address bar |
| Microsoft Edge | 90+ | `edge://version` in address bar |

Required browser features (all present in the versions above):
- CSS Grid and Flexbox (Bootstrap 5 layouts)
- Fetch API (async form submissions)
- ES6 JavaScript (loading spinners, confirmation modals)
- `<input type="file">` with multiple attribute (document uploads)

---

## 15. Git Version Control

| Check | Requirement | Command |
|-------|-------------|---------|
| Git installed | 2.30+ | `git --version` |
| Repo initialized | `.git/` folder exists | `git status` |
| `.env` is gitignored | Must not be tracked | `git check-ignore -v .env` |

**Set up `.gitignore` if missing:**
```bash
python -c "
content = '''
.env
venv/
__pycache__/
*.pyc
*.pyo
instance/
uploads/
*.db
migrations/
.DS_Store
'''
with open('.gitignore', 'w') as f:
    f.write(content.strip())
print('.gitignore created.')
"
```

---

## 16. Hardware Checks

```bash
python -c "
import os, shutil, platform

# CPU info
print('=== Hardware Check ===')
print(f'Processor: {platform.processor()}')

# RAM
try:
    import psutil
    ram = psutil.virtual_memory()
    ram_gb = ram.total / (1024**3)
    status = 'OK' if ram_gb >= 4 else 'WARN: below 4 GB minimum'
    print(f'RAM: {ram_gb:.1f} GB — {status}')
except ImportError:
    print('RAM: Install psutil to check: pip install psutil')

# Disk space
total, used, free = shutil.disk_usage('.')
free_gb = free / (1024**3)
status = 'OK' if free_gb >= 5 else 'WARN: low disk space'
print(f'Free Disk: {free_gb:.1f} GB — {status}')

# Python architecture
print(f'Architecture: {platform.architecture()[0]}')
"
```

**Expected passing output:**
```
=== Hardware Check ===
Processor: Intel64 Family 6 ... (or equivalent)
RAM: 8.0 GB — OK          ← minimum 4.0 GB
Free Disk: 50.3 GB — OK   ← minimum 5 GB free
Architecture: 64bit
```

---

## 17. Security Checklist

Before deploying or submitting for demonstration, verify these are in place:

| # | Check | How to Verify |
|---|-------|---------------|
| 1 | `SECRET_KEY` is not the default value | Check `.env` — must not be `"your-secret-key-change-this"` |
| 2 | `.env` is in `.gitignore` | `git check-ignore -v .env` → should return `.env` |
| 3 | Admin default password is changed | Log in and change from `admin123` before demonstration |
| 4 | CSRF protection on all forms | Every form template must include `{{ form.hidden_tag() }}` |
| 5 | Role-based route decorators in place | Every admin route must use `@login_required` + role check |
| 6 | Passwords stored as bcrypt hashes | `User.password_hash` — never store plain text |
| 7 | Debug mode is OFF in production | `FLASK_ENV=production` in production `.env` |
| 8 | MySQL password is strong | At least 12 characters, mixed case, numbers, symbols |

---

## 18. Full End-to-End Startup Test

Run this sequence after all checks above pass. It confirms the full system comes alive:

```bash
# 1. Activate virtual environment
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate           # Windows

# 2. Apply database migrations
flask db upgrade

# 3. Seed the database
flask seed

# 4. Generate test candidates
flask generate-candidates 50

# 5. Start the mock JAMB server (new terminal)
# python -m app.utils.mock_jamb_server

# 6. Start the main application
python run.py

# 7. Open in browser
# http://localhost:5000
# Login: admin / admin123
```

**Expected in terminal after step 6:**
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on (development) / off (production)
```

**Expected in browser after step 7:**
- Login page loads at `http://localhost:5000/auth/login`
- After login: dashboard shows session stats
- Navigation: Programmes, Candidates, Admission Processing, Reports all reachable

---

## 19. Summary Checklist

Copy this table and fill in your status column before starting development:

| # | Area | Requirement | Your Status |
|---|------|-------------|-------------|
| 1 | OS | Windows 10/11 · Ubuntu 20.04+ · macOS 12+ | ☐ |
| 2 | Python | 3.8 or higher | ☐ |
| 3 | pip | Available inside virtualenv | ☐ |
| 4 | Flask | 2.0 or higher | ☐ |
| 5 | Flask-SQLAlchemy | 3.0 or higher | ☐ |
| 6 | Flask-Migrate | 4.0 or higher | ☐ |
| 7 | Flask-Login | 0.6 or higher | ☐ |
| 8 | Flask-WTF + WTForms | 1.1 / 3.0 or higher | ☐ |
| 9 | bcrypt / Flask-Bcrypt | 4.0 / 1.0 or higher | ☐ |
| 10 | PyMySQL | 1.0 or higher | ☐ |
| 11 | python-dotenv | 1.0 or higher | ☐ |
| 12 | openpyxl | 3.1 or higher | ☐ |
| 13 | reportlab | 4.0 or higher | ☐ |
| 14 | requests | 2.31 or higher | ☐ |
| 15 | MySQL Server | 8.0 or higher and running | ☐ |
| 16 | `admission_db` created | Database and user exist | ☐ |
| 17 | `.env` file | All required vars present | ☐ |
| 18 | Project structure | All folders and files in place | ☐ |
| 19 | All 12 models | Import without error | ☐ |
| 20 | App factory | Creates with all blueprints | ☐ |
| 21 | DB migrations | All 12 tables created | ☐ |
| 22 | Flask seed | Runs without error | ☐ |
| 23 | Test candidates | Generated successfully | ☐ |
| 24 | Mock JAMB API | Returns JSON on POST | ☐ |
| 25 | CDN assets | Bootstrap 5 reachable | ☐ |
| 26 | Browser | Chrome/Firefox/Edge modern version | ☐ |
| 27 | Git | Initialized, `.env` ignored | ☐ |
| 28 | RAM | 4 GB minimum | ☐ |
| 29 | Disk | 5 GB free minimum | ☐ |
| 30 | Security | All 8 security items confirmed | ☐ |

---

*Generated for: Automated Rule-Based Admission Decision System*  
*Author: Emmanuel Onucheojo Ocheme — 22L1SE0086, CUSTECH Osara*  
*Document version: 1.0 — generated alongside final thesis submission*
