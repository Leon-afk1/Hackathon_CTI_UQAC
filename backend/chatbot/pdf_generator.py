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


def analyze_chart_with_ai(chart_data: dict, model) -> str:
    """
    Analyse un graphique avec Gemini pour générer une description intelligente.
    
    Args:
        chart_data: Dictionnaire contenant le graphique Plotly et son contexte
        model: Modèle Gemini
        
    Returns:
        str: Description narrative du graphique
    """
    try:
        # Extraire les informations du graphique
        chart = chart_data.get('chart')
        user_question = chart_data.get('question', '')
        
        # Obtenir les données du graphique
        chart_json = chart.to_json() if chart else '{}'
        
        prompt = f"""Tu es un analyste de données qui décrit des visualisations de manière professionnelle.

QUESTION DE L'UTILISATEUR:
{user_question}

DONNÉES DU GRAPHIQUE:
{chart_json[:1000]}  (aperçu)

Ta mission: Rédige une description narrative de ce graphique (2-3 phrases).

STRUCTURE:
1. Ce que montre le graphique (type, axes, données)
2. Les tendances ou patterns principaux observés
3. L'insight clé à retenir

Exemple: "Ce graphique en barres présente la répartition des événements par niveau de criticité sur le dernier trimestre. On observe une prédominance des incidents de niveau 3 (45%), suivis des niveaux 2 (30%) et 1 (25%). Cette distribution suggère une gestion efficace des cas critiques, avec une majorité d'incidents de criticité modérée."

MAINTENANT, décris le graphique de manière professionnelle et concise:"""
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "Ce graphique illustre les données relatives à la question posée, permettant une analyse visuelle des tendances observées."


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
    # Séparer les échanges avec et sans graphiques
    exchanges_with_charts = []
    exchanges_without_charts = []
    
    for i, msg in enumerate(messages):
        if msg.get('role') == 'user':
            user_msg = msg.get('content', '')
            # Chercher la réponse assistant correspondante
            assistant_msg = messages[i + 1] if i + 1 < len(messages) else {}
            
            if assistant_msg.get('chart'):
                exchanges_with_charts.append({
                    'question': user_msg,
                    'answer': assistant_msg.get('content', '')[:300],
                    'has_chart': True
                })
            else:
                exchanges_without_charts.append({
                    'question': user_msg,
                    'answer': assistant_msg.get('content', '')[:300],
                    'has_chart': False
                })
    
    # Construire le contexte pour l'IA
    conversation_text = ""
    
    if exchanges_with_charts:
        conversation_text += "ÉCHANGES AVEC VISUALISATIONS:\n"
        for exc in exchanges_with_charts:
            conversation_text += f"Q: {exc['question'][:200]}\nR: {exc['answer']}\n\n"
    
    if exchanges_without_charts:
        conversation_text += "\nÉCHANGES TEXTUELS:\n"
        for exc in exchanges_without_charts:
            conversation_text += f"Q: {exc['question'][:200]}\nR: {exc['answer']}\n\n"
    
    analysis_prompt = f"""Tu es un analyste senior qui rédige un rapport de synthèse professionnel.

CONVERSATION ANALYSÉE:
{conversation_text}

IMPORTANT: 
- {len(exchanges_with_charts)} échange(s) ont généré des visualisations graphiques
- {len(exchanges_without_charts)} échange(s) sont purement textuels
- Intègre TOUS les échanges dans ton analyse de manière fluide

Ta mission: Créer un rapport narratif et fluide, COMME UN HUMAIN L'ÉCRIRAIT.

GÉNÈRE 4 SECTIONS (sépare-les par "---SECTION---"):

1. **INTRODUCTION** (2-3 phrases)
   - Contexte de l'analyse
   - Mentionne les thématiques explorées (avec ET sans graphiques)
   - Objectifs de la consultation
   - Ton: Professionnel mais naturel

2. **ANALYSE THÉMATIQUE** (2-3 paragraphes)
   - Regroupe TOUS les sujets abordés par thèmes (graphiques + textuels)
   - Identifie les préoccupations principales
   - Pour les questions avec graphiques: mentionne qu'une visualisation sera présentée
   - Pour les questions sans graphiques: synthétise les échanges et leur apport au contexte
   - Mentionne les données clés sans format "Question/Réponse"
   - Ton: Analytique et synthétique

3. **OBSERVATIONS ET INSIGHTS** (2-3 paragraphes)
   - Points saillants découverts dans TOUTE la conversation
   - Tendances observées (visuelles et textuelles)
   - Corrélations ou patterns identifiés
   - Intègre les insights des échanges textuels au contexte général
   - Ton: Objectif et factuel

4. **RECOMMANDATIONS STRATÉGIQUES** (3-5 points numérotés)
   - Actions concrètes et priorisées
   - Basées sur TOUTES les données discutées (graphiques + textuelles)
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
    # Extraire les graphiques avec leur contexte
    chart_data_list = []
    for i, msg in enumerate(messages):
        if 'chart' in msg and msg.get('chart'):
            # Trouver la question utilisateur correspondante
            user_question = ""
            if i > 0 and messages[i-1].get('role') == 'user':
                user_question = messages[i-1].get('content', '')
            
            chart_data_list.append({
                'chart': msg['chart'],
                'question': user_question,
                'index': len(chart_data_list) + 1
            })
    
    if chart_data_list:
        story.append(Paragraph("📈 VISUALISATIONS DES DONNÉES", heading_style))
        story.append(Paragraph("Les graphiques ci-dessous illustrent les principales tendances identifiées lors de l'analyse. Chaque visualisation est accompagnée d'une description détaillée pour en faciliter la compréhension.", body_style))
        story.append(Spacer(1, 0.3 * inch))
        
        with st.spinner(f"🎨 Analyse intelligente de {len(chart_data_list)} graphique(s)..."):
            for chart_data in chart_data_list:
                idx = chart_data['index']
                chart = chart_data['chart']
                
                try:
                    # Exporter le graphique Plotly en image
                    img_bytes = chart.to_image(format="png", width=600, height=400)
                    img_buffer = BytesIO(img_bytes)
                    
                    # Analyser le graphique avec l'IA
                    chart_description = analyze_chart_with_ai(chart_data, model)
                    
                    # Titre du graphique
                    story.append(Paragraph(f"<b>Figure {idx} - Visualisation des données</b>", subheading_style))
                    
                    # Image du graphique
                    img = Image(img_buffer, width=5.5*inch, height=3.7*inch)
                    story.append(img)
                    story.append(Spacer(1, 0.15 * inch))
                    
                    # Description IA
                    description_style = ParagraphStyle(
                        'ChartDescription',
                        parent=styles['BodyText'],
                        fontSize=9,
                        textColor=colors.HexColor('#374151'),
                        spaceAfter=10,
                        leftIndent=15,
                        rightIndent=15,
                        alignment=TA_JUSTIFY,
                        fontName='Helvetica',
                        backColor=colors.HexColor('#f3f4f6'),
                        borderPadding=10
                    )
                    
                    story.append(Paragraph(f"<i>Analyse: {chart_description.replace('<', '&lt;').replace('>', '&gt;')}</i>", 
                                         description_style))
                    story.append(Spacer(1, 0.3 * inch))
                    
                except Exception as e:
                    story.append(Paragraph(f"<i>[Graphique {idx} non disponible: {str(e)[:100]}]</i>", body_style))
                    story.append(Spacer(1, 0.2 * inch))
        
        story.append(Spacer(1, 0.2 * inch))
    else:
        # Si aucun graphique, mentionner que l'analyse est basée sur les échanges textuels
        story.append(Paragraph("💬 SYNTHÈSE DES ÉCHANGES", heading_style))
        story.append(Paragraph("L'analyse présentée dans ce rapport est basée sur les échanges textuels de la consultation. Les sections suivantes synthétisent les thématiques abordées et les insights dégagés.", body_style))
        story.append(Spacer(1, 0.3 * inch))
    
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
