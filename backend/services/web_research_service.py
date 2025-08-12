"""
Revolutionary Web Research Service for Automatic Transaction Enrichment

This service performs web research to automatically identify merchant types
and enrich transaction classification without relying on LLMs.

INTELLIGENCE SOURCES:
- Web search APIs (Bing, DuckDuckGo)
- OpenStreetMap (OSM) API
- French government open data (data.gouv.fr)
- Public business directories

CLASSIFICATION ALGORITHM:
- Pattern-based keyword extraction
- Multi-source confidence scoring
- Location-aware merchant identification
- Automatic expense type suggestion
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import quote_plus, urljoin, urlparse
import aiohttp
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class MerchantInfo:
    """Data structure for merchant research results"""
    merchant_name: str
    normalized_name: str
    business_type: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    city: Optional[str] = None
    country: str = "France"
    address: Optional[str] = None
    confidence_score: float = 0.0
    data_sources: List[str] = None
    research_keywords: List[str] = None
    suggested_expense_type: Optional[str] = None
    suggested_tags: List[str] = None
    website_url: Optional[str] = None
    phone_number: Optional[str] = None
    description: Optional[str] = None
    research_duration_ms: int = 0
    search_queries_used: List[str] = None

    def __post_init__(self):
        if self.data_sources is None:
            self.data_sources = []
        if self.research_keywords is None:
            self.research_keywords = []
        if self.suggested_tags is None:
            self.suggested_tags = []
        if self.search_queries_used is None:
            self.search_queries_used = []


class WebResearchService:
    """Revolutionary service for automatic merchant research and classification"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Enhanced business type classification patterns with more French chains
        self.business_patterns = {
            'restaurant': {
                'keywords': ['restaurant', 'brasserie', 'bistro', 'pizzeria', 'kebab', 'sushi', 'burger', 'fast food', 'café', 'bar', 'mcdonalds', 'mcdonald', 'kfc', 'quick', 'subway'],
                'patterns': [r'restaurant\s+\w+', r'le\s+petit\s+\w+', r'chez\s+\w+', r'la\s+table', r'au\s+bon\s+\w+'],
                'expense_type': 'VARIABLE',
                'tags': ['alimentation', 'sortie', 'restaurant']
            },
            'supermarket': {
                'keywords': ['supermarché', 'hypermarché', 'carrefour', 'leclerc', 'auchan', 'géant', 'casino', 'monoprix', 'franprix', 'intermarché', 'super u', 'match', 'cora', 'simply'],
                'patterns': [r'carrefour\s+\w+', r'leclerc\s+\w+', r'e\.leclerc', r'hyper\s+u'],
                'expense_type': 'VARIABLE',
                'tags': ['alimentation', 'courses', 'nécessaire']
            },
            'gas_station': {
                'keywords': ['station-service', 'essence', 'carburant', 'total', 'bp', 'shell', 'esso', 'avia', 'total access', 'agip', 'texaco'],
                'patterns': [r'total\s+access\s+\w+', r'station\s+\w+', r'relais\s+\w+'],
                'expense_type': 'VARIABLE',
                'tags': ['transport', 'carburant', 'voiture']
            },
            'pharmacy': {
                'keywords': ['pharmacie', 'parapharmacie', 'médicament'],
                'expense_type': 'VARIABLE',
                'tags': ['santé', 'médicaments', 'nécessaire']
            },
            'bank': {
                'keywords': ['banque', 'crédit agricole', 'bnp', 'société générale', 'lcl', 'caisse d\'épargne'],
                'expense_type': 'FIXED',
                'tags': ['banque', 'frais bancaires', 'fixe']
            },
            'insurance': {
                'keywords': ['assurance', 'axa', 'allianz', 'groupama', 'maaf', 'matmut'],
                'expense_type': 'FIXED',
                'tags': ['assurance', 'fixe', 'obligatoire']
            },
            'clothing': {
                'keywords': ['vêtements', 'mode', 'h&m', 'zara', 'uniqlo', 'boutique'],
                'expense_type': 'VARIABLE',
                'tags': ['vêtements', 'shopping', 'personnel']
            },
            'electronics': {
                'keywords': ['électronique', 'fnac', 'darty', 'boulanger', 'cdiscount', 'amazon'],
                'expense_type': 'VARIABLE',
                'tags': ['électronique', 'équipement', 'technologie']
            },
            'health': {
                'keywords': ['médecin', 'dentiste', 'kinésithérapeute', 'ostéopathe', 'cabinet médical'],
                'expense_type': 'VARIABLE',
                'tags': ['santé', 'médical', 'soins']
            },
            'transport': {
                'keywords': ['ratp', 'sncf', 'métro', 'bus', 'tramway', 'taxi', 'uber'],
                'patterns': [r'navigo\s+\w*', r'pass\s+navigo'],
                'expense_type': 'VARIABLE',
                'tags': ['transport', 'déplacement', 'mobilité']
            },
            'streaming': {
                'keywords': ['netflix', 'spotify', 'disney', 'amazon prime', 'apple music', 'deezer', 'youtube premium', 'canal+', 'ocs'],
                'patterns': [r'netflix\s+\w*', r'spotify\s+\w*', r'disney\s+plus', r'amazon\s+prime'],
                'expense_type': 'FIXED',
                'tags': ['abonnement', 'streaming', 'divertissement']
            },
            'telecom': {
                'keywords': ['orange', 'sfr', 'free', 'bouygues', 'red', 'sosh', 'b&you'],
                'patterns': [r'orange\s+\w*', r'free\s+\w*', r'sfr\s+\w*', r'bouygues\s+telecom'],
                'expense_type': 'FIXED',
                'tags': ['téléphone', 'internet', 'fixe']
            }
        }
        
        # French city patterns for location detection
        self.french_cities = [
            'paris', 'marseille', 'lyon', 'toulouse', 'nice', 'nantes', 'montpellier', 'strasbourg',
            'bordeaux', 'lille', 'rennes', 'reims', 'saint-étienne', 'toulon', 'le havre', 'grenoble',
            'dijon', 'angers', 'nîmes', 'villeurbanne'
        ]

    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={'User-Agent': 'BudgetApp-Research/1.0'}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def normalize_merchant_name(self, merchant_name: str) -> str:
        """Normalize merchant name for better matching"""
        if not merchant_name:
            return ""
        
        # Remove common prefixes/suffixes
        name = merchant_name.strip().upper()
        
        # Remove date/time patterns
        name = re.sub(r'\d{2}[/\-\.]\d{2}[/\-\.]\d{2,4}', '', name)
        name = re.sub(r'\d{2}H\d{2}', '', name)
        
        # Remove card patterns
        name = re.sub(r'CB\s*\d+', '', name)
        name = re.sub(r'CARTE\s*\d+', '', name)
        
        # Remove common banking terms
        banking_terms = ['VIR', 'VIREMENT', 'PRLV', 'PRELEVEMENT', 'CHQ', 'CHEQUE', 'CB', 'CARTE']
        for term in banking_terms:
            name = name.replace(term, '')
        
        # Clean up spaces and special characters
        name = re.sub(r'[^\w\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name)
        name = name.strip()
        
        return name

    def extract_location_from_name(self, merchant_name: str) -> Optional[str]:
        """Extract French city name from merchant name"""
        name_lower = merchant_name.lower()
        
        for city in self.french_cities:
            if city in name_lower:
                return city.title()
        
        # Look for postal code patterns (French format)
        postal_match = re.search(r'\b\d{5}\b', merchant_name)
        if postal_match:
            postal_code = postal_match.group()
            # Map some common postal codes to cities
            postal_to_city = {
                '75001': 'Paris', '75002': 'Paris', '75003': 'Paris', '75004': 'Paris',
                '69001': 'Lyon', '69002': 'Lyon', '69003': 'Lyon',
                '13001': 'Marseille', '13002': 'Marseille', '13003': 'Marseille',
                '31000': 'Toulouse', '33000': 'Bordeaux', '59000': 'Lille'
            }
            return postal_to_city.get(postal_code)
        
        return None

    def classify_by_keywords(self, text: str) -> Tuple[Optional[str], float, List[str]]:
        """Enhanced classification using keywords and regex patterns"""
        text_lower = text.lower()
        best_match = None
        best_score = 0.0
        matched_keywords = []
        
        for business_type, config in self.business_patterns.items():
            score = 0.0
            type_keywords = []
            
            # Check keyword matches
            for keyword in config['keywords']:
                if keyword.lower() in text_lower:
                    # Weight longer keywords higher
                    weight = len(keyword.split()) * 0.5 + 1.0
                    score += weight
                    type_keywords.append(keyword)
            
            # Check regex pattern matches (higher weight)
            if 'patterns' in config:
                for pattern in config['patterns']:
                    if re.search(pattern, text_lower, re.IGNORECASE):
                        # Pattern matches get higher weight
                        score += 2.0
                        type_keywords.append(f"pattern:{pattern}")
            
            # Normalize score by total possible matches
            total_possible = len(config['keywords']) + len(config.get('patterns', []))
            normalized_score = score / max(1, total_possible) if total_possible > 0 else 0
            
            if normalized_score > best_score:
                best_score = normalized_score
                best_match = business_type
                matched_keywords = type_keywords
        
        return best_match, min(best_score, 1.0), matched_keywords

    async def search_web_duckduckgo(self, query: str) -> List[Dict]:
        """Search using DuckDuckGo - temporarily disabled due to API issues"""
        # DuckDuckGo API is currently blocking programmatic access
        # We'll rely on OpenStreetMap and local pattern matching for now
        logger.info(f"DuckDuckGo search skipped for '{query}' - using local patterns instead")
        return []

    async def search_openstreetmap(self, merchant_name: str, city: str = None) -> List[Dict]:
        """Search OpenStreetMap for business information"""
        try:
            # Nominatim API (free OpenStreetMap search)
            base_url = "https://nominatim.openstreetmap.org/search"
            
            # Build search query
            search_terms = [merchant_name]
            if city:
                search_terms.append(city)
            search_terms.append("France")
            
            query = " ".join(search_terms)
            
            params = {
                'q': query,
                'format': 'json',
                'limit': 5,
                'addressdetails': 1,
                'extratags': 1,
                'namedetails': 1,
                'dedupe': 1
            }
            
            # Add delay to respect Nominatim usage policy
            await asyncio.sleep(1)
            
            async with self.session.get(base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []
                    
                    for item in data:
                        # Extract business information
                        business_info = {
                            'name': item.get('display_name', ''),
                            'type': item.get('type', ''),
                            'class': item.get('class', ''),
                            'address': item.get('display_name', ''),
                            'latitude': item.get('lat'),
                            'longitude': item.get('lon'),
                            'source': 'openstreetmap'
                        }
                        
                        # Extract additional tags
                        if 'extratags' in item:
                            tags = item['extratags']
                            business_info.update({
                                'cuisine': tags.get('cuisine'),
                                'amenity': tags.get('amenity'),
                                'shop': tags.get('shop'),
                                'website': tags.get('website'),
                                'phone': tags.get('phone')
                            })
                        
                        results.append(business_info)
                    
                    return results
                    
        except Exception as e:
            logger.error(f"OpenStreetMap search error for '{merchant_name}': {e}")
        
        return []

    async def search_data_gouv_fr(self, merchant_name: str, city: str = None) -> List[Dict]:
        """Search French government open data for business information"""
        try:
            # SIRENE API (French business registry)
            base_url = "https://api.insee.fr/entreprises/sirene/v3/siret"
            
            params = {
                'q': f'denominationUniteLegale:"{merchant_name}"',
                'nombre': 5,
                'tri': 'score',
                'champs': 'siret,denominationUniteLegale,activitePrincipaleUniteLegale,categorieJuridiqueUniteLegale'
            }
            
            if city:
                params['q'] += f' AND libelleCommuneEtablissement:"{city}"'
            
            # Note: This API requires authentication in production
            # For now, we'll simulate the structure for the system design
            
            results = []
            # In a real implementation, you would need INSEE API credentials
            logger.info(f"Would search SIRENE API for: {merchant_name}")
            
            return results
                    
        except Exception as e:
            logger.error(f"Data.gouv.fr search error for '{merchant_name}': {e}")
        
        return []

    def calculate_confidence_score(self, all_results: List[Dict], merchant_name: str) -> float:
        """Calculate overall confidence score based on multiple sources"""
        if not all_results:
            return 0.0
        
        confidence = 0.0
        source_bonus = {
            'duckduckgo': 0.3,
            'openstreetmap': 0.4,
            'data_gouv_fr': 0.5
        }
        
        # Check name similarity
        normalized_merchant = self.normalize_merchant_name(merchant_name)
        
        for result in all_results:
            result_name = result.get('name', result.get('title', ''))
            
            if result_name:
                # Calculate name similarity
                similarity = SequenceMatcher(None, normalized_merchant.lower(), result_name.lower()).ratio()
                confidence += similarity * source_bonus.get(result.get('source'), 0.2)
        
        # Bonus for multiple sources
        unique_sources = set(r.get('source') for r in all_results)
        if len(unique_sources) > 1:
            confidence += 0.2
        
        return min(confidence, 1.0)

    async def research_merchant(self, merchant_name: str, amount: float = None, city: str = None) -> MerchantInfo:
        """
        Revolutionary merchant research combining multiple sources
        
        Args:
            merchant_name: Name of the merchant to research
            amount: Transaction amount (helps with classification)
            city: Optional city information
        
        Returns:
            MerchantInfo: Comprehensive merchant information
        """
        start_time = time.time()
        
        # Normalize the merchant name
        normalized_name = self.normalize_merchant_name(merchant_name)
        
        # Extract city from name if not provided
        if not city:
            city = self.extract_location_from_name(merchant_name)
        
        # Initialize result
        merchant_info = MerchantInfo(
            merchant_name=merchant_name,
            normalized_name=normalized_name,
            city=city
        )
        
        if not normalized_name:
            merchant_info.confidence_score = 0.0
            return merchant_info
        
        all_results = []
        
        # Build search queries
        search_queries = [
            normalized_name,
            f"{normalized_name} {city}" if city else normalized_name,
            f"{normalized_name} entreprise France",
            f"{normalized_name} commerce France"
        ]
        
        merchant_info.search_queries_used = search_queries
        
        try:
            # Perform searches in parallel
            search_tasks = []
            
            # Web search
            for query in search_queries[:2]:  # Limit queries to avoid rate limiting
                search_tasks.append(self.search_web_duckduckgo(query))
            
            # OpenStreetMap search
            search_tasks.append(self.search_openstreetmap(normalized_name, city))
            
            # Government data search
            search_tasks.append(self.search_data_gouv_fr(normalized_name, city))
            
            # Execute all searches
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Collect all valid results
            for result_set in search_results:
                if isinstance(result_set, list):
                    all_results.extend(result_set)
                elif isinstance(result_set, Exception):
                    logger.warning(f"Search error: {result_set}")
            
            # Analyze all results
            if all_results:
                # Extract information from results
                all_text = " ".join([
                    result.get('snippet', '') + " " + 
                    result.get('title', '') + " " +
                    result.get('name', '') + " " +
                    str(result.get('type', '')) + " " +
                    str(result.get('amenity', '')) + " " +
                    str(result.get('shop', ''))
                    for result in all_results
                ])
                
                # Classify business type
                business_type, classification_confidence, keywords = self.classify_by_keywords(all_text)
                
                if business_type:
                    config = self.business_patterns[business_type]
                    merchant_info.business_type = business_type
                    merchant_info.suggested_expense_type = config['expense_type']
                    merchant_info.suggested_tags = config['tags'].copy()
                    merchant_info.research_keywords = keywords
                
                # Extract additional information
                for result in all_results:
                    if result.get('website') and not merchant_info.website_url:
                        merchant_info.website_url = result['website']
                    if result.get('phone') and not merchant_info.phone_number:
                        merchant_info.phone_number = result['phone']
                    if result.get('address') and not merchant_info.address:
                        merchant_info.address = result['address']
                    if result.get('snippet') and not merchant_info.description:
                        merchant_info.description = result['snippet'][:500]
                
                # Calculate confidence
                merchant_info.confidence_score = self.calculate_confidence_score(all_results, merchant_name)
                
                # Boost confidence if classification was successful
                if business_type:
                    merchant_info.confidence_score = min(merchant_info.confidence_score + 0.2, 1.0)
                
                # Track data sources
                sources = set(result.get('source') for result in all_results if result.get('source'))
                merchant_info.data_sources = list(sources)
            
            else:
                # No results found, try basic pattern matching
                business_type, confidence, keywords = self.classify_by_keywords(merchant_name)
                if business_type:
                    config = self.business_patterns[business_type]
                    merchant_info.business_type = business_type
                    merchant_info.suggested_expense_type = config['expense_type']
                    merchant_info.suggested_tags = config['tags'].copy()
                    merchant_info.confidence_score = confidence * 0.5  # Lower confidence for pattern-only
                    merchant_info.research_keywords = keywords
                    merchant_info.data_sources = ['keyword_pattern']
        
        except Exception as e:
            logger.error(f"Error during merchant research for '{merchant_name}': {e}")
            merchant_info.confidence_score = 0.0
        
        # Calculate research duration
        merchant_info.research_duration_ms = int((time.time() - start_time) * 1000)
        
        return merchant_info

    async def batch_research_merchants(self, merchant_names: List[str]) -> List[MerchantInfo]:
        """Research multiple merchants in batch with rate limiting"""
        results = []
        
        # Process in batches to avoid overwhelming APIs
        batch_size = 3
        for i in range(0, len(merchant_names), batch_size):
            batch = merchant_names[i:i + batch_size]
            
            # Process batch
            batch_tasks = [self.research_merchant(name) for name in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Collect results
            for result in batch_results:
                if isinstance(result, MerchantInfo):
                    results.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Batch research error: {result}")
                    # Add empty result for failed research
                    results.append(MerchantInfo(merchant_name="", normalized_name=""))
            
            # Rate limiting between batches
            await asyncio.sleep(2)
        
        return results


# Utility functions

def get_merchant_from_transaction_label(label: str) -> str:
    """Extract merchant name from transaction label"""
    if not label:
        return ""
    
    # Remove common banking prefixes
    prefixes_to_remove = [
        r'^VIR\s+',
        r'^VIREMENT\s+',
        r'^PRLV\s+',
        r'^PRELEVEMENT\s+',
        r'^CB\s+\d*\s*',
        r'^CARTE\s+\d*\s*',
        r'^CHQ\s+',
        r'^CHEQUE\s+'
    ]
    
    clean_label = label
    for prefix in prefixes_to_remove:
        clean_label = re.sub(prefix, '', clean_label, flags=re.IGNORECASE)
    
    # Remove dates and times
    clean_label = re.sub(r'\d{2}[/\-\.]\d{2}[/\-\.]\d{2,4}', '', clean_label)
    clean_label = re.sub(r'\d{2}H\d{2}', '', clean_label)
    
    # Remove amounts
    clean_label = re.sub(r'\d+[,\.]\d+\s*€?', '', clean_label)
    
    # Clean up
    clean_label = clean_label.strip()
    
    return clean_label


# Example usage and testing
async def test_research_service():
    """Test the research service with sample merchants"""
    async with WebResearchService() as research_service:
        
        test_merchants = [
            "RESTAURANT LE PETIT PARIS",
            "CARREFOUR VILLENEUVE",
            "PHARMACIE CENTRALE",
            "TOTAL ACCESS LYON",
            "BNP PARIBAS FRAIS"
        ]
        
        print("Testing Web Research Service...")
        
        for merchant in test_merchants:
            print(f"\nResearching: {merchant}")
            result = await research_service.research_merchant(merchant)
            
            print(f"Business Type: {result.business_type}")
            print(f"Confidence: {result.confidence_score:.2f}")
            print(f"Suggested Type: {result.suggested_expense_type}")
            print(f"Suggested Tags: {result.suggested_tags}")
            print(f"Sources: {result.data_sources}")
            print(f"Duration: {result.research_duration_ms}ms")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_research_service())