"""
Background Tasks (Celery)
All heavy/async operations are defined here.
"""
import logging
from datetime import datetime

from app import db
from app.celery_app import make_celery

# Lazy import — celery instance is initialised when the worker starts
# via celery_worker.py. This avoids a circular import with app/__init__.py.
from celery import shared_task

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CAPS Verification Tasks
# ---------------------------------------------------------------------------

@shared_task(bind=True, name="tasks.bulk_verify_candidates")
def bulk_verify_candidates_task(self, candidate_ids: list) -> dict:
    """
    Asynchronously verify a list of candidates against CAPS.

    Returns a summary dict:
        {verified: int, failed: int, errors: list}
    """
    import time
    from app.models import Candidate
    from app.services.mock_caps import MockCAPSService

    total = len(candidate_ids)
    verified_count = 0
    failed_count = 0
    errors = []

    self.update_state(state="PROGRESS", meta={"current": 0, "total": total, "status": "Starting..."})
    start_time = time.time()

    for idx, cid in enumerate(candidate_ids, 1):
        try:
            candidate = Candidate.query.get(cid)
            if not candidate:
                failed_count += 1
                errors.append(f"Candidate ID {cid} not found")
                continue

            MockCAPSService.seed_from_candidates([candidate])
            result = MockCAPSService.verify_candidate(candidate.jamb_reg_number)

            candidate.caps_verified = result["verified"]
            candidate.caps_verification_date = datetime.utcnow() if result["verified"] else None
            candidate.caps_verification_issues = result.get("issues", [])
            candidate.caps_status = result["status"]
            db.session.commit()

            if result["verified"]:
                verified_count += 1
            else:
                failed_count += 1

        except Exception as exc:
            db.session.rollback()
            failed_count += 1
            errors.append(f"Candidate {cid}: {str(exc)}")
            logger.exception("Error verifying candidate %s", cid)

        # Update progress for every candidate
        elapsed = time.time() - start_time
        rate = idx / elapsed if elapsed > 0 else 0
        eta = (total - idx) / rate if rate > 0 else 0

        self.update_state(
            state="PROGRESS",
            meta={
                "current": idx,
                "total": total,
                "status": f"Verifying candidate {idx} of {total}...",
                "verified": verified_count,
                "failed": failed_count,
                "eta": eta
            },
        )

    from app.utils.helpers import log_audit
    log_audit("bulk_verify_caps", "Candidate", None, {"total": total, "verified": verified_count, "failed": failed_count})
    db.session.commit()

    return {
        "status": "completed",
        "total": total,
        "verified": verified_count,
        "failed": failed_count,
        "errors": errors[:20],  # Cap errors returned
    }


# ---------------------------------------------------------------------------
# CAPS Upload Tasks
# ---------------------------------------------------------------------------

@shared_task(bind=True, name="tasks.upload_admission_list_to_caps")
def upload_admission_list_task(self, programme_id: int, session_id: int, user_id: int) -> dict:
    """
    Asynchronously upload an admission list to CAPS.
    """
    from app.models import AdmissionRecord
    from app.services.caps_sync import CAPSSyncService

    self.update_state(state="PROGRESS", meta={"status": "Fetching admitted candidates..."})

    try:
        admitted_records = AdmissionRecord.query.filter_by(
            programme_id=programme_id,
            session_id=session_id,
            status="admitted",
        ).all()

        if not admitted_records:
            return {"status": "failed", "message": "No admitted candidates found"}

        self.update_state(
            state="PROGRESS",
            meta={"status": f"Uploading {len(admitted_records)} records to CAPS..."},
        )

        result = CAPSSyncService.submit_admission_list_to_caps(
            programme_id, admitted_records, user_id
        )
        from app.utils.helpers import log_audit
        log_audit("upload_caps_admission_list", "Programme", programme_id, {"session_id": session_id, "user_id": user_id, "records_count": len(admitted_records)})
        db.session.commit()
        return result

    except Exception as exc:
        logger.exception("CAPS upload failed for programme %s", programme_id)
        from app.utils.helpers import log_audit
        log_audit("upload_caps_admission_list_failed", "Programme", programme_id, {"session_id": session_id, "error": str(exc)})
        db.session.commit()
        return {"status": "failed", "message": str(exc)}


# ---------------------------------------------------------------------------
# Merit List Generation Task
# ---------------------------------------------------------------------------

@shared_task(bind=True, name="tasks.generate_merit_list")
def generate_merit_list_task(self, programme_id: int, session_id: int) -> dict:
    """
    Asynchronously generate a merit list for a programme.
    """
    import time
    from app.services.merit_list import MeritListGenerator
    from app.models import Programme

    self.update_state(state="PROGRESS", meta={"current": 0, "total": 100, "status": "Initializing generator...", "eta": 1.0})
    start_time = time.time()

    try:
        programme = Programme.query.get(programme_id)
        prog_name = programme.code if programme else f"#{programme_id}"

        self.update_state(state="PROGRESS", meta={"current": 20, "total": 100, "status": f"Ranking candidates for {prog_name}...", "eta": 0.8})
        time.sleep(0.1)

        generator = MeritListGenerator(programme_id, session_id)
        
        self.update_state(state="PROGRESS", meta={"current": 50, "total": 100, "status": f"Applying quota limits for {prog_name}...", "eta": 0.5})
        result = generator.generate_full_list(persist=True)
        time.sleep(0.1)

        total_admitted = (
            len(result.get("merit", {}).get("admitted", [])) +
            len(result.get("catchment", {}).get("admitted", [])) +
            len(result.get("elds", {}).get("admitted", []))
        )

        self.update_state(state="PROGRESS", meta={"current": 90, "total": 100, "status": f"Finalizing database transactions for {prog_name}...", "eta": 0.1})
        db.session.commit()

        from app.utils.helpers import log_audit
        log_audit("generate_merit_list", "Programme", programme_id, {"session_id": session_id, "admitted": total_admitted})
        db.session.commit()

        return {
            "status": "completed",
            "programme_id": programme_id,
            "total_records": total_admitted,
        }

    except Exception as exc:
        db.session.rollback()
        logger.exception("Merit list generation failed for programme %s", programme_id)
        from app.utils.helpers import log_audit
        log_audit("generate_merit_list_failed", "Programme", programme_id, {"session_id": session_id, "error": str(exc)})
        db.session.commit()
        return {"status": "failed", "message": str(exc)}


@shared_task(bind=True, name="tasks.generate_all_merit_lists")
def generate_all_merit_lists_task(self, session_id: int) -> dict:
    """
    Asynchronously generate merit lists for ALL programmes.
    """
    import time
    from app.models import Programme
    from app.services.merit_list import MeritListGenerator

    self.update_state(state="PROGRESS", meta={"current": 0, "total": 100, "status": "Fetching academic programmes..."})

    try:
        programmes = Programme.query.all()
        total = len(programmes)
        if total == 0:
            return {"status": "completed", "total_programmes": 0, "total_admitted": 0}

        total_admitted = 0
        results = []
        start_time = time.time()

        for idx, programme in enumerate(programmes, 1):
            try:
                generator = MeritListGenerator(programme.id, session_id)
                merit_data = generator.generate_full_list(persist=True)
                stats = generator.get_statistics(merit_data)
                total_admitted += stats['filled']
                results.append({
                    'programme': programme.name,
                    'code': programme.code,
                    'admitted': stats['filled'],
                    'slots': stats['total_slots']
                })
            except Exception as prog_err:
                results.append({
                    'programme': programme.name,
                    'code': programme.code,
                    'error': str(prog_err)
                })

            # Update progress
            elapsed = time.time() - start_time
            rate = idx / elapsed if elapsed > 0 else 0
            eta = (total - idx) / rate if rate > 0 else 0

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": idx,
                    "total": total,
                    "status": f"Generating list for {programme.code} ({idx}/{total})...",
                    "total_admitted": total_admitted,
                    "eta": eta
                }
            )

        from app.utils.helpers import log_audit
        log_audit("generate_all_merit_lists", "AcademicSession", session_id, {"total_programmes": total, "total_admitted": total_admitted})
        db.session.commit()
        return {
            "status": "completed",
            "total_programmes": total,
            "total_admitted": total_admitted,
            "results": results
        }

    except Exception as exc:
        db.session.rollback()
        logger.exception("Global merit list generation failed")
        from app.utils.helpers import log_audit
        log_audit("generate_all_merit_lists_failed", "AcademicSession", session_id, {"error": str(exc)})
        db.session.commit()
        return {"status": "failed", "message": str(exc)}


@shared_task(bind=True, name="tasks.import_candidates")
def import_candidates_task(self, file_path: str, session_id: int) -> dict:
    """
    Asynchronously import candidates from a CSV file.
    """
    import time
    import pandas as pd
    from app.services.candidate_processor import CandidateProcessor

    self.update_state(state="PROGRESS", meta={"current": 0, "total": 100, "status": "Reading uploaded CSV file..."})

    try:
        df = pd.read_csv(file_path)
        processor = CandidateProcessor()

        if not processor.is_jamb_format(df):
            raise ValueError(
                "File is not in JAMB format. Expected columns: JAMB_REG, UTME_ENG, UTME_MATH, G1_SUBJECT, etc."
            )

        processor.validate_jamb_csv(df)

        total = len(df)
        successful_rows = 0
        start_time = time.time()

        for idx, row in df.iterrows():
            current_idx = idx + 1
            try:
                result = processor.process_jamb_row(row, session_id)
                if result:
                    successful_rows += 1
            except Exception as e:
                processor.errors.append(f"Row {current_idx+1}: {str(e)}")
                processor.skipped_count += 1

            # Update progress
            elapsed = time.time() - start_time
            rate = current_idx / elapsed if elapsed > 0 else 0
            eta = (total - current_idx) / rate if rate > 0 else 0

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": current_idx,
                    "total": total,
                    "status": f"Importing candidate {current_idx} of {total}...",
                    "created": processor.created_count,
                    "skipped": processor.skipped_count,
                    "errors": len(processor.errors),
                    "eta": eta
                }
            )

        if successful_rows > 0:
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                processor.errors.append(f"Failed to commit changes: {str(e)}")
                processor.created_count = 0
                processor.skipped_count += successful_rows

        # Clean up temp file
        try:
            import os
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

        from app.utils.helpers import log_audit
        log_audit("import_candidates", "AcademicSession", session_id, {
            "created": processor.created_count,
            "skipped": processor.skipped_count,
            "errors": len(processor.errors)
        })
        db.session.commit()

        return {
            "status": "completed",
            "created": processor.created_count,
            "updated": processor.updated_count,
            "skipped": processor.skipped_count,
            "errors": len(processor.errors),
            "error_details": processor.errors[:10]
        }
    except Exception as e:
        # Clean up temp file on failure too
        try:
            import os
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        from app.utils.helpers import log_audit
        log_audit("import_candidates_failed", "AcademicSession", session_id, {"error": str(e)})
        db.session.commit()
        return {"status": "failed", "message": str(e)}


@shared_task(bind=True, name="tasks.screen_candidates")
def screen_candidates_task(self, candidate_ids: list) -> dict:
    """
    Asynchronously screen a list of candidates.
    """
    import time
    from app.models import University, Candidate, AdmissionRecord, AdmissionBatch
    from app.services.screening_engine import ScreeningEngine

    total = len(candidate_ids)
    if total == 0:
        return {"status": "completed", "total": 0, "admitted": 0, "rejected": 0}

    self.update_state(state="PROGRESS", meta={"current": 0, "total": total, "status": "Starting screening..."})

    university = University.query.first()
    if not university:
        return {"status": "failed", "message": "No university configured"}

    from app.utils.helpers import get_active_session
    active_session = get_active_session()
    if not active_session:
        return {"status": "failed", "message": "No active academic session found"}

    candidates = Candidate.query.filter(Candidate.id.in_(candidate_ids)).all()
    
    # Group by programme
    programme_groups = {}
    for candidate in candidates:
        if not candidate.first_choice_programme_id:
            continue
        pid = candidate.first_choice_programme_id
        programme_groups.setdefault(pid, []).append(candidate)

    if not programme_groups:
        return {"status": "completed", "total": 0, "admitted": 0, "rejected": 0}

    # Initialize a batch to track progress
    batch = AdmissionBatch(
        session_id=active_session.id,
        programme_id=next(iter(programme_groups)),
        batch_name=f"AsyncBatch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        quota_category="all",
        total_candidates=len(candidates),
        admitted_count=0,
        rejected_count=0
    )
    db.session.add(batch)
    db.session.flush()

    total_admitted = 0
    total_rejected = 0
    processed_count = 0
    start_time = time.time()

    for programme_id, prog_candidates in programme_groups.items():
        try:
            engine = ScreeningEngine(
                university_id=university.id,
                programme_id=programme_id,
                session_id=active_session.id
            )
            for c in prog_candidates:
                result = engine.screen_candidate(c)
                if result.get('status') == 'recommended':
                    total_admitted += 1
                else:
                    total_rejected += 1
                processed_count += 1
                
                # Update progress
                elapsed = time.time() - start_time
                rate = processed_count / elapsed if elapsed > 0 else 0
                eta = (total - processed_count) / rate if rate > 0 else 0
                
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": processed_count,
                        "total": total,
                        "status": f"Screening candidate {processed_count} of {total} ({c.full_name})...",
                        "admitted": total_admitted,
                        "rejected": total_rejected,
                        "eta": eta
                    }
                )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.exception("Screening failed for programme %s", programme_id)

    batch.admitted_count = total_admitted
    batch.rejected_count = total_rejected
    batch.processed_at = datetime.utcnow()
    
    from app.utils.helpers import log_audit
    log_audit("screen_candidates_completed", "AcademicSession", active_session.id, {
        "batch_id": batch.id,
        "total": total,
        "admitted": total_admitted,
        "rejected": total_rejected
    })
    db.session.commit()

    return {
        "status": "completed",
        "batch_id": batch.id,
        "total": total,
        "admitted": total_admitted,
        "rejected": total_rejected
    }


# ---------------------------------------------------------------------------
# Email Notification Stub (Phase 4 - ready to wire in SMTP)
# ---------------------------------------------------------------------------

@shared_task(bind=True, name="tasks.send_notification_email")
def send_notification_email_task(self, recipient_email: str, subject: str, body: str) -> dict:
    """
    Send an email notification asynchronously.
    Currently a stub — wire in Flask-Mail or SMTP in Phase 4.
    """
    logger.info("EMAIL STUB: To=%s | Subject=%s", recipient_email, subject)
    # TODO: Integrate Flask-Mail in Phase 4
    return {"status": "sent_stub", "recipient": recipient_email}
