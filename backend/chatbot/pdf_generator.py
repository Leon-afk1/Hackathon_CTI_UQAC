"""
Module de génération de rapports PDF professionnels et narratifs.

Ce module contient toutes les fonctions nécessaires pour :
- Détecter les demandes de génération de PDF
- Analyser la conversation avec Gemini
- Générer un rapport PDF narratif professionnel
"""

import streamlit as st
import re
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY


def detect_pdf_request(prompt: str) -> bool:
    """
    Détecte si l'utilisateur demande un PDF de la conversation.
    
    Args:
        prompt: Message de l'utilisateur
        
    Returns:
        bool: True si une demande de PDF est détectée
    """
    pdf_keywords = [
        r'\bpdf\b',
        r'\brapport\b',
        r'\bdocument\b',
        r'\bexport\w*\b',
        r'\bt[ée]l[ée]charg\w*\b',
        r'\bg[ée]n[ée]r\w*\s+(un\s+)?rapport\b',
        r'\bcr[ée]\w*\s+(un\s+)?pdf\b',
        r'\bfaire\s+un\s+rapport\b',
        r'\bsauvegarder\b',
        r'\benregistrer\b'
    ]
    
    prompt_lower = prompt.lower()
    return any(re.search(pattern, prompt_lower, re.IGNORECASE) for pattern in pdf_keywords)


def analyze_conversation_for_synthesis(messages: list, model) -> dict:
    """
    Utilise Gemini pour créer une synthèse narrative de la conversation.
    
    Args:
        messages: Liste des messages de la conversation
        model: Modèle Gemini pour l'analyse
        
    Returns:
        dict: Dictionnaire avec 4 sections (introduction, analyse_thematique, insights, recommandations)
    """
    # Préparer le contexte de la conversation
    conversation_text = "\n\n".join([
        f"{'Utilisateur' if msg['role'] == 'user' else 'Assistant'}: {msg.get('content', '')[:500]}"
        for msg in messages if msg.get('content')
    ])
    
    analysis_prompt = f"""Tu es un analyste senior qui rédige un rapport de synthèse professionnel.

CONVERSATION ANALYSÉE:
{conversation_text}

Ta mission: Créer un rapport narratif et fluide, COMME UN HUMAIN L'ÉCRIRAIT.

GÉNÈRE 4 SECTIONS (sépare-les par "---SECTION---"):

1. **INTRODUCTION** (2-3 phrases)
   - Contexte de l'analyse
   - Période/scope concerné
   - Objectifs de la consultation
   - Ton: Professionnel mais naturel

2. **ANALYSE THÉMATIQUE** (1-2 paragraphes)
   - Regroupe les sujets abordés par thèmes
   - Identifie les préoccupations principales
   - Mentionne les données clés sans format "Question/Réponse"
   - Ton: Analytique et synthétique

3. **OBSERVATIONS ET INSIGHTS** (1-2 paragraphes)
   - Points saillants découverts
   - Tendances observées
   - Corrélations ou patterns identifiés
   - Ton: Objectif et factuel

4. **RECOMMANDATIONS STRATÉGIQUES** (3-5 points numérotés)
   - Actions concrètes et priorisées
   - Basées sur les données réelles discutées
   - Chiffrées quand possible
   - Ton: Directif et actionnable

EXEMPLE DE STRUCTURE:

L'analyse des données de gestion des événements révèle plusieurs axes d'attention prioritaires. L'utilisateur a consulté les informations relatives aux incidents critiques du dernier trimestre, ainsi que les mesures correctives associées.

---SECTION---

L'examen des événements montre une concentration des incidents de niveau 3, représentant 45% des cas traités. Les domaines principaux concernés incluent la sécurité opérationnelle et la gestion des équipements. Une attention particulière a été portée aux délais de résolution, avec une moyenne constatée de 72 heures pour les incidents critiques.

---SECTION---

Trois observations majeures émergent de cette analyse. Premièrement, une hausse de 28% des incidents est constatée sur les trois derniers mois. Deuxièmement, 60% des mesures correctives restent au statut "en cours" au-delà du délai prévu. Troisièmement, les événements récurrents sur les mêmes équipements suggèrent une maintenance insuffisante.

---SECTION---

1. **Renforcer la surveillance proactive**: Mettre en place un système d'alerte automatique pour les équipements présentant plus de 2 incidents par mois.
2. **Accélérer la résolution des mesures correctives**: Assigner des responsables clairs pour les 15 actions en attente depuis plus de 30 jours.
3. **Planifier une maintenance préventive renforcée**: Cibler prioritairement les 5 équipements ayant généré 40% des incidents du trimestre.

MAINTENANT, GÉNÈRE TON RAPPORT BASÉ SUR LA CONVERSATION RÉELLE:"""
    
    try:
        response = model.generate_content(analysis_prompt)
        content = response.text.strip()
        
        # Séparer les sections
        sections = content.split("---SECTION---")
        
        if len(sections) >= 4:
            return {
                'introduction': sections[0].strip(),
                'analyse_thematique': sections[1].strip(),
                'insights': sections[2].strip(),
                'recommandations': sections[3].strip()
            }
        else:
            # Fallback si le format n'est pas respecté
            return {
                'introduction': content[:500] if len(content) > 500 else content,
                'analyse_thematique': content[500:1000] if len(content) > 1000 else content[500:],
                'insights': "L'analyse des données révèle plusieurs points d'attention nécessitant un suivi approfondi.",
                'recommandations': "1. **Poursuivre la surveillance**: Continuer à monitorer les indicateurs clés.\n2. **Optimiser les processus**: Identifier les axes d'amélioration prioritaires."
            }
    except Exception as e:
        return {
            'introduction': "Cette analyse porte sur la consultation des données de gestion d'événements et de risques effectuée via l'assistant IA.",
            'analyse_thematique': "Les thématiques principales abordées concernent l'identification des incidents critiques, l'évaluation des risques opérationnels et le suivi des mesures correctives.",
            'insights': "Les données consultées mettent en évidence plusieurs axes d'amélioration dans la gestion proactive des risques et la rapidité de mise en œuvre des actions correctives.",
            'recommandations': "1. **Renforcer la surveillance**: Mettre en place des indicateurs de suivi régulier.\n2. **Améliorer la réactivité**: Réduire les délais de traitement des incidents critiques.\n3. **Optimiser la documentation**: Assurer une traçabilité complète de toutes les actions."
        }


def generate_professional_pdf(messages: list, model) -> BytesIO:
    """
    Génère un rapport PDF professionnel et narratif de la conversation.
    
    Args:
        messages: Liste des messages de la conversation
        model: Modèle Gemini pour l'analyse
        
    Returns:
        BytesIO: Buffer contenant le PDF généré
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Styles personnalisés
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=8,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        spaceAfter=10,
        alignment=TA_JUSTIFY,
        fontName='Helvetica'
    )
    
    recommendation_style = ParagraphStyle(
        'Recommendation',
        parent=styles['BodyText'],
        fontSize=10,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=10,
        leftIndent=20,
        fontName='Helvetica'
    )
    
    # Contenu du PDF
    story = []
    
    # En-tête avec ligne décorative
    story.append(Paragraph("🛡️ RAPPORT D'ANALYSE", title_style))
    story.append(Paragraph("Gestion d'Événements & Risques", subheading_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Informations du rapport
    current_date = datetime.now().strftime("%d/%m/%Y à %H:%M")
    info_data = [
        ['Date du rapport:', current_date],
        ['Nombre de messages:', str(len(messages))],
        ['Générateur:', 'Assistant IA Gemini'],
        ['Type:', 'Rapport de synthèse narratif']
    ]
    
    info_table = Table(info_data, colWidths=[2.5*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e0e7ff')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e3a8a')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 0.4 * inch))
    
    # Générer la synthèse narrative avec l'IA
    with st.spinner("📝 Génération de la synthèse narrative..."):
        synthesis = analyze_conversation_for_synthesis(messages, model)
    
    # Section 1: INTRODUCTION / CONTEXTE
    story.append(Paragraph("📊 CONTEXTE DE L'ANALYSE", heading_style))
    intro_text = synthesis.get('introduction', 'Introduction non disponible')
    story.append(Paragraph(intro_text.replace('<', '&lt;').replace('>', '&gt;'), body_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Section 2: ANALYSE THÉMATIQUE
    story.append(Paragraph("🔍 ANALYSE THÉMATIQUE", heading_style))
    analyse_text = synthesis.get('analyse_thematique', 'Analyse non disponible')
    story.append(Paragraph(analyse_text.replace('<', '&lt;').replace('>', '&gt;'), body_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Section 3: VISUALISATIONS ET DONNÉES CLÉS
    # Extraire les graphiques de la conversation
    charts = [msg.get('chart') for msg in messages if 'chart' in msg]
    
    if charts:
        story.append(Paragraph("📈 VISUALISATIONS DES DONNÉES", heading_style))
        story.append(Paragraph("Les graphiques ci-dessous illustrent les principales tendances identifiées lors de l'analyse:", body_style))
        story.append(Spacer(1, 0.2 * inch))
        
        for idx, chart in enumerate(charts, 1):
            try:
                # Exporter le graphique Plotly en image
                img_bytes = chart.to_image(format="png", width=600, height=400)
                img_buffer = BytesIO(img_bytes)
                
                story.append(Paragraph(f"<b>Figure {idx}</b>", subheading_style))
                img = Image(img_buffer, width=5.5*inch, height=3.7*inch)
                story.append(img)
                story.append(Spacer(1, 0.25 * inch))
            except Exception as e:
                story.append(Paragraph(f"<i>[Graphique {idx} non disponible]</i>", body_style))
                story.append(Spacer(1, 0.1 * inch))
        
        story.append(Spacer(1, 0.2 * inch))
    
    # Section 4: OBSERVATIONS ET INSIGHTS
    story.append(Paragraph("💡 OBSERVATIONS ET INSIGHTS", heading_style))
    insights_text = synthesis.get('insights', 'Insights non disponibles')
    story.append(Paragraph(insights_text.replace('<', '&lt;').replace('>', '&gt;'), body_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Page break avant recommandations
    story.append(PageBreak())
    
    # Section 5: RECOMMANDATIONS STRATÉGIQUES
    story.append(Paragraph("🎯 RECOMMANDATIONS STRATÉGIQUES", heading_style))
    story.append(Spacer(1, 0.15 * inch))
    
    story.append(Paragraph("""Sur la base de l'analyse effectuée, voici les axes d'action prioritaires 
    pour optimiser la gestion des événements et renforcer la maîtrise des risques:""", body_style))
    story.append(Spacer(1, 0.2 * inch))
    
    # Ajouter les recommandations
    recommendations_text = synthesis.get('recommandations', 'Recommandations non disponibles')
    story.append(Paragraph(recommendations_text.replace('<', '&lt;').replace('>', '&gt;'), recommendation_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Footer / Conclusion
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("📝 CONCLUSION", heading_style))
    conclusion_text = """Ce rapport synthétise l'analyse effectuée et fournit des recommandations actionnables 
    pour optimiser la gestion des événements et des risques au sein de votre organisation. 
    Il est recommandé de mettre en œuvre ces suggestions de manière progressive et de mesurer leur impact."""
    story.append(Paragraph(conclusion_text, body_style))
    
    story.append(Spacer(1, 0.4 * inch))
    story.append(Paragraph(f"<i>Rapport généré automatiquement le {current_date}</i>", 
                          ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, 
                                       textColor=colors.grey, alignment=TA_CENTER)))
    
    # Construction du PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
