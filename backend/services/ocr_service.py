"""
OCR Service for Receipt Scanning
Budget Famille v4.1 - Intelligent Receipt Parser

Features:
- EasyOCR for text extraction (CPU mode, French support)
- EXIF auto-rotation for smartphone photos
- Smart parsing for French receipts (merchant, amount, date)
- Tag suggestion based on merchant name
"""

import re
import io
import logging
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path

logger = logging.getLogger(__name__)

# Lazy load EasyOCR to avoid slow startup
_ocr_reader = None
EASYOCR_AVAILABLE = False

try:
    from PIL import Image, ExifTags
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger.warning("Pillow not available - image processing disabled")


def get_ocr_reader():
    """Lazy load EasyOCR reader (singleton)"""
    global _ocr_reader, EASYOCR_AVAILABLE

    if _ocr_reader is None:
        try:
            import easyocr
            # Initialize with French and English, GPU disabled for CPU compatibility
            _ocr_reader = easyocr.Reader(['fr', 'en'], gpu=False, verbose=False)
            EASYOCR_AVAILABLE = True
            logger.info("EasyOCR initialized successfully (CPU mode)")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            EASYOCR_AVAILABLE = False
            return None

    return _ocr_reader


@dataclass
class ReceiptData:
    """Extracted data from a receipt"""
    merchant: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[str] = None  # Format YYYY-MM-DD
    raw_text: str = ""
    confidence: float = 0.0
    suggested_tag: Optional[str] = None
    all_amounts: List[float] = field(default_factory=list)
    extraction_details: Dict = field(default_factory=dict)


# Common French receipt patterns
MERCHANT_PATTERNS = [
    # Supermarkets
    (r'carrefour', 'courses'),
    (r'leclerc', 'courses'),
    (r'auchan', 'courses'),
    (r'lidl', 'courses'),
    (r'aldi', 'courses'),
    (r'intermarche', 'courses'),
    (r'super\s*u', 'courses'),
    (r'monoprix', 'courses'),
    (r'franprix', 'courses'),
    (r'casino', 'courses'),
    (r'picard', 'courses'),
    (r'biocoop', 'courses'),

    # Restaurants & Fast food
    (r'mcdonald', 'restaurant'),
    (r'burger\s*king', 'restaurant'),
    (r'kfc', 'restaurant'),
    (r'subway', 'restaurant'),
    (r'domino', 'restaurant'),
    (r'pizza', 'restaurant'),
    (r'restaurant', 'restaurant'),
    (r'brasserie', 'restaurant'),
    (r'cafe|café', 'restaurant'),
    (r'bistro', 'restaurant'),

    # Gas stations
    (r'total\s*energies', 'carburant'),
    (r'shell', 'carburant'),
    (r'bp\s', 'carburant'),
    (r'esso', 'carburant'),
    (r'avia', 'carburant'),
    (r'carburant', 'carburant'),
    (r'station\s*service', 'carburant'),

    # Pharmacies
    (r'pharmacie', 'sante'),
    (r'parapharmacie', 'sante'),

    # DIY stores
    (r'leroy\s*merlin', 'bricolage'),
    (r'castorama', 'bricolage'),
    (r'brico', 'bricolage'),
    (r'mr\s*bricolage', 'bricolage'),

    # Electronics
    (r'fnac', 'high-tech'),
    (r'darty', 'high-tech'),
    (r'boulanger', 'high-tech'),
    (r'apple', 'high-tech'),

    # Clothing
    (r'zara', 'vetements'),
    (r'h\s*&\s*m', 'vetements'),
    (r'kiabi', 'vetements'),
    (r'decathlon', 'sport'),
    (r'intersport', 'sport'),

    # Online
    (r'amazon', 'amazon'),
    (r'cdiscount', 'achats en ligne'),
]

# Amount patterns for French receipts
AMOUNT_PATTERNS = [
    r'total\s*(?:ttc|a\s*payer|du|euros?)?\s*[:\s]*(\d+[.,]\d{2})',
    r'(?:montant|somme)\s*(?:total|du|a\s*payer)?\s*[:\s]*(\d+[.,]\d{2})',
    r'a\s*payer\s*[:\s]*(\d+[.,]\d{2})',
    r'cb\s*[:\s]*(\d+[.,]\d{2})',
    r'carte\s*(?:bancaire)?\s*[:\s]*(\d+[.,]\d{2})',
    r'especes?\s*[:\s]*(\d+[.,]\d{2})',
    r'(\d+[.,]\d{2})\s*(?:euros?|eur|€)',
    r'€\s*(\d+[.,]\d{2})',
]

# Date patterns for French receipts
DATE_PATTERNS = [
    r'(\d{2})[/.-](\d{2})[/.-](\d{4})',  # DD/MM/YYYY
    r'(\d{2})[/.-](\d{2})[/.-](\d{2})',  # DD/MM/YY
    r'(\d{4})[/.-](\d{2})[/.-](\d{2})',  # YYYY-MM-DD
]


def fix_image_orientation(image: 'Image.Image') -> 'Image.Image':
    """
    Fix image orientation based on EXIF data.
    Smartphones often save images with rotation metadata.
    """
    try:
        # Get EXIF orientation tag
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break

        exif = image._getexif()
        if exif is None:
            return image

        orientation_value = exif.get(orientation)

        if orientation_value == 3:
            image = image.rotate(180, expand=True)
        elif orientation_value == 6:
            image = image.rotate(270, expand=True)
        elif orientation_value == 8:
            image = image.rotate(90, expand=True)

    except (AttributeError, KeyError, TypeError) as e:
        logger.debug(f"No EXIF orientation data: {e}")

    return image


def preprocess_image(image_bytes: bytes, max_size: int = 2000) -> Optional['Image.Image']:
    """
    Preprocess image for OCR:
    - Fix orientation from EXIF
    - Resize if too large (for faster processing)
    - Convert to RGB
    """
    if not PILLOW_AVAILABLE:
        logger.error("Pillow not available for image preprocessing")
        return None

    try:
        image = Image.open(io.BytesIO(image_bytes))

        # Fix orientation
        image = fix_image_orientation(image)

        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Resize if too large (preserving aspect ratio)
        width, height = image.size
        if max(width, height) > max_size:
            ratio = max_size / max(width, height)
            new_size = (int(width * ratio), int(height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            logger.debug(f"Image resized from {width}x{height} to {new_size}")

        return image

    except Exception as e:
        logger.error(f"Image preprocessing failed: {e}")
        return None


def extract_text_from_image(image: 'Image.Image') -> Tuple[str, float]:
    """
    Extract text from image using EasyOCR.
    Returns (extracted_text, average_confidence)
    """
    reader = get_ocr_reader()
    if reader is None:
        return "", 0.0

    try:
        # Convert PIL Image to numpy array
        import numpy as np
        image_array = np.array(image)

        # Run OCR
        results = reader.readtext(image_array)

        if not results:
            return "", 0.0

        # Combine all text blocks
        text_parts = []
        confidences = []

        for (bbox, text, confidence) in results:
            text_parts.append(text)
            confidences.append(confidence)

        full_text = "\n".join(text_parts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        logger.debug(f"OCR extracted {len(text_parts)} text blocks, avg confidence: {avg_confidence:.2f}")

        return full_text, avg_confidence

    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return "", 0.0


def extract_merchant(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract merchant name and suggest a tag.
    Returns (merchant_name, suggested_tag)
    """
    text_lower = text.lower()

    # Try to match known patterns
    for pattern, tag in MERCHANT_PATTERNS:
        if re.search(pattern, text_lower):
            # Try to extract the actual merchant name from first lines
            lines = text.strip().split('\n')
            merchant = None

            for line in lines[:5]:  # Check first 5 lines
                line_clean = line.strip()
                if len(line_clean) > 3 and re.search(pattern, line_clean.lower()):
                    merchant = line_clean
                    break

            if merchant is None and lines:
                # Use first non-empty line as merchant
                for line in lines[:3]:
                    if len(line.strip()) > 3:
                        merchant = line.strip()
                        break

            return merchant, tag

    # No pattern matched, try to get first significant line as merchant
    lines = text.strip().split('\n')
    for line in lines[:3]:
        line_clean = line.strip()
        # Skip lines that look like dates, amounts, or addresses
        if len(line_clean) > 3 and not re.match(r'^[\d/.-]+$', line_clean):
            if not re.search(r'\d+[.,]\d{2}', line_clean):
                return line_clean, None

    return None, None


def extract_amount(text: str) -> Tuple[Optional[float], List[float]]:
    """
    Extract the total amount from receipt text.
    Returns (main_amount, all_amounts_found)
    """
    text_lower = text.lower()
    all_amounts = []

    # Find all amounts in the text
    for pattern in AMOUNT_PATTERNS:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            try:
                # Handle French decimal format (comma)
                amount_str = match.replace(',', '.')
                amount = float(amount_str)
                if 0.01 <= amount <= 10000:  # Reasonable receipt range
                    all_amounts.append(amount)
            except ValueError:
                continue

    # Also find standalone amounts
    standalone_pattern = r'(\d+)[.,](\d{2})'
    for match in re.finditer(standalone_pattern, text):
        try:
            amount = float(f"{match.group(1)}.{match.group(2)}")
            if 0.01 <= amount <= 10000:
                all_amounts.append(amount)
        except ValueError:
            continue

    # Remove duplicates while preserving order
    seen = set()
    unique_amounts = []
    for amount in all_amounts:
        rounded = round(amount, 2)
        if rounded not in seen:
            seen.add(rounded)
            unique_amounts.append(rounded)

    # The total is usually the largest amount, or explicitly marked
    if unique_amounts:
        # Sort by value, take the largest
        main_amount = max(unique_amounts)
        return main_amount, sorted(unique_amounts, reverse=True)

    return None, []


def extract_date(text: str) -> Optional[str]:
    """
    Extract date from receipt text.
    Returns date in YYYY-MM-DD format.
    """
    today = date.today()

    for pattern in DATE_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                if len(match[0]) == 4:
                    # YYYY-MM-DD format
                    year, month, day = int(match[0]), int(match[1]), int(match[2])
                elif len(match[2]) == 4:
                    # DD/MM/YYYY format
                    day, month, year = int(match[0]), int(match[1]), int(match[2])
                else:
                    # DD/MM/YY format
                    day, month, year = int(match[0]), int(match[1]), int(match[2])
                    year = 2000 + year if year < 100 else year

                # Validate date
                if 1 <= day <= 31 and 1 <= month <= 12 and 2000 <= year <= today.year + 1:
                    parsed_date = date(year, month, day)
                    # Don't accept dates too far in the future
                    if parsed_date <= today + __import__('datetime').timedelta(days=7):
                        return parsed_date.isoformat()

            except (ValueError, TypeError):
                continue

    return None


def parse_receipt(image_bytes: bytes) -> ReceiptData:
    """
    Main function to parse a receipt image.

    Args:
        image_bytes: Raw image data (JPEG, PNG, etc.)

    Returns:
        ReceiptData with extracted information
    """
    result = ReceiptData()

    # Preprocess image
    image = preprocess_image(image_bytes)
    if image is None:
        result.extraction_details['error'] = "Image preprocessing failed"
        return result

    # Extract text
    raw_text, confidence = extract_text_from_image(image)
    result.raw_text = raw_text
    result.confidence = confidence

    if not raw_text:
        result.extraction_details['error'] = "No text extracted from image"
        return result

    # Extract merchant
    merchant, suggested_tag = extract_merchant(raw_text)
    result.merchant = merchant
    result.suggested_tag = suggested_tag

    # Extract amount
    amount, all_amounts = extract_amount(raw_text)
    result.amount = amount
    result.all_amounts = all_amounts

    # Extract date
    result.date = extract_date(raw_text)

    # Add extraction details
    result.extraction_details = {
        'text_length': len(raw_text),
        'lines_count': len(raw_text.split('\n')),
        'amounts_found': len(all_amounts),
        'ocr_available': EASYOCR_AVAILABLE,
    }

    logger.info(f"Receipt parsed: merchant={merchant}, amount={amount}, date={result.date}")

    return result


def is_ocr_available() -> bool:
    """Check if OCR is available"""
    return PILLOW_AVAILABLE and get_ocr_reader() is not None
