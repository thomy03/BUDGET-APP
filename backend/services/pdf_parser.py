"""
PDF Bank Statement Parser for Budget Famille v4.1
Extracts transactions from PDF bank statements

Supports multiple French banks:
- BoursoBank (Boursorama)
- LCL
- Societe Generale
- BNP Paribas
- Credit Agricole
- And more...

Uses pdfplumber for table extraction with fallback to text parsing.
"""

import re
import io
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, date
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import pdfplumber
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    logger.warning("pdfplumber not installed. PDF parsing will be limited.")

# Try PyPDF2 as fallback
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False


@dataclass
class PDFTransaction:
    """Parsed transaction from PDF"""
    date_op: date
    label: str
    amount: float
    date_value: Optional[date] = None
    is_credit: bool = False
    page_number: int = 0
    raw_line: str = ""


class BoursobankParser:
    """
    Parser specific to BoursoBank PDF statements

    BoursoBank format:
    - Header with account info, IBAN, period
    - Table: Date opération | Libellé | Valeur | Débit | Crédit
    - SOLDE AU: xxx at the start
    - Multi-line labels (description continues on next lines)

    BoursoBank text format (when tables fail):
    - Lines like: "CARTE28/12/25MERCHANT NAME 15,70EUR CB*1234"
    - Or: "VIR SEPA 28/12/2025 DESCRIPTION 100,00"
    """

    # Patterns for BoursoBank - support both DD/MM/YYYY and DD/MM/YY
    DATE_PATTERN_LONG = r'(\d{2}/\d{2}/\d{4})'
    DATE_PATTERN_SHORT = r'(\d{2}/\d{2}/\d{2})'
    HEADER_PATTERN = r'Date\s*opération.*Libellé.*Valeur.*Débit.*Crédit'
    SOLDE_PATTERN = r'SOLDE AU\s*:\s*(\d{2}/\d{2}/\d{4})\s*([\d\s,\.]+)'

    # Card number pattern to exclude from amount parsing
    CARD_PATTERN = r'CB\*?\d{4}'

    # Amount at end of line: number with 2 decimals, optionally followed by EUR
    AMOUNT_END_PATTERN = r'(\d+[,\.]\d{2})\s*(?:EUR|€)?\s*$'

    # Transaction type prefixes
    TX_PREFIXES = ['CARTE', 'VIR', 'VIREMENT', 'PRLV', 'PRELEVEMENT', 'AVOIR', 'RETRAIT', 'CHQ', 'CHEQUE']

    # Transaction type prefixes that should be separated from merchant names
    TX_PREFIX_PATTERNS = ['CARTE', 'VIR', 'VIREMENT', 'PRLV', 'PRELEVEMENT', 'AVOIR', 'RETRAIT', 'CHQ', 'CHEQUE']

    # Common merchant name patterns to help split concatenated words
    # Sorted by length (longest first) to match longer patterns before shorter ones
    KNOWN_MERCHANTS = sorted([
        'FRANPRIX', 'CARREFOUR', 'LECLERC', 'AUCHAN', 'LIDL', 'INTERMARCHE',
        'MONOPRIX', 'CASINO', 'PICARD', 'BIOCOOP', 'NATURALIA', 'PERSPECTIVE',
        'AMAZON', 'CDISCOUNT', 'FNAC', 'DARTY', 'BOULANGER',
        'SNCF', 'RATP', 'UBER', 'BOLT', 'LIME', 'VELIB',
        'ORANGE', 'SFR', 'FREE', 'BOUYGUES',
        'EDF', 'ENGIE', 'VEOLIA', 'SUEZ',
        'NETFLIX', 'SPOTIFY', 'DEEZER', 'DISNEY', 'APPLE', 'GOOGLE',
        'PAYPAL', 'STRIPE', 'SUMUP',
        'IKEA', 'LEROY', 'MERLIN', 'CASTORAMA', 'BRICORAMA',
        'DECATHLON', 'INTERSPORT', 'GOSP', 'SPORT',
        'MCDONALDS', 'MCDONALD', 'BURGER', 'KING', 'KFC', 'SUBWAY', 'STARBUCKS',
        'LAFAYETTE', 'GALERIES', 'PRINTEMPS', 'ZARA', 'H&M', 'UNIQLO',
        'PHARMACIE', 'PARAPHARMACIE', 'OPTIC',
        'CAFE', 'RESTAURANT', 'BRASSERIE', 'BISTROT', 'BAR',
        'HOTEL', 'AIRBNB', 'BOOKING',
        'TOTAL', 'SHELL', 'BP', 'ESSO', 'AVIA',
        'TEMU', 'SHEIN', 'ALIEXPRESS', 'WISH',
        'LEBONCOIN', 'VINTED', 'EBAY',
        'ASSURANCE', 'MUTUELLE', 'MAIF', 'MACIF', 'MAAF', 'AXA', 'ALLIANZ',
        'SEPA', 'EUROPEEN', 'INST', 'EMIS',
        # Additional merchants
        'ONATERA', 'SUNDAY', 'OPENAI', 'CHATGPT', 'GOURMANDISE', 'TOMOKAZU',
        'GIFI', 'PETITSCULOTTES', 'CHAUD', 'PERSPECTIVE', 'FLO',
        'EAUVIVE', 'EAU', 'VIVE', 'BIO', 'SUPER', 'MARCHE',
        # Keep compound words together
        'MARKETPLACE', 'SUPERMARCHE', 'HYPERMARCHE',
    ], key=len, reverse=True)

    def clean_merchant_label(self, raw_label: str) -> str:
        """
        Clean and format merchant label by adding spaces between concatenated words.
        ONLY separates TX prefixes (CARTE, VIR, etc.) from the rest.
        Example: "CARTEJASMIN" -> "CARTE JASMIN"
        Example: "VIRVIREMENTDEPUIS" -> "VIR VIREMENT DEPUIS"
        Example: "CARTEE.LECLERC" -> "CARTE E. LECLERC"
        """
        if not raw_label:
            return raw_label

        label = raw_label.upper().strip()

        # Step 1: Separate transaction type prefixes at the START
        # These are often concatenated with merchant names in PDF extraction
        for prefix in self.TX_PREFIX_PATTERNS:
            if label.startswith(prefix) and len(label) > len(prefix):
                rest = label[len(prefix):]
                # Only add space if next char is a letter (concatenated)
                if rest[0].isalpha():
                    label = prefix + ' ' + rest
                break  # Only match one prefix at start

        # Step 2: Handle "VIR INSTXXX" or "VIR VIREMENTXXX" patterns
        if label.startswith('VIR '):
            rest = label[4:]
            for inner_prefix in ['INST', 'VIREMENT', 'SEPA']:
                if rest.startswith(inner_prefix) and len(rest) > len(inner_prefix):
                    inner_rest = rest[len(inner_prefix):]
                    if inner_rest and inner_rest[0].isalpha():
                        label = 'VIR ' + inner_prefix + ' ' + inner_rest
                    break

        # Step 3: Handle special case "E.LECLERC" -> "E. LECLERC"
        label = re.sub(r'([A-Z])\.([A-Z])', r'\1. \2', label)

        # Step 4: Clean up multiple spaces
        label = re.sub(r'\s+', ' ', label).strip()

        return label

    def parse_page_text(self, text: str, page_num: int) -> List[PDFTransaction]:
        """Parse a single page of BoursoBank statement"""
        transactions = []
        lines = text.split('\n')
        logger.info(f"BoursoBank text parser: {len(lines)} lines on page {page_num}")

        lines_with_dates = 0

        for i, line in enumerate(lines):
            original_line = line
            line = line.strip()
            if not line or len(line) < 10:
                continue

            # Skip header detection
            if re.search(self.HEADER_PATTERN, line, re.IGNORECASE):
                logger.debug(f"Found header pattern at line {i}")
                continue

            # Skip SOLDE lines (they're summaries, not transactions)
            if 'SOLDE AU' in line.upper():
                logger.debug(f"Skipping SOLDE line: {line[:50]}")
                continue

            # Skip footer/page info
            if any(x in line.lower() for x in ['page', 'boursorama', 'service client', 'médiateur', 'iban']):
                continue

            # Try to find dates in line (both formats)
            date_matches_long = re.findall(self.DATE_PATTERN_LONG, line)
            date_matches_short = re.findall(self.DATE_PATTERN_SHORT, line)

            # Log for debugging
            if date_matches_long or date_matches_short:
                lines_with_dates += 1
                if lines_with_dates <= 5:
                    logger.debug(f"Line with date: {line[:100]}")

            op_date = None
            op_date_str = None
            date_format = None

            # Prefer long format, fallback to short
            if date_matches_long:
                op_date_str = date_matches_long[0]
                date_format = '%d/%m/%Y'
            elif date_matches_short:
                op_date_str = date_matches_short[0]
                date_format = '%d/%m/%y'

            if not op_date_str:
                continue

            try:
                op_date = datetime.strptime(op_date_str, date_format).date()
            except Exception as e:
                logger.debug(f"Failed to parse date {op_date_str}: {e}")
                continue

            # Clean the line for amount extraction:
            # 1. Remove card numbers (CB*1234 or CB1234)
            line_cleaned = re.sub(r'CB\*?\d+', '', line)
            # 2. Remove dates
            for d in date_matches_long + date_matches_short:
                line_cleaned = line_cleaned.replace(d, '')

            logger.debug(f"Cleaned line for amount: {line_cleaned[:80]}")

            # Extract amount from END of cleaned line
            # Pattern: digits with comma/point and 2 decimals, optionally EUR
            amount_match = re.search(r'(\d+[,\.]\d{2})\s*(?:EUR|€)?\s*$', line_cleaned, re.IGNORECASE)

            # Fallback: try to find amount followed by EUR anywhere
            if not amount_match:
                amount_match = re.search(r'(\d+[,\.]\d{2})\s*EUR', line_cleaned, re.IGNORECASE)

            # Last fallback: find the last number with 2 decimals
            if not amount_match:
                all_amounts = re.findall(r'(\d+[,\.]\d{2})', line_cleaned)
                if all_amounts:
                    # Take the last one, it's usually the amount
                    amount_str = all_amounts[-1]
                    amount_match = type('obj', (object,), {'group': lambda self, n: amount_str})()

            if not amount_match:
                logger.debug(f"No amount found in line: {line[:60]}")
                continue

            amount_str = amount_match.group(1) if hasattr(amount_match, 'group') else amount_match
            amount_str = amount_str.replace(',', '.').replace(' ', '')

            try:
                amount = float(amount_str)
            except ValueError:
                logger.debug(f"Failed to parse amount: {amount_str}")
                continue

            # Sanity check: amounts should be reasonable (< 1,000,000)
            if amount > 1000000:
                logger.warning(f"Suspiciously large amount {amount}, skipping line: {line[:60]}")
                continue

            # Extract label - text between type/date and amount
            # Find where the date is in the original line
            date_pos = line.find(op_date_str)
            label_start = date_pos + len(op_date_str) if date_pos >= 0 else 0

            # Get everything after date, before the amount
            label = line[label_start:]

            # Remove amount and EUR from label
            label = re.sub(r'\d+[,\.]\d{2}\s*(?:EUR|€)?', '', label)
            # Remove card numbers
            label = re.sub(r'CB\*?\d+', '', label)
            # Remove secondary dates (value dates like 30/12/2025)
            label = re.sub(r'\d{2}/\d{2}/\d{4}', '', label)
            label = re.sub(r'\d{2}/\d{2}/\d{2}', '', label)
            # Clean up spaces
            label = re.sub(r'\s+', ' ', label).strip()

            # Determine transaction type prefix
            tx_type_prefix = ""
            if date_pos > 0:
                prefix = line[:date_pos].strip().upper()
                for tx_type in self.TX_PREFIXES:
                    if prefix.endswith(tx_type) or prefix == tx_type:
                        tx_type_prefix = tx_type
                        break

            # Clean the merchant label (add spaces between concatenated words)
            label = self.clean_merchant_label(label)

            # Format the final label: "TYPE MERCHANT" for recognition
            if tx_type_prefix:
                label = f"{tx_type_prefix} {label}" if label else tx_type_prefix

            # Determine if debit or credit
            is_credit = False
            if any(x in line.upper() for x in ['AVOIR', 'VIR RECU', 'REMISE', 'VIREMENT RECU']):
                is_credit = True
                amount = abs(amount)
            else:
                # Most transactions are debits
                amount = -abs(amount)

            if label and amount != 0:
                tx = PDFTransaction(
                    date_op=op_date,
                    label=label,
                    amount=amount,
                    date_value=None,
                    is_credit=is_credit,
                    page_number=page_num,
                    raw_line=original_line
                )
                transactions.append(tx)
                logger.debug(f"Created TX: {op_date} | {label[:40]} | {amount:.2f}€")
            else:
                logger.debug(f"Skipped line (label={bool(label)}, amount={amount}): {line[:60]}")

        logger.info(f"BoursoBank text parser: found {lines_with_dates} lines with dates, {len(transactions)} transactions created")
        return transactions

    def parse_table(self, table: List[List], page_num: int) -> List[PDFTransaction]:
        """Parse extracted table from pdfplumber"""
        transactions = []

        for row in table:
            if not row or len(row) < 3:
                continue

            # Skip header rows
            row_text = ' '.join(str(c) for c in row if c)
            if any(x in row_text.lower() for x in ['date', 'libellé', 'valeur', 'opération']):
                continue

            # Try to extract date from first column
            date_str = str(row[0]).strip() if row[0] else ""
            try:
                op_date = datetime.strptime(date_str, '%d/%m/%Y').date()
            except:
                continue

            # Label from second column
            label = str(row[1]).strip() if len(row) > 1 and row[1] else ""

            # Value date from third column (if exists)
            value_date = None
            if len(row) > 2 and row[2]:
                try:
                    value_date = datetime.strptime(str(row[2]).strip(), '%d/%m/%Y').date()
                except:
                    pass

            # Amounts from debit/credit columns
            debit = 0.0
            credit = 0.0

            if len(row) > 3 and row[3]:
                debit_str = str(row[3]).replace(' ', '').replace(',', '.')
                try:
                    debit = float(debit_str)
                except:
                    pass

            if len(row) > 4 and row[4]:
                credit_str = str(row[4]).replace(' ', '').replace(',', '.')
                try:
                    credit = float(credit_str)
                except:
                    pass

            # Determine final amount
            if debit > 0:
                amount = -debit
                is_credit = False
            elif credit > 0:
                amount = credit
                is_credit = True
            else:
                continue

            if label:
                # Clean the merchant label (add spaces between concatenated words)
                label = self.clean_merchant_label(label)

                tx = PDFTransaction(
                    date_op=op_date,
                    label=label,
                    amount=amount,
                    date_value=value_date,
                    is_credit=is_credit,
                    page_number=page_num
                )
                transactions.append(tx)

        return transactions


class GenericPDFParser:
    """
    Generic PDF parser that tries to extract transactions
    using pattern matching on text content
    """

    DATE_PATTERNS = [
        r'(\d{2}/\d{2}/\d{4})',
        r'(\d{2}/\d{2}/\d{2})',
        r'(\d{4}-\d{2}-\d{2})',
    ]

    AMOUNT_PATTERN = r'(-?\d[\d\s]*[,\.]\d{2})\s*[€$]?'

    def parse_text(self, text: str, page_num: int) -> List[PDFTransaction]:
        """Generic text parsing for unknown bank formats"""
        transactions = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue

            # Try to find a date
            date_match = None
            for pattern in self.DATE_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    date_match = match
                    break

            if not date_match:
                continue

            # Try to parse the date
            date_str = date_match.group(1)
            op_date = None
            for fmt in ['%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d']:
                try:
                    op_date = datetime.strptime(date_str, fmt).date()
                    break
                except:
                    continue

            if not op_date:
                continue

            # Find amounts in line
            amounts = re.findall(self.AMOUNT_PATTERN, line)
            if not amounts:
                continue

            # Clean and convert amounts
            amount_values = []
            for a in amounts:
                a_clean = a.replace(' ', '').replace(',', '.')
                try:
                    amount_values.append(float(a_clean))
                except:
                    pass

            if not amount_values:
                continue

            # Extract label (text between date and amount)
            label_start = date_match.end()
            label = line[label_start:].strip()

            # Remove amount from label
            for a in amounts:
                label = label.replace(a, '').strip()

            # Take the last amount as the transaction amount
            amount = amount_values[-1]

            if label and amount != 0:
                tx = PDFTransaction(
                    date_op=op_date,
                    label=label,
                    amount=amount,
                    page_number=page_num,
                    raw_line=line
                )
                transactions.append(tx)

        return transactions


class PDFBankStatementParser:
    """
    Main PDF parser that coordinates bank-specific parsers
    """

    def __init__(self):
        self.boursobank_parser = BoursobankParser()
        self.generic_parser = GenericPDFParser()

    def detect_bank(self, text: str) -> str:
        """Detect bank from PDF content"""
        text_lower = text.lower()

        if any(x in text_lower for x in ['boursobank', 'boursorama', 'bousfrpp', '40618']):
            return 'boursobank'
        elif any(x in text_lower for x in ['lcl ', 'credit lyonnais']):
            return 'lcl'
        elif any(x in text_lower for x in ['societe generale', 'sg ']):
            return 'societe_generale'
        elif any(x in text_lower for x in ['bnp ', 'paribas']):
            return 'bnp'
        elif any(x in text_lower for x in ['credit agricole']):
            return 'credit_agricole'
        elif any(x in text_lower for x in ['fortuneo']):
            return 'fortuneo'
        else:
            return 'generic'

    def parse(self, content: bytes, filename: str) -> 'ParseResult':
        """Parse PDF bank statement"""
        from services.smart_parser import ParseResult, ColumnMapping, ParsedTransaction, FileFormat, BankSource

        if not HAS_PDFPLUMBER:
            return ParseResult(
                success=False,
                file_format=FileFormat.PDF,
                bank_source=BankSource.UNKNOWN,
                column_mapping=ColumnMapping(),
                transactions=[],
                raw_columns=[],
                sample_data=[],
                errors=["pdfplumber n'est pas installé. Installez-le avec: pip install pdfplumber"]
            )

        transactions = []
        all_text = ""
        errors = []
        warnings = []
        metadata = {}

        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                metadata['page_count'] = len(pdf.pages)
                logger.info(f"PDF has {len(pdf.pages)} pages")

                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text
                    page_text = page.extract_text() or ""
                    all_text += page_text + "\n"
                    logger.info(f"Page {page_num}: extracted {len(page_text)} chars of text")

                    # Try to extract tables
                    tables = page.extract_tables()
                    logger.info(f"Page {page_num}: found {len(tables) if tables else 0} tables")

                    if tables:
                        # Use table extraction (more reliable)
                        for table_idx, table in enumerate(tables):
                            if table and len(table) > 1:
                                logger.info(f"Page {page_num}, Table {table_idx}: {len(table)} rows")
                                # Log first few rows for debug
                                for row in table[:3]:
                                    logger.debug(f"  Row sample: {row}")
                                bank = self.detect_bank(page_text)
                                if bank == 'boursobank':
                                    page_txs = self.boursobank_parser.parse_table(table, page_num)
                                else:
                                    # Generic table parsing
                                    page_txs = self.boursobank_parser.parse_table(table, page_num)
                                logger.info(f"  -> Extracted {len(page_txs)} transactions from table")
                                transactions.extend(page_txs)

                    # Always try text parsing as well (tables might not be detected)
                    bank = self.detect_bank(page_text)
                    logger.info(f"Page {page_num}: detected bank = {bank}")
                    if bank == 'boursobank':
                        page_txs = self.boursobank_parser.parse_page_text(page_text, page_num)
                    else:
                        page_txs = self.generic_parser.parse_text(page_text, page_num)
                    logger.info(f"Page {page_num}: text parsing found {len(page_txs)} transactions")
                    transactions.extend(page_txs)

        except Exception as e:
            errors.append(f"Erreur lecture PDF: {str(e)}")
            logger.error(f"PDF parsing error: {e}")

        # Detect bank from full text
        bank = self.detect_bank(all_text)
        bank_source = {
            'boursobank': BankSource.BOURSOBANK,
            'lcl': BankSource.LCL,
            'societe_generale': BankSource.SOCIETE_GENERALE,
            'bnp': BankSource.BNP,
            'credit_agricole': BankSource.CREDIT_AGRICOLE,
            'fortuneo': BankSource.FORTUNEO,
        }.get(bank, BankSource.GENERIC)

        # Convert PDFTransactions to ParsedTransactions
        parsed_transactions = []
        for tx in transactions:
            parsed_tx = ParsedTransaction(
                date_op=tx.date_op,
                label=tx.label,
                amount=tx.amount,
                date_value=tx.date_value,
                raw_data={
                    'page': tx.page_number,
                    'raw_line': tx.raw_line,
                    'is_credit': tx.is_credit
                }
            )
            parsed_transactions.append(parsed_tx)

        # Remove duplicates (same date, label, amount)
        seen = set()
        unique_transactions = []
        for tx in parsed_transactions:
            key = (tx.date_op, tx.label[:50], round(tx.amount, 2))
            if key not in seen:
                seen.add(key)
                unique_transactions.append(tx)

        # Create sample data
        sample_data = []
        for tx in unique_transactions[:5]:
            sample_data.append({
                'Date': tx.date_op.strftime('%d/%m/%Y') if tx.date_op else '',
                'Libellé': tx.label,
                'Montant': tx.amount
            })

        metadata['bank_detected'] = bank
        metadata['transactions_found'] = len(unique_transactions)
        metadata['duplicates_removed'] = len(transactions) - len(unique_transactions)

        return ParseResult(
            success=len(unique_transactions) > 0,
            file_format=FileFormat.PDF,
            bank_source=bank_source,
            column_mapping=ColumnMapping(
                date_column="Date opération",
                label_column="Libellé",
                debit_column="Débit",
                credit_column="Crédit"
            ),
            transactions=unique_transactions,
            raw_columns=['Date opération', 'Libellé', 'Valeur', 'Débit', 'Crédit'],
            sample_data=sample_data,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
