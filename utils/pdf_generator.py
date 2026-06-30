import io
import datetime
from PIL import Image as PILImage
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_meal_pdf(image_pil, annotated_image_pil, items, totals, targets, dietitian_feedback, profile_name, meal_name) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#4f46e5'), # Indigo
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=12
    )
    
    section_heading = ParagraphStyle(
        'SecHeading',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1e1b4b'), # Dark indigo
        spaceBefore=8,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#374151')
    )
    
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    # Document Header
    story.append(Paragraph("🍽️ Food Nutrition Report", title_style))
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")
    story.append(Paragraph(f"Generated on {now_str} | Profile: <b>{profile_name}</b>", subtitle_style))
    
    # Meal details metadata
    meta_data = [
        [Paragraph(f"<b>Meal Name:</b> {meal_name}", body_style), Paragraph(f"<b>Total Calories:</b> {totals.get('calories', 0):.0f} kcal", body_style)],
        [Paragraph(f"<b>Protein:</b> {totals.get('protein_g', 0.0):.1f}g | <b>Carbs:</b> {totals.get('carbs_g', 0.0):.1f}g | <b>Fat:</b> {totals.get('fat_g', 0.0):.1f}g", body_style), 
         Paragraph(f"<b>Daily Calorie Goal:</b> {targets.get('calories', 2000.0):.0f} kcal", body_style)]
    ]
    meta_table = Table(meta_data, colWidths=[250, 250])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f9fafb')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e5e7eb')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))
    
    # Detections table and image
    img_flow = None
    if annotated_image_pil:
        img_byte_arr = io.BytesIO()
        # Convert image to RGB if it's RGBA
        annotated_image_pil.convert('RGB').save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        
        # Calculate aspect ratio
        orig_w, orig_h = annotated_image_pil.size
        target_w = 210
        target_h = int((orig_h / orig_w) * target_w)
        # Limit height to avoid page overflow
        if target_h > 210:
            target_h = 210
            target_w = int((orig_w / orig_h) * target_h)
            
        img_flow = RLImage(img_byte_arr, width=target_w, height=target_h)
    
    # Build food item table
    table_data = [["Food Item", "Portion", "Calories", "Protein", "Carbs", "Fat"]]
    for item in items:
        # Get nutrition values
        nutr = item.get('nutrition', {}) if isinstance(item.get('nutrition'), dict) else item
        label = item.get('label', 'Unknown')
        portion = float(item.get('portion', 1.0))
        
        cal = float(nutr.get('calories') or 0.0) * portion
        prot = float(nutr.get('protein_g') or nutr.get('protein') or 0.0) * portion
        fat = float(nutr.get('fat_g') or nutr.get('fat') or 0.0) * portion
        carbs = float(nutr.get('carbs_g') or nutr.get('carbs') or 0.0) * portion
        
        table_data.append([
            Paragraph(f"<b>{label}</b>", body_style),
            f"{portion:.1f}x",
            f"{cal:.0f} kcal",
            f"{prot:.1f}g",
            f"{carbs:.1f}g",
            f"{fat:.1f}g"
        ])
    
    # Append total row
    table_data.append([
        Paragraph("<b>Total Intake</b>", body_style),
        "-",
        f"<b>{totals.get('calories', 0):.0f} kcal</b>",
        f"<b>{totals.get('protein_g', 0.0):.1f}g</b>",
        f"<b>{totals.get('carbs_g', 0.0):.1f}g</b>",
        f"<b>{totals.get('fat_g', 0.0):.1f}g</b>"
    ])
    
    # Adjust table colWidths to fit page width
    item_table = Table(table_data, colWidths=[100, 45, 55, 45, 45, 45])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f9fafb')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e0e7ff')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    # Render layout: side-by-side or sequential
    if img_flow:
        layout_table_data = [[item_table, img_flow]]
        layout_table = Table(layout_table_data, colWidths=[290, 220])
        layout_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (1,0), (1,0), 10),
            ('RIGHTPADDING', (0,0), (0,0), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(layout_table)
    else:
        story.append(item_table)
        
    story.append(Spacer(1, 15))
    
    # AI Dietitian Coaching Report
    coaching_story = []
    coaching_story.append(Paragraph("💡 AI Dietitian Coaching Feedback", section_heading))
    
    rating = dietitian_feedback.get('balance_rating', 'Well-balanced')
    coaching_story.append(Paragraph(f"<b>Meal Balance Rating:</b> <font color='#7c3aed'><b>{rating}</b></font>", body_style))
    coaching_story.append(Spacer(1, 6))
    
    coaching_story.append(Paragraph("<b>Dietary Insights:</b>", body_style))
    for insight in dietitian_feedback.get('insights', []):
        coaching_story.append(Paragraph(f"• {insight}", bullet_style))
    coaching_story.append(Spacer(1, 6))
    
    coaching_story.append(Paragraph("<b>Dietary Recommendations:</b>", body_style))
    for rec in dietitian_feedback.get('recommendations', []):
        coaching_story.append(Paragraph(f"• {rec}", bullet_style))
        
    # Put AI feedback in a clean bordered container
    coaching_container = Table([[coaching_story]], colWidths=[510])
    coaching_container.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f5f3ff')), # Purple background tint
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#ddd6fe')),
        ('PADDING', (0,0), (-1,-1), 12),
    ]))
    
    story.append(KeepTogether(coaching_container))
    
    # Build Document
    doc.build(story)
    buffer.seek(0)
    return buffer
