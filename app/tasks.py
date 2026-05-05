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
    from app.models import Candidate
    from app.services.mock_caps import MockCAPSService

    total = len(candidate_ids)
    verified_count = 0
    failed_count = 0
    errors = []

    self.update_state(state="PROGRESS", meta={"current": 0, "total": total, "status": "Starting..."})

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
        self.update_state(
            state="PROGRESS",
            meta={
                "current": idx,
                "total": total,
                "status": f"Processed {idx}/{total}",
                "verified": verified_count,
                "failed": failed_count,
            },
        )

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
        return result

    except Exception as exc:
        logger.exception("CAPS upload failed for programme %s", programme_id)
        return {"status": "failed", "message": str(exc)}


# ---------------------------------------------------------------------------
# Merit List Generation Task
# ---------------------------------------------------------------------------

@shared_task(bind=True, name="tasks.generate_merit_list")
def generate_merit_list_task(self, programme_id: int, session_id: int) -> dict:
    """
    Asynchronously generate a merit list for a programme.
    """
    from app.services.merit_list import MeritListGenerator

    self.update_state(state="PROGRESS", meta={"status": "Generating merit list..."})

    try:
        generator = MeritListGenerator(programme_id, session_id)
        result = generator.generate_full_list()

        return {
            "status": "completed",
            "programme_id": programme_id,
            "total_records": len(result.get("all_candidates", [])),
        }

    except Exception as exc:
        logger.exception("Merit list generation failed for programme %s", programme_id)
        return {"status": "failed", "message": str(exc)}


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
