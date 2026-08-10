# Automated Rule-Based Admission Decision System

## For: Confluence University of Science and Technology, Osara (CUSTECH)

A comprehensive, rule-based admission management system that automates candidate screening, merit list generation, and admission letter production with JAMB CAPS integration capabilities.

### Key Features

#### 1. Rule-Based Candidate Screening
- **Configurable admission rules** per programme with custom conditions
- **Multi-criteria evaluation** including:
  - UTME scores and subject combinations
  - O'Level results and credit requirements
  - Subject combination validation with compound subject support
  - Automatic aggregate score calculation
- **ScreeningEngine** service with detailed evaluation logs and reasoning traces

#### 2. Quota Management System
- **Three-tier quota allocation**: Merit (45%), Catchment (35%), ELDS (20%)
- **Sequential allocation algorithm**: Candidates compete for Merit first, then Catchment (if eligible), then ELDS (if eligible)
- **Configurable slot limits** per programme and quota category
- **Automatic tie-breaking** by aggregate score, UTME score, and candidate ID

#### 3. Multi-Level Approval Workflow
- **Department level approval** by admission officers
- **Faculty level approval** by faculty officers
- **Senate level approval** by administrators
- **MeritListApproval** model tracks approval status at each level
- **Audit trail** for all approval actions

#### 4. JAMB CAPS Integration
- **Mock CAPS service** for testing and development
- **Candidate verification** against JAMB records
- **Bulk admission list upload** to CAPS
- **Acceptance status tracking** and simulation
- **Real-time verification statistics** and progress monitoring

#### 5. Background Task Processing
- **Celery integration** for asynchronous operations
- **Bulk candidate verification** with progress tracking
- **Merit list generation** for single or all programmes
- **Candidate import** from CSV files with progress updates
- **Batch screening** with real-time status updates

#### 6. Comprehensive Reporting
- **Admission letter generation** (PDF) with university branding
- **Bulk letter generation** (ZIP) for all admitted candidates
- **Excel export** of admission lists by programme and quota
- **Statistics reports** with admission analytics
- **Real-time dashboards** with Chart.js visualizations

#### 7. User Management & Security
- **Role-based access control**:Admin, Super Admin, Admission Officer, Faculty Officer, Candidate
- **CSRF protection** across all forms
- **Password hashing** with Werkzeug security
- **Session management** with Flask-Login
- **Comprehensive audit logging** for all system actions

#### 8. Data Import & Processing
- **JAMB-format CSV import** with flexible column mapping
- **Standard CSV import** for candidate data
- **Duplicate validation** and error handling
- **Preview functionality** before committing imports
- **Manual candidate entry** with form validation

### Installation

#### Prerequisites
- Python 3.8+
- Redis (for Celery background tasks)
- SQLite (default) or PostgreSQL/MySQL

#### Setup Steps
1. **Clone repository**
   ```bash
   git clone <repository-url>
   cd aads
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize database**
   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

6. **Seed initial data**
   ```bash
   flask seed
   ```

7. **Generate test candidates** (optional)
   ```bash
   flask generate-candidates 100
   ```

8. **Start Redis** (for background tasks)
   ```bash
   redis-server
   ```

9. **Start Celery worker** (for background tasks)
   ```bash
   celery -A app.celery_app worker --loglevel=info
   ```

10. **Run application**
    ```bash
    python run.py
    ```

### Default Login Credentials
- **Username**: admin
- **Password**: admin123

### Project Structure

```
aads/
├── app/
│   ├── __init__.py              # Flask application factory
│   ├── celery_app.py            # Celery configuration
│   ├── forms.py                 # WTForms validation classes
│   ├── models.py                # SQLAlchemy ORM models
│   ├── tasks.py                 # Celery background tasks
│   ├── routes/                  # Application blueprints
│   │   ├── __init__.py
│   │   ├── admin.py             # Admin dashboard & management
│   │   ├── admission.py         # Admission processing & screening
│   │   ├── admission_conclusion.py  # Final admission decisions
│   │   ├── api.py               # REST API endpoints
│   │   ├── auth.py              # Authentication routes
│   │   ├── candidate.py         # Candidate portal
│   │   └── reports.py           # Report generation
│   ├── services/                # Business logic layer
│   │   ├── candidate_processor.py  # CSV import & data processing
│   │   ├── caps_sync.py         # JAMB CAPS integration
│   │   ├── merit_list.py        # Merit list generation
│   │   ├── mock_caps.py         # Mock CAPS service for testing
│   │   ├── report_generator.py  # PDF/Excel report generation
│   │   └── screening_engine.py  # Rule-based screening engine
│   ├── static/                  # Static assets (CSS, JS, images)
│   ├── templates/               # Jinja2 templates
│   │   ├── admin/               # Admin interface templates
│   │   ├── auth/                # Authentication templates
│   │   ├── candidate/           # Candidate portal templates
│   │   ├── errors/              # Error page templates
│   │   ├── base.html            # Main base template
│   │   └── base_public.html     # Public-facing base template
│   └── utils/                   # Utility functions
│       ├── helpers.py           # Helper functions
│       └── seed.py              # Database seeding commands
├── migrations/                  # Database migration files
├── instance/                    # Instance-specific data (SQLite DB)
├── uploads/                     # File upload directory
├── config.py                    # Application configuration
├── requirements.txt             # Python dependencies
├── run.py                       # Application entry point
├── celery_worker.py             # Celery worker startup script
├── create_admin.py              # Admin user creation script
├── .env.example                 # Environment variables template
└── .gitignore                   # Git ignore rules
```

### Database Models

#### Core Entities

**AcademicSession**
- Manages academic years/sessions
- Tracks active session for admissions
- Relationships: candidates, admission_records, admission_batches

**University**
- University configuration and settings
- Customizable admission formulas (STANDARD, CUSTECH, OAU, UNILAG)
- Grade points mapping (A1=8, B2=7, B3=6, C4=5, C5=4, C6=3)
- Quota percentages (Merit, Catchment, ELDS)
- Catchment states configuration
- Branding (colors, logo)

**Faculty**
- Faculty/college management
- Linked to university
- Contains multiple programmes

**Programme**
- Academic programmes with admission criteria
- Required UTME subjects (supports compound subjects like "Chemistry/Economics")
- Mandatory O'Level subjects
- Slot allocation (total, merit, catchment, ELDS)
- Cutoff scores per quota category
- Configurable admission rules

**Candidate**
- Student application data
- JAMB registration, UTME scores, subject combinations
- O'Level results (multiple sittings supported)
- First and second choice programmes
- CAPS verification status
- Screening status and rejection reasons

**AdmissionRecord**
- Admission decisions and evaluations
- Quota category assignment
- Aggregate score components (JAMB, Post-UTME, O'Level)
- Multi-level approval tracking (department, faculty, senate)
- Evaluation log with detailed reasoning
- CAPS upload and letter generation status

**User**
- System users with role-based access
- Roles: admin, super_admin, admission_officer, faculty_officer, candidate
- Faculty assignment for faculty officers
- Linked to candidate profile for candidate users

#### Supporting Models

**AdmissionRule**
- Configurable screening rules per programme
- Condition fields, operators, and values
- Logic groups (AND/OR) for complex rules
- Priority-based rule execution

**OLevelResult**
- O'Level examination results
- Exam bodies: WAEC, NECO, NABTEB
- Multiple sitting support
- Subject-grade pairs

**CatchmentState**
- University catchment area states
- Linked to university

**ELDSState**
- Educationally Less Developed States
- Pre-seeded with 23 ELDS states

**AdmissionBatch**
- Tracks batch screening operations
- Progress statistics (total, admitted, rejected)
- Processed by user and timestamp

**MeritListApproval**
- Multi-level approval tracking
- Department, faculty, senate approval status
- Approval timestamps and approvers
- Finalization flag

**AuditLog**
- System audit trail
- User actions with timestamps
- Entity type and ID tracking
- IP address logging

### Services & Business Logic

#### ScreeningEngine (`app/services/screening_engine.py`)
- Core rule-based evaluation engine
- UTME cutoff validation
- Subject combination checking with compound subject support
- O'Level credit counting and mandatory subject validation
- Sitting limit validation
- Aggregate score calculation with customizable formulas
- Detailed evaluation logs with reasoning traces

#### MeritListGenerator (`app/services/merit_list.py`)
- Ranks candidates by aggregate score
- Sequential quota allocation algorithm
- Slot limit enforcement per quota category
- Tie-breaking by UTME score and candidate ID
- Waiting list management
- Excel export functionality
- Approval status tracking

#### ReportGenerator (`app/services/report_generator.py`)
- PDF admission letter generation with ReportLab
- Bulk ZIP file generation for multiple letters
- Excel export of admission lists
- Statistics report generation
- Dashboard data aggregation
- Chart.js data preparation

#### CandidateProcessor (`app/services/candidate_processor.py`)
- JAMB-format CSV import with flexible column mapping
- Standard CSV import support
- Column alias resolution for common naming variations
- Duplicate validation
- Data normalization and validation
- Error collection and reporting

#### CAPSSyncService (`app/services/caps_sync.py`)
- JAMB CAPS integration layer
- Admission list submission
- Candidate verification
- Acceptance status tracking
- Upload status monitoring

#### MockCAPSService (`app/services/mock_caps.py`)
- Mock CAPS service for testing
- Simulates CAPS verification responses
- Test data seeding from candidates
- Upload simulation with progress tracking

### Background Tasks (Celery)

#### CAPS Verification Tasks
- `bulk_verify_candidates_task`: Bulk verify candidates against CAPS
- Progress tracking with ETA calculation
- Error collection and reporting

#### CAPS Upload Tasks
- `upload_admission_list_task`: Upload admission lists to CAPS
- Programme-specific upload handling
- Audit logging for uploads

#### Merit List Generation Tasks
- `generate_merit_list_task`: Generate merit list for single programme
- `generate_all_merit_lists_task`: Generate merit lists for all programmes
- Progress tracking and statistics

#### Candidate Import Tasks
- `import_candidates_task`: Import candidates from CSV files
- JAMB format validation
- Progress tracking with error reporting
- Temporary file cleanup

#### Screening Tasks
- `screen_candidates_task`: Batch screen candidates
- Programme grouping for efficient processing
- Batch tracking with admission/rejection counts

### CLI Commands

#### Database Management
```bash
# Seed database with initial data (university, faculties, programmes, ELDS states)
flask seed

# Generate test candidates with random data
flask generate-candidates [count]

# Create admin user interactively
flask create-admin
```

### Configuration

#### Environment Variables
```bash
# Application
FLASK_ENV=development                    # development or production
SECRET_KEY=your-secret-key-here         # Flask secret key

# Database
DATABASE_URL=sqlite:///instance/app.db  # SQLite (default)
# DATABASE_URL=postgresql://user:pass@localhost/dbname  # PostgreSQL
# DATABASE_URL=mysql://user:pass@localhost/dbname       # MySQL

# File Uploads
UPLOAD_FOLDER=uploads                   # Upload directory

# Celery/Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=false          # Set to true to run tasks synchronously
```

#### University Configuration (via Admin UI)
- **Formula Type**: STANDARD, CUSTECH, OAU, UNILAG
- **JAMB Divisor**: Default 8.0
- **Post-UTME Divisor**: Default 4.0
- **Grade Points**: A1=8, B2=7, B3=6, C4=5, C5=4, C6=3
- **Quota Percentages**: Merit 45%, Catchment 35%, ELDS 20%
- **Minimum Requirements**: UTME score, O'Level credits, O'Level sittings
- **Branding**: Primary color, secondary color, logo URL

### API Endpoints

#### Admin Routes (`/admin/*`)
- `/admin/dashboard` - Main admin dashboard
- `/admin/candidates` - Candidate management
- `/admin/programmes` - Programme management
- `/admin/faculties` - Faculty management
- `/admin/university/config` - University configuration
- `/admin/screening` - Screening dashboard
- `/admin/merit-list` - Merit list management
- `/admin/caps/dashboard` - CAPS integration dashboard
- `/admin/reports` - Reports and analytics

#### Admission Routes (`/admission/*`)
- `/admission/screening` - Screening operations
- `/admission/merit-list` - Merit list generation
- `/admission/caps/*` - CAPS integration endpoints
- `/admission/health` - Health check endpoint

#### API Routes (`/api/*`)
- `/api/admission/generate/<programme_id>` - Generate merit list (sync)
- `/api/admission/generate-all` - Generate all merit lists (sync)
- `/api/admission/screen` - Batch screening endpoint
- `/api/health` - API health check

#### Reports Routes (`/reports/*`)
- `/reports/dashboard-data` - Dashboard statistics
- `/reports/admission-letter/<record_id>` - Generate single letter
- `/reports/bulk-letters/<programme_id>` - Generate bulk letters
- `/reports/admitted-candidates/<programme_id>` - Get admitted candidates
- `/reports/statistics` - Generate statistics report
- `/reports/export/<programme_id>` - Export to Excel

#### Candidate Routes (`/candidate/*`)
- `/candidate/dashboard` - Candidate portal
- `/candidate/change-password` - Password management

### Security Features

- **Authentication**: Flask-Login with session management
- **Authorization**: Role-based access control with route protection
- **CSRF Protection**: Flask-WTF CSRF protection on all forms
- **Password Security**: Werkzeug password hashing
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **XSS Protection**: Jinja2 auto-escaping
- **Audit Logging**: Comprehensive audit trail for sensitive operations
- **Session Security**: HTTP-only, secure cookies in production

### Testing & Development

#### Development Mode
- Set `FLASK_ENV=development` for debug mode
- Set `CELERY_TASK_ALWAYS_EAGER=true` to run tasks synchronously
- SQLite database for easy setup
- Detailed error pages with stack traces

#### Testing Strategy
- Mock CAPS service for isolated testing
- Test data generation utilities
- Database seeding for consistent test environments
- Error handling and validation testing

### Deployment Considerations

#### Production Configuration
- Use PostgreSQL or MySQL for production database
- Configure production-grade Redis for Celery
- Set `FLASK_ENV=production`
- Use strong `SECRET_KEY`
- Enable secure cookies (`SESSION_COOKIE_SECURE=True`)
- Configure proper file permissions for uploads
- Set up database backups
- Configure logging for production monitoring

#### Performance Optimization
- Database indexing on frequently queried fields
- SQLAlchemy joinedload for efficient queries
- Celery for long-running tasks
- Pagination for large datasets
- Static asset caching
- Database connection pooling

### Troubleshooting

#### Common Issues

**Celery tasks not executing**
- Ensure Redis is running: `redis-server`
- Start Celery worker: `celery -A app.celery_app worker --loglevel=info`
- Check Celery broker URL in `.env`

**Database migration errors**
- Drop and recreate database: `rm instance/app.db`
- Run migrations: `flask db upgrade`
- Seed data: `flask seed`

**Import errors**
- Verify CSV format matches expected columns
- Check column aliases in `candidate_processor.py`
- Review error messages in import preview

**Screening not working**
- Ensure active session is configured
- Verify university settings are configured
- Check programme slot allocations
- Review screening engine logs

### Author
**Emmanuel Onucheojo Ocheme (22L1SE0086)**  
Software Engineering, CUSTECH

### License
© 2025 Confluence University of Science and Technology, Osara  
Automated Rule-Based Admission Decision System
