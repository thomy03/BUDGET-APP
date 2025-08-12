"""
Module d'export complet pour Budget Famille v2.3
Gère tous les formats d'export : CSV, Excel, PDF, JSON avec filtres avancés
"""

import io
import json
import uuid
import zipfile
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Union, BinaryIO
from pathlib import Path
import tempfile
import os

import pandas as pd
from sqlalchemy.orm import Session
from fastapi import HTTPException
from fastapi.responses import StreamingResponse, FileResponse

# Import conditionnel des librairies d'export
try:
    import xlsxwriter
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

from pydantic import BaseModel, Field, validator
from enum import Enum

logger = logging.getLogger(__name__)

# ================= MODÈLES D'EXPORT =================

class ExportFormat(str, Enum):
    CSV = "csv"
    EXCEL = "excel" 
    PDF = "pdf"
    JSON = "json"
    ZIP = "zip"

class ExportScope(str, Enum):
    TRANSACTIONS = "transactions"
    SUMMARY = "summary"  
    ANALYTICS = "analytics"
    CONFIG = "config"
    ALL = "all"

class ExportFilters(BaseModel):
    """Filtres pour personnaliser l'export"""
    months: Optional[List[str]] = Field(None, description="Mois spécifiques (YYYY-MM)")
    date_start: Optional[date] = Field(None, description="Date de début")
    date_end: Optional[date] = Field(None, description="Date de fin")
    categories: Optional[List[str]] = Field(None, description="Catégories à inclure")
    members: Optional[List[str]] = Field(None, description="Membres concernés")
    exclude_hidden: bool = Field(True, description="Exclure les transactions masquées")
    include_duplicates: bool = Field(False, description="Inclure les doublons")
    tags: Optional[List[str]] = Field(None, description="Tags à filtrer")

class ExportRequest(BaseModel):
    """Requête d'export complète"""
    format: ExportFormat = Field(..., description="Format d'export")
    scope: ExportScope = Field(ExportScope.ALL, description="Périmètre d'export")
    filters: Optional[ExportFilters] = Field(None, description="Filtres d'export")
    options: Optional[Dict[str, Any]] = Field(None, description="Options spécifiques au format")
    template: Optional[str] = Field(None, description="Template personnalisé")
    compress: bool = Field(False, description="Compresser le résultat")

class ExportJob(BaseModel):
    """Job d'export pour suivi asynchrone"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = Field("pending", description="pending, processing, completed, failed")
    format: ExportFormat
    scope: ExportScope
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    user_id: str
    download_count: int = Field(default=0)
    expires_at: datetime = Field(default_factory=lambda: datetime.now() + timedelta(hours=24))

# ================= CLASSES D'EXPORT =================

class BaseExporter:
    """Classe de base pour tous les exporters"""
    
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def apply_filters(self, query, filters: ExportFilters):
        """Applique les filtres à une requête SQLAlchemy"""
        if not filters:
            return query
            
        # Import local pour éviter les dépendances circulaires
        from app import Transaction
        
        if filters.months:
            query = query.filter(Transaction.month.in_(filters.months))
        
        if filters.date_start:
            query = query.filter(Transaction.date_op >= filters.date_start)
        
        if filters.date_end:
            query = query.filter(Transaction.date_op <= filters.date_end)
        
        if filters.categories:
            query = query.filter(Transaction.category.in_(filters.categories))
        
        if filters.exclude_hidden:
            query = query.filter(Transaction.exclude == False)
        
        if filters.tags:
            # Recherche dans les tags (format CSV dans la DB)
            for tag in filters.tags:
                query = query.filter(Transaction.tags.contains(tag))
        
        return query
    
    def get_filtered_data(self, filters: ExportFilters) -> Dict[str, Any]:
        """Récupère les données filtrées pour export"""
        from app import Transaction, Config, FixedLine, ImportMetadata
        
        data = {}
        
        # Configuration
        config = self.db.query(Config).first()
        data['config'] = config
        
        # Transactions
        query = self.db.query(Transaction)
        query = self.apply_filters(query, filters)
        data['transactions'] = query.order_by(Transaction.date_op.desc()).all()
        
        # Lignes fixes
        data['fixed_lines'] = self.db.query(FixedLine).filter(FixedLine.active == True).all()
        
        # Métadonnées d'imports
        data['imports'] = self.db.query(ImportMetadata).order_by(ImportMetadata.created_at.desc()).limit(20).all()
        
        return data

class CSVExporter(BaseExporter):
    """Exporteur CSV avec options avancées"""
    
    def export(self, filters: ExportFilters, options: Dict[str, Any] = None) -> io.BytesIO:
        """Exporte en CSV"""
        options = options or {}
        
        data = self.get_filtered_data(filters)
        output = io.BytesIO()
        
        # Créer un DataFrame avec toutes les transactions
        transactions_data = []
        for tx in data['transactions']:
            transactions_data.append({
                'Date': tx.date_op.isoformat() if tx.date_op else '',
                'Mois': tx.month,
                'Libellé': tx.label,
                'Catégorie': tx.category,
                'Catégorie Parent': tx.category_parent,
                'Montant': tx.amount,
                'Compte': tx.account_label,
                'Est Dépense': tx.is_expense,
                'Exclu': tx.exclude,
                'Tags': tx.tags,
                'Import ID': tx.import_id or ''
            })
        
        df = pd.DataFrame(transactions_data)
        
        # Options CSV
        separator = options.get('separator', ',')
        encoding = options.get('encoding', 'utf-8-sig')  # BOM pour Excel
        
        csv_content = df.to_csv(
            index=False, 
            sep=separator, 
            encoding=encoding,
            quoting=1  # Quote tous les champs
        )
        
        output.write(csv_content.encode(encoding))
        output.seek(0)
        
        self.logger.info(f"Export CSV généré: {len(df)} transactions")
        return output

class ExcelExporter(BaseExporter):
    """Exporteur Excel multi-onglets"""
    
    def export(self, filters: ExportFilters, options: Dict[str, Any] = None) -> io.BytesIO:
        """Exporte en Excel avec onglets multiples"""
        if not XLSX_AVAILABLE:
            raise HTTPException(status_code=500, detail="Module xlsxwriter non disponible")
        
        options = options or {}
        data = self.get_filtered_data(filters)
        
        output = io.BytesIO()
        
        with xlsxwriter.Workbook(output, {'in_memory': True}) as workbook:
            # Styles
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#366092',
                'font_color': 'white',
                'border': 1
            })
            
            currency_format = workbook.add_format({'num_format': '#,##0.00 €'})
            date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
            percent_format = workbook.add_format({'num_format': '0.00%'})
            
            # Onglet Transactions
            self._create_transactions_sheet(workbook, data['transactions'], header_format, currency_format, date_format)
            
            # Onglet Synthèse par mois
            self._create_summary_sheet(workbook, data, header_format, currency_format)
            
            # Onglet Configuration
            self._create_config_sheet(workbook, data['config'], data['fixed_lines'], header_format, currency_format, percent_format)
            
            # Onglet Analytics (si demandé)
            if options.get('include_analytics', True):
                self._create_analytics_sheet(workbook, data, header_format, currency_format)
        
        output.seek(0)
        self.logger.info(f"Export Excel généré avec {len(data['transactions'])} transactions")
        return output
    
    def _create_transactions_sheet(self, workbook, transactions, header_format, currency_format, date_format):
        """Crée l'onglet des transactions"""
        worksheet = workbook.add_worksheet('Transactions')
        
        headers = ['Date', 'Mois', 'Libellé', 'Catégorie', 'Catégorie Parent', 
                  'Montant', 'Compte', 'Dépense', 'Exclu', 'Tags', 'Import ID']
        
        # En-têtes
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Données
        for row, tx in enumerate(transactions, 1):
            worksheet.write(row, 0, tx.date_op, date_format)
            worksheet.write(row, 1, tx.month)
            worksheet.write(row, 2, tx.label or '')
            worksheet.write(row, 3, tx.category or '')
            worksheet.write(row, 4, tx.category_parent or '')
            worksheet.write(row, 5, tx.amount or 0, currency_format)
            worksheet.write(row, 6, tx.account_label or '')
            worksheet.write(row, 7, 'Oui' if tx.is_expense else 'Non')
            worksheet.write(row, 8, 'Oui' if tx.exclude else 'Non')
            worksheet.write(row, 9, tx.tags or '')
            worksheet.write(row, 10, tx.import_id or '')
        
        # Auto-ajustement des colonnes
        worksheet.autofilter(0, 0, len(transactions), len(headers) - 1)
        worksheet.freeze_panes(1, 0)
    
    def _create_summary_sheet(self, workbook, data, header_format, currency_format):
        """Crée l'onglet de synthèse par mois"""
        worksheet = workbook.add_worksheet('Synthèse Mensuelle')
        
        # Calculer les synthèses par mois
        monthly_summary = {}
        for tx in data['transactions']:
            month = tx.month
            if month not in monthly_summary:
                monthly_summary[month] = {
                    'revenus': 0,
                    'depenses': 0,
                    'transactions': 0,
                    'depenses_excl': 0
                }
            
            monthly_summary[month]['transactions'] += 1
            if tx.is_expense:
                if tx.exclude:
                    monthly_summary[month]['depenses_excl'] += abs(tx.amount or 0)
                else:
                    monthly_summary[month]['depenses'] += abs(tx.amount or 0)
            else:
                monthly_summary[month]['revenus'] += tx.amount or 0
        
        headers = ['Mois', 'Revenus', 'Dépenses', 'Dépenses Exclues', 'Net', 'Nb Transactions']
        
        # En-têtes
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Données
        for row, (month, summary) in enumerate(sorted(monthly_summary.items()), 1):
            net = summary['revenus'] - summary['depenses']
            worksheet.write(row, 0, month)
            worksheet.write(row, 1, summary['revenus'], currency_format)
            worksheet.write(row, 2, summary['depenses'], currency_format)
            worksheet.write(row, 3, summary['depenses_excl'], currency_format)
            worksheet.write(row, 4, net, currency_format)
            worksheet.write(row, 5, summary['transactions'])
        
        worksheet.autofilter(0, 0, len(monthly_summary), len(headers) - 1)
    
    def _create_config_sheet(self, workbook, config, fixed_lines, header_format, currency_format, percent_format):
        """Crée l'onglet de configuration"""
        worksheet = workbook.add_worksheet('Configuration')
        
        row = 0
        
        # Configuration générale
        worksheet.write(row, 0, 'CONFIGURATION GÉNÉRALE', header_format)
        row += 2
        
        config_items = [
            ('Membre 1', config.member1 if config else ''),
            ('Membre 2', config.member2 if config else ''),
            ('Revenus Membre 1', config.rev1 if config else 0),
            ('Revenus Membre 2', config.rev2 if config else 0),
            ('Mode de Répartition', config.split_mode if config else ''),
            ('Part Membre 1', config.split1 if config else 0),
            ('Part Membre 2', config.split2 if config else 0),
            ('Prêt Égal', 'Oui' if config and config.loan_equal else 'Non'),
            ('Montant Prêt', config.loan_amount if config else 0),
        ]
        
        for label, value in config_items:
            worksheet.write(row, 0, label)
            if isinstance(value, (int, float)) and 'Revenus' in label or 'Montant' in label:
                worksheet.write(row, 1, value, currency_format)
            elif isinstance(value, (int, float)) and 'Part' in label:
                worksheet.write(row, 1, value, percent_format)
            else:
                worksheet.write(row, 1, value)
            row += 1
        
        row += 2
        
        # Lignes fixes
        worksheet.write(row, 0, 'CHARGES FIXES', header_format)
        row += 2
        
        fixed_headers = ['Libellé', 'Montant', 'Fréquence', 'Mode Répartition', 'Part 1', 'Part 2']
        for col, header in enumerate(fixed_headers):
            worksheet.write(row, col, header, header_format)
        row += 1
        
        for line in fixed_lines:
            worksheet.write(row, 0, line.label or '')
            worksheet.write(row, 1, line.amount or 0, currency_format)
            worksheet.write(row, 2, line.freq or '')
            worksheet.write(row, 3, line.split_mode or '')
            worksheet.write(row, 4, line.split1 or 0, percent_format)
            worksheet.write(row, 5, line.split2 or 0, percent_format)
            row += 1
    
    def _create_analytics_sheet(self, workbook, data, header_format, currency_format):
        """Crée l'onglet d'analytics"""
        worksheet = workbook.add_worksheet('Analytics')
        
        # Analytics par catégorie
        category_analysis = {}
        for tx in data['transactions']:
            if tx.is_expense and not tx.exclude and tx.amount:
                cat = tx.category or 'Autre'
                if cat not in category_analysis:
                    category_analysis[cat] = {'amount': 0, 'count': 0}
                category_analysis[cat]['amount'] += abs(tx.amount)
                category_analysis[cat]['count'] += 1
        
        worksheet.write(0, 0, 'ANALYSE PAR CATÉGORIE', header_format)
        
        headers = ['Catégorie', 'Montant Total', 'Nb Transactions', 'Montant Moyen']
        for col, header in enumerate(headers):
            worksheet.write(2, col, header, header_format)
        
        row = 3
        for cat, data_cat in sorted(category_analysis.items(), key=lambda x: x[1]['amount'], reverse=True):
            avg = data_cat['amount'] / data_cat['count'] if data_cat['count'] > 0 else 0
            worksheet.write(row, 0, cat)
            worksheet.write(row, 1, data_cat['amount'], currency_format)
            worksheet.write(row, 2, data_cat['count'])
            worksheet.write(row, 3, avg, currency_format)
            row += 1

class PDFExporter(BaseExporter):
    """Exporteur PDF avec mise en forme professionnelle"""
    
    def export(self, filters: ExportFilters, options: Dict[str, Any] = None) -> io.BytesIO:
        """Exporte en PDF"""
        if not PDF_AVAILABLE:
            raise HTTPException(status_code=500, detail="Module reportlab non disponible")
        
        options = options or {}
        data = self.get_filtered_data(filters)
        
        output = io.BytesIO()
        
        # Configuration du document
        doc = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            textColor=colors.darkblue
        )
        
        # Contenu
        story = []
        
        # Titre
        story.append(Paragraph("Rapport Budget Famille", title_style))
        story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Synthèse exécutive
        self._add_executive_summary(story, data, styles)
        
        # Détail des transactions
        if options.get('include_transactions', True):
            story.append(PageBreak())
            self._add_transactions_detail(story, data['transactions'], styles)
        
        # Configuration
        if options.get('include_config', True):
            story.append(PageBreak())
            self._add_configuration_detail(story, data['config'], data['fixed_lines'], styles)
        
        # Génération du PDF
        doc.build(story)
        output.seek(0)
        
        self.logger.info(f"Export PDF généré avec {len(data['transactions'])} transactions")
        return output
    
    def _add_executive_summary(self, story, data, styles):
        """Ajoute la synthèse exécutive"""
        story.append(Paragraph("Synthèse Exécutive", styles['Heading2']))
        
        # Calculer les totaux
        total_revenus = sum(tx.amount for tx in data['transactions'] 
                           if not tx.is_expense and not tx.exclude and tx.amount > 0)
        total_depenses = sum(abs(tx.amount) for tx in data['transactions'] 
                            if tx.is_expense and not tx.exclude and tx.amount < 0)
        net = total_revenus - total_depenses
        
        summary_data = [
            ['Indicateur', 'Valeur'],
            ['Total Revenus', f"{total_revenus:.2f} €"],
            ['Total Dépenses', f"{total_depenses:.2f} €"],
            ['Solde Net', f"{net:.2f} €"],
            ['Nb Transactions', str(len(data['transactions']))],
        ]
        
        table = Table(summary_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
    
    def _add_transactions_detail(self, story, transactions, styles):
        """Ajoute le détail des transactions"""
        story.append(Paragraph("Détail des Transactions", styles['Heading2']))
        
        # Limiter à 50 transactions max pour le PDF
        display_transactions = transactions[:50]
        
        if len(transactions) > 50:
            story.append(Paragraph(f"Affichage des 50 premières transactions sur {len(transactions)} au total.", 
                                 styles['Normal']))
            story.append(Spacer(1, 12))
        
        transaction_data = [['Date', 'Libellé', 'Catégorie', 'Montant']]
        
        for tx in display_transactions:
            transaction_data.append([
                tx.date_op.strftime('%d/%m/%Y') if tx.date_op else '',
                (tx.label or '')[:30] + ('...' if len(tx.label or '') > 30 else ''),
                tx.category or '',
                f"{tx.amount:.2f} €" if tx.amount else '0.00 €'
            ])
        
        table = Table(transaction_data, colWidths=[80, 200, 120, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),  # Montants alignés à droite
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
        ]))
        
        story.append(table)
    
    def _add_configuration_detail(self, story, config, fixed_lines, styles):
        """Ajoute le détail de la configuration"""
        story.append(Paragraph("Configuration", styles['Heading2']))
        
        if config:
            config_data = [
                ['Paramètre', 'Valeur'],
                ['Membre 1', config.member1 or ''],
                ['Membre 2', config.member2 or ''],
                ['Revenus Membre 1', f"{config.rev1:.2f} €" if config.rev1 else "0.00 €"],
                ['Revenus Membre 2', f"{config.rev2:.2f} €" if config.rev2 else "0.00 €"],
                ['Mode Répartition', config.split_mode or ''],
            ]
            
            table = Table(config_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
            story.append(Spacer(1, 20))
        
        if fixed_lines:
            story.append(Paragraph("Charges Fixes", styles['Heading3']))
            
            fixed_data = [['Libellé', 'Montant', 'Fréquence']]
            for line in fixed_lines:
                fixed_data.append([
                    line.label or '',
                    f"{line.amount:.2f} €" if line.amount else "0.00 €",
                    line.freq or ''
                ])
            
            table = Table(fixed_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)

class JSONExporter(BaseExporter):
    """Exporteur JSON pour backup/restore"""
    
    def export(self, filters: ExportFilters, options: Dict[str, Any] = None) -> io.BytesIO:
        """Exporte en JSON complet"""
        options = options or {}
        data = self.get_filtered_data(filters)
        
        # Préparer les données pour sérialisation JSON
        export_data = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'export_version': '1.0',
                'user_id': self.user_id,
                'filters': filters.dict() if filters else None,
                'total_transactions': len(data['transactions'])
            },
            'config': self._serialize_config(data['config']),
            'transactions': [self._serialize_transaction(tx) for tx in data['transactions']],
            'fixed_lines': [self._serialize_fixed_line(fl) for fl in data['fixed_lines']],
            'imports_metadata': [self._serialize_import(imp) for imp in data['imports']]
        }
        
        # Options de format JSON
        indent = 2 if options.get('pretty', True) else None
        ensure_ascii = options.get('ensure_ascii', False)
        
        json_content = json.dumps(export_data, indent=indent, ensure_ascii=ensure_ascii, default=str)
        
        output = io.BytesIO()
        output.write(json_content.encode('utf-8'))
        output.seek(0)
        
        self.logger.info(f"Export JSON généré avec {len(data['transactions'])} transactions")
        return output
    
    def _serialize_config(self, config):
        """Sérialise la configuration"""
        if not config:
            return None
        
        return {
            'id': config.id,
            'member1': config.member1,
            'member2': config.member2,
            'rev1': float(config.rev1) if config.rev1 else 0.0,
            'rev2': float(config.rev2) if config.rev2 else 0.0,
            'split_mode': config.split_mode,
            'split1': float(config.split1) if config.split1 else 0.0,
            'split2': float(config.split2) if config.split2 else 0.0,
            'loan_equal': config.loan_equal,
            'loan_amount': float(config.loan_amount) if config.loan_amount else 0.0,
            'other_fixed_simple': config.other_fixed_simple,
            'other_fixed_monthly': float(config.other_fixed_monthly) if config.other_fixed_monthly else 0.0,
            'vac_percent': float(config.vac_percent) if config.vac_percent else 0.0,
            'vac_base': config.vac_base
        }
    
    def _serialize_transaction(self, tx):
        """Sérialise une transaction"""
        return {
            'id': tx.id,
            'month': tx.month,
            'date_op': tx.date_op.isoformat() if tx.date_op else None,
            'label': tx.label,
            'category': tx.category,
            'category_parent': tx.category_parent,
            'amount': float(tx.amount) if tx.amount else 0.0,
            'account_label': tx.account_label,
            'is_expense': tx.is_expense,
            'exclude': tx.exclude,
            'row_id': tx.row_id,
            'tags': tx.tags,
            'import_id': tx.import_id
        }
    
    def _serialize_fixed_line(self, fl):
        """Sérialise une ligne fixe"""
        return {
            'id': fl.id,
            'label': fl.label,
            'amount': float(fl.amount) if fl.amount else 0.0,
            'freq': fl.freq,
            'split_mode': fl.split_mode,
            'split1': float(fl.split1) if fl.split1 else 0.0,
            'split2': float(fl.split2) if fl.split2 else 0.0,
            'active': fl.active
        }
    
    def _serialize_import(self, imp):
        """Sérialise les métadonnées d'import"""
        return {
            'id': imp.id,
            'filename': imp.filename,
            'created_at': imp.created_at.isoformat() if imp.created_at else None,
            'user_id': imp.user_id,
            'duplicates_count': imp.duplicates_count,
            'processing_ms': imp.processing_ms
        }

class ZIPExporter(BaseExporter):
    """Exporteur ZIP pour exports multiples"""
    
    def export(self, formats: List[ExportFormat], filters: ExportFilters, options: Dict[str, Any] = None) -> io.BytesIO:
        """Exporte multiple formats dans un ZIP"""
        options = options or {}
        
        output = io.BytesIO()
        
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Créer un dossier avec timestamp
            folder_name = f"budget_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            for format_type in formats:
                try:
                    if format_type == ExportFormat.CSV:
                        exporter = CSVExporter(self.db, self.user_id)
                        content = exporter.export(filters, options.get('csv_options', {}))
                        zipf.writestr(f"{folder_name}/transactions.csv", content.getvalue())
                    
                    elif format_type == ExportFormat.EXCEL:
                        exporter = ExcelExporter(self.db, self.user_id)
                        content = exporter.export(filters, options.get('excel_options', {}))
                        zipf.writestr(f"{folder_name}/budget_complet.xlsx", content.getvalue())
                    
                    elif format_type == ExportFormat.PDF:
                        exporter = PDFExporter(self.db, self.user_id)
                        content = exporter.export(filters, options.get('pdf_options', {}))
                        zipf.writestr(f"{folder_name}/rapport_budget.pdf", content.getvalue())
                    
                    elif format_type == ExportFormat.JSON:
                        exporter = JSONExporter(self.db, self.user_id)
                        content = exporter.export(filters, options.get('json_options', {}))
                        zipf.writestr(f"{folder_name}/backup_complet.json", content.getvalue())
                        
                except Exception as e:
                    self.logger.error(f"Erreur export {format_type}: {e}")
                    # Ajouter un fichier d'erreur dans le ZIP
                    error_msg = f"Erreur lors de l'export {format_type}: {str(e)}"
                    zipf.writestr(f"{folder_name}/ERREUR_{format_type}.txt", error_msg)
            
            # Ajouter un fichier README
            readme_content = f"""Export Budget Famille
====================

Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
Utilisateur: {self.user_id}

Contenu:
- transactions.csv: Toutes les transactions au format CSV
- budget_complet.xlsx: Rapport complet multi-onglets
- rapport_budget.pdf: Rapport formaté pour impression
- backup_complet.json: Backup complet pour restauration

Filtres appliqués:
{json.dumps(filters.dict() if filters else {}, indent=2, ensure_ascii=False)}
"""
            zipf.writestr(f"{folder_name}/README.txt", readme_content)
        
        output.seek(0)
        self.logger.info(f"Export ZIP généré avec {len(formats)} formats")
        return output

# ================= GESTIONNAIRE PRINCIPAL =================

class ExportManager:
    """Gestionnaire principal des exports"""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(f"{__name__}.ExportManager")
    
    def create_export_job(self, request: ExportRequest, user_id: str) -> ExportJob:
        """Crée un job d'export"""
        job = ExportJob(
            format=request.format,
            scope=request.scope,
            user_id=user_id
        )
        
        # Sauvegarder le job en DB (à implémenter selon le modèle de données)
        self.logger.info(f"Job d'export créé: {job.id} pour utilisateur {user_id}")
        return job
    
    def execute_export(self, request: ExportRequest, user_id: str) -> Union[StreamingResponse, FileResponse]:
        """Execute un export et retourne la réponse HTTP"""
        try:
            filters = request.filters or ExportFilters()
            options = request.options or {}
            
            if request.format == ExportFormat.CSV:
                exporter = CSVExporter(self.db, user_id)
                content = exporter.export(filters, options)
                
                filename = f"budget_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                return StreamingResponse(
                    io.BytesIO(content.getvalue()),
                    media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
            
            elif request.format == ExportFormat.EXCEL:
                exporter = ExcelExporter(self.db, user_id)
                content = exporter.export(filters, options)
                
                filename = f"budget_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                return StreamingResponse(
                    io.BytesIO(content.getvalue()),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
            
            elif request.format == ExportFormat.PDF:
                exporter = PDFExporter(self.db, user_id)
                content = exporter.export(filters, options)
                
                filename = f"budget_rapport_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                return StreamingResponse(
                    io.BytesIO(content.getvalue()),
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
            
            elif request.format == ExportFormat.JSON:
                exporter = JSONExporter(self.db, user_id)
                content = exporter.export(filters, options)
                
                filename = f"budget_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                return StreamingResponse(
                    io.BytesIO(content.getvalue()),
                    media_type="application/json",
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
            
            elif request.format == ExportFormat.ZIP:
                # Export ZIP multi-formats
                formats = options.get('formats', [ExportFormat.CSV, ExportFormat.EXCEL, ExportFormat.PDF])
                exporter = ZIPExporter(self.db, user_id)
                content = exporter.export(formats, filters, options)
                
                filename = f"budget_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                return StreamingResponse(
                    io.BytesIO(content.getvalue()),
                    media_type="application/zip",
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
            
            else:
                raise HTTPException(status_code=400, detail="Format d'export non supporté")
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'export: {e}")
            raise HTTPException(status_code=500, detail=f"Erreur lors de l'export: {str(e)}")
    
    def get_export_templates(self) -> Dict[str, Dict[str, Any]]:
        """Retourne les templates d'export disponibles"""
        return {
            "synthese_mensuelle": {
                "name": "Synthèse Mensuelle",
                "description": "Export des synthèses par mois avec graphiques",
                "formats": ["excel", "pdf"],
                "scope": "analytics"
            },
            "detail_complet": {
                "name": "Détail Complet",
                "description": "Export complet de toutes les données",
                "formats": ["zip"],
                "scope": "all"
            },
            "backup_restauration": {
                "name": "Backup pour Restauration",
                "description": "Export JSON complet pour backup",
                "formats": ["json"],
                "scope": "all"
            },
            "rapport_tresorerie": {
                "name": "Rapport de Trésorerie",
                "description": "Rapport PDF formaté pour présentation",
                "formats": ["pdf"],
                "scope": "summary"
            }
        }