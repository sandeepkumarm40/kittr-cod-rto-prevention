import os
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)

def create_memo_pdf(output_path="docs/business_memo.pdf"):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=10
    )
    
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=14,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor('#2563EB'),
        spaceBefore=8,
        spaceAfter=3
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=4
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2
    )

    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#475569')
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=body_style,
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#1E3A8A'),
        backColor=colors.HexColor('#EFF6FF'),
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=6
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("EXECUTIVE BUSINESS MEMORANDUM", title_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=10))

    meta_table_data = [
        [Paragraph("<b>TO:</b> Founder & CEO, Kittr", meta_style), Paragraph("<b>DATE:</b> October 30, 2026", meta_style)],
        [Paragraph("<b>FROM:</b> Associate Software Engineer", meta_style), Paragraph("<b>SUBJECT:</b> COD RTO Prevention Decision Engine", meta_style)]
    ]
    meta_table = Table(meta_table_data, colWidths=[260, 260])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(meta_table)
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceBefore=8, spaceAfter=8))

    # Section 1: Findings
    story.append(Paragraph("1. WHAT WE FOUND IN THE DATA (SURPRISING FINDINGS)", h1_style))
    story.append(Paragraph("An analysis of <b>2,018 historical COD orders</b> revealed stark structural drivers behind Kittr's 28.4% baseline RTO rate (573 returns, direct loss ₹169.40/order):", body_style))

    story.append(Paragraph("<b>Finding 1: Placeholder Addresses Account for 7.7% of Orders — 63.5% Return Rate</b>", h2_style))
    story.append(Paragraph("156 orders contained placeholder addresses ('xyz', '.', 'call me', 'near station'). These delivered at only 36.5% vs. 74.5% for complete addresses. 16 orders were explicitly named 'Test Order' with an 81.2% RTO rate. These are zero-intent or test orders that burn money at courier dispatch.", body_style))

    story.append(Paragraph("<b>Finding 2: 2+ Prior RTOs Predict a 76.5% Return Rate (Strongest Single Signal)</b>", h2_style))
    prior_rto_data = [
        ["Prior Customer RTOs", "Historical Orders", "RTO Rate", "Business Assessment"],
        ["0 Prior RTOs", "1,873", "27.2%", "Baseline risk; trust first-time buyers"],
        ["1 Prior RTO", "111", "34.2%", "Elevated risk; requires WhatsApp verification"],
        ["2+ Prior RTOs", "34", "76.5%", "High-confidence repeat refusal; auto-hold candidate"]
    ]
    t1 = Table(prior_rto_data, colWidths=[110, 85, 75, 250])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t1)

    story.append(Paragraph("<b>Finding 3: Severe Geographic Polarization (Tier 2/3 Cities at 50–63% RTO)</b>", h2_style))
    story.append(Paragraph("Metros experience manageable RTOs (Mumbai 17.8%, Pune 18.1%, Delhi 21.5%), whereas Tier 2/3 clusters suffer massive delivery failures: <b>Gorakhpur (63.0%), Darbhanga (58.1%), Sagar (50.9%), and Patna (47.5%)</b>. Rather than blanket-banning these cities, localized risk weighting and prepaid nudges unlock them safely.", body_style))

    story.append(Paragraph("<b>Finding 4: Acquisition Channel Risk (Meta Ads 31.3% vs Direct 22.7%)</b>", h2_style))
    story.append(Paragraph("Meta Ads represents 780 orders (38.7% of volume) but has an 8.6% higher RTO rate than organic direct traffic. While critical for scaling, Meta traffic carries lower initial brand commitment and requires automated WhatsApp validation.", body_style))

    story.append(Paragraph("<b>Finding 5: High-Value First Orders (₹2,000+) RTO at 40.4%</b>", h2_style))
    story.append(Paragraph("Orders >3× the ₹649 AOV have a 40.4% RTO rate on first-time buyers due to buyer remorse upon doorstep delivery. These represent ideal candidates for prepaid discount conversion.", body_style))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceBefore=8, spaceAfter=8))

    # Section 2: Engine & Backtest
    story.append(Paragraph("2. RECOMMENDED SYSTEM & HISTORICAL BACKTEST PERFORMANCE", h1_style))
    story.append(Paragraph("We deployed a transparent 0–100 risk scoring engine that buckets each COD order into one of 4 auditable actions before shipping:", body_style))

    dec_data = [
        ["Bucket", "Score Range", "Backtest Orders", "Share", "Operational Action Taken"],
        ["✅ Ship as-is", "< 25", "1,584", "78.5%", "Dispatched immediately without friction"],
        ["🟡 Confirm WhatsApp", "25 – 34", "249", "12.3%", "Sent 1-click Hinglish confirmation; ship if YES"],
        ["🔵 Nudge Prepaid", "35 – 49", "147", "7.3%", "Offered 5% discount to switch to UPI/Card"],
        ["🔴 Hold / Cancel", "≥ 50 or Hard Flag", "38", "1.9%", "Flagged for ops review; blocked from auto-ship"]
    ]
    t2 = Table(dec_data, colWidths=[110, 75, 75, 55, 205])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t2)

    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Backtest Results:</b> Out of 38 held orders, <b>30 were actual RTOs (78.9% precision)</b> and only 8 were false holds. Avoided RTO costs and converted nudges totaled <b>₹8,394</b>, against ₹6,789 in margin/discount costs, delivering a <b>+₹1,605 net financial gain</b> on this sample batch (~₹15,000–₹25,000/month scaled to 3,000 orders).", body_style))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceBefore=8, spaceAfter=8))

    # Section 3: Ops vs Marketing
    story.append(Paragraph("3. OPERATIONS VS. MARKETING: RESOLVING THE ₹ TRADE-OFF", h1_style))
    story.append(Paragraph("<b>The Unit Economics Asymmetry:</b>", body_style))
    story.append(Paragraph("• <b>Cost of an RTO:</b> ₹65 forward + ₹65 return + ₹25 handling + 8% damage on ₹180 product = <b>₹169.40 per RTO</b>.", bullet_style))
    story.append(Paragraph("• <b>Cost of cancelling a genuine first-time buyer:</b> ₹402.38 (62% gross margin on ₹649 AOV) + ₹300 (wasted Meta CAC) = <b>₹702.38 total loss</b>.", bullet_style))
    story.append(Paragraph("• <b>The Breakeven Threshold:</b> ₹702.38 / (₹702.38 + ₹169.40) = <b>80.5% Precision</b>. Cancelling orders below 80.5% precision burns more cash in lost margin and marketing CAC than it saves in courier bills.", bullet_style))

    story.append(Paragraph("<b>The Resolution:</b>", body_style))
    story.append(Paragraph("1. <b>Zero blind cancellation of first-time buyers:</b> Only chronic repeat offenders (2+ prior RTOs), literal dummy names ('Test Order'), ₹0 orders, or placeholder addresses ('xyz') are held automatically.", bullet_style))
    story.append(Paragraph("2. <b>WhatsApp confirmation acts as a non-destructive filter:</b> First-time buyers in Tier-2/3 cities are asked to confirm via WhatsApp. Responsive customers get shipped; unresponsive orders are paused without damaging customer trust.", bullet_style))
    story.append(Paragraph("3. <b>Prepaid Nudge is Mathematically Profitable:</b> Expected RTO loss on a high-risk order (50% zone) is ₹84.70. A 5% prepaid discount costs ₹32.45. Converting customers yields a <b>net gain of +₹52.25 per order</b> while eliminating delivery refusal risk.", bullet_style))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceBefore=8, spaceAfter=8))

    # Section 4: Failure modes & Roadmap
    story.append(Paragraph("4. FAILURE MODES & MONITORING SAFEGUARDS", h1_style))
    story.append(Paragraph("• <b>Over-cancellation drift:</b> Track weekly % of held orders that submit support tickets. Alert if false-positive rate > 22%.", bullet_style))
    story.append(Paragraph("• <b>WhatsApp delivery drops:</b> Monitor delivery status; if response drops below 40%, trigger automated SMS fallback.", bullet_style))
    story.append(Paragraph("• <b>Pincode staleness:</b> Calculate pincode RTO rates on a rolling 60-day window rather than all-time historical data.", bullet_style))

    story.append(Paragraph("5. TWO-WEEK EXECUTION ROADMAP", h1_style))
    story.append(Paragraph("1. <b>Real-time Shopify Webhook:</b> Execute scoring synchronously upon `orders/create` rather than in batch.", bullet_style))
    story.append(Paragraph("2. <b>Courier Smart-Routing:</b> Route confirmed Tier-2 orders to Delhivery (25.9% RTO) instead of Xpressbees (31.2%).", bullet_style))
    story.append(Paragraph("3. <b>Prepaid Discount A/B Test:</b> Test 5% vs. flat ₹50 off to maximize conversion elasticity.", bullet_style))
    story.append(Paragraph("4. <b>Customer Risk Ledger:</b> Persist customer phone risk history across repeat purchases in a lightweight database.", bullet_style))

    doc.build(story)
    print(f"PDF successfully generated at: {output_path}")

if __name__ == "__main__":
    create_memo_pdf()
