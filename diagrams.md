# Automated Admission Decision System - Diagrams

This document contains Mermaid diagrams illustrating the structure, data flows, and architecture of the Automated Admission Decision System.

---

## 1. System Flowchart for the Admission Evaluation Process

```mermaid
flowchart TD
    Start([Begin Admission Processing Session]) --> Retrieve[Retrieve candidate data and programme rules from database]
    Retrieve --> CheckUTME{Check UTME score meets cut-off?}
    
    CheckUTME -- No --> Reject[Set decision to Rejected]
    CheckUTME -- Yes --> CheckCredits{Check O'Level credits sufficient?}
    
    CheckCredits -- No --> Reject
    CheckCredits -- Yes --> CheckSubject{Check O'Level subject combination valid?}
    
    CheckSubject -- No --> Reject
    CheckSubject -- Yes --> Classify[Classify candidate into quota category:<br/>Merit, Catchment, or ELDS]
    
    Classify --> Compute[Compute aggregate score]
    Compute --> CheckSlot{Check quota slot availability}
    
    CheckSlot -- Slot Exists --> Admitted[Set decision to Admitted]
    CheckSlot -- No Slot --> Pending[Set decision to Pending]
    
    Admitted --> Store[Store decision in AdmissionRecord<br/>and log to AuditLog]
    Pending --> Store
    Reject --> Store
    
    Store --> End([End])
```

---

## 2. Dataflow Diagram (Level 0 DFD)

```mermaid
flowchart LR
    %% External Entities
    Admin[Administrator]
    App[Applicant]
    Jamb[Mock JAMB CAPS Server]
    
    %% System Process
    System((Automated Rule-Based Admission Decision System))
    
    %% Data Flows
    Admin -->|System configurations, programme data, & admission rules| System
    System -->|Admission decision reports| Admin
    
    App -->|Academic data| System
    System -->|Admission status output| App
    
    System -->|Candidate registration data| Jamb
    Jamb -->|Verification responses| System
```

---

## 3. Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    CANDIDATE ||--o{ OLEVEL_RESULT : has
    PROGRAMME ||--o{ CANDIDATE : chooses
    CANDIDATE ||--o{ ADMISSION_RECORD : evaluates
    PROGRAMME ||--o{ ADMISSION_RECORD : offers
    USER ||--o{ ADMISSION_RECORD : processes
    PROGRAMME ||--o{ ADMISSION_RULE : configures
    FACULTY ||--o{ PROGRAMME : contains
    UNIVERSITY ||--o{ PROGRAMME : defines
    USER ||--o{ AUDIT_LOG : creates
    CATCHMENT_STATE ||--o{ CANDIDATE : references
    ELDS_STATE ||--o{ CANDIDATE : references
    ACADEMIC_SESSION ||--o{ ADMISSION_RECORD : includes
```

---

## 4. Use Case Diagram

```mermaid
flowchart LR
    %% Actors
    Admin((Administrator))
    Applicant((Applicant))
    Jamb[Mock JAMB CAPS Server]

    %% System Boundary
    subgraph AADS [Automated Admission Decision System]
        %% Admin Use Cases
        UC_Login([Login])
        UC_ManageProg([Manage Programmes])
        UC_ConfigRules([Configure Admission Rules])
        UC_ProcessCand([Process Candidates])
        UC_ApproveDec([Approve Decisions])
        UC_GenReports([Generate Reports])
        UC_ManageSessions([Manage Academic Sessions])
        
        %% Applicant Use Cases
        UC_CheckStatus([Check Admission Status])
        UC_DownloadLetter([Download Admission Letter])
        
        %% External Use Case
        UC_VerifyReg([Verify Candidate Registration])
    end

    %% Actor Associations
    Admin --> UC_Login
    Admin --> UC_ManageProg
    Admin --> UC_ConfigRules
    Admin --> UC_ProcessCand
    Admin --> UC_ApproveDec
    Admin --> UC_GenReports
    Admin --> UC_ManageSessions

    Applicant --> UC_CheckStatus
    Applicant --> UC_DownloadLetter

    UC_VerifyReg --- Jamb
```

---

## 5. Three-Tier Architecture

```mermaid
flowchart TD
    subgraph Presentation [Presentation Layer]
        UI[Browser-Based User Interface]
    end

    subgraph AppLayer [Application Layer - Flask MVC Backend]
        InferenceEngine[Rule-Based Inference Engine]
        ServiceModules[Service Modules]
    end

    subgraph Data [Data Layer]
        MySQL[(MySQL Database)]
    end

    subgraph External [External System]
        CapsAPI[Mock JAMB CAPS API Module]
    end

    %% Communication Channels
    UI <-->|HTTP Requests / Responses| AppLayer
    AppLayer <-->|Data Storage & Retrieval| MySQL
    AppLayer <-->|Simulated Regulatory Verification| CapsAPI
```
