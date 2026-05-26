# Automated Rule-Based Admission Decision System

## For: Confluence University of Science and Technology, Osara (CUSTECH)

### Features
- Rule-based candidate screening with configurable criteria
- Quota system (Merit, Catchment, ELDS)
- Aggregate score calculation with customizable formulas
- Mock JAMB CAPS integration
- Admission letter generation
- Comprehensive reporting and analytics
- Real-time system health monitoring
- User-friendly interface with loading spinners and confirmation modals
- Quick help tooltips for new users

### Installation
1. Clone repository
2. Create virtual environment: `python -m venv venv` 
3. Activate: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
4. Install dependencies: `pip install -r requirements.txt` 
5. Copy `.env.example` to `.env` and set values
6. Initialize database: `flask db init && flask db migrate && flask db upgrade` 
7. Seed data: `flask seed` 
8. Generate test candidates: `flask generate-candidates 100` 
9. Run: `python run.py` 

### Default Login
- Username: admin
- Password: admin123

### Project Structure
```
admission_system/
|-- app/
|   |-- __init__.py              # Flask application factory
|   |-- forms.py                 # WTForms classes
|   |-- models.py                # SQLAlchemy models
|   |-- routes/                  # Blueprint routes
|   |   |-- __init__.py
|   |   |-- admin.py             # Admin dashboard routes
|   |   |-- admission.py         # Admission processing routes
|   |   |-- auth.py              # Authentication routes
|   |-- services/                # Business logic services
|   |   |-- __init__.py
|   |   |-- candidate_processor.py
|   |   |-- merit_list.py
|   |-- static/                  # Static assets
|   |   |-- css/
|   |   |-- js/
|   |   |-- favicon.ico
|   |-- templates/               # Jinja2 templates
|   |   |-- admin/               # Admin templates
|   |   |-- auth/                # Authentication templates
|   |   |-- errors/              # Error page templates
|   |   |-- base.html            # Base template
|   |-- utils/                   # Utility modules
|       |-- __init__.py
|       |-- helpers.py
|       |-- seed.py              # Database seeding utilities
|-- instance/                    # Instance-specific files
|-- migrations/                  # Database migration files
|-- uploads/                     # File upload directory
|-- config.py                    # Application configuration
|-- requirements.txt             # Python dependencies
|-- run.py                       # Application entry point
|-- .env.example                 # Environment variables example
|-- .gitignore                   # Git ignore file
```

### System Diagrams

The diagrams below use Mermaid syntax and can be rendered directly by GitHub, GitLab, VS Code Mermaid extensions, and most Markdown documentation tools.

#### Flowchart Notation Standard

```mermaid
flowchart LR
    Terminator([Start / End])
    Process[Process]
    Decision{Decision}
    InputOutput[/Input or Output/]
    DataStore[(Data Store)]
    Connector((Connector))
```

#### 1. High-Level System Architecture

```mermaid
flowchart TB
    subgraph Users["System Users"]
        CandidateUser["Candidate"]
        AdminUser["Admin"]
        AdmissionOfficer["Admission Officer"]
        FacultyOfficer["Faculty Officer"]
    end

    subgraph WebApp["Flask Web Application"]
        Templates["Jinja2 Templates"]
        StaticAssets["Static Assets<br/>CSS / JS / Images"]
        Blueprints["Blueprint Routes<br/>auth, admin, admission, api, reports, candidate"]
        Forms["WTForms Validation"]
        Services["Business Services"]
    end

    subgraph ServiceLayer["Service Layer"]
        ScreeningEngine["ScreeningEngine"]
        CandidateProcessor["Candidate Processor"]
        MeritListGenerator["MeritListGenerator"]
        ReportGenerator["Report Generator"]
        MockCaps["Mock JAMB CAPS"]
        CapsSync["CAPS Sync"]
    end

    subgraph Persistence["Persistence Layer"]
        SQLAlchemy["SQLAlchemy ORM"]
        Database[("Application Database")]
        Uploads[("Uploads Directory")]
        Migrations["Flask-Migrate / Alembic"]
    end

    Users --> Templates
    Templates --> Blueprints
    StaticAssets --> Templates
    Blueprints --> Forms
    Blueprints --> Services
    Services --> ServiceLayer
    ServiceLayer --> SQLAlchemy
    Blueprints --> SQLAlchemy
    SQLAlchemy --> Database
    Migrations --> Database
    CandidateProcessor --> Uploads
    ReportGenerator --> Uploads
    MockCaps --> CapsSync
```

#### 2. Application Component Diagram

```mermaid
flowchart LR
    RunPy["run.py"] --> Factory["create_app()"]
    Factory --> Extensions["Extensions<br/>SQLAlchemy, Migrate, CSRF, LoginManager"]
    Factory --> Context["Global Context Processor"]
    Factory --> ErrorHandlers["Error Handlers"]
    Factory --> CLI["CLI Commands"]
    Factory --> Celery["Celery App"]
    Factory --> Router["register_blueprints()"]

    Router --> Auth["auth_bp"]
    Router --> Admin["admin_bp"]
    Router --> Admission["admission_bp<br/>/admission"]
    Router --> API["api_bp"]
    Router --> Reports["reports_bp"]
    Router --> Candidate["candidate_bp"]

    Auth --> UserModel["User"]
    Admin --> Models["SQLAlchemy Models"]
    Admission --> Screening["ScreeningEngine"]
    Admission --> Merit["MeritListGenerator"]
    API --> Models
    Reports --> ReportService["Report Generator"]
    Candidate --> CandidateModel["Candidate"]
```

#### 3. UML Class Diagram

```mermaid
classDiagram
    class AcademicSession {
        int id
        string name
        bool is_active
        date start_date
        date end_date
    }

    class University {
        int id
        string name
        string short_code
        string formula_type
        float jamb_divisor
        float post_utme_divisor
        float merit_quota_percent
        float catchment_quota_percent
        float elds_quota_percent
        int min_olevel_credits
        int max_olevel_sittings
        int min_utme_score
        get_grade_point(grade)
    }

    class Faculty {
        int id
        int university_id
        string name
        string code
    }

    class Programme {
        int id
        int university_id
        int faculty_id
        string name
        string code
        int total_slots
        int merit_slots
        int catchment_slots
        int elds_slots
        float merit_cutoff
        float catchment_cutoff
        float elds_cutoff
        allocate_quota_slots()
    }

    class Candidate {
        int id
        string jamb_reg_number
        string full_name
        string state_of_origin
        int utme_score
        float post_utme_score
        bool post_utme_present
        string status
    }

    class OLevelResult {
        int id
        string exam_body
        int exam_year
        int sitting_number
        string subject
        string grade
    }

    class AdmissionRule {
        int id
        string rule_name
        string condition_field
        string operator
        string value
        string logic_group
        bool is_active
        int priority
    }

    class AdmissionRecord {
        int id
        bool utme_cutoff_passed
        bool subject_combination_passed
        bool olevel_credits_passed
        bool olevel_sittings_passed
        string quota_category
        float aggregate_score
        string status
        string rejection_reason
        bool dept_approved
        bool faculty_approved
        bool senate_approved
        mark_department_approval()
    }

    class AdmissionBatch {
        int id
        string batch_name
        string quota_category
        int total_candidates
        int admitted_count
        int rejected_count
        update_counts()
    }

    class MeritListApproval {
        int id
        bool department_approved
        bool faculty_approved
        bool senate_approved
        bool finalized
        can_approve(user, level)
        approve(user, level)
    }

    class User {
        int id
        string username
        string email
        string full_name
        string role
        bool is_active
        set_password(password)
        check_password(password)
    }

    class AuditLog {
        int id
        string action
        string entity_type
        int entity_id
        json details
        string ip_address
        datetime timestamp
    }

    class CatchmentState {
        int id
        string state_name
    }

    class ELDSState {
        int id
        string state_name
        seed_defaults()
    }

    AcademicSession "1" --> "many" Candidate
    AcademicSession "1" --> "many" AdmissionRecord
    AcademicSession "1" --> "many" AdmissionBatch
    University "1" --> "many" Faculty
    University "1" --> "many" Programme
    University "1" --> "many" CatchmentState
    Faculty "1" --> "many" Programme
    Faculty "1" --> "many" User
    Programme "1" --> "many" AdmissionRule
    Programme "1" --> "many" AdmissionRecord
    Programme "1" --> "many" AdmissionBatch
    Programme "1" --> "many" Candidate : first_choice
    Candidate "1" --> "many" OLevelResult
    Candidate "1" --> "many" AdmissionRecord
    User "1" --> "many" AuditLog
    User "1" --> "many" AdmissionRecord : approver
    MeritListApproval --> Programme
    MeritListApproval --> AcademicSession
    MeritListApproval --> User : approvers
```

#### 4. Entity Relationship Diagram

```mermaid
erDiagram
    ACADEMIC_SESSIONS ||--o{ CANDIDATES : contains
    ACADEMIC_SESSIONS ||--o{ ADMISSION_RECORDS : records
    ACADEMIC_SESSIONS ||--o{ ADMISSION_BATCHES : batches
    ACADEMIC_SESSIONS ||--o{ MERIT_LIST_APPROVALS : approves

    UNIVERSITIES ||--o{ FACULTIES : has
    UNIVERSITIES ||--o{ PROGRAMMES : offers
    UNIVERSITIES ||--o{ CATCHMENT_STATES : defines

    FACULTIES ||--o{ PROGRAMMES : manages
    FACULTIES ||--o{ USERS : assigns

    PROGRAMMES ||--o{ ADMISSION_RULES : configures
    PROGRAMMES ||--o{ ADMISSION_RECORDS : evaluates
    PROGRAMMES ||--o{ ADMISSION_BATCHES : groups
    PROGRAMMES ||--o{ MERIT_LIST_APPROVALS : submits
    PROGRAMMES ||--o{ CANDIDATES : first_choice
    PROGRAMMES ||--o{ CANDIDATES : second_choice

    CANDIDATES ||--o{ OLEVEL_RESULTS : owns
    CANDIDATES ||--o{ ADMISSION_RECORDS : receives
    USERS ||--o{ AUDIT_LOGS : performs
    USERS ||--o{ ADMISSION_RECORDS : approves
    USERS ||--o{ ADMISSION_BATCHES : processes
```

#### 5. Candidate Screening Activity Diagram

```mermaid
flowchart TD
    Start([Start]) --> InputCandidate[/Candidate selected for screening/]
    InputCandidate --> LoadContext[Load candidate, university, programme, and session]
    LoadContext --> CandidateStore[(Application database)]
    CandidateStore --> CheckUTME{Does UTME score meet cutoff?}

    CheckUTME -- No --> RejectUTME[Create rejected admission record]
    RejectUTME --> ReasonUTME[/Rejection reason: utme_cutoff/]
    ReasonUTME --> End([End])

    CheckUTME -- Yes --> CheckSubjects{Are required UTME subjects present?}
    CheckSubjects -- No --> RejectSubjects[Create rejected admission record]
    RejectSubjects --> ReasonSubjects[/Rejection reason: subject_combination/]
    ReasonSubjects --> End

    CheckSubjects -- Yes --> CheckCredits{Are minimum O'Level credits and mandatory subjects passed?}
    CheckCredits -- No --> RejectCredits[Create rejected admission record]
    RejectCredits --> ReasonCredits[/Rejection reason: olevel_credits/]
    ReasonCredits --> End

    CheckCredits -- Yes --> CheckSittings{Are O'Level sittings within allowed limit?}
    CheckSittings -- No --> RejectSittings[Create rejected admission record]
    RejectSittings --> ReasonSittings[/Rejection reason: olevel_sittings/]
    ReasonSittings --> End

    CheckSittings -- Yes --> Aggregate[Calculate aggregate score]
    Aggregate --> Quota[Classify quota category]
    Quota --> Rules[Evaluate active programme rules]
    Rules --> Cutoff{Does aggregate meet quota cutoff?}

    Cutoff -- No --> RejectCutoff[Create or update rejected admission record]
    RejectCutoff --> ReasonCutoff[/Rejection reason: quota cutoff not met/]
    ReasonCutoff --> End

    Cutoff -- Yes --> Recommend[Create or update recommended admission record]
    Recommend --> OutputDecision[/Screening result: status, quota, score, evaluation log/]
    OutputDecision --> End
```

#### 6. Screening Sequence Diagram

```mermaid
sequenceDiagram
    actor Officer as Admission Officer
    participant Route as Admission Route
    participant Engine as ScreeningEngine
    participant DB as Database
    participant Record as AdmissionRecord

    Officer->>Route: Start candidate/batch screening
    Route->>DB: Load programme, session, candidate IDs
    Route->>Engine: screen_candidate(candidate)
    Engine->>DB: Read university and programme rules
    Engine->>Engine: Check UTME cutoff
    Engine->>Engine: Check subject combination
    Engine->>DB: Read O'Level results
    Engine->>Engine: Check credits and sittings
    Engine->>Engine: Calculate aggregate score
    Engine->>DB: Read catchment and ELDS states
    Engine->>Engine: Classify quota category
    Engine->>DB: Read active AdmissionRule rows
    Engine->>Engine: Evaluate dynamic rules
    Engine->>Record: Create or update decision
    Record->>DB: Flush AdmissionRecord
    Engine-->>Route: Return status, quota, aggregate, log
    Route-->>Officer: Display screening result
```

#### 7. Merit List and Quota Allocation Flow

```mermaid
flowchart TD
    Start([Start]) --> InputSelection[/Programme and academic session selected/]
    InputSelection --> LoadRecords[Load eligible admission records]
    LoadRecords --> RecordsStore[(AdmissionRecord table)]
    RecordsStore --> HasRecords{Are eligible records available?}
    HasRecords -- No --> EmptyOutput[/Return empty merit list/]
    EmptyOutput --> End([End])

    HasRecords -- Yes --> SplitQuota[Split records by quota category]
    SplitQuota --> Merit[Prepare merit quota list]
    SplitQuota --> Catchment[Prepare catchment quota list]
    SplitQuota --> ELDS[Prepare ELDS quota list]

    Merit --> RankMerit[Rank merit candidates by aggregate score]
    Catchment --> RankCatchment[Rank catchment candidates by aggregate score]
    ELDS --> RankELDS[Rank ELDS candidates by aggregate score]

    RankMerit --> MeritSlots[Apply merit slot limit]
    RankCatchment --> CatchmentSlots[Apply catchment slot limit]
    RankELDS --> ELDSSlots[Apply ELDS slot limit]

    MeritSlots --> UpdateStatus[Update admitted and waiting statuses]
    CatchmentSlots --> UpdateStatus
    ELDSSlots --> UpdateStatus
    UpdateStatus --> Persist[Commit database changes]
    Persist --> Output[/Return admitted lists, waiting lists, and cutoffs/]
    Output --> End
```

#### 8. Multi-Level Approval State Diagram

```mermaid
stateDiagram-v2
    [*] --> Generated: Merit list generated
    Generated --> DepartmentApproved: Department approval
    DepartmentApproved --> FacultyApproved: Faculty approval
    FacultyApproved --> SenateApproved: Senate approval
    SenateApproved --> Finalized: finalized = true
    Finalized --> CAPSUploaded: Upload/push to CAPS
    CAPSUploaded --> Accepted: Candidate accepts offer
    CAPSUploaded --> Declined: Candidate declines offer
    Accepted --> LetterGenerated: Admission letter generated
    Declined --> WaitingListReplacement: Slot released
    WaitingListReplacement --> Generated: Regenerate list
```

#### 9. Candidate Portal Use Case Diagram

```mermaid
flowchart LR
    Candidate["Candidate"]
    Admin["Admin"]
    FacultyOfficer["Faculty Officer"]
    AdmissionOfficer["Admission Officer"]

    subgraph UseCases["System Use Cases"]
        Login["Login / Logout"]
        ManageData["Manage candidate data"]
        VerifyCAPS["Verify CAPS data"]
        ConfigureRules["Configure admission rules"]
        RunScreening["Run screening"]
        GenerateMerit["Generate merit list"]
        ApproveList["Approve merit list"]
        ViewStatus["View admission status"]
        AcceptDecline["Accept or decline admission"]
        GenerateLetter["Generate admission letter"]
        Reports["View reports and analytics"]
    end

    Candidate --> Login
    Candidate --> ViewStatus
    Candidate --> AcceptDecline
    Candidate --> GenerateLetter

    Admin --> Login
    Admin --> ManageData
    Admin --> VerifyCAPS
    Admin --> ConfigureRules
    Admin --> RunScreening
    Admin --> GenerateMerit
    Admin --> ApproveList
    Admin --> Reports

    AdmissionOfficer --> Login
    AdmissionOfficer --> ManageData
    AdmissionOfficer --> VerifyCAPS
    AdmissionOfficer --> RunScreening
    AdmissionOfficer --> GenerateMerit
    AdmissionOfficer --> ApproveList
    AdmissionOfficer --> Reports

    FacultyOfficer --> Login
    FacultyOfficer --> ApproveList
    FacultyOfficer --> Reports
```

#### 10. System Use Case Diagram

```mermaid
flowchart LR
    CandidateActor["Candidate"]
    AdminActor["Admin"]
    AdmissionActor["Admission Officer"]
    FacultyActor["Faculty Officer"]
    SenateActor["Senate / Final Approver"]
    MockCapsActor["Mock JAMB CAPS"]

    subgraph AADS["Automated Admission Decision System"]
        UCLogin(("Authenticate user"))
        UCSubmitData(("Submit / update candidate data"))
        UCViewStatus(("View admission status"))
        UCAcceptOffer(("Accept or decline admission"))
        UCGenerateLetter(("Generate admission letter"))

        UCManageUsers(("Manage users and roles"))
        UCManageProgrammes(("Manage faculties and programmes"))
        UCConfigureRules(("Configure admission rules"))
        UCConfigureQuotas(("Configure quotas and cutoffs"))
        UCVerifyCandidates(("Verify candidate data"))
        UCRunScreening(("Run rule-based screening"))
        UCGenerateMerit(("Generate merit list"))
        UCApproveDepartment(("Approve at department level"))
        UCApproveFaculty(("Approve at faculty level"))
        UCApproveSenate(("Approve at senate level"))
        UCPushCaps(("Upload admission list to CAPS"))
        UCCapsStatus(("Check CAPS upload status"))
        UCReports(("View reports and analytics"))
        UCAudit(("View audit trail"))
    end

    CandidateActor --> UCLogin
    CandidateActor --> UCSubmitData
    CandidateActor --> UCViewStatus
    CandidateActor --> UCAcceptOffer
    CandidateActor --> UCGenerateLetter

    AdminActor --> UCLogin
    AdminActor --> UCManageUsers
    AdminActor --> UCManageProgrammes
    AdminActor --> UCConfigureRules
    AdminActor --> UCConfigureQuotas
    AdminActor --> UCVerifyCandidates
    AdminActor --> UCRunScreening
    AdminActor --> UCGenerateMerit
    AdminActor --> UCApproveDepartment
    AdminActor --> UCApproveFaculty
    AdminActor --> UCApproveSenate
    AdminActor --> UCPushCaps
    AdminActor --> UCCapsStatus
    AdminActor --> UCReports
    AdminActor --> UCAudit

    AdmissionActor --> UCLogin
    AdmissionActor --> UCVerifyCandidates
    AdmissionActor --> UCRunScreening
    AdmissionActor --> UCGenerateMerit
    AdmissionActor --> UCApproveDepartment
    AdmissionActor --> UCPushCaps
    AdmissionActor --> UCCapsStatus
    AdmissionActor --> UCReports

    FacultyActor --> UCLogin
    FacultyActor --> UCApproveFaculty
    FacultyActor --> UCReports

    SenateActor --> UCLogin
    SenateActor --> UCApproveSenate
    SenateActor --> UCReports

    MockCapsActor --> UCVerifyCandidates
    MockCapsActor --> UCPushCaps
    MockCapsActor --> UCCapsStatus
    MockCapsActor --> UCAcceptOffer

    UCRunScreening -. includes .-> UCVerifyCandidates
    UCGenerateMerit -. includes .-> UCRunScreening
    UCPushCaps -. requires .-> UCApproveSenate
    UCGenerateLetter -. requires .-> UCAcceptOffer
```

#### 11. Route to Service Dependency Diagram

```mermaid
flowchart TB
    subgraph Routes["Blueprint Routes"]
        AuthRoute["auth.py"]
        AdminRoute["admin.py"]
        AdmissionRoute["admission.py"]
        ApiRoute["api.py"]
        CandidateRoute["candidate.py"]
        ReportsRoute["reports.py"]
    end

    subgraph Services["Services"]
        ScreeningEngine["screening_engine.py"]
        CandidateProcessor["candidate_processor.py"]
        MeritList["merit_list.py"]
        MockCaps["mock_caps.py"]
        CapsSync["caps_sync.py"]
        ReportGenerator["report_generator.py"]
    end

    subgraph Models["Models"]
        User["User"]
        Candidate["Candidate"]
        Programme["Programme"]
        AdmissionRecord["AdmissionRecord"]
        AdmissionRule["AdmissionRule"]
        AcademicSession["AcademicSession"]
        AuditLog["AuditLog"]
    end

    AuthRoute --> User
    AdminRoute --> Candidate
    AdminRoute --> Programme
    AdminRoute --> AdmissionRule
    AdmissionRoute --> ScreeningEngine
    AdmissionRoute --> MeritList
    ApiRoute --> Candidate
    ApiRoute --> Programme
    CandidateRoute --> Candidate
    CandidateRoute --> AdmissionRecord
    ReportsRoute --> ReportGenerator

    ScreeningEngine --> Candidate
    ScreeningEngine --> Programme
    ScreeningEngine --> AdmissionRule
    ScreeningEngine --> AdmissionRecord
    CandidateProcessor --> Candidate
    MeritList --> AdmissionRecord
    MeritList --> Programme
    MockCaps --> Candidate
    CapsSync --> AdmissionRecord
    ReportGenerator --> AdmissionRecord
    ReportGenerator --> AcademicSession
    AdminRoute --> AuditLog
```

#### 12. Deployment Diagram

```mermaid
flowchart TB
    Browser["User Browser"] --> HTTP["HTTP/HTTPS"]
    HTTP --> FlaskServer["Flask Application Server<br/>python run.py / WSGI"]

    FlaskServer --> Templates["Jinja2 Templates"]
    FlaskServer --> Static["Static Files"]
    FlaskServer --> UploadDir["Upload Directory"]
    FlaskServer --> DB[("Database<br/>SQLite or DATABASE_URL")]
    FlaskServer --> Migrations["Alembic Migrations"]

    subgraph OptionalAsync["Optional Background Processing"]
        CeleryWorker["Celery Worker"]
        Broker["Message Broker"]
    end

    FlaskServer -. schedules .-> Broker
    Broker -. dispatches .-> CeleryWorker
    CeleryWorker -. reads/writes .-> DB
```

#### 13. Data Flow Diagram

```mermaid
flowchart LR
    CandidateData[/Candidate data<br/>Bio-data, UTME, O'Level, Post-UTME/] --> Validation[Validate form or upload data]
    Validation --> CandidateStore[(Candidate and OLevelResult tables)]
    CandidateStore --> Screening[Run screening engine]
    RuleConfig[/Programme criteria and admission rules/] --> Screening
    UniversityConfig[/University quotas, cutoffs, grade points/] --> Screening
    Screening --> DecisionStore[(AdmissionRecord table)]
    DecisionStore --> MeritGeneration[Generate merit list]
    MeritGeneration --> Approval[Process department, faculty, and senate approval]
    Approval --> CAPS[/Mock JAMB CAPS sync/]
    Approval --> Reports[/Reports and analytics/]
    Approval --> CandidatePortal[/Candidate status and admission letter/]
```

### Key Features

#### 1. Rule-Based Screening
- Configurable admission rules for each programme
- Automatic candidate evaluation based on:
  - UTME scores and subject combinations
  - O'Level results and credit requirements
  - Quota allocations (Merit, Catchment, ELDS)
- Aggregate score calculation with customizable formulas

#### 2. Quota Management
- Merit quota (45% default)
- Catchment quota (35% default) 
- ELDS quota (20% default)
- Configurable per university and programme

#### 3. Multi-Level Approval System
- Department level approval
- Faculty level approval
- Senate level approval
- Audit trail for all actions

#### 4. Reporting & Analytics
- Comprehensive admission statistics
- Export functionality (Excel, PDF)
- Real-time dashboards
- System health monitoring

#### 5. User Interface Enhancements
- Loading spinners for async operations
- Confirmation modals for destructive actions
- Breadcrumb navigation
- Quick help tooltips
- Responsive design for mobile devices

### Database Models

#### Core Entities
- **AcademicSession**: Academic year management
- **University**: University configuration and settings
- **Faculty**: Faculty/college management
- **Programme**: Academic programmes with admission criteria
- **Candidate**: Student applications and data
- **AdmissionRecord**: Admission decisions and approvals
- **User**: System users with role-based access

#### Supporting Models
- **AdmissionRule**: Configurable screening rules
- **OLevelResult**: O'Level examination results
- **CatchmentState**: University catchment areas
- **ELDSState**: Educationally Less Developed States
- **AuditLog**: System audit trail

### CLI Commands

#### Database Management
```bash
# Seed database with initial data
flask seed

# Generate test candidates
flask generate-candidates 100

# Create admin user interactively
flask create-admin
```

### Configuration

#### Environment Variables
```bash
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///admission.db
UPLOAD_FOLDER=uploads
```

#### University Settings
- JAMB divisor: 8.0
- Post-UTME divisor: 4.0
- Grade points mapping (A1=8, B2=7, etc.)
- Minimum UTME score: 140
- Minimum O'Level credits: 5
- Maximum O'Level sittings: 2

### Security Features
- Role-based access control (Admin, Faculty Officer, Admission Officer)
- CSRF protection
- Password hashing
- Session management
- Audit logging

### API Integration
- Mock JAMB CAPS integration for testing
- Configurable endpoints for production integration
- Data validation and error handling

### Testing
- Unit tests for core functionality
- Integration tests for workflows
- Test data generation utilities
- Database seeding for test environments

### Deployment Considerations
- Production-ready configuration
- Environment-specific settings
- Database migration support
- Static asset management
- Error handling and logging

### Author
**Emmanuel Onucheojo Ocheme (22L1SE0086)**  
Software Engineering, CUSTECH

### License
© 2025 Confluence University of Science and Technology, Osara  
Automated Rule-Based Admission Decision System
