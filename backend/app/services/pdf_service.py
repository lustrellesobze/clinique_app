"""
Service de génération de PDF pour factures, ordonnances, rapports
"""
from datetime import datetime
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.models.invoice import Facture
from app.models.patient import Patient
from app.models.insurance import Insurance
from app.models.prescription import Prescription


class PDFService:
    """Service pour générer des documents PDF"""
    
    @staticmethod
    def generate_invoice_pdf(facture: Facture, patient: Patient, insurance: Optional[Insurance] = None) -> BytesIO:
        """
        Génère un PDF de facture
        
        Args:
            facture: Objet Facture
            patient: Objet Patient
            insurance: Objet Insurance (optionnel)
            
        Returns:
            BytesIO contenant le PDF généré
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, 
                               topMargin=2*cm, bottomMargin=2*cm)
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e3a5f'),
            spaceAfter=30,
            alignment=1  # Center
        )
        
        # Contenu du document
        story = []
        
        # En-tête
        story.append(Paragraph("CLINIQUE MÉDICALE", title_style))
        story.append(Paragraph("Facture", styles['Heading2']))
        story.append(Spacer(1, 0.5*cm))
        
        # Informations facture
        info_data = [
            ['Numéro de facture:', facture.numero_facture],
            ['Date:', facture.created_at.strftime('%d/%m/%Y %H:%M')],
            ['Statut:', facture.statut.value.upper()],
        ]
        
        info_table = Table(info_data, colWidths=[5*cm, 10*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1e3a5f')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.5*cm))
        
        # Informations patient
        story.append(Paragraph("Informations Patient", styles['Heading3']))
        patient_data = [
            ['Nom:', f"{patient.nom} {patient.prenom}"],
            ['Téléphone:', patient.telephone or 'N/A'],
            ['Email:', patient.email or 'N/A'],
        ]
        
        if insurance:
            patient_data.append(['Assurance:', insurance.nom_compagnie])
            patient_data.append(['Taux de couverture:', f"{insurance.taux_couverture}%"])
        
        patient_table = Table(patient_data, colWidths=[5*cm, 10*cm])
        patient_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(patient_table)
        story.append(Spacer(1, 1*cm))
        
        # Détails de la facture
        story.append(Paragraph("Détails de la facture", styles['Heading3']))
        
        # Lignes de facture
        if facture.lignes:
            ligne_data = [['Désignation', 'Qté', 'Prix Unit.', 'Remise', 'Total']]
            for ligne in facture.lignes:
                ligne_data.append([
                    ligne.designation,
                    str(ligne.quantite),
                    f"{ligne.prix_unitaire:,.0f} FCFA",
                    f"{ligne.remise_montant:,.0f} FCFA",
                    f"{ligne.montant_ligne:,.0f} FCFA"
                ])
            
            ligne_table = Table(ligne_data, colWidths=[7*cm, 2*cm, 3*cm, 2.5*cm, 2.5*cm])
            ligne_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(ligne_table)
            story.append(Spacer(1, 0.5*cm))
        
        # Totaux
        totaux_data = [
            ['Montant total:', f"{facture.montant_total:,.0f} FCFA"],
        ]
        
        if facture.remise_globale and facture.remise_globale > 0:
            totaux_data.append(['Remise globale:', f"{facture.remise_globale:,.0f} FCFA"])
        
        if facture.part_assurance and facture.part_assurance > 0:
            totaux_data.append(['Part assurance:', f"{facture.part_assurance:,.0f} FCFA"])
            totaux_data.append(['Part patient:', f"{facture.part_patient:,.0f} FCFA"])
        
        totaux_data.append(['Montant réglé:', f"{facture.montant_regle:,.0f} FCFA"])
        reste = facture.montant_total - facture.montant_regle
        totaux_data.append(['Reste à payer:', f"{reste:,.0f} FCFA"])
        
        totaux_table = Table(totaux_data, colWidths=[10*cm, 7*cm])
        totaux_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#e87722')),
            ('FONTSIZE', (0, -1), (-1, -1), 13),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#1e3a5f')),
        ]))
        story.append(totaux_table)
        
        # Pied de page
        story.append(Spacer(1, 2*cm))
        story.append(Paragraph("Merci de votre confiance", styles['Normal']))
        
        # Générer le PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def generate_prescription_pdf(prescription: Prescription, patient: Patient) -> BytesIO:
        """
        Génère un PDF d'ordonnance
        
        Args:
            prescription: Objet Prescription
            patient: Objet Patient
            
        Returns:
            BytesIO contenant le PDF généré
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e3a5f'),
            spaceAfter=30,
            alignment=1
        )
        
        story = []
        
        # En-tête
        story.append(Paragraph("CLINIQUE MÉDICALE", title_style))
        story.append(Paragraph("Ordonnance Médicale", styles['Heading2']))
        story.append(Spacer(1, 0.5*cm))
        
        # Date
        story.append(Paragraph(f"Date: {prescription.created_at.strftime('%d/%m/%Y')}", styles['Normal']))
        story.append(Spacer(1, 0.5*cm))
        
        # Informations patient
        story.append(Paragraph("Patient", styles['Heading3']))
        patient_info = f"{patient.nom} {patient.prenom}<br/>Né(e) le: {patient.date_naissance.strftime('%d/%m/%Y')}"
        story.append(Paragraph(patient_info, styles['Normal']))
        story.append(Spacer(1, 1*cm))
        
        # Médicaments prescrits
        story.append(Paragraph("Prescription", styles['Heading3']))
        
        if prescription.items:
            for idx, item in enumerate(prescription.items, 1):
                med_text = f"<b>{idx}. {item.nom_medicament}</b><br/>"
                med_text += f"Dosage: {item.dosage}<br/>"
                med_text += f"Fréquence: {item.frequence}<br/>"
                med_text += f"Durée: {item.duree}<br/>"
                if item.instructions:
                    med_text += f"Instructions: {item.instructions}"
                
                story.append(Paragraph(med_text, styles['Normal']))
                story.append(Spacer(1, 0.5*cm))
        
        # Signature
        story.append(Spacer(1, 2*cm))
        story.append(Paragraph("Signature du médecin", styles['Normal']))
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph("_______________________", styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
