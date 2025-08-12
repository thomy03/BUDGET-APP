"""
Web Research Engine for Merchant Intelligence

This module implements automated web research capabilities to enrich
the merchant knowledge base with real-time information from various sources.
"""

import logging
import json
import re
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
import aiohttp
from urllib.parse import quote_plus
from sqlalchemy.orm import Session

from intelligence_system import WebResearchEngine, get_web_research_engine
from models.database import MerchantKnowledgeBase, ResearchCache

logger = logging.getLogger(__name__)


@dataclass
class ResearchResult:
    """Structured result from web research"""
    merchant_name: str
    business_type: Optional[str]
    category: Optional[str]
    location: Optional[Dict[str, str]]
    contact_info: Optional[Dict[str, str]]
    confidence_score: float
    sources: List[str]
    research_duration_ms: int
    quality_score: float


class WebSearchProvider:
    """Base class for web search providers"""
    
    def __init__(self, name: str, base_confidence: float = 0.5):
        self.name = name
        self.base_confidence = base_confidence
    
    async def search(self, query: str) -> Dict[str, Any]:
        """Perform search and return structured results"""
        raise NotImplementedError
    
    def extract_business_info(self, search_results: Dict) -> Dict[str, Any]:
        """Extract business information from search results"""
        raise NotImplementedError


class MockWebSearchProvider(WebSearchProvider):
    """Mock web search provider for development/testing"""
    
    def __init__(self):
        super().__init__("mock_search", 0.6)
    
    async def search(self, query: str) -> Dict[str, Any]:
        """Mock search implementation with realistic delays"""
        await asyncio.sleep(0.5)  # Simulate network delay
        
        # Generate mock results based on query patterns
        query_lower = query.lower()
        
        # Business type detection patterns
        business_patterns = {
            'restaurant': ['restaurant', 'brasserie', 'bistro', 'cafe', 'pizzeria'],
            'supermarket': ['supermarche', 'hypermarche', 'carrefour', 'leclerc', 'auchan', 'intermarche'],
            'pharmacy': ['pharmacie', 'parapharmacie'],
            'gas_station': ['station', 'essence', 'total', 'bp', 'shell', 'esso'],
            'bank': ['banque', 'credit', 'societe generale', 'bnp', 'lcl', 'caisse'],
            'insurance': ['assurance', 'axa', 'generali', 'allianz', 'maaf'],
            'telecommunications': ['orange', 'sfr', 'bouygues', 'free', 'telecom'],
            'clothing': ['vetement', 'mode', 'zara', 'h&m', 'uniqlo'],
            'electronics': ['fnac', 'darty', 'boulanger', 'electro'],
            'healthcare': ['medical', 'clinique', 'hopital', 'docteur']
        }
        
        detected_type = None
        detected_category = None
        
        for business_type, patterns in business_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                detected_type = business_type
                break
        
        # Generate mock location based on common French cities
        mock_locations = [
            {"city": "Paris", "country": "France", "region": "Île-de-France"},
            {"city": "Lyon", "country": "France", "region": "Auvergne-Rhône-Alpes"},
            {"city": "Marseille", "country": "France", "region": "Provence-Alpes-Côte d'Azur"},
            {"city": "Toulouse", "country": "France", "region": "Occitanie"},
            {"city": "Nantes", "country": "France", "region": "Pays de la Loire"}
        ]
        
        import random
        mock_location = random.choice(mock_locations)
        
        # Category mapping
        category_mapping = {
            'restaurant': 'food_service',
            'supermarket': 'grocery_retail',
            'pharmacy': 'healthcare_retail',
            'gas_station': 'automotive_fuel',
            'bank': 'financial_services',
            'insurance': 'insurance_services',
            'telecommunications': 'telecom_services',
            'clothing': 'fashion_retail',
            'electronics': 'electronics_retail',
            'healthcare': 'medical_services'
        }
        
        detected_category = category_mapping.get(detected_type, 'general_retail')
        
        return {
            'business_type': detected_type,
            'category': detected_category,
            'location': mock_location,
            'contact_info': {
                'website': f"https://www.{query.replace(' ', '-').lower()}.fr",
                'phone': f"0{random.randint(1, 9)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)}"
            },
            'description': f"Mock business information for {query}",
            'confidence': 0.7 if detected_type else 0.3,
            'sources': ['mock_web_search', 'mock_business_directory'],
            'quality_score': 0.6
        }
    
    def extract_business_info(self, search_results: Dict) -> Dict[str, Any]:
        """Extract business information from mock search results"""
        return search_results


class GoogleSearchProvider(WebSearchProvider):
    """Google search provider (requires API key)"""
    
    def __init__(self, api_key: str, search_engine_id: str):
        super().__init__("google_search", 0.8)
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"
    
    async def search(self, query: str) -> Dict[str, Any]:
        """Perform Google Custom Search"""
        params = {
            'key': self.api_key,
            'cx': self.search_engine_id,
            'q': f"{query} France business",
            'num': 5,
            'fields': 'items(title,snippet,link,pagemap)'
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self.extract_business_info(data)
                    else:
                        logger.warning(f"Google search failed with status {response.status}")
                        return {}
            except Exception as e:
                logger.error(f"Google search error: {e}")
                return {}
    
    def extract_business_info(self, search_results: Dict) -> Dict[str, Any]:
        """Extract business information from Google search results"""
        items = search_results.get('items', [])
        
        business_info = {
            'business_type': None,
            'category': None,
            'location': {},
            'contact_info': {},
            'description': '',
            'confidence': 0.0,
            'sources': ['google_search'],
            'quality_score': 0.0
        }
        
        # Analyze snippets for business information
        all_text = ' '.join([item.get('snippet', '') for item in items])
        
        # Business type detection
        business_keywords = {
            'restaurant': ['restaurant', 'cuisine', 'menu', 'chef'],
            'retail': ['magasin', 'boutique', 'vente', 'shopping'],
            'service': ['service', 'conseil', 'expertise', 'professionnel'],
            'healthcare': ['médical', 'santé', 'pharmacie', 'clinique']
        }
        
        for btype, keywords in business_keywords.items():
            if any(keyword in all_text.lower() for keyword in keywords):
                business_info['business_type'] = btype
                business_info['confidence'] += 0.3
                break
        
        # Extract contact information from structured data
        for item in items:
            pagemap = item.get('pagemap', {})
            
            # Extract organization info
            organizations = pagemap.get('organization', [])
            for org in organizations:
                if 'url' in org:
                    business_info['contact_info']['website'] = org['url']
                if 'telephone' in org:
                    business_info['contact_info']['phone'] = org['telephone']
            
            # Extract local business info
            local_businesses = pagemap.get('localbusiness', [])
            for business in local_businesses:
                if 'addresslocality' in business:
                    business_info['location']['city'] = business['addresslocality']
                if 'addresscountry' in business:
                    business_info['location']['country'] = business['addresscountry']
        
        # Calculate quality score
        quality_factors = [
            business_info['business_type'] is not None,
            bool(business_info['location']),
            bool(business_info['contact_info']),
            len(items) > 0
        ]
        business_info['quality_score'] = sum(quality_factors) / len(quality_factors)
        
        return business_info


class IntelligentWebResearcher:
    """Main web research orchestrator"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cache_engine = get_web_research_engine(db)
        
        # Initialize search providers
        self.providers = [
            MockWebSearchProvider()  # Always available for testing
        ]
        
        # Add Google provider if API keys are available
        google_api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
        google_search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        
        if google_api_key and google_search_engine_id:
            self.providers.append(
                GoogleSearchProvider(google_api_key, google_search_engine_id)
            )
            logger.info("Google Search provider enabled")
    
    async def research_merchant(
        self, 
        merchant_name: str,
        force_refresh: bool = False
    ) -> ResearchResult:
        """Research a merchant using multiple sources"""
        start_time = time.time()
        
        # Check cache first
        if not force_refresh:
            cached_result = self.cache_engine.get_cached_research(merchant_name)
            if cached_result:
                logger.info(f"Using cached research for: {merchant_name}")
                return self._build_research_result(
                    merchant_name, cached_result, 
                    int((time.time() - start_time) * 1000)
                )
        
        # Perform new research
        logger.info(f"Starting web research for: {merchant_name}")
        
        # Prepare search query
        search_query = self._prepare_search_query(merchant_name)
        
        # Research with multiple providers
        research_results = []
        for provider in self.providers:
            try:
                logger.info(f"Searching with {provider.name}...")
                result = await provider.search(search_query)
                if result:
                    result['provider'] = provider.name
                    result['provider_confidence'] = provider.base_confidence
                    research_results.append(result)
            except Exception as e:
                logger.error(f"Error with provider {provider.name}: {e}")
        
        # Combine and analyze results
        combined_result = self._combine_research_results(research_results)
        
        # Calculate research duration
        duration_ms = int((time.time() - start_time) * 1000)
        combined_result['research_duration_ms'] = duration_ms
        
        # Cache the results
        self.cache_engine.cache_research_results(
            search_term=merchant_name,
            results=combined_result,
            confidence=combined_result.get('confidence', 0.5),
            sources_count=len(combined_result.get('sources', [])),
            duration_ms=duration_ms
        )
        
        return self._build_research_result(merchant_name, combined_result, duration_ms)
    
    def _prepare_search_query(self, merchant_name: str) -> str:
        """Prepare optimized search query"""
        # Clean up merchant name
        cleaned_name = re.sub(r'[^\w\s]', ' ', merchant_name)
        cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()
        
        # Remove common noise words
        noise_words = ['CB', 'CARTE', 'SARL', 'SAS', 'SA', 'SASU', 'EURL']
        words = cleaned_name.split()
        filtered_words = [w for w in words if w.upper() not in noise_words]
        
        return ' '.join(filtered_words)
    
    def _combine_research_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Combine results from multiple providers"""
        if not results:
            return {
                'business_type': None,
                'category': None,
                'location': {},
                'contact_info': {},
                'description': 'No research results available',
                'confidence': 0.1,
                'sources': [],
                'quality_score': 0.0
            }
        
        # Initialize combined result
        combined = {
            'business_type': None,
            'category': None,
            'location': {},
            'contact_info': {},
            'description': '',
            'confidence': 0.0,
            'sources': [],
            'quality_score': 0.0
        }
        
        # Combine information with confidence weighting
        total_confidence = 0
        for result in results:
            weight = result.get('provider_confidence', 0.5)
            total_confidence += weight
            
            # Business type - use highest confidence
            if result.get('business_type') and (
                combined['business_type'] is None or 
                result.get('confidence', 0) > combined.get('type_confidence', 0)
            ):
                combined['business_type'] = result['business_type']
                combined['type_confidence'] = result.get('confidence', 0)
            
            # Category
            if result.get('category') and not combined['category']:
                combined['category'] = result['category']
            
            # Location - merge information
            if result.get('location'):
                combined['location'].update(result['location'])
            
            # Contact info - merge
            if result.get('contact_info'):
                combined['contact_info'].update(result['contact_info'])
            
            # Sources
            combined['sources'].extend(result.get('sources', []))
            combined['sources'] = list(set(combined['sources']))  # Remove duplicates
            
            # Quality score - weighted average
            combined['quality_score'] += result.get('quality_score', 0) * weight
        
        # Calculate final confidence and quality
        if total_confidence > 0:
            combined['confidence'] = min(total_confidence / len(results), 1.0)
            combined['quality_score'] /= total_confidence
        
        # Generate description
        business_type = combined.get('business_type', 'business')
        location = combined.get('location', {}).get('city', 'Unknown location')
        combined['description'] = f"Automated research suggests this is a {business_type} located in {location}"
        
        return combined
    
    def _build_research_result(
        self, 
        merchant_name: str, 
        research_data: Dict, 
        duration_ms: int
    ) -> ResearchResult:
        """Build structured research result"""
        return ResearchResult(
            merchant_name=merchant_name,
            business_type=research_data.get('business_type'),
            category=research_data.get('category'),
            location=research_data.get('location'),
            contact_info=research_data.get('contact_info'),
            confidence_score=research_data.get('confidence', 0.0),
            sources=research_data.get('sources', []),
            research_duration_ms=duration_ms,
            quality_score=research_data.get('quality_score', 0.0)
        )
    
    async def batch_research_merchants(
        self, 
        merchant_names: List[str],
        max_concurrent: int = 3
    ) -> List[ResearchResult]:
        """Research multiple merchants concurrently"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def research_with_semaphore(merchant_name: str) -> ResearchResult:
            async with semaphore:
                return await self.research_merchant(merchant_name)
        
        tasks = [research_with_semaphore(name) for name in merchant_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log errors
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Research failed for {merchant_names[i]}: {result}")
            else:
                valid_results.append(result)
        
        return valid_results


# Utility functions for integration

import os

def create_web_researcher(db: Session) -> IntelligentWebResearcher:
    """Create web researcher instance"""
    return IntelligentWebResearcher(db)


async def research_unknown_merchants(db: Session, limit: int = 10) -> Dict[str, Any]:
    """Research merchants with low confidence scores"""
    # Find merchants needing research
    merchants_needing_research = db.query(MerchantKnowledgeBase).filter(
        MerchantKnowledgeBase.confidence_score < 0.5,
        MerchantKnowledgeBase.needs_review == True
    ).limit(limit).all()
    
    if not merchants_needing_research:
        return {
            "message": "No merchants need research",
            "processed": 0,
            "results": []
        }
    
    # Research merchants
    researcher = create_web_researcher(db)
    merchant_names = [m.merchant_name for m in merchants_needing_research]
    
    results = await researcher.batch_research_merchants(merchant_names)
    
    # Update merchants with research results
    updated_count = 0
    for result in results:
        merchant = db.query(MerchantKnowledgeBase).filter(
            MerchantKnowledgeBase.merchant_name == result.merchant_name
        ).first()
        
        if merchant:
            # Update with research results
            merchant.business_type = result.business_type
            merchant.category = result.category
            merchant.confidence_score = result.confidence_score
            merchant.research_quality = result.quality_score
            merchant.research_date = datetime.now()
            merchant.research_duration_ms = result.research_duration_ms
            merchant.needs_review = result.confidence_score < 0.5
            
            # Update location and contact info
            if result.location:
                merchant.city = result.location.get('city')
                merchant.country = result.location.get('country', 'France')
                merchant.address = result.location.get('address')
            
            if result.contact_info:
                merchant.website_url = result.contact_info.get('website')
                merchant.phone_number = result.contact_info.get('phone')
            
            # Update data sources
            sources_data = {source: 0.7 for source in result.sources}
            merchant.data_sources = json.dumps(sources_data)
            
            updated_count += 1
    
    db.commit()
    
    logger.info(f"Researched and updated {updated_count} merchants")
    
    return {
        "message": f"Successfully researched {updated_count} merchants",
        "processed": updated_count,
        "results": [
            {
                "merchant_name": r.merchant_name,
                "business_type": r.business_type,
                "confidence_score": r.confidence_score,
                "research_duration_ms": r.research_duration_ms
            }
            for r in results
        ]
    }


logger.info("Web research engine initialized successfully")