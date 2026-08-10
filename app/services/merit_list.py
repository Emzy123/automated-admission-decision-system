from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
from io import BytesIO

from app import db
from app.models import AdmissionRecord, Programme, MeritListApproval, ELDSState


class MeritListGenerator:
    """
    Ranks candidates and generates merit lists per quota category.
    Applies slot limits and produces final admitted lists.
    """
    
    def __init__(self, programme_id: int, session_id: int):
        self.programme = Programme.query.get(programme_id)
        self.session_id = session_id
        if not self.programme:
            raise ValueError(f"Programme with ID {programme_id} not found")
    
    def _run_sequential_allocation(self, persist: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Executes the sequential quota allocation algorithm.
        All candidates compete for Merit first, then Catchment (if eligible), then ELDS (if eligible).
        Resolves ties in aggregate score by UTME score (DESC) and candidate database ID (ASC).
        """
        # Fetch all qualified candidates for this programme and session
        records = AdmissionRecord.query.filter(
            AdmissionRecord.programme_id == self.programme.id,
            AdmissionRecord.session_id == self.session_id,
            AdmissionRecord.status.in_(['recommended', 'admitted', 'finalized', 'waiting_list', 'accepted', 'declined'])
        ).options(
            db.joinedload(AdmissionRecord.candidate)
        ).all()

        # Catchment and ELDS states for eligibility checks
        catchment_states = {c.state_name for c in self.programme.university.catchment_states}
        elds_states = {s.state_name for s in ELDSState.query.all()}

        # Sort records:
        # 1. aggregate_score DESC
        # 2. Candidate.utme_score DESC
        # 3. Candidate.id ASC
        records.sort(
            key=lambda r: (
                -r.aggregate_score,
                -(r.candidate.utme_score if r.candidate else 0),
                (r.candidate.id if r.candidate else 0)
            )
        )

        merit_slots = self.programme.merit_slots
        catchment_slots = self.programme.catchment_slots
        elds_slots = self.programme.elds_slots

        merit_admitted = []
        merit_waiting = []
        catchment_admitted = []
        catchment_waiting = []
        elds_admitted = []
        elds_waiting = []

        merit_admitted_count = 0
        catchment_admitted_count = 0
        elds_admitted_count = 0

        # Run sequential allocation
        for r in records:
            candidate = r.candidate
            if not candidate:
                continue

            state = candidate.state_of_origin
            is_catchment = state in catchment_states
            is_elds = state in elds_states

            # 1. Competes for Merit first
            if merit_admitted_count < merit_slots:
                merit_admitted.append(r)
                if r.status != 'declined':
                    merit_admitted_count += 1
                r.quota_category = 'merit'
            # 2. Competes for Catchment next
            elif is_catchment and catchment_admitted_count < catchment_slots:
                catchment_admitted.append(r)
                if r.status != 'declined':
                    catchment_admitted_count += 1
                r.quota_category = 'catchment'
            # 3. Competes for ELDS next
            elif is_elds and elds_admitted_count < elds_slots:
                elds_admitted.append(r)
                if r.status != 'declined':
                    elds_admitted_count += 1
                r.quota_category = 'elds'
            # 4. Otherwise, goes to waiting list
            else:
                if is_catchment:
                    r.quota_category = 'catchment'
                    catchment_waiting.append(r)
                elif is_elds:
                    r.quota_category = 'elds'
                    elds_waiting.append(r)
                else:
                    r.quota_category = 'merit'
                    merit_waiting.append(r)

        # Update candidate/record statuses
        all_admitted = merit_admitted + catchment_admitted + elds_admitted
        all_waiting = merit_waiting + catchment_waiting + elds_waiting

        for r in all_admitted:
            if r.status == 'recommended':
                r.status = 'admitted'
                r.admitted_at = datetime.utcnow()
            if r.candidate:
                r.candidate.status = r.status

        for r in all_waiting:
            if r.status == 'admitted':
                r.status = 'recommended'
                r.admitted_at = None
            if r.candidate:
                r.candidate.status = r.status

        if persist:
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise e

        return {
            'merit': {
                'admitted': merit_admitted,
                'waiting': merit_waiting,
                'slot_limit': merit_slots
            },
            'catchment': {
                'admitted': catchment_admitted,
                'waiting': catchment_waiting,
                'slot_limit': catchment_slots
            },
            'elds': {
                'admitted': elds_admitted,
                'waiting': elds_waiting,
                'slot_limit': elds_slots
            }
        }

    def generate_quota_list(self, quota_category: str, persist: bool = False) -> Dict[str, Any]:
        """Generate ranked list and apply slot limit using sequential allocation"""
        full_list = self.generate_full_list(persist=persist)
        return full_list.get(quota_category)
    
    def generate_full_list(self, persist: bool = False) -> Dict[str, Any]:
        """Generate all three quota lists using sequential allocation"""
        allocation = self._run_sequential_allocation(persist=persist)
        
        result = {}
        for quota in ['merit', 'catchment', 'elds']:
            quota_data = allocation[quota]
            admitted = quota_data['admitted']
            waiting = quota_data['waiting']
            slot_limit = quota_data['slot_limit']
            
            eligible = [c for c in admitted + waiting if c.status != 'declined']
            
            admitted_formatted = self._format_candidates(admitted)
            waiting_formatted = self._format_candidates(waiting)
            
            # Cutoffs
            non_declined_admitted = [c for c in admitted if c.status != 'declined']
            cutoff_score = non_declined_admitted[-1].aggregate_score if non_declined_admitted else 0
            waiting_cutoff = waiting[0].aggregate_score if waiting else 0
            
            result[quota] = {
                'quota': quota,
                'slot_limit': slot_limit,
                'qualified_count': len(eligible),
                'admitted': admitted_formatted,
                'waiting': waiting_formatted,
                'cutoff_score': cutoff_score,
                'waiting_cutoff': waiting_cutoff
            }
            
        # Revert session dirtying if we didn't persist, ensuring read-only safety
        if not persist:
            db.session.rollback()
            
        result['programme'] = {
            'id': self.programme.id,
            'name': self.programme.name,
            'code': self.programme.code,
            'total_slots': self.programme.total_slots,
            'merit_slots': self.programme.merit_slots,
            'catchment_slots': self.programme.catchment_slots,
            'elds_slots': self.programme.elds_slots
        }
        
        return result
    
    def _format_candidates(self, records: List[AdmissionRecord]) -> List[Dict[str, Any]]:
        """Format admission records for display"""
        formatted = []
        for idx, record in enumerate(records, 1):
            candidate = record.candidate
            formatted.append({
                'rank': idx,
                'id': candidate.id,
                'jamb_reg': candidate.jamb_reg_number,
                'name': candidate.full_name,
                'state': candidate.state_of_origin,
                'aggregate': record.aggregate_score,
                'record_id': record.id,
                'utme_score': candidate.utme_score,
                'post_utme_score': candidate.post_utme_score,
                'quota_category': record.quota_category,
                'status': record.status
            })
        return formatted

    
    def export_to_excel(self, quota_category: Optional[str] = None) -> BytesIO:
        """Export merit list to Excel file"""
        if quota_category:
            # Export single quota list
            quota_data = self.generate_quota_list(quota_category)
            data = []
            
            # Add admitted candidates
            for candidate in quota_data['admitted']:
                data.append({
                    'Rank': candidate['rank'],
                    'JAMB Reg': candidate['jamb_reg'],
                    'Name': candidate['name'],
                    'State': candidate['state'],
                    'UTME Score': candidate['utme_score'],
                    'Post-UTME': candidate['post_utme_score'],
                    'Aggregate': candidate['aggregate'],
                    'Quota': quota_category.title(),
                    'Status': 'Admitted'
                })
            
            # Add waiting list
            for candidate in quota_data['waiting']:
                data.append({
                    'Rank': candidate['rank'],
                    'JAMB Reg': candidate['jamb_reg'],
                    'Name': candidate['name'],
                    'State': candidate['state'],
                    'UTME Score': candidate['utme_score'],
                    'Post-UTME': candidate['post_utme_score'],
                    'Aggregate': candidate['aggregate'],
                    'Quota': quota_category.title(),
                    'Status': 'Waiting List'
                })
            
            f"{self.programme.code}_{quota_category}_merit_list.xlsx"
        else:
            # Export full merit list
            full_data = self.generate_full_list()
            data = []
            
            for quota in ['merit', 'catchment', 'elds']:
                quota_data = full_data[quota]
                
                # Add admitted candidates
                for candidate in quota_data['admitted']:
                    data.append({
                        'Rank': candidate['rank'],
                        'JAMB Reg': candidate['jamb_reg'],
                        'Name': candidate['name'],
                        'State': candidate['state'],
                        'UTME Score': candidate['utme_score'],
                        'Post-UTME': candidate['post_utme_score'],
                        'Aggregate': candidate['aggregate'],
                        'Quota': quota.title(),
                        'Status': 'Admitted'
                    })
                
                # Add waiting list
                for candidate in quota_data['waiting']:
                    data.append({
                        'Rank': candidate['rank'],
                        'JAMB Reg': candidate['jamb_reg'],
                        'Name': candidate['name'],
                        'State': candidate['state'],
                        'UTME Score': candidate['utme_score'],
                        'Post-UTME': candidate['post_utme_score'],
                        'Aggregate': candidate['aggregate'],
                        'Quota': quota.title(),
                        'Status': 'Waiting List'
                    })
            
            f"{self.programme.code}_full_merit_list.xlsx"
        
        # Create Excel file
        df = pd.DataFrame(data)
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Merit List', index=False)
            
            # Get the worksheet
            worksheet = writer.sheets['Merit List']
            
            # Adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 30)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        return output
    
    def get_statistics(self, merit_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get admission statistics for the programme. If merit_data is not provided, runs sequential allocation in-memory (read-only)."""
        if merit_data is None:
            merit_data = self.generate_full_list(persist=False)
            
        total_slots = self.programme.total_slots
        
        def get_quota_stats(quota_key):
            quota_info = merit_data.get(quota_key, {})
            admitted = quota_info.get('admitted', [])
            waiting = quota_info.get('waiting', [])
            
            filled = sum(1 for c in admitted if c['status'] in ['admitted', 'finalized', 'accepted'])
            recommended = len(waiting)
            slots = quota_info.get('slot_limit', 0)
            
            return {
                'slots': slots,
                'filled': filled,
                'available': max(slots - filled, 0),
                'recommended': recommended
            }
            
        merit_stats = get_quota_stats('merit')
        catchment_stats = get_quota_stats('catchment')
        elds_stats = get_quota_stats('elds')
        
        total_filled = merit_stats['filled'] + catchment_stats['filled'] + elds_stats['filled']
        total_recommended = merit_stats['recommended'] + catchment_stats['recommended'] + elds_stats['recommended']
        
        return {
            'total_slots': total_slots,
            'filled': total_filled,
            'available': max(total_slots - total_filled, 0),
            'total_recommended': total_recommended,
            'merit': merit_stats,
            'catchment': catchment_stats,
            'elds': elds_stats
        }
    
    def finalize_list(self) -> bool:
        """Finalize the merit list and prevent further changes"""
        try:
            # Update all admitted records to finalized status in database and sync candidates
            admitted_records = AdmissionRecord.query.filter_by(
                programme_id=self.programme.id,
                session_id=self.session_id,
                status='admitted'
            ).all()
            for record in admitted_records:
                record.status = 'finalized'
                if record.candidate:
                    record.candidate.status = 'finalized'
            
            # Update all recommended but not admitted to waiting list in database and sync candidates
            recommended_records = AdmissionRecord.query.filter_by(
                programme_id=self.programme.id,
                session_id=self.session_id,
                status='recommended'
            ).all()
            for record in recommended_records:
                record.status = 'waiting_list'
                if record.candidate:
                    record.candidate.status = 'waiting_list'
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    def get_approval_status(self) -> Dict[str, Any]:
        """Get approval status for the merit list"""
        approval = MeritListApproval.query.filter_by(
            programme_id=self.programme.id,
            session_id=self.session_id
        ).first()
        
        if not approval:
            return {
                'department_approved': False,
                'faculty_approved': False,
                'senate_approved': False,
                'finalized': False
            }
        
        return {
            'department_approved': approval.department_approved,
            'faculty_approved': approval.faculty_approved,
            'senate_approved': approval.senate_approved,
            'finalized': approval.finalized,
            'department_approved_by': approval.department_approved_by,
            'faculty_approved_by': approval.faculty_approved_by,
            'senate_approved_by': approval.senate_approved_by,
            'department_approved_at': approval.department_approved_at,
            'faculty_approved_at': approval.faculty_approved_at,
            'senate_approved_at': approval.senate_approved_at
        }


def build_merit_list(screened_candidates):
    """
    Legacy function for backward compatibility.
    """
    return {
        "message": "Use MeritListGenerator class instead.",
        "total_screened_candidates": len(screened_candidates) if screened_candidates else 0,
    }
