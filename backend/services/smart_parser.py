"""
Smart Parser Service for Budget Famille v4.1
Intelligent multi-format file parser with automatic bank detection

Supports:
- CSV files (various bank formats)
- XLSX files (Excel)
- PDF files (bank statements)

Features:
- Auto-detect file format
- Auto-detect bank source
- Auto-map columns to transaction fields
- Preview mode for user confirmation
"""

import io
import re
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, date
import pandas as pd

logger = logging.getLogger(__name__)


class FileFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"
    UNKNOWN = "unknown"


class BankSource(str, Enum):
    BOURSOBANK = "boursobank"
    LCL = "lcl"
    SOCIETE_GENERALE = "societe_generale"
    BNP = "bnp"
    CREDIT_AGRICOLE = "credit_agricole"
    CREDIT_MUTUEL = "credit_mutuel"
    CAISSE_EPARGNE = "caisse_epargne"
    LA_BANQUE_POSTALE = "la_banque_postale"
    FORTUNEO = "fortuneo"
    HELLO_BANK = "hello_bank"
    N26 = "n26"
    REVOLUT = "revolut"
    GENERIC = "generic"
    UNKNOWN = "unknown"


@dataclass
class ColumnMapping:
    """Mapping between source columns and transaction fields"""
    date_column: Optional[str] = None
    label_column: Optional[str] = None
    amount_column: Optional[str] = None
    debit_column: Optional[str] = None
    credit_column: Optional[str] = None
    value_date_column: Optional[str] = None
    category_column: Optional[str] = None

    # For PDF parsing where columns are positional
    date_index: Optional[int] = None
    label_index: Optional[int] = None
    amount_index: Optional[int] = None
    debit_index: Optional[int] = None
    credit_index: Optional[int] = None


@dataclass
class ParsedTransaction:
    """A single parsed transaction"""
    date_op: date
    label: str
    amount: float
    date_value: Optional[date] = None
    category: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "date_op": self.date_op.isoformat() if self.date_op else None,
            "label": self.label,
            "amount": self.amount,
            "date_value": self.date_value.isoformat() if self.date_value else None,
            "category": self.category,
            "month": self.date_op.strftime("%Y-%m") if self.date_op else None
        }


@dataclass
class ParseResult:
    """Result of parsing a file"""
    success: bool
    file_format: FileFormat
    bank_source: BankSource
    column_mapping: ColumnMapping
    transactions: List[ParsedTransaction]
    raw_columns: List[str]
    sample_data: List[Dict]  # First 5 rows for preview
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "file_format": self.file_format.value,
            "bank_source": self.bank_source.value,
            "column_mapping": {
                "date_column": self.column_mapping.date_column,
                "label_column": self.column_mapping.label_column,
                "amount_column": self.column_mapping.amount_column,
                "debit_column": self.column_mapping.debit_column,
                "credit_column": self.column_mapping.credit_column,
            },
            "transaction_count": len(self.transactions),
            "raw_columns": self.raw_columns,
            "sample_data": self.sample_data[:5],
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "transactions_preview": [t.to_dict() for t in self.transactions[:10]]
        }


class SmartParser:
    """
    Intelligent file parser that auto-detects format and bank source
    """

    # Bank detection patterns
    BANK_PATTERNS = {
        BankSource.BOURSOBANK: [
            r"bourso", r"bousfrpp", r"40618", r"boursorama"
        ],
        BankSource.LCL: [
            r"lcl\b", r"credit lyonnais", r"30002"
        ],
        BankSource.SOCIETE_GENERALE: [
            r"societe generale", r"sg\b", r"30003"
        ],
        BankSource.BNP: [
            r"bnp\b", r"paribas", r"30004"
        ],
        BankSource.CREDIT_AGRICOLE: [
            r"credit agricole", r"ca\b", r"18206"
        ],
        BankSource.CREDIT_MUTUEL: [
            r"credit mutuel", r"cm\b", r"10278"
        ],
        BankSource.CAISSE_EPARGNE: [
            r"caisse.*epargne", r"ce\b", r"11315"
        ],
        BankSource.FORTUNEO: [
            r"fortuneo", r"arkea"
        ],
        BankSource.N26: [
            r"n26", r"number26"
        ],
        BankSource.REVOLUT: [
            r"revolut"
        ],
    }

    # Common date formats
    DATE_FORMATS = [
        "%d/%m/%Y",    # 31/12/2025
        "%d/%m/%y",    # 31/12/25
        "%Y-%m-%d",    # 2025-12-31
        "%d-%m-%Y",    # 31-12-2025
        "%d.%m.%Y",    # 31.12.2025
        "%Y/%m/%d",    # 2025/12/31
    ]

    # Column name patterns for auto-detection
    COLUMN_PATTERNS = {
        "date": [
            r"date.*op", r"dateop", r"date$", r"date_op",
            r"date operation", r"date opération", r"jour"
        ],
        "label": [
            r"libel", r"label", r"description", r"intitulé",
            r"motif", r"reference", r"désignation", r"nature"
        ],
        "amount": [
            r"montant", r"amount", r"somme", r"valeur"
        ],
        "debit": [
            r"debit", r"débit", r"sortie", r"depense", r"dépense"
        ],
        "credit": [
            r"credit", r"crédit", r"entree", r"entrée", r"recette"
        ],
        "value_date": [
            r"valeur", r"date.*valeur", r"value.*date"
        ],
        "category": [
            r"categ", r"type", r"categorie", r"catégorie"
        ]
    }

    def __init__(self):
        self.pdf_parser = None

    def detect_file_format(self, filename: str, content: bytes) -> FileFormat:
        """Detect file format from filename and content"""
        filename_lower = filename.lower()

        if filename_lower.endswith('.csv'):
            return FileFormat.CSV
        elif filename_lower.endswith(('.xlsx', '.xls')):
            return FileFormat.XLSX
        elif filename_lower.endswith('.pdf'):
            return FileFormat.PDF

        # Try to detect from content
        # PDF magic bytes
        if content[:4] == b'%PDF':
            return FileFormat.PDF
        # XLSX magic bytes (ZIP archive)
        elif content[:2] == b'PK':
            return FileFormat.XLSX
        # Try to decode as text (CSV)
        else:
            try:
                content.decode('utf-8')
                return FileFormat.CSV
            except:
                try:
                    content.decode('latin-1')
                    return FileFormat.CSV
                except:
                    return FileFormat.UNKNOWN

        return FileFormat.UNKNOWN

    def detect_bank_source(self, content: str, filename: str = "") -> BankSource:
        """Detect bank source from file content"""
        search_text = (content + " " + filename).lower()

        for bank, patterns in self.BANK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, search_text, re.IGNORECASE):
                    logger.info(f"Detected bank: {bank.value} (pattern: {pattern})")
                    return bank

        return BankSource.GENERIC

    def detect_columns(self, columns: List[str]) -> ColumnMapping:
        """Auto-detect column mapping from column names"""
        mapping = ColumnMapping()
        # Convert all column names to strings first (Excel can have numeric column headers)
        columns_lower = {col: str(col).lower() for col in columns}

        for col, col_lower in columns_lower.items():
            # Date column
            if not mapping.date_column:
                for pattern in self.COLUMN_PATTERNS["date"]:
                    if re.search(pattern, col_lower):
                        mapping.date_column = col
                        break

            # Label column
            if not mapping.label_column:
                for pattern in self.COLUMN_PATTERNS["label"]:
                    if re.search(pattern, col_lower):
                        mapping.label_column = col
                        break

            # Amount column (combined)
            if not mapping.amount_column:
                for pattern in self.COLUMN_PATTERNS["amount"]:
                    if re.search(pattern, col_lower):
                        mapping.amount_column = col
                        break

            # Debit column
            if not mapping.debit_column:
                for pattern in self.COLUMN_PATTERNS["debit"]:
                    if re.search(pattern, col_lower):
                        mapping.debit_column = col
                        break

            # Credit column
            if not mapping.credit_column:
                for pattern in self.COLUMN_PATTERNS["credit"]:
                    if re.search(pattern, col_lower):
                        mapping.credit_column = col
                        break

            # Value date
            if not mapping.value_date_column:
                for pattern in self.COLUMN_PATTERNS["value_date"]:
                    if re.search(pattern, col_lower):
                        mapping.value_date_column = col
                        break

            # Category
            if not mapping.category_column:
                for pattern in self.COLUMN_PATTERNS["category"]:
                    if re.search(pattern, col_lower):
                        mapping.category_column = col
                        break

        return mapping

    def parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string with multiple format support"""
        if not date_str or pd.isna(date_str):
            return None

        date_str = str(date_str).strip()

        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        # Try pandas as fallback
        try:
            return pd.to_datetime(date_str, dayfirst=True).date()
        except:
            return None

    def parse_amount(self, value: Any, is_debit: bool = False) -> Optional[float]:
        """Parse amount string to float"""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None

        if isinstance(value, (int, float)):
            amount = float(value)
        else:
            # String cleaning
            value_str = str(value).strip()
            # Remove currency symbols
            value_str = re.sub(r'[€$£¤]', '', value_str)
            # Replace comma with dot
            value_str = value_str.replace(',', '.').replace(' ', '')
            # Remove multiple dots (keep only last one)
            parts = value_str.rsplit('.', 1)
            if len(parts) == 2:
                value_str = parts[0].replace('.', '') + '.' + parts[1]

            try:
                amount = float(value_str)
            except ValueError:
                return None

        # Make negative if debit
        if is_debit and amount > 0:
            amount = -amount

        return amount

    def parse_csv(self, content: bytes, filename: str) -> ParseResult:
        """Parse CSV file"""
        errors = []
        warnings = []

        # Try different encodings
        df = None
        encoding_used = None

        for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
            try:
                df = pd.read_csv(io.BytesIO(content), encoding=encoding, sep=None, engine='python')
                encoding_used = encoding
                break
            except Exception as e:
                continue

        if df is None:
            return ParseResult(
                success=False,
                file_format=FileFormat.CSV,
                bank_source=BankSource.UNKNOWN,
                column_mapping=ColumnMapping(),
                transactions=[],
                raw_columns=[],
                sample_data=[],
                errors=["Impossible de lire le fichier CSV avec les encodages supportés"]
            )

        # Detect bank source
        content_str = content.decode(encoding_used, errors='ignore')
        bank_source = self.detect_bank_source(content_str, filename)

        # Detect columns - convert all to strings (Excel can have numeric column headers)
        columns = [str(col) for col in df.columns.tolist()]
        mapping = self.detect_columns(columns)

        # Parse transactions
        transactions = []
        sample_data = df.head(5).to_dict('records')

        for idx, row in df.iterrows():
            try:
                # Get date
                date_val = None
                if mapping.date_column and mapping.date_column in row:
                    date_val = self.parse_date(row[mapping.date_column])

                if not date_val:
                    warnings.append(f"Ligne {idx+1}: date invalide")
                    continue

                # Get label
                label = ""
                if mapping.label_column and mapping.label_column in row:
                    label = str(row[mapping.label_column])

                # Get amount
                amount = None
                if mapping.amount_column and mapping.amount_column in row:
                    amount = self.parse_amount(row[mapping.amount_column])
                elif mapping.debit_column or mapping.credit_column:
                    # Separate debit/credit columns
                    debit = self.parse_amount(row.get(mapping.debit_column), is_debit=True) if mapping.debit_column else None
                    credit = self.parse_amount(row.get(mapping.credit_column)) if mapping.credit_column else None

                    if debit is not None and debit != 0:
                        amount = debit
                    elif credit is not None and credit != 0:
                        amount = credit

                if amount is None:
                    warnings.append(f"Ligne {idx+1}: montant invalide")
                    continue

                # Get value date
                date_value = None
                if mapping.value_date_column and mapping.value_date_column in row:
                    date_value = self.parse_date(row[mapping.value_date_column])

                # Get category
                category = None
                if mapping.category_column and mapping.category_column in row:
                    category = str(row[mapping.category_column])

                tx = ParsedTransaction(
                    date_op=date_val,
                    label=label,
                    amount=amount,
                    date_value=date_value,
                    category=category,
                    raw_data=row.to_dict()
                )
                transactions.append(tx)

            except Exception as e:
                warnings.append(f"Ligne {idx+1}: erreur de parsing - {str(e)}")

        return ParseResult(
            success=len(transactions) > 0,
            file_format=FileFormat.CSV,
            bank_source=bank_source,
            column_mapping=mapping,
            transactions=transactions,
            raw_columns=columns,
            sample_data=sample_data,
            errors=errors,
            warnings=warnings,
            metadata={
                "encoding": encoding_used,
                "total_rows": len(df),
                "parsed_transactions": len(transactions)
            }
        )

    def _looks_like_date(self, value: str) -> bool:
        """Check if a string looks like a date (YYYY-MM-DD or similar)"""
        import re
        if not value:
            return False
        value_str = str(value).strip()
        # Match YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY patterns
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}',  # 2025-12-30
            r'^\d{2}/\d{2}/\d{4}',  # 30/12/2025
            r'^\d{2}-\d{2}-\d{4}',  # 30-12-2025
        ]
        for pattern in date_patterns:
            if re.match(pattern, value_str):
                return True
        return False

    def parse_xlsx(self, content: bytes, filename: str) -> ParseResult:
        """Parse Excel file"""
        errors = []
        warnings = []

        try:
            df = pd.read_excel(io.BytesIO(content), engine='openpyxl')
        except Exception as e:
            return ParseResult(
                success=False,
                file_format=FileFormat.XLSX,
                bank_source=BankSource.UNKNOWN,
                column_mapping=ColumnMapping(),
                transactions=[],
                raw_columns=[],
                sample_data=[],
                errors=[f"Erreur lecture Excel: {str(e)}"]
            )

        # Check if file has no header (first column name looks like a date)
        columns = [str(col) for col in df.columns.tolist()]
        has_no_header = len(columns) > 0 and self._looks_like_date(columns[0])

        if has_no_header:
            logger.info(f"XLSX file appears to have NO HEADER ROW - re-reading with header=None")
            # Re-read without header
            df = pd.read_excel(io.BytesIO(content), engine='openpyxl', header=None)
            # Assign generic column names
            columns = [f"col_{i}" for i in range(len(df.columns))]
            df.columns = columns
            logger.info(f"Re-read XLSX with {len(df)} rows and {len(columns)} columns")

            # For BoursoBank without header, use positional mapping:
            # Col 0: Date op, Col 1: Date value, Col 2: Label, Col 3: Category
            # Col 4: Sub-category, Col 5: Tag, Col 6: Amount, Col 7: ?, Col 8: Account, Col 9: Bank, Col 10: Balance
            if len(columns) >= 7:
                logger.info(f"Using BoursoBank positional mapping for headerless file")
                mapping = ColumnMapping(
                    date_column="col_0",
                    value_date_column="col_1",
                    label_column="col_2",
                    category_column="col_3",
                    amount_column="col_6"
                )
                bank_source = BankSource.BOURSOBANK
            else:
                logger.warning(f"Headerless file has unexpected column count: {len(columns)}")
                mapping = ColumnMapping()
                bank_source = BankSource.UNKNOWN
        else:
            # Normal file with headers
            # Convert to CSV-like processing
            # First, detect bank from sheet content
            content_str = df.to_string()
            bank_source = self.detect_bank_source(content_str, filename)

            # Detect columns - convert all to strings (Excel can have numeric column headers)
            logger.info(f"XLSX columns detected: {columns}")
            mapping = self.detect_columns(columns)

        logger.info(f"Column mapping: date={mapping.date_column}, label={mapping.label_column}, amount={mapping.amount_column}, debit={mapping.debit_column}, credit={mapping.credit_column}")

        # Parse transactions (same logic as CSV)
        transactions = []
        sample_data = df.head(5).to_dict('records')
        logger.info(f"Sample data (first row): {sample_data[0] if sample_data else 'empty'}")

        for idx, row in df.iterrows():
            try:
                date_val = None
                if mapping.date_column and mapping.date_column in row:
                    date_val = self.parse_date(row[mapping.date_column])

                if not date_val:
                    continue

                label = ""
                if mapping.label_column and mapping.label_column in row:
                    label = str(row[mapping.label_column])

                amount = None
                if mapping.amount_column and mapping.amount_column in row:
                    amount = self.parse_amount(row[mapping.amount_column])
                elif mapping.debit_column or mapping.credit_column:
                    debit = self.parse_amount(row.get(mapping.debit_column), is_debit=True) if mapping.debit_column else None
                    credit = self.parse_amount(row.get(mapping.credit_column)) if mapping.credit_column else None
                    amount = debit if debit else credit

                if amount is None:
                    continue

                tx = ParsedTransaction(
                    date_op=date_val,
                    label=label,
                    amount=amount,
                    raw_data=row.to_dict()
                )
                transactions.append(tx)

            except Exception as e:
                warnings.append(f"Ligne {idx+1}: {str(e)}")

        return ParseResult(
            success=len(transactions) > 0,
            file_format=FileFormat.XLSX,
            bank_source=bank_source,
            column_mapping=mapping,
            transactions=transactions,
            raw_columns=columns,
            sample_data=sample_data,
            errors=errors,
            warnings=warnings,
            metadata={
                "total_rows": len(df),
                "parsed_transactions": len(transactions)
            }
        )

    def parse_pdf(self, content: bytes, filename: str) -> ParseResult:
        """Parse PDF bank statement"""
        from services.pdf_parser import PDFBankStatementParser

        parser = PDFBankStatementParser()
        return parser.parse(content, filename)

    def parse(self, content: bytes, filename: str) -> ParseResult:
        """
        Main entry point: detect format and parse file
        """
        logger.info(f"Smart parsing file: {filename} ({len(content)} bytes)")

        # Detect format
        file_format = self.detect_file_format(filename, content)
        logger.info(f"Detected format: {file_format.value}")

        if file_format == FileFormat.CSV:
            return self.parse_csv(content, filename)
        elif file_format == FileFormat.XLSX:
            return self.parse_xlsx(content, filename)
        elif file_format == FileFormat.PDF:
            return self.parse_pdf(content, filename)
        else:
            return ParseResult(
                success=False,
                file_format=FileFormat.UNKNOWN,
                bank_source=BankSource.UNKNOWN,
                column_mapping=ColumnMapping(),
                transactions=[],
                raw_columns=[],
                sample_data=[],
                errors=[f"Format de fichier non supporté: {filename}"]
            )

    def apply_custom_mapping(
        self,
        content: bytes,
        filename: str,
        custom_mapping: Dict[str, str]
    ) -> ParseResult:
        """
        Re-parse file with custom column mapping provided by user
        """
        # First do basic parse to get DataFrame
        file_format = self.detect_file_format(filename, content)

        if file_format == FileFormat.CSV:
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    df = pd.read_csv(io.BytesIO(content), encoding=encoding, sep=None, engine='python')
                    break
                except:
                    continue
        elif file_format == FileFormat.XLSX:
            df = pd.read_excel(io.BytesIO(content))
        else:
            return ParseResult(
                success=False,
                file_format=file_format,
                bank_source=BankSource.UNKNOWN,
                column_mapping=ColumnMapping(),
                transactions=[],
                raw_columns=[],
                sample_data=[],
                errors=["Mapping personnalisé non supporté pour ce format"]
            )

        # Apply custom mapping
        mapping = ColumnMapping(
            date_column=custom_mapping.get("date"),
            label_column=custom_mapping.get("label"),
            amount_column=custom_mapping.get("amount"),
            debit_column=custom_mapping.get("debit"),
            credit_column=custom_mapping.get("credit"),
        )

        # Parse with custom mapping
        transactions = []
        for idx, row in df.iterrows():
            try:
                date_val = self.parse_date(row.get(mapping.date_column)) if mapping.date_column else None
                if not date_val:
                    continue

                label = str(row.get(mapping.label_column, "")) if mapping.label_column else ""

                amount = None
                if mapping.amount_column:
                    amount = self.parse_amount(row.get(mapping.amount_column))
                elif mapping.debit_column or mapping.credit_column:
                    debit = self.parse_amount(row.get(mapping.debit_column), is_debit=True) if mapping.debit_column else None
                    credit = self.parse_amount(row.get(mapping.credit_column)) if mapping.credit_column else None
                    amount = debit if debit else credit

                if amount is None:
                    continue

                tx = ParsedTransaction(
                    date_op=date_val,
                    label=label,
                    amount=amount,
                    raw_data=row.to_dict()
                )
                transactions.append(tx)
            except:
                continue

        return ParseResult(
            success=len(transactions) > 0,
            file_format=file_format,
            bank_source=BankSource.GENERIC,
            column_mapping=mapping,
            transactions=transactions,
            raw_columns=df.columns.tolist(),
            sample_data=df.head(5).to_dict('records'),
            metadata={"custom_mapping": True}
        )


# Singleton instance
_smart_parser = None

def get_smart_parser() -> SmartParser:
    global _smart_parser
    if _smart_parser is None:
        _smart_parser = SmartParser()
    return _smart_parser
