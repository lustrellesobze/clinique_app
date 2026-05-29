"""
Service de génération de PDF pour factures, ordonnances, rapports
"""
from datetime import datetime
from io import BytesIO
from typing import Optional

import qrcode
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
from app.models.payment import Paiement
from app.models.prescription import Prescription

MODE_PAIEMENT_LABELS: dict[str, str] = {
    "especes": "Espèces (Cash)",
    "mtn_momo": "MTN MoMo",
    "orange_money": "Orange Money",
    "carte": "Carte bancaire",
    "assurance": "Assurance",
}


def _payment_mode_key(p: Paiement) -> str:
    if hasattr(p.mode_paiement, "value"):
        return str(p.mode_paiement.value)
    return str(p.mode_paiement)


def _build_qr_image(payload: str, size_cm: float = 3.5):
    img = qrcode.make(payload)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Image(buf, width=size_cm * cm, height=size_cm * cm)


def _qr_payload_for_payment(p: Paiement, numero_facture: str) -> str:
    mode = _payment_mode_key(p)
    return (
        f"CLINIQUE|facture={numero_facture}|montant={float(p.montant):.0f}|"
        f"provider={mode}|ref={p.reference_transaction or ''}"
    )


def _is_paiement_confirme(p: Paiement) -> bool:
    st = p.statut.value if hasattr(p.statut, "value") else str(p.statut)
    return st == "confirme"


def _summarize_payments(paiements: list[Paiement]) -> dict:
    """Récapitulatif espèces / mobile pour affichage facture."""
    especes = 0.0
    orange = 0.0
    mtn = 0.0
    autres = 0.0
    for p in paiements:
        mode = _payment_mode_key(p)
        amt = float(p.montant or 0)
        if mode == "especes":
            especes += amt
        elif mode == "orange_money":
            orange += amt
        elif mode == "mtn_momo":
            mtn += amt
        else:
            autres += amt
    modes: list[str] = []
    if especes > 0:
        modes.append(f"Espèces (Cash): {especes:,.0f} FCFA")
    if orange > 0:
        modes.append(f"Orange Money: {orange:,.0f} FCFA")
    if mtn > 0:
        modes.append(f"MTN MoMo: {mtn:,.0f} FCFA")
    if autres > 0:
        modes.append(f"Autres: {autres:,.0f} FCFA")
    is_mixte = sum(1 for x in (especes, orange, mtn) if x > 0) > 1
    label = "Paiement mixte" if is_mixte else (modes[0].split(":")[0] if modes else "—")
    return {
        "especes": especes,
        "orange": orange,
        "mtn": mtn,
        "is_mixte": is_mixte,
        "label": label,
        "lines": modes,
    }


def _statut_facture_label(statut: object) -> str:
    if hasattr(statut, "value"):
        return str(statut.value).replace("_", " ").upper()
    return str(statut).replace("_", " ").upper()


class PDFService:
    """Service pour générer des documents PDF"""
    
    @staticmethod
    def generate_invoice_pdf(
        facture: Facture,
        patient: Patient,
        insurance: Optional[Insurance] = None,
        *,
        consultation_info: Optional[dict] = None,
        paiements: Optional[list[Paiement]] = None,
        caissier_nom: Optional[str] = None,
    ) -> BytesIO:
        """
        Génère un PDF de facture (consultation, labo, etc.).
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
        story.append(Paragraph("CLINIQUE ESPOIR", title_style))
        story.append(Paragraph("Facture", styles['Heading2']))
        story.append(Spacer(1, 0.5*cm))
        
        ci = consultation_info or {}
        service_label = ci.get("type_consultation_label") or "Consultation"
        heure = (
            facture.created_at.strftime("%Hh%M") if facture.created_at else "—"
        )
        date_str = (
            facture.created_at.strftime("%d/%m/%Y") if facture.created_at else "—"
        )

        story.append(
            Paragraph(
                "BP 1234, Douala — Cameroun · +237 6XX XX XX XX",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.35 * cm))

        left_lines = [
            f"<b>FACTURE N° {facture.numero_facture}</b>",
            f"Date : {date_str}",
            f"Heure : {heure}",
            f"Caissier : {caissier_nom or '—'}",
            f"Service : {service_label}",
        ]
        if ci.get("medecin_nom"):
            left_lines.append(f"Médecin : {ci['medecin_nom']}")
        if ci.get("batiment"):
            left_lines.append(f"Lieu : {ci['batiment']}")

        assur_note = patient.assureur or "Non assuré"
        if not patient.assureur:
            assur_note += " (non applicable pour cette facture)"
        right_lines = [
            f"Nom : <b>{patient.nom}</b>",
            f"Prénom : <b>{patient.prenom}</b>",
            f"ID : <b>{patient.code_patient}</b>",
            f"Contact : {patient.telephone or 'N/A'}",
            f"Assurance : {assur_note}",
        ]

        two_col = Table(
            [
                [Paragraph("<br/>".join(left_lines), styles["Normal"]), Paragraph("<br/>".join(right_lines), styles["Normal"])],
            ],
            colWidths=[8.5 * cm, 8.5 * cm],
        )
        two_col.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(two_col)
        story.append(Spacer(1, 0.5 * cm))
        
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
        
        sous_total = float(facture.montant_total or 0) + float(facture.remise_globale or 0)
        totaux_data = [
            ['SOUS-TOTAL:', f"{sous_total:,.0f} FCFA"],
            ['Remise fidélité:', f"{float(facture.remise_globale or 0):,.0f} FCFA"],
            ['TOTAL À PAYER:', f"{float(facture.montant_total or 0):,.0f} FCFA"],
        ]
        
        if facture.remise_globale and facture.remise_globale > 0:
            pass
        
        if facture.part_assurance and facture.part_assurance > 0:
            totaux_data.append(['Part assurance:', f"{facture.part_assurance:,.0f} FCFA"])
            totaux_data.append(['Part patient:', f"{facture.part_patient:,.0f} FCFA"])
        
        totaux_data.append(['Montant réglé:', f"{facture.montant_regle:,.0f} FCFA"])
        reste = float(facture.montant_total or 0) - float(facture.montant_regle or 0)
        if reste > 0:
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

        if facture.commentaire:
            story.append(Spacer(1, 0.4 * cm))
            story.append(Paragraph("Commentaire", styles['Heading3']))
            story.append(Paragraph(str(facture.commentaire), styles['Normal']))

        paiements = paiements or []
        confirmed = [p for p in paiements if _is_paiement_confirme(p)]

        if confirmed:
            recap = _summarize_payments(confirmed)
            story.append(Spacer(1, 0.6 * cm))
            story.append(Paragraph("Mode de paiement", styles['Heading3']))
            recap_rows = [["Récapitulatif", recap["label"]]]
            for line in recap["lines"]:
                recap_rows.append(["", line])
            recap_table = Table(recap_rows, colWidths=[5 * cm, 10 * cm])
            recap_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
            ]))
            story.append(recap_table)
            story.append(Spacer(1, 0.4 * cm))

            story.append(Paragraph("Détail des paiements", styles['Heading3']))
            pay_data = [['Date', 'Mode', 'Montant', 'Référence', 'Statut']]
            mobile_for_qr: list[Paiement] = []
            for p in confirmed:
                mode_key = _payment_mode_key(p)
                statut_key = (
                    p.statut.value if hasattr(p.statut, "value") else str(p.statut)
                )
                pay_data.append([
                    p.created_at.strftime('%d/%m/%Y %H:%M') if p.created_at else '-',
                    MODE_PAIEMENT_LABELS.get(mode_key, mode_key),
                    f"{float(p.montant):,.0f} FCFA",
                    p.reference_transaction or '—',
                    statut_key.replace('_', ' ').upper(),
                ])
                if mode_key in ("orange_money", "mtn_momo"):
                    mobile_for_qr.append(p)
            pay_table = Table(
                pay_data, colWidths=[3.2 * cm, 3.5 * cm, 3 * cm, 4 * cm, 2.3 * cm]
            )
            pay_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ]))
            story.append(pay_table)

            if mobile_for_qr:
                for p in mobile_for_qr:
                    mode_key = _payment_mode_key(p)
                    story.append(
                        Paragraph(
                            f"QR {MODE_PAIEMENT_LABELS.get(mode_key, mode_key)} — "
                            f"Réf. {p.reference_transaction or '—'}",
                            styles['Normal'],
                        )
                    )
                    story.append(
                        _build_qr_image(
                            _qr_payload_for_payment(p, facture.numero_facture)
                        )
                    )
                    story.append(Spacer(1, 0.25 * cm))

        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("Scan pour historique patient", styles['Normal']))
        story.append(
            _build_qr_image(f"PATIENT|{patient.code_patient}", size_cm=3.2)
        )
        story.append(Spacer(1, 0.3 * cm))
        story.append(
            Paragraph(
                "<para align=center>Merci de votre visite !<br/>Conservez cette facture</para>",
                styles['Normal'],
            )
        )
        
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
