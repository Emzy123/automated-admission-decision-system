"""
Report Generation Service
Generates various admission reports in PDF and Excel formats
"""

import pandas as pd
from io import BytesIO
from datetime import datetime
from typing import Dict, Any, Optional

from app import db
from app.models import (
    AdmissionRecord, Candidate, Programme, AcademicSession, 
    University
)
from app.services.merit_list import MeritListGenerator
from app.services.mock_caps import MockCAPSService


class ReportGenerator:
    """Generate various admission reports in PDF and Excel formats"""
    
    def __init__(self, session_id: int):
        self.session = AcademicSession.query.get(session_id)
        if not self.session:
            raise ValueError(f"Session with ID {session_id} not found")
    
    def generate_admission_letter(self, admission_record: AdmissionRecord) -> BytesIO:
        """Generate provisional admission letter PDF"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.enums import TA_LEFT
            from reportlab.lib import colors
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            candidate = admission_record.candidate
            programme = admission_record.programme
            university = University.query.first()
            
            # University Logo and Header
            title_style = styles['Heading1']
            story.append(Paragraph(f"{university.name.upper()}", title_style))
            story.append(Paragraph("PROVISIONAL ADMISSION LETTER", title_style))
            story.append(Spacer(1, 20))
            
            # Session and Date
            normal_style = styles['Normal']
            story.append(Paragraph(f"Session: {self.session.name}", normal_style))
            story.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", normal_style))
            story.append(Spacer(1, 20))
            
            # Candidate Details
            story.append(Paragraph(f"Dear {candidate.full_name},", normal_style))
            story.append(Spacer(1, 10))
            
            # Admission Details
            admission_data = [
                ['JAMB Registration Number:', candidate.jamb_reg_number],
                ['Programme of Study:', programme.name],
                ['Faculty:', programme.faculty.name if programme.faculty else 'N/A'],
                ['Duration:', f"{programme.duration_years} Years"],
                ['Quota Category:', admission_record.quota_category.upper()],
                ['Aggregate Score:', str(admission_record.aggregate_score)]
            ]
            
            admission_table = Table(admission_data, colWidths=[2.5*inch, 4*inch])
            admission_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.grey),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            story.append(admission_table)
            story.append(Spacer(1, 20))
            
            # Body text
            body_text = """
            Congratulations! I am pleased to inform you that you have been offered provisional admission to the above-named programme for the {duration_years} year programme, subject to the following conditions:
            
            1. You must accept this offer on the JAMB Central Admissions Processing System (CAPS) within 2 weeks from the date of this letter.
            2. You must present your original credentials for physical verification during the clearance exercise.
            3. This admission is provisional and may be withdrawn if any discrepancy is found in your credentials.
            4. Payment of the acceptance fee must be made within the stipulated period.
            5. You must meet all registration requirements by the specified deadlines.
            
            We look forward to welcoming you to our institution.
            """.format(duration_years=programme.duration_years)
            
            story.append(Paragraph(body_text, normal_style))
            story.append(Spacer(1, 20))
            
            # Conditions
            conditions_style = styles['Heading3']
            story.append(Paragraph("Conditions of Admission:", conditions_style))
            
            conditions = [
                "1. You must accept this offer on JAMB CAPS within 2 weeks.",
                "2. You must present original credentials for physical verification.",
                "3. This admission is provisional and subject to credential verification.",
                "4. Payment of acceptance fee must be made within stipulated period.",
                "5. You must meet all registration requirements by specified deadlines."
            ]
            
            for condition in conditions:
                story.append(Paragraph(condition, normal_style))
            
            story.append(Spacer(1, 30))
            
            # Signature section
            signature_style = styles['Normal']
            story.append(Paragraph("__________________________", signature_style))
            story.append(Paragraph("Registrar", signature_style))
            story.append(Paragraph(university.name, signature_style))
            
            # JAMB Reference (simulated)
            story.append(Spacer(1, 20))
            jamb_ref = MockCAPSService.generate_admission_letter_reference(
                candidate.jamb_reg_number, 
                programme.code
            )
            story.append(Paragraph(f"JAMB Reference: {jamb_ref}", normal_style))
            
            doc.build(story)
            buffer.seek(0)
            return buffer
            
        except ImportError:
            # Fallback to simple text if reportlab not available
            buffer = BytesIO()
            content = f"""
            PROVISIONAL ADMISSION LETTER
            
            Date: {datetime.now().strftime('%B %d, %Y')}
            
            Dear {candidate.full_name},
            
            Congratulations! You have been offered provisional admission to {programme.name}.
            
            JAMB Registration: {candidate.jamb_reg_number}
            Programme: {programme.name}
            Duration: {programme.duration_years} Years
            Quota: {admission_record.quota_category}
            Aggregate: {admission_record.aggregate_score}
            
            Please accept this offer on JAMB CAPS within 2 weeks and present your original credentials for verification.
            
            Registrar
            {university.name}
            """
            
            buffer.write(content.encode())
            buffer.seek(0)
            return buffer
    
    def generate_statistics_report(self, programme_id: Optional[int] = None) -> BytesIO:
        """Generate comprehensive admission statistics PDF report"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.enums import TA_CENTER
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title_style = styles['Heading1']
            story.append(Paragraph("ADMISSION STATISTICS REPORT", title_style))
            story.append(Paragraph(f"Session: {self.session.name}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            if programme_id:
                programmes = [Programme.query.get(programme_id)]
            else:
                programmes = Programme.query.all()
            
            for programme in programmes:
                generator = MeritListGenerator(programme.id, self.session.id)
                stats = generator.get_statistics()
                
                # Programme header
                programme_style = styles['Heading2']
                story.append(Paragraph(f"Programme: {programme.name}", programme_style))
                story.append(Paragraph(f"Code: {programme.code}", styles['Normal']))
                story.append(Spacer(1, 12))
                
                # Summary table
                summary_data = [
                    ['Category', 'Slots', 'Filled', 'Available', 'Utilization'],
                    ['Merit', stats['merit']['slots'], stats['merit']['filled'], 
                     stats['merit']['available'], f"{stats['merit']['filled']}/{stats['merit']['slots']}"],
                    ['Catchment', stats['catchment']['slots'], stats['catchment']['filled'],
                     stats['catchment']['available'], f"{stats['catchment']['filled']}/{stats['catchment']['slots']}"],
                    ['ELDS', stats['elds']['slots'], stats['elds']['filled'],
                     stats['elds']['available'], f"{stats['elds']['filled']}/{stats['elds']['slots']}"],
                    ['TOTAL', stats['total_slots'], stats['filled'], 
                     stats['available'], f"{stats['filled']}/{stats['total_slots']}"]
                ]
                
                summary_table = Table(summary_data, colWidths=[1.2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
                summary_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.grey),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                
                story.append(summary_table)
                story.append(Spacer(1, 20))
            
            doc.build(story)
            buffer.seek(0)
            return buffer
            
        except ImportError:
            # Fallback to simple text if reportlab not available
            buffer = BytesIO()
            content = f"""
            ADMISSION STATISTICS REPORT
            Session: {self.session.name}
            Generated: {datetime.now().strftime('%B %d, %Y')}
            
            """
            
            for programme in programmes:
                content += f"""
                Programme: {programme.name} ({programme.code})
                Total Slots: {programme.total_slots}
                """
            
            buffer.write(content.encode())
            buffer.seek(0)
            return buffer
    
    def generate_excel_export(self, programme_id: int, quota_category: Optional[str] = None) -> BytesIO:
        """Export admission list to Excel"""
        programme = Programme.query.get(programme_id)
        if not programme:
            raise ValueError(f"Programme with ID {programme_id} not found")
        
        # Get admitted candidates
        query = AdmissionRecord.query.filter_by(
            programme_id=programme_id,
            session_id=self.session.id,
            status='admitted'
        )
        
        if quota_category:
            query = query.filter_by(quota_category=quota_category)
        
        records = query.order_by(AdmissionRecord.aggregate_score.desc()).all()
        
        # Build dataframe
        data = []
        for idx, record in enumerate(records, 1):
            candidate = record.candidate
            data.append({
                'Rank': idx,
                'JAMB Reg Number': candidate.jamb_reg_number,
                'Full Name': candidate.full_name,
                'State of Origin': candidate.state_of_origin,
                'UTME Score': candidate.utme_score,
                'Post-UTME Score': candidate.post_utme_score or 'N/A',
                'Aggregate Score': record.aggregate_score,
                'Quota Category': record.quota_category.upper(),
                'Status': record.status.upper(),
                'Admission Date': record.admitted_at.strftime('%Y-%m-%d') if record.admitted_at else 'N/A'
            })
        
        df = pd.DataFrame(data)
        
        # Create Excel file
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            sheet_name = f"{programme.code}_{quota_category or 'ALL'}"
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets[sheet_name]
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
        
        buffer.seek(0)
        return buffer
    
    def generate_summary_dashboard_data(self) -> Dict[str, Any]:
        """Generate JSON data for dashboard charts"""
        total_candidates = Candidate.query.filter_by(session_id=self.session.id).count()
        
        screened = AdmissionRecord.query.filter_by(session_id=self.session.id).count()
        
        admitted = AdmissionRecord.query.filter_by(
            session_id=self.session.id,
            status='admitted'
        ).count()
        
        rejected = AdmissionRecord.query.filter_by(
            session_id=self.session.id,
            status='rejected'
        ).count()
        
        pending = total_candidates - screened
        
        # Quota distribution
        quota_data = db.session.query(
            AdmissionRecord.quota_category,
            db.func.count(AdmissionRecord.id)
        ).filter_by(
            session_id=self.session.id,
            status='admitted'
        ).group_by(AdmissionRecord.quota_category).all()
        
        # State distribution
        state_data = db.session.query(
            Candidate.state_of_origin,
            db.func.count(Candidate.id)
        ).join(AdmissionRecord).filter(
            AdmissionRecord.session_id == self.session.id,
            AdmissionRecord.status == 'admitted'
        ).group_by(Candidate.state_of_origin).order_by(
            db.func.count(Candidate.id).desc()
        ).limit(10).all()
        
        return {
            'summary': {
                'total_candidates': total_candidates,
                'screened': screened,
                'admitted': admitted,
                'rejected': rejected,
                'pending': pending,
                'admission_rate': (admitted / screened * 100) if screened > 0 else 0
            },
            'quota_distribution': dict(quota_data),
            'state_distribution': dict(state_data),
            'last_updated': datetime.now().isoformat()
        }
    
    def generate_batch_letters(self, programme_id: int) -> BytesIO:
        """Generate ZIP file with all admission letters for a programme"""
        import zipfile
        
        programme = Programme.query.get(programme_id)
        if not programme:
            raise ValueError(f"Programme with ID {programme_id} not found")
        
        records = AdmissionRecord.query.filter_by(
            programme_id=programme_id,
            session_id=self.session.id,
            status='admitted'
        ).all()
        
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for record in records:
                pdf_buffer = self.generate_admission_letter(record)
                filename = f"{record.candidate.jamb_reg_number}_{record.candidate.full_name.replace(' ', '_')}.pdf"
                zip_file.writestr(filename, pdf_buffer.getvalue())
        
        zip_buffer.seek(0)
        return zip_buffer
