"""
PDF Export Service for Budget Famille
Generates professional PDF reports for monthly budget summaries

v4.1 enhancements:
- Pie chart for category breakdown
- AI-generated monthly summary
- Comparison with previous month
- Top merchants section
"""

import io
import logging
import math
from datetime import datetime
from typing import Dict, List, Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Wedge
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF

logger = logging.getLogger(__name__)

# Color palette matching the app theme
COLORS = {
    "primary": colors.HexColor("#3B82F6"),      # Blue
    "success": colors.HexColor("#10B981"),      # Green
    "danger": colors.HexColor("#EF4444"),       # Red
    "warning": colors.HexColor("#F59E0B"),      # Orange
    "gray_dark": colors.HexColor("#374151"),
    "gray_light": colors.HexColor("#9CA3AF"),
    "background": colors.HexColor("#F3F4F6"),
}

# Chart color palette (for pie charts, etc.)
CHART_COLORS = [
    colors.HexColor("#3B82F6"),  # Blue
    colors.HexColor("#10B981"),  # Green
    colors.HexColor("#F59E0B"),  # Orange
    colors.HexColor("#EF4444"),  # Red
    colors.HexColor("#8B5CF6"),  # Purple
    colors.HexColor("#EC4899"),  # Pink
    colors.HexColor("#06B6D4"),  # Cyan
    colors.HexColor("#84CC16"),  # Lime
    colors.HexColor("#F97316"),  # Orange Dark
    colors.HexColor("#6366F1"),  # Indigo
]


def format_currency(amount: float) -> str:
    """Format amount as currency"""
    return f"{amount:,.2f} EUR".replace(",", " ").replace(".", ",")


def format_month(month_str: str) -> str:
    """Format YYYY-MM to readable month name in French"""
    months_fr = {
        "01": "Janvier", "02": "Fevrier", "03": "Mars", "04": "Avril",
        "05": "Mai", "06": "Juin", "07": "Juillet", "08": "Aout",
        "09": "Septembre", "10": "Octobre", "11": "Novembre", "12": "Decembre"
    }
    try:
        year, month = month_str.split("-")
        return f"{months_fr.get(month, month)} {year}"
    except:
        return month_str


class BudgetPDFReport:
    """Generate PDF budget reports with charts and AI insights"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _create_pie_chart(self, data: List[tuple], width: float = 200, height: float = 180) -> Drawing:
        """
        Create a pie chart drawing from data.

        Args:
            data: List of (label, value) tuples
            width: Chart width in points
            height: Chart height in points

        Returns:
            Drawing object containing the pie chart
        """
        drawing = Drawing(width, height)

        if not data or all(v == 0 for _, v in data):
            # Empty data - show placeholder
            drawing.add(String(width/2, height/2, "Pas de donnees",
                              textAnchor='middle', fontSize=10, fillColor=COLORS["gray_light"]))
            return drawing

        # Create pie chart
        pie = Pie()
        pie.x = 30
        pie.y = 20
        pie.width = int(width - 60)
        pie.height = int(height - 40)

        # Prepare data
        labels = [label[:15] + '...' if len(label) > 15 else label for label, _ in data[:8]]
        values = [max(0.1, abs(value)) for _, value in data[:8]]  # Ensure no zero values

        pie.data = values
        pie.labels = labels
        pie.slices.strokeWidth = 0.5
        pie.slices.strokeColor = colors.white

        # Assign colors
        for i in range(len(data[:8])):
            pie.slices[i].fillColor = CHART_COLORS[i % len(CHART_COLORS)]
            pie.slices[i].popout = 2 if i == 0 else 0  # Pop out largest slice

        pie.sideLabels = True
        pie.simpleLabels = True
        pie.slices.fontSize = 8
        pie.slices.labelRadius = 1.2

        drawing.add(pie)
        return drawing

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='Title_Custom',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=20,
            textColor=COLORS["gray_dark"],
            alignment=TA_CENTER
        ))

        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            spaceAfter=15,
            textColor=COLORS["gray_light"],
            alignment=TA_CENTER
        ))

        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=10,
            textColor=COLORS["primary"],
            borderPadding=5
        ))

        self.styles.add(ParagraphStyle(
            name='Amount_Positive',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=COLORS["success"],
            alignment=TA_RIGHT
        ))

        self.styles.add(ParagraphStyle(
            name='Amount_Negative',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=COLORS["danger"],
            alignment=TA_RIGHT
        ))

    def generate_monthly_report(
        self,
        month: str,
        summary: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        config: Dict[str, Any],
        tags_summary: Optional[Dict[str, Any]] = None,
        ai_summary: Optional[str] = None,
        previous_month_data: Optional[Dict[str, Any]] = None,
        top_merchants: Optional[List[Dict[str, Any]]] = None
    ) -> bytes:
        """
        Generate a complete monthly budget report PDF

        Args:
            month: Month in YYYY-MM format
            summary: Summary data from /summary endpoint
            transactions: List of transactions
            config: User configuration
            tags_summary: Optional tags breakdown
            ai_summary: Optional AI-generated summary text
            previous_month_data: Optional previous month data for comparison
            top_merchants: Optional list of top merchants

        Returns:
            PDF content as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        story = []

        # Title
        story.append(Paragraph("Budget Famille", self.styles['Title_Custom']))
        story.append(Paragraph(
            f"Rapport Mensuel - {format_month(month)}",
            self.styles['Subtitle']
        ))
        story.append(Paragraph(
            f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')}",
            self.styles['Subtitle']
        ))
        story.append(Spacer(1, 20))

        # AI Summary section (v4.1)
        if ai_summary:
            story.append(Paragraph("Resume IA", self.styles['SectionHeader']))
            story.append(Paragraph(
                ai_summary,
                ParagraphStyle(
                    name='AISummary',
                    parent=self.styles['Normal'],
                    fontSize=10,
                    textColor=COLORS["gray_dark"],
                    spaceAfter=10,
                    leftIndent=10,
                    rightIndent=10,
                    borderPadding=10,
                    backColor=colors.HexColor("#F0F9FF")  # Light blue background
                )
            ))
            story.append(Spacer(1, 15))

        # Summary section
        story.append(Paragraph("Resume Financier", self.styles['SectionHeader']))
        story.extend(self._create_summary_section(summary, config))
        story.append(Spacer(1, 15))

        # Comparison with previous month (v4.1)
        if previous_month_data:
            story.append(Paragraph("Comparaison Mois Precedent", self.styles['SectionHeader']))
            story.extend(self._create_comparison_section(summary, previous_month_data))
            story.append(Spacer(1, 15))

        # Member breakdown
        story.append(Paragraph("Repartition par Membre", self.styles['SectionHeader']))
        story.extend(self._create_member_breakdown(summary, config))
        story.append(Spacer(1, 15))

        # Tags breakdown with chart (v4.1)
        if tags_summary and tags_summary.get('tags'):
            story.append(Paragraph("Depenses par Categorie", self.styles['SectionHeader']))

            # Add pie chart
            tags = tags_summary.get('tags', {})
            sorted_tags = sorted(tags.items(), key=lambda x: x[1].get('total', 0), reverse=True)
            chart_data = [(name.capitalize(), abs(data.get('total', 0))) for name, data in sorted_tags[:8]]

            if chart_data:
                chart = self._create_pie_chart(chart_data, width=250, height=180)
                story.append(chart)
                story.append(Spacer(1, 10))

            story.extend(self._create_tags_section(tags_summary))
            story.append(Spacer(1, 15))

        # Top merchants section (v4.1)
        if top_merchants:
            story.append(Paragraph("Top 5 Marchands", self.styles['SectionHeader']))
            story.extend(self._create_merchants_section(top_merchants[:5]))
            story.append(Spacer(1, 15))

        # Top transactions
        if transactions:
            story.append(Paragraph("Principales Transactions", self.styles['SectionHeader']))
            story.extend(self._create_transactions_section(transactions[:15]))

        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph(
            "Budget Famille v4.1 - Rapport confidentiel",
            ParagraphStyle(
                name='Footer',
                parent=self.styles['Normal'],
                fontSize=9,
                textColor=COLORS["gray_light"],
                alignment=TA_CENTER
            )
        ))

        doc.build(story)
        pdf_content = buffer.getvalue()
        buffer.close()

        return pdf_content

    def _create_comparison_section(self, current: Dict, previous: Dict) -> List:
        """Create comparison table between current and previous month"""
        elements = []

        current_total = current.get('grand_total', 0)
        previous_total = previous.get('grand_total', 0)
        difference = current_total - previous_total
        diff_percent = (difference / previous_total * 100) if previous_total != 0 else 0

        current_var = current.get('var_total', 0)
        previous_var = previous.get('var_total', 0)
        var_diff = current_var - previous_var

        current_fixed = current.get('fixed_lines_total', 0)
        previous_fixed = previous.get('fixed_lines_total', 0)
        fixed_diff = current_fixed - previous_fixed

        def format_diff(diff: float) -> str:
            if diff > 0:
                return f"+{format_currency(diff)}"
            elif diff < 0:
                return format_currency(diff)
            return "="

        data = [
            ["Categorie", "Mois actuel", "Mois precedent", "Evolution"],
            ["Variables", format_currency(current_var), format_currency(previous_var), format_diff(var_diff)],
            ["Fixes", format_currency(current_fixed), format_currency(previous_fixed), format_diff(fixed_diff)],
            ["TOTAL", format_currency(current_total), format_currency(previous_total), f"{format_diff(difference)} ({diff_percent:+.1f}%)"],
        ]

        table = Table(data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLORS["primary"]),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (0, -1), (-1, -1), COLORS["background"]),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS["gray_light"]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(table)
        return elements

    def _create_merchants_section(self, merchants: List[Dict]) -> List:
        """Create top merchants table"""
        elements = []

        data = [["Rang", "Marchand", "Nb Trans.", "Total"]]
        for i, merchant in enumerate(merchants, 1):
            data.append([
                f"#{i}",
                merchant.get('name', 'Inconnu')[:25],
                str(merchant.get('count', 0)),
                format_currency(abs(merchant.get('total', 0)))
            ])

        table = Table(data, colWidths=[2*cm, 7*cm, 2.5*cm, 4*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLORS["warning"]),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS["gray_light"]),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLORS["background"]]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(table)
        return elements

    def _create_summary_section(self, summary: Dict, config: Dict) -> List:
        """Create summary table"""
        elements = []

        var_total = summary.get('var_total', 0)
        fixed_total = summary.get('fixed_lines_total', 0)
        provisions_total = summary.get('provisions_total', 0)
        grand_total = summary.get('grand_total', var_total + fixed_total + provisions_total)

        data = [
            ["Type", "Montant"],
            ["Depenses Variables", format_currency(var_total)],
            ["Charges Fixes", format_currency(fixed_total)],
            ["Provisions/Epargne", format_currency(provisions_total)],
            ["TOTAL", format_currency(grand_total)],
        ]

        table = Table(data, colWidths=[10*cm, 5*cm])
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), COLORS["primary"]),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Body
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 10),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),

            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), COLORS["background"]),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS["gray_light"]),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, COLORS["background"]]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(table)
        return elements

    def _create_member_breakdown(self, summary: Dict, config: Dict) -> List:
        """Create member breakdown table"""
        elements = []

        member1 = summary.get('member1', 'Membre 1')
        member2 = summary.get('member2', 'Membre 2')

        data = [
            ["", member1, member2],
            ["Variables", format_currency(summary.get('var_p1', 0)), format_currency(summary.get('var_p2', 0))],
            ["Fixes", format_currency(summary.get('fixed_p1', 0)), format_currency(summary.get('fixed_p2', 0))],
            ["Provisions", format_currency(summary.get('provisions_p1', 0)), format_currency(summary.get('provisions_p2', 0))],
            ["TOTAL", format_currency(summary.get('total_p1', 0)), format_currency(summary.get('total_p2', 0))],
        ]

        table = Table(data, colWidths=[6*cm, 4.5*cm, 4.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLORS["primary"]),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (0, -1), (-1, -1), COLORS["background"]),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS["gray_light"]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(table)
        return elements

    def _create_tags_section(self, tags_summary: Dict) -> List:
        """Create tags breakdown table"""
        elements = []

        tags = tags_summary.get('tags', {})
        if not tags:
            return elements

        # Sort by amount descending
        sorted_tags = sorted(tags.items(), key=lambda x: x[1].get('total', 0), reverse=True)

        data = [["Categorie", "Nb Trans.", "Montant"]]
        for tag_name, tag_data in sorted_tags[:10]:  # Top 10
            data.append([
                tag_name.capitalize(),
                str(tag_data.get('count', 0)),
                format_currency(abs(tag_data.get('total', 0)))
            ])

        table = Table(data, colWidths=[7*cm, 3*cm, 5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLORS["success"]),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS["gray_light"]),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLORS["background"]]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(table)
        return elements

    def _create_transactions_section(self, transactions: List[Dict]) -> List:
        """Create transactions table"""
        elements = []

        data = [["Date", "Libelle", "Montant"]]
        for tx in transactions:
            date_str = ""
            if tx.get('date_op'):
                try:
                    if isinstance(tx['date_op'], str):
                        date_str = tx['date_op'][:10]
                    else:
                        date_str = tx['date_op'].strftime('%d/%m/%Y')
                except:
                    date_str = str(tx.get('date_op', ''))[:10]

            label = tx.get('label', '')[:40]
            if len(tx.get('label', '')) > 40:
                label += '...'

            amount = tx.get('amount', 0)
            amount_str = format_currency(amount)

            data.append([date_str, label, amount_str])

        table = Table(data, colWidths=[3*cm, 9*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLORS["warning"]),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS["gray_light"]),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLORS["background"]]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))

        elements.append(table)
        return elements


# Singleton instance
pdf_service = BudgetPDFReport()


def generate_budget_pdf(
    month: str,
    summary: Dict[str, Any],
    transactions: List[Dict[str, Any]],
    config: Dict[str, Any],
    tags_summary: Optional[Dict[str, Any]] = None,
    ai_summary: Optional[str] = None,
    previous_month_data: Optional[Dict[str, Any]] = None,
    top_merchants: Optional[List[Dict[str, Any]]] = None
) -> bytes:
    """
    Main function to generate budget PDF report (v4.1 enhanced)

    Args:
        month: Month in YYYY-MM format
        summary: Summary data from /summary endpoint
        transactions: List of transactions
        config: User configuration
        tags_summary: Optional tags breakdown
        ai_summary: Optional AI-generated summary text
        previous_month_data: Optional previous month data for comparison
        top_merchants: Optional list of top merchants

    Returns:
        PDF content as bytes
    """
    return pdf_service.generate_monthly_report(
        month=month,
        summary=summary,
        transactions=transactions,
        config=config,
        tags_summary=tags_summary,
        ai_summary=ai_summary,
        previous_month_data=previous_month_data,
        top_merchants=top_merchants
    )
