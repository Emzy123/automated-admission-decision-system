from typing import Dict, List, Any

from app import db
from app.models import (
    AdmissionRecord, AdmissionRule, Candidate, ELDSState, 
    Programme, University
)

DEFAULT_GRADE_POINTS = {
    "A1": 8, "B2": 7, "B3": 6, "C4": 5, "C5": 4, "C6": 3
}


class ScreeningEngine:
    """
    Core rule-based evaluation engine for candidate screening.
    Applies all admission rules and generates decisions with reasoning trace.
    """
    
    def __init__(self, university_id: int, programme_id: int, session_id: int):
        self.university = University.query.get(university_id)
        self.programme = Programme.query.get(programme_id)
        self.session_id = session_id
        self.grade_points = self.university.grade_points or DEFAULT_GRADE_POINTS
    
    def check_utme_cutoff(self, candidate: Candidate) -> Dict[str, Any]:
        """Check if UTME score meets departmental minimum"""
        min_score = self.programme.min_utme_score or self.university.min_utme_score
        passed = candidate.utme_score >= min_score
        return {
            'passed': passed,
            'candidate_score': candidate.utme_score,
            'required_score': min_score,
            'message': f"UTME: {candidate.utme_score} {'>=' if passed else '<'} {min_score}"
        }
    
    def check_subject_combination(self, candidate: Candidate) -> Dict[str, Any]:
        """Verify JAMB subject combination matches programme requirements"""
        required = set(self.programme.required_utme_subjects or [])
        taken = set(candidate.utme_subjects.keys()) if candidate.utme_subjects else set()
        
        missing = required - taken
        passed = len(missing) == 0
        
        return {
            'passed': passed,
            'required': list(required),
            'taken': list(taken),
            'missing': list(missing),
            'message': f"Subjects: {'Valid' if passed else f'Missing {missing}'}"
        }
    
    def check_olevel_credits(self, candidate: Candidate) -> Dict[str, Any]:
        """Count O'Level credits and check mandatory subjects"""
        credit_grades = ['A1', 'B2', 'B3', 'C4', 'C5', 'C6']
        results = candidate.olevel_results
        
        # Count total credits
        credits = [r for r in results if r.grade.upper() in credit_grades]
        credit_count = len(set(f"{r.subject}_{r.sitting_number}" for r in credits))
        
        # Check mandatory subjects
        mandatory = self.programme.mandatory_olevel_subjects or ['English Language', 'Mathematics']
        mandatory_passed = []
        mandatory_failed = []
        
        for subject in mandatory:
            subject_credits = [r for r in credits if r.subject.lower() == subject.lower()]
            if subject_credits:
                best_grade = max(subject_credits, key=lambda x: self.grade_points.get(x.grade.upper(), 0))
                mandatory_passed.append({'subject': subject, 'grade': best_grade.grade})
            else:
                mandatory_failed.append(subject)
        
        min_credits = self.university.min_olevel_credits
        passed = credit_count >= min_credits and len(mandatory_failed) == 0
        
        return {
            'passed': passed,
            'credit_count': credit_count,
            'required_credits': min_credits,
            'mandatory_passed': mandatory_passed,
            'mandatory_failed': mandatory_failed,
            'message': f"O'Level: {credit_count}/{min_credits} credits"
        }
    
    def check_olevel_sittings(self, candidate: Candidate) -> Dict[str, Any]:
        """Verify number of exam sittings is within limit"""
        results = candidate.olevel_results
        sittings = set()
        for r in results:
            sittings.add(f"{r.exam_body}_{r.exam_year}")
        
        max_sittings = self.university.max_olevel_sittings
        sitting_count = len(sittings)
        passed = sitting_count <= max_sittings
        
        return {
            'passed': passed,
            'sitting_count': sitting_count,
            'max_allowed': max_sittings,
            'sittings': list(sittings),
            'message': f"Sittings: {sitting_count}/{max_sittings}"
        }
    
    def calculate_olevel_points(self, candidate: Candidate) -> Dict[str, Any]:
        """Calculate O'Level component based on university grading scale"""
        results = candidate.olevel_results
        
        # Get best grades per subject across sittings
        subject_best = {}
        for r in results:
            subject = r.subject.lower()
            points = self.grade_points.get(r.grade.upper(), 0)
            if subject not in subject_best or points > subject_best[subject]:
                subject_best[subject] = points
        
        # Get relevant subjects (mandatory + best others)
        mandatory = [s.lower() for s in (self.programme.mandatory_olevel_subjects or [])]
        
        mandatory_points = []
        for subj in mandatory:
            if subj in subject_best:
                mandatory_points.append(subject_best[subj])
            else:
                mandatory_points.append(0)
        
        # Get remaining best subjects to make 5 total (or all if less)
        remaining = [v for k, v in subject_best.items() if k not in mandatory]
        remaining.sort(reverse=True)
        
        needed = 5 - len(mandatory_points)
        additional = remaining[:max(0, needed)]
        
        all_points = mandatory_points + additional
        total_points = sum(all_points)
        
        return {
            'total_points': total_points,
            'max_possible': self.university.olevel_max_points or 50,
            'subjects_used': len(all_points),
            'breakdown': all_points
        }
    
    def calculate_aggregate(self, candidate: Candidate) -> Dict[str, Any]:
        """Calculate aggregate score based on CUSTECH formula"""
        
        # CUSTECH formula: (JAMB / 8) + (Post-UTME / 2)
        jamb_divisor = 8.0
        post_utme_divisor = 2.0  # CUSTECH uses 2, not 4
        
        jamb_comp = candidate.utme_score / jamb_divisor
        
        post_utme_comp = 0
        if candidate.post_utme_present and candidate.post_utme_score:
            post_utme_comp = candidate.post_utme_score / post_utme_divisor
        
        aggregate = jamb_comp + post_utme_comp
        
        return {
            'aggregate': round(aggregate, 2),
            'jamb_component': round(jamb_comp, 2),
            'post_utme_component': round(post_utme_comp, 2),
            'olevel_component': 0,
            'formula': 'CUSTECH'
        }
    
    def classify_quota_category(self, candidate: Candidate) -> str:
        """Determine quota category based on state of origin.
        
        Per JAMB policy, catchment (host state + immediate neighbours) takes
        precedence over the ELDS (educationally less-developed states) designation
        so that a state like Kogi — CUSTECH's host state — is correctly classified
        as catchment even though it also appears on the federal ELDS list.
        """
        state = candidate.state_of_origin

        # Check catchment FIRST — host-state quota has highest priority
        catchment_states = [c.state_name for c in self.university.catchment_states]
        if state in catchment_states:
            return 'catchment'

        # Then check ELDS
        elds_states = [s.state_name for s in ELDSState.query.all()]
        if state in elds_states:
            return 'elds'

        return 'merit'
    
    def evaluate_dynamic_rules(self, candidate: Candidate) -> List[Dict[str, Any]]:
        """Apply custom IF-THEN rules defined for the programme"""
        rules = AdmissionRule.query.filter_by(
            programme_id=self.programme.id, 
            is_active=True
        ).order_by(AdmissionRule.priority, AdmissionRule.logic_group).all()
        
        results = []
        for rule in rules:
            passed = self._evaluate_single_rule(rule, candidate)
            results.append({
                'rule_name': rule.rule_name,
                'passed': passed,
                'message': f"{rule.rule_name}: {'PASS' if passed else 'FAIL'}"
            })
        
        return results
    
    def _evaluate_single_rule(self, rule: AdmissionRule, candidate: Candidate) -> bool:
        """Evaluate a single rule against candidate data"""
        field_value = self._get_field_value(rule.condition_field, candidate)
        
        if rule.operator == ">=":
            return field_value >= float(rule.value)
        elif rule.operator == "<=":
            return field_value <= float(rule.value)
        elif rule.operator == "==":
            return str(field_value) == rule.value
        elif rule.operator == "!=":
            return str(field_value) != rule.value
        elif rule.operator == ">":
            return field_value > float(rule.value)
        elif rule.operator == "<":
            return field_value < float(rule.value)
        elif rule.operator == "IN":
            return str(field_value) in [v.strip() for v in rule.value.split(",")]
        elif rule.operator == "NOT_IN":
            return str(field_value) not in [v.strip() for v in rule.value.split(",")]
        
        return False
    
    def _get_field_value(self, field: str, candidate: Candidate):
        """Get candidate field value for rule evaluation"""
        if field == "utme_score":
            return candidate.utme_score
        elif field == "post_utme_score":
            return candidate.post_utme_score or 0
        elif field == "aggregate_score":
            agg = self.calculate_aggregate(candidate)
            return agg['aggregate']
        elif field == "olevel_english":
            for r in candidate.olevel_results:
                if r.subject.lower() == "english":
                    return self.grade_points.get(r.grade.upper(), 0)
            return 0
        elif field == "olevel_math":
            for r in candidate.olevel_results:
                if r.subject.lower() == "mathematics":
                    return self.grade_points.get(r.grade.upper(), 0)
            return 0
        elif field == "state_of_origin":
            return candidate.state_of_origin or ""
        
        return None
    
    def screen_candidate(self, candidate: Candidate) -> Dict[str, Any]:
        """Run complete screening pipeline on a single candidate"""
        evaluation_log = []
        
        # Step 1: UTME Cutoff
        utme_check = self.check_utme_cutoff(candidate)
        evaluation_log.append({'step': 'utme_cutoff', **utme_check})
        if not utme_check['passed']:
            return self._create_rejection(candidate, 'utme_cutoff', evaluation_log)
        
        # Step 2: Subject Combination
        subject_check = self.check_subject_combination(candidate)
        evaluation_log.append({'step': 'subject_combination', **subject_check})
        if not subject_check['passed']:
            return self._create_rejection(candidate, 'subject_combination', evaluation_log)
        
        # Step 3: O'Level Credits
        credit_check = self.check_olevel_credits(candidate)
        evaluation_log.append({'step': 'olevel_credits', **credit_check})
        if not credit_check['passed']:
            return self._create_rejection(candidate, 'olevel_credits', evaluation_log)
        
        # Step 4: O'Level Sittings
        sitting_check = self.check_olevel_sittings(candidate)
        evaluation_log.append({'step': 'olevel_sittings', **sitting_check})
        if not sitting_check['passed']:
            return self._create_rejection(candidate, 'olevel_sittings', evaluation_log)
        
        # Step 5: Calculate Aggregate
        aggregate_data = self.calculate_aggregate(candidate)
        evaluation_log.append({'step': 'aggregate', **aggregate_data})
        
        # Step 6: Quota Classification
        quota = self.classify_quota_category(candidate)
        evaluation_log.append({'step': 'quota', 'category': quota})
        
        # Step 7: Dynamic Rules (if any)
        rule_results = self.evaluate_dynamic_rules(candidate)
        evaluation_log.extend([{'step': 'dynamic_rule', **r} for r in rule_results])
        
        # Step 8: Cutoff Evaluation
        cutoff_field = f'{quota}_cutoff'
        cutoff = getattr(self.programme, cutoff_field, self.programme.merit_cutoff)
        aggregate_meets_cutoff = aggregate_data['aggregate'] >= (cutoff or 0)
        
        evaluation_log.append({
            'step': 'cutoff',
            'quota': quota,
            'aggregate': aggregate_data['aggregate'],
            'cutoff': cutoff,
            'passed': aggregate_meets_cutoff
        })
        
        status = 'recommended' if aggregate_meets_cutoff else 'rejected'
        
        return self._create_record(
            candidate, status, quota, aggregate_data, 
            evaluation_log, 
            utme_check['passed'],
            subject_check['passed'],
            credit_check['passed'],
            sitting_check['passed']
        )
    
    def screen_batch(self, candidate_ids: List[int]) -> Dict[str, Any]:
        """Screen multiple candidates and return summary"""
        results = []
        admitted = 0
        rejected = 0
        
        for cid in candidate_ids:
            candidate = Candidate.query.get(cid)
            if candidate:
                result = self.screen_candidate(candidate)
                results.append(result)
                if result.get('status') == 'recommended':
                    admitted += 1
                else:
                    rejected += 1
        
        return {
            'total': len(results),
            'admitted': admitted,
            'rejected': rejected,
            'results': results
        }
    
    def _create_rejection(self, candidate: Candidate, reason: str, log: List[Dict]) -> Dict[str, Any]:
        """Persist a rejection AdmissionRecord and return the result dict.

        Previously this method only returned an in-memory dict, leaving no
        database record for early-failed candidates (UTME cutoff, subjects,
        OLevel credits, sittings).  Every screened candidate now gets a row
        in admission_records so the dashboard counts, merit lists, and the
        screening results page all reflect the true outcome.
        """
        zero_aggregate = {
            'aggregate': 0.0,
            'jamb_component': 0.0,
            'post_utme_component': 0.0,
            'olevel_component': 0.0,
        }
        # Determine which checks already passed before the first failure
        step_names = ['utme_cutoff', 'subject_combination', 'olevel_credits', 'olevel_sittings']
        passed_flags = {s: False for s in step_names}
        for entry in log:
            step = entry.get('step')
            if step in passed_flags:
                passed_flags[step] = bool(entry.get('passed', False))

        return self._create_record(
            candidate=candidate,
            status='rejected',
            quota=None,
            aggregate_data=zero_aggregate,
            log=log,
            utme_ok=passed_flags['utme_cutoff'],
            subjects_ok=passed_flags['subject_combination'],
            credits_ok=passed_flags['olevel_credits'],
            sittings_ok=passed_flags['olevel_sittings'],
        )
    
    def _create_record(self, candidate: Candidate, status: str, quota: str, 
                      aggregate_data: Dict, log: List[Dict], utme_ok: bool, 
                      subjects_ok: bool, credits_ok: bool, sittings_ok: bool) -> Dict[str, Any]:
        """Create or update AdmissionRecord"""
        
        # Check if record already exists
        existing = AdmissionRecord.query.filter_by(
            candidate_id=candidate.id,
            programme_id=self.programme.id,
            session_id=self.session_id
        ).first()
        
        if existing:
            record = existing
        else:
            record = AdmissionRecord(
                candidate_id=candidate.id,
                programme_id=self.programme.id,
                session_id=self.session_id
            )
            db.session.add(record)
        
        # Update record fields
        record.utme_cutoff_passed = utme_ok
        record.subject_combination_passed = subjects_ok
        record.olevel_credits_passed = credits_ok
        record.olevel_sittings_passed = sittings_ok
        record.quota_category = quota
        record.jamb_component = aggregate_data['jamb_component']
        record.post_utme_component = aggregate_data['post_utme_component']
        record.olevel_component = aggregate_data['olevel_component']
        record.aggregate_score = aggregate_data['aggregate']
        record.status = status
        record.evaluation_log = log
        
        if status == 'rejected':
            # Find first failed step for rejection reason
            for step in log:
                if not step.get('passed', True):
                    record.rejection_reason = step.get('step', 'Unknown')
                    break
        
        db.session.flush()
        
        return {
            'candidate_id': candidate.id,
            'status': status,
            'quota_category': quota,
            'aggregate_score': aggregate_data['aggregate'],
            'evaluation_log': log,
            'record_id': record.id
        }


def run_screening_engine(candidates):
    """
    Legacy function for backward compatibility.
    """
    return {
        "message": "Use ScreeningEngine class instead.",
        "total_candidates_received": len(candidates) if candidates else 0,
    }
