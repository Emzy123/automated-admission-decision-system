from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
from io import BytesIO

from app import db
from app.models import AdmissionRecord, Programme, MeritListApproval


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
    
    def get_qualified_candidates(self, quota_category: str) -> List[AdmissionRecord]:
        """Get all candidates in a quota category (excluding pending/rejected)"""
        return AdmissionRecord.query.filter(
            AdmissionRecord.programme_id == self.programme.id,
            AdmissionRecord.session_id == self.session_id,
            AdmissionRecord.quota_category == quota_category,
            AdmissionRecord.status.in_(['recommended', 'admitted', 'accepted', 'declined'])
        ).options(
            db.joinedload(AdmissionRecord.candidate)
        ).order_by(AdmissionRecord.aggregate_score.desc()).all()
    
    def generate_quota_list(self, quota_category: str) -> Dict[str, Any]:
        """Generate ranked list and apply slot limit"""
        candidates = self.get_qualified_candidates(quota_category)
        
        # Only non-declined candidates count toward slot limits
        eligible = [c for c in candidates if c.status != 'declined']
        slot_limit = getattr(self.programme, f'{quota_category}_slots', 0)
        
        admitted = eligible[:slot_limit]
        waiting = eligible[slot_limit:]
        
        # Include declined records in the admitted section for visibility (they won't take up real slots)
        declined_records = [c for c in candidates if c.status == 'declined']
        
        # Update status for admitted candidates
        for record in admitted:
            if record.status == 'recommended':
                record.status = 'admitted'
                record.admitted_at = datetime.utcnow()
                
        # Reset status for waiting list candidates if they were previously admitted
        for record in waiting:
            if record.status == 'admitted':
                record.status = 'recommended'
                record.admitted_at = None
                
        try:
            db.session.commit()
        except:
            db.session.rollback()
        
        # Format for display — declined records shown in admitted section but visually muted
        return {
            'quota': quota_category,
            'slot_limit': slot_limit,
            'qualified_count': len(eligible),
            'admitted': self._format_candidates(admitted + declined_records),
            'waiting': self._format_candidates(waiting),
            'cutoff_score': admitted[-1].aggregate_score if admitted else 0,
            'waiting_cutoff': waiting[0].aggregate_score if waiting else 0
        }
    
    def generate_full_list(self) -> Dict[str, Any]:
        """Generate all three quota lists"""
        return {
            'merit': self.generate_quota_list('merit'),
            'catchment': self.generate_quota_list('catchment'),
            'elds': self.generate_quota_list('elds'),
            'programme': {
                'id': self.programme.id,
                'name': self.programme.name,
                'code': self.programme.code,
                'total_slots': self.programme.total_slots,
                'merit_slots': self.programme.merit_slots,
                'catchment_slots': self.programme.catchment_slots,
                'elds_slots': self.programme.elds_slots
            }
        }
    
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
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get admission statistics for the programme"""
        total_slots = self.programme.total_slots
        
        # Count admitted candidates by quota
        admitted_merit = AdmissionRecord.query.filter_by(
            programme_id=self.programme.id,
            session_id=self.session_id,
            status='admitted',
            quota_category='merit'
        ).count()
        
        admitted_catchment = AdmissionRecord.query.filter_by(
            programme_id=self.programme.id,
            session_id=self.session_id,
            status='admitted',
            quota_category='catchment'
        ).count()
        
        admitted_elds = AdmissionRecord.query.filter_by(
            programme_id=self.programme.id,
            session_id=self.session_id,
            status='admitted',
            quota_category='elds'
        ).count()
        
        # Count recommended candidates by quota
        recommended_merit = AdmissionRecord.query.filter_by(
            programme_id=self.programme.id,
            session_id=self.session_id,
            status='recommended',
            quota_category='merit'
        ).count()
        
        recommended_catchment = AdmissionRecord.query.filter_by(
            programme_id=self.programme.id,
            session_id=self.session_id,
            status='recommended',
            quota_category='catchment'
        ).count()
        
        recommended_elds = AdmissionRecord.query.filter_by(
            programme_id=self.programme.id,
            session_id=self.session_id,
            status='recommended',
            quota_category='elds'
        ).count()
        
        total_filled = admitted_merit + admitted_catchment + admitted_elds
        total_recommended = recommended_merit + recommended_catchment + recommended_elds
        
        return {
            'total_slots': total_slots,
            'filled': total_filled,
            'available': total_slots - total_filled,
            'total_recommended': total_recommended,
            'merit': {
                'slots': self.programme.merit_slots,
                'filled': admitted_merit,
                'available': self.programme.merit_slots - admitted_merit,
                'recommended': recommended_merit
            },
            'catchment': {
                'slots': self.programme.catchment_slots,
                'filled': admitted_catchment,
                'available': self.programme.catchment_slots - admitted_catchment,
                'recommended': recommended_catchment
            },
            'elds': {
                'slots': self.programme.elds_slots,
                'filled': admitted_elds,
                'available': self.programme.elds_slots - admitted_elds,
                'recommended': recommended_elds
            }
        }
    
    def finalize_list(self) -> bool:
        """Finalize the merit list and prevent further changes"""
        try:
            # Update all admitted records to finalized status
            AdmissionRecord.query.filter_by(
                programme_id=self.programme.id,
                session_id=self.session_id,
                status='admitted'
            ).update({'status': 'finalized'})
            
            # Update all recommended but not admitted to waiting list
            AdmissionRecord.query.filter_by(
                programme_id=self.programme.id,
                session_id=self.session_id,
                status='recommended'
            ).update({'status': 'waiting_list'})
            
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
