"""
Pydantic schemas for Budget Famille v2.3
Shared data models for API requests/responses
"""
import datetime as dt
from typing import List, Optional, Dict, Union, Any
from pydantic import BaseModel, validator, Field
from email_validator import validate_email, EmailNotValidError

# Configuration Schemas
class ConfigIn(BaseModel):
    member1: str = Field(default="diana", description="Nom membre 1")
    member2: str = Field(default="thomas", description="Nom membre 2")
    rev1: float = Field(default=0.0, ge=0, description="Revenu membre 1")
    rev2: float = Field(default=0.0, ge=0, description="Revenu membre 2")
    split_mode: str = Field(default="revenus", pattern="^(revenus|manuel)$", description="Mode de répartition")
    split1: float = Field(default=0.5, ge=0, le=1, description="Split membre 1 (si manuel)")
    split2: float = Field(default=0.5, ge=0, le=1, description="Split membre 2 (si manuel)")
    other_split_mode: str = Field(default="clé", pattern="^(clé|50/50)$", description="Mode répartition autres")
    var_percent: float = Field(default=30.0, ge=0, le=100, description="Pourcentage variable sur revenus")
    max_var: float = Field(default=0.0, ge=0, description="Maximum variable")
    min_fixed: float = Field(default=0.0, ge=0, description="Minimum fixe")

    @validator('split1', 'split2')
    def validate_split(cls, v, values):
        if 'split1' in values and 'split2' in values:
            if abs(values.get('split1', 0) + v - 1.0) > 0.01:  # Allow small float errors
                raise ValueError('Les répartitions split1 et split2 doivent totaliser 1.0')
        return v

class ConfigOut(ConfigIn):
    id: int
    created_at: Optional[dt.datetime] = None
    updated_at: Optional[dt.datetime] = None

    class Config:
        from_attributes = True

# Transaction Schemas
class TxOut(BaseModel):
    id: int
    month: Optional[str]
    date_op: Optional[dt.date]
    date_valeur: Optional[dt.date]
    amount: Optional[float]
    label: Optional[str]
    category: Optional[str]
    subcategory: Optional[str]
    is_expense: Optional[bool]
    exclude: bool
    expense_type: str = Field(default="VARIABLE", pattern="^(FIXED|VARIABLE|PROVISION)$", description="Type de dépense pour séparation stricte")
    tags: List[str] = []

    class Config:
        from_attributes = True

class ExcludeIn(BaseModel):
    exclude: bool

class TagsIn(BaseModel):
    tags: Union[str, List[str]] = Field(
        description="Tags à associer à la transaction - accepte une string avec virgules ou un array de strings",
        example="urgent,personnel,impôts"
    )
    
    @validator('tags', pre=True)
    def normalize_tags(cls, v):
        """Normalize tags input to string format"""
        if isinstance(v, list):
            # Convert list to comma-separated string
            return ','.join([str(tag).strip() for tag in v if str(tag).strip()])
        elif isinstance(v, str):
            # Clean up the string
            return v.strip()
        elif v is None:
            return ""
        else:
            raise ValueError("Tags must be either a string or a list of strings")

# Schéma unifié pour PATCH /transactions/{id}
class TransactionUpdate(BaseModel):
    """Schéma unifié pour mettre à jour une transaction (exclude, tags, expense_type, ou combinaison)"""
    exclude: Optional[bool] = Field(
        None,
        description="Nouvelle valeur d'exclusion - true pour exclure la transaction des calculs"
    )
    tags: Optional[Union[str, List[str]]] = Field(
        None,
        description="Tags à associer à la transaction - accepte une string avec virgules ou un array de strings",
        example="urgent,personnel,impôts"
    )
    expense_type: Optional[str] = Field(
        None,
        pattern="^(FIXED|VARIABLE|PROVISION)$",
        description="Type de dépense - FIXED pour charges fixes, VARIABLE pour dépenses variables, PROVISION pour épargne"
    )
    
    @validator('tags', pre=True)
    def normalize_tags(cls, v):
        """Normalize tags input to string format"""
        if v is None:
            return None
        if isinstance(v, list):
            # Convert list to comma-separated string
            return ','.join([str(tag).strip() for tag in v if str(tag).strip()])
        elif isinstance(v, str):
            # Clean up the string
            return v.strip()
        else:
            raise ValueError("Tags must be either a string or a list of strings")
    
    class Config:
        schema_extra = {
            "example": {
                "exclude": False,
                "tags": "urgent,famille,alimentation",
                "expense_type": "VARIABLE"
            }
        }

# Schéma spécifique pour conversion de type de dépense
class ExpenseTypeConversion(BaseModel):
    """Schéma pour convertir le type d'une dépense entre FIXED, VARIABLE, PROVISION"""
    expense_type: str = Field(
        pattern="^(FIXED|VARIABLE|PROVISION)$",
        description="Nouveau type de dépense"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "expense_type": "FIXED"
            }
        }

# Fixed Lines Schemas
class FixedLineIn(BaseModel):
    label: str = Field(min_length=1, max_length=200, description="Libellé de la ligne fixe")
    amount: float = Field(description="Montant de la ligne fixe")
    freq: str = Field(pattern="^(mensuelle|trimestrielle|annuelle)$", description="Fréquence")
    split_mode: str = Field(default="clé", pattern="^(clé|50/50|m1|m2|manuel)$", description="Mode de répartition")
    split1: float = Field(default=50.0, ge=0, le=100, description="Répartition membre 1 (%)")
    split2: float = Field(default=50.0, ge=0, le=100, description="Répartition membre 2 (%)")
    category: str = Field(default="autres", pattern="^(logement|transport|services|loisirs|santé|autres)$", description="Catégorie")
    active: bool = Field(default=True, description="Ligne active")

    @validator('split1', 'split2')
    def validate_split_percentages(cls, v, values):
        if 'split1' in values and 'split2' in values:
            if abs(values.get('split1', 0) + v - 100) > 0.1:  # Allow small float errors
                raise ValueError('Les répartitions split1 et split2 doivent totaliser 100%')
        return v

class FixedLineOut(FixedLineIn):
    id: int

    class Config:
        from_attributes = True

# Custom Provisions Schemas
class CustomProvisionBase(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="Nom de la provision")
    description: Optional[str] = Field(None, max_length=500, description="Description détaillée")
    percentage: Optional[float] = Field(None, ge=0, le=100, description="Pourcentage du revenu de base")
    base_calculation: str = Field(default="total", pattern="^(total|member1|member2|fixed)$")
    fixed_amount: Optional[float] = Field(None, ge=0, description="Montant fixe si base_calculation = 'fixed'")
    split_mode: str = Field(default="key", pattern="^(key|50/50|custom|100/0|0/100)$")
    split_member1: float = Field(default=50.0, ge=0, le=100, description="Répartition membre 1 (%)")
    split_member2: float = Field(default=50.0, ge=0, le=100, description="Répartition membre 2 (%)")
    icon: str = Field(default="💰", max_length=10, description="Icône de la provision")
    color: str = Field(default="#3B82F6", pattern="^#[0-9A-Fa-f]{6}$", description="Couleur hexadécimale")
    display_order: int = Field(default=0, ge=0, description="Ordre d'affichage")
    is_active: bool = Field(default=True, description="Provision active")
    is_temporary: bool = Field(default=False, description="Provision temporaire")
    start_date: Optional[dt.date] = Field(None, description="Date de début (pour provisions temporaires)")
    end_date: Optional[dt.date] = Field(None, description="Date de fin (pour provisions temporaires)")
    target_amount: Optional[float] = Field(None, ge=0, description="Montant cible à atteindre")
    category: str = Field(default="épargne", max_length=50, description="Catégorie de la provision")

    @validator('split_member1', 'split_member2')
    def validate_split_percentages_provision(cls, v, values):
        if 'split_member1' in values and 'split_member2' in values:
            if abs(values.get('split_member1', 0) + v - 100) > 0.1:
                raise ValueError('Les répartitions split_member1 et split_member2 doivent totaliser 100%')
        return v

    @validator('end_date')
    def validate_end_date_after_start(cls, v, values):
        start_date = values.get('start_date')
        if start_date and v and v <= start_date:
            raise ValueError('La date de fin doit être postérieure à la date de début')
        return v

    @validator('fixed_amount')
    def validate_fixed_amount(cls, v, values):
        base_calc = values.get('base_calculation')
        if base_calc == 'fixed' and not v:
            raise ValueError('fixed_amount est requis quand base_calculation = "fixed"')
        return v

class CustomProvisionCreate(BaseModel):
    """Schema for creating custom provisions - very permissive for frontend compatibility"""
    name: str = Field(min_length=1, max_length=100, description="Nom de la provision")
    description: Optional[str] = Field(default=None, max_length=500, description="Description détaillée")
    percentage: Optional[float] = Field(default=None, ge=0, le=100, description="Pourcentage du revenu de base")
    base_calculation: Optional[str] = Field(default="total", pattern="^(total|member1|member2|fixed)$")
    fixed_amount: Optional[float] = Field(default=None, description="Montant fixe")
    split_mode: Optional[str] = Field(default="key", pattern="^(key|50/50|custom|100/0|0/100)$")
    split_member1: Optional[float] = Field(default=50.0, ge=0, le=100, description="Répartition membre 1 (%)")
    split_member2: Optional[float] = Field(default=50.0, ge=0, le=100, description="Répartition membre 2 (%)")
    icon: Optional[str] = Field(default="💰", max_length=10, description="Icône de la provision")
    color: Optional[str] = Field(default="#3B82F6", description="Couleur hexadécimale")
    display_order: Optional[int] = Field(default=0, ge=0, description="Ordre d'affichage")
    is_active: Optional[bool] = Field(default=True, description="Provision active")
    is_temporary: Optional[bool] = Field(default=False, description="Provision temporaire")
    start_date: Optional[dt.date] = Field(default=None, description="Date de début")
    end_date: Optional[dt.date] = Field(default=None, description="Date de fin")
    target_amount: Optional[float] = Field(default=None, description="Montant cible")
    category: Optional[str] = Field(default="épargne", max_length=50, description="Catégorie")
    
    @validator('color', pre=True, always=True)
    def validate_color(cls, v):
        if v and not str(v).startswith('#'):
            return f"#{v}"
        return v or "#3B82F6"
    
    @validator('fixed_amount', always=True)
    def validate_fixed_amount_create(cls, v, values):
        base_calc = values.get('base_calculation')
        if base_calc == 'fixed' and (v is None or v <= 0):
            raise ValueError('fixed_amount doit être > 0 quand base_calculation = "fixed"')
        return v

class CustomProvisionUpdate(BaseModel):
    name: Optional[str] = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(max_length=500)
    percentage: Optional[float] = Field(ge=0, le=100)
    base_calculation: Optional[str] = Field(pattern="^(total|member1|member2|fixed)$")
    fixed_amount: Optional[float] = Field(ge=0)
    split_mode: Optional[str] = Field(pattern="^(key|50/50|custom|100/0|0/100)$")
    split_member1: Optional[float] = Field(ge=0, le=100)
    split_member2: Optional[float] = Field(ge=0, le=100)
    icon: Optional[str] = Field(max_length=10)
    color: Optional[str] = Field(pattern="^#[0-9A-Fa-f]{6}$")
    display_order: Optional[int] = Field(ge=0)
    is_active: Optional[bool]
    is_temporary: Optional[bool]
    start_date: Optional[dt.date]
    end_date: Optional[dt.date]
    target_amount: Optional[float] = Field(ge=0)
    current_amount: Optional[float] = Field(ge=0)
    category: Optional[str] = Field(max_length=50)

class CustomProvisionResponse(CustomProvisionBase):
    id: int
    current_amount: float = Field(default=0.0, description="Montant actuellement épargné")
    created_at: dt.datetime
    updated_at: Optional[dt.datetime] = Field(default=None, description="Date de dernière modification")
    created_by: str
    monthly_amount: Optional[float] = Field(description="Montant mensuel calculé")
    progress_percentage: Optional[float] = Field(description="Pourcentage de progression vers l'objectif")

    class Config:
        from_attributes = True

class CustomProvisionSummary(BaseModel):
    total_active_provisions: int = Field(description="Nombre de provisions actives")
    total_monthly_amount: float = Field(description="Total des montants mensuels")
    total_target_amount: float = Field(description="Total des montants cibles")
    total_current_amount: float = Field(description="Total des montants actuels")
    average_progress_percentage: float = Field(description="Pourcentage moyen de progression")
    provisions_by_category: Dict[str, Dict[str, Union[int, float]]] = Field(description="Provisions par catégorie")

# Import/Export Schemas
class ImportMonth(BaseModel):
    month: str
    transaction_count: int
    date_range: Dict[str, Optional[str]]
    total_amount: float
    categories: List[str]

class ImportResponse(BaseModel):
    import_id: str
    status: str  # "success", "partial", "failed"
    filename: str
    rows_processed: int
    months_detected: List[ImportMonth]
    duplicates_info: Dict[str, Any]
    validation_errors: List[str]
    message: str

# Analytics Schemas
class MonthlyTrend(BaseModel):
    month: str
    total_expenses: float
    total_income: float
    net_balance: float
    expense_trend: float  # % change from previous month

class CategoryBreakdown(BaseModel):
    category: str
    amount: float
    percentage: float
    transaction_count: int
    avg_transaction: float

class KPISummary(BaseModel):
    total_income: float
    total_expenses: float
    net_balance: float
    savings_rate: float
    avg_monthly_expense: float
    expense_trend: float
    top_categories: List[CategoryBreakdown]
    months_analyzed: List[str]

class SpendingPattern(BaseModel):
    day_of_week: int  # 0 = Monday
    day_name: str
    avg_amount: float
    transaction_count: int

class AnomalyDetection(BaseModel):
    transaction_id: int
    date: str
    amount: float
    category: str
    label: str
    anomaly_type: str  # "high_amount", "unusual_category", etc.
    score: float  # 0-1 confidence score

class BudgetComparison(BaseModel):
    category: str
    budgeted_amount: float
    actual_amount: float
    variance: float
    variance_percentage: float

# Tag-to-Fixed Line Mapping Schemas
class TagFixedLineMappingBase(BaseModel):
    tag_name: str = Field(min_length=1, max_length=100, description="Nom du tag")
    fixed_line_id: int = Field(description="ID de la ligne fixe associée")
    label_pattern: Optional[str] = Field(None, max_length=200, description="Motif pour reconnaître les libellés")
    is_active: bool = Field(default=True, description="Mapping actif")

class TagFixedLineMappingCreate(TagFixedLineMappingBase):
    auto_created: Optional[bool] = Field(default=True, description="Créé automatiquement")
    created_by: Optional[str] = Field(None, max_length=50, description="Utilisateur créateur")

class TagFixedLineMappingUpdate(BaseModel):
    tag_name: Optional[str] = Field(None, min_length=1, max_length=100)
    fixed_line_id: Optional[int] = None
    label_pattern: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None

class TagFixedLineMappingResponse(TagFixedLineMappingBase):
    id: int
    auto_created: bool
    created_at: dt.datetime
    created_by: Optional[str]
    usage_count: int = Field(default=0, description="Nombre d'utilisations du mapping")
    last_used: Optional[dt.datetime] = Field(None, description="Dernière utilisation")
    
    # Include related fixed line information
    fixed_line: Optional[FixedLineOut] = None
    
    class Config:
        from_attributes = True

class TagAutomationStats(BaseModel):
    """Statistics for tag automation system"""
    total_mappings: int = Field(description="Nombre total de mappings actifs")
    auto_created_mappings: int = Field(description="Mappings créés automatiquement")
    manual_mappings: int = Field(description="Mappings créés manuellement")
    total_usage_count: int = Field(description="Nombre total d'utilisations")
    most_used_tags: List[dict] = Field(description="Tags les plus utilisés")
    recent_mappings: List[TagFixedLineMappingResponse] = Field(description="Mappings récents")

# Merchant Knowledge Base Schemas
class MerchantKnowledgeBaseCreate(BaseModel):
    merchant_name: str = Field(min_length=1, max_length=200, description="Nom du marchand")
    business_type: Optional[str] = Field(None, max_length=100, description="Type d'entreprise")
    category: Optional[str] = Field(None, max_length=100, description="Catégorie spécifique")
    sub_category: Optional[str] = Field(None, max_length=100, description="Sous-catégorie")
    expense_type: str = Field(default="VARIABLE", pattern="^(FIXED|VARIABLE|PROVISION)$")
    city: Optional[str] = Field(None, max_length=100, description="Ville")
    country: str = Field(default="France", max_length=50)
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Score de confiance")
    suggested_tags: Optional[str] = Field(None, max_length=500, description="Tags suggérés")
    description: Optional[str] = Field(None, description="Description du marchand")

class MerchantKnowledgeBaseUpdate(BaseModel):
    merchant_name: Optional[str] = Field(None, min_length=1, max_length=200)
    business_type: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    sub_category: Optional[str] = Field(None, max_length=100)
    expense_type: Optional[str] = Field(None, pattern="^(FIXED|VARIABLE|PROVISION)$")
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=50)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    suggested_tags: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None

class MerchantKnowledgeBaseResponse(BaseModel):
    id: int
    merchant_name: str
    normalized_name: str
    business_type: Optional[str]
    category: Optional[str]
    sub_category: Optional[str]
    expense_type: str
    city: Optional[str]
    country: str
    confidence_score: float
    data_sources: Optional[Dict[str, Any]] = None
    usage_count: int
    last_updated: dt.datetime
    last_used: Optional[dt.datetime]
    accuracy_rating: float
    user_corrections: int
    success_rate: float
    suggested_tags: Optional[str]
    description: Optional[str]
    created_at: dt.datetime
    created_by: str
    is_active: bool
    is_verified: bool
    needs_review: bool

    class Config:
        from_attributes = True

class MerchantSearchResult(BaseModel):
    id: int
    merchant_name: str
    normalized_name: str
    business_type: Optional[str]
    category: Optional[str]
    expense_type: str
    confidence_score: float
    similarity_score: float
    combined_score: float
    usage_count: int
    is_verified: bool
    last_used: Optional[str]
    suggested_tags: Optional[str]
    data_sources: Dict[str, Any] = {}
    accuracy_rating: float
    needs_review: bool

class MerchantValidationFeedback(BaseModel):
    type: str = Field(default="validation", description="Type de feedback")
    is_correct: bool = Field(description="La classification est-elle correcte?")
    corrections: Dict[str, Any] = Field(default_factory=dict, description="Corrections à apporter")
    
    class Config:
        schema_extra = {
            "example": {
                "type": "validation",
                "is_correct": False,
                "corrections": {
                    "business_type": "restaurant",
                    "expense_type": "VARIABLE"
                }
            }
        }

class MerchantKnowledgeStats(BaseModel):
    total_merchants: int
    verified_merchants: int
    needs_review: int
    confidence_distribution: Dict[str, int]
    business_type_distribution: List[Dict[str, Any]]
    expense_type_distribution: List[Dict[str, Any]]
    top_merchants: List[Dict[str, Any]]
    average_metrics: Dict[str, float]

class MerchantBulkImport(BaseModel):
    merchants: List[Dict[str, Any]] = Field(description="Liste des marchands à importer")
    source: str = Field(default="bulk_import", description="Source de l'import")

class MerchantBulkImportResponse(BaseModel):
    created: int
    updated: int
    errors: int
    total_processed: int
    message: str

# Research Cache Schemas
class ResearchCacheResponse(BaseModel):
    search_term: str
    research_results: Dict[str, Any]
    confidence_score: float
    result_quality: float
    sources_count: int
    created_at: dt.datetime
    last_used: Optional[dt.datetime]
    usage_count: int
    is_valid: bool
    
    class Config:
        from_attributes = True

# Tag Management Schemas
class TagOut(BaseModel):
    """Schema for tag information with statistics"""
    id: int
    name: str
    expense_type: str = Field(pattern="^(FIXED|VARIABLE|PROVISION)$", description="Type de dépense")
    transaction_count: int = Field(description="Nombre de transactions avec ce tag")
    total_amount: float = Field(description="Montant total des transactions")
    patterns: List[str] = Field(default_factory=list, description="Patterns de reconnaissance automatique")
    category: Optional[str] = Field(None, description="Catégorie du tag")
    created_at: dt.datetime
    last_used: Optional[dt.datetime] = Field(None, description="Dernière utilisation du tag")
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "name": "restaurant",
                "expense_type": "VARIABLE",
                "transaction_count": 15,
                "total_amount": 450.50,
                "patterns": ["CHEZ PAUL", "BISTROT"],
                "category": "Alimentation",
                "created_at": "2024-01-01T00:00:00",
                "last_used": "2024-08-12T12:00:00"
            }
        }

class TagUpdate(BaseModel):
    """Schema for updating a tag"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Nouveau nom du tag")
    expense_type: Optional[str] = Field(None, pattern="^(FIXED|VARIABLE|PROVISION)$", description="Nouveau type de dépense")
    patterns: Optional[List[str]] = Field(None, description="Nouveaux patterns de reconnaissance")
    category: Optional[str] = Field(None, max_length=100, description="Nouvelle catégorie")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "restaurant_updated",
                "expense_type": "VARIABLE",
                "patterns": ["RESTAURANT", "CHEZ", "BISTROT"],
                "category": "Alimentation"
            }
        }

class TagStats(BaseModel):
    """Schema for tag statistics"""
    transaction_count: int = Field(description="Nombre de transactions avec ce tag")
    total_amount: float = Field(description="Montant total des transactions")
    last_used: Optional[dt.datetime] = Field(None, description="Dernière utilisation")
    most_common_merchant: Optional[str] = Field(None, description="Marchand le plus fréquent")
    average_amount: float = Field(description="Montant moyen par transaction")
    monthly_frequency: float = Field(description="Fréquence mensuelle moyenne")
    
    class Config:
        schema_extra = {
            "example": {
                "transaction_count": 15,
                "total_amount": 450.50,
                "last_used": "2024-08-12T12:00:00",
                "most_common_merchant": "CHEZ PAUL",
                "average_amount": 30.03,
                "monthly_frequency": 5.0
            }
        }

class TagPatterns(BaseModel):
    """Schema for adding tag patterns"""
    patterns: List[str] = Field(description="Liste des patterns à ajouter pour reconnaissance automatique")
    
    @validator('patterns')
    def validate_patterns(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Au moins un pattern est requis')
        # Remove empty patterns and duplicates
        cleaned = list(set([p.strip().upper() for p in v if p.strip()]))
        if not cleaned:
            raise ValueError('Aucun pattern valide trouvé')
        return cleaned
    
    class Config:
        schema_extra = {
            "example": {
                "patterns": ["CHEZ PAUL", "RESTAURANT PAUL", "BISTROT PAUL"]
            }
        }

class TagDelete(BaseModel):
    """Schema for tag deletion options"""
    cascade: bool = Field(default=False, description="Si True, supprime le tag de toutes les transactions")
    
    class Config:
        schema_extra = {
            "example": {
                "cascade": False
            }
        }

class TagsListResponse(BaseModel):
    """Schema for tags list response"""
    tags: List[TagOut] = Field(description="Liste des tags avec leurs statistiques")
    total_count: int = Field(description="Nombre total de tags")
    stats: Dict[str, Any] = Field(description="Statistiques globales des tags")
    
    class Config:
        schema_extra = {
            "example": {
                "tags": [],
                "total_count": 25,
                "stats": {
                    "most_used_tags": ["restaurant", "essence", "courses"],
                    "total_transactions_tagged": 450,
                    "expense_type_distribution": {"VARIABLE": 20, "FIXED": 5}
                }
            }
        }

# Summary Schema - Compatible with frontend Dashboard
class SummaryOut(BaseModel):
    month: str
    var_total: float
    fixed_lines_total: float      # Total des lignes fixes personnalisables
    provisions_total: float       # Total des provisions personnalisables 
    r1: float
    r2: float
    member1: str
    member2: str
    total_p1: float
    total_p2: float
    detail: Dict[str, Any]
    
    # Nouveaux champs pour optimiser les calculs frontend
    var_p1: Optional[float] = None       # Part membre 1 des variables
    var_p2: Optional[float] = None       # Part membre 2 des variables
    fixed_p1: Optional[float] = None     # Part membre 1 des fixes
    fixed_p2: Optional[float] = None     # Part membre 2 des fixes
    provisions_p1: Optional[float] = None # Part membre 1 des provisions
    provisions_p2: Optional[float] = None # Part membre 2 des provisions
    grand_total: Optional[float] = None   # Total général (P1 + P2)
    
    # Métadonnées pour les calculs
    transaction_count: Optional[int] = None      # Nombre total de transactions
    active_fixed_lines: Optional[int] = None     # Nombre de lignes fixes actives
    active_provisions: Optional[int] = None      # Nombre de provisions actives
    
    # Totals object for unified structure
    totals: Optional[Dict[str, float]] = None    # Totals breakdown with total_expenses, total_fixed, total_variable

# Batch Auto-Tagging Schemas

class BatchAutoTagRequest(BaseModel):
    """Request schema for batch auto-tagging operations"""
    month: str = Field(description="Month to process in YYYY-MM format", pattern=r"^\d{4}-\d{2}$")
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum confidence threshold for auto-tagging")
    force_retag: bool = Field(default=False, description="Re-tag already tagged transactions")
    include_fixed_variable: bool = Field(default=True, description="Include expense type classification")
    use_web_research: bool = Field(default=False, description="Enable web research for unknown merchants")
    max_concurrent: int = Field(default=5, ge=1, le=20, description="Maximum concurrent processing tasks")
    
    class Config:
        schema_extra = {
            "example": {
                "month": "2025-07",
                "confidence_threshold": 0.5,
                "force_retag": False,
                "include_fixed_variable": True,
                "use_web_research": False,
                "max_concurrent": 5
            }
        }

class BatchAutoTagResponse(BaseModel):
    """Response schema for batch auto-tagging initiation"""
    batch_id: str = Field(description="Unique identifier for this batch operation")
    status: str = Field(description="Initial status", default="initiated")
    message: str = Field(description="Human-readable status message")
    total_transactions: int = Field(description="Total transactions to process")
    estimated_duration_minutes: float = Field(description="Estimated processing time in minutes")
    
    class Config:
        schema_extra = {
            "example": {
                "batch_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "initiated",
                "message": "Batch auto-tagging initiated successfully",
                "total_transactions": 150,
                "estimated_duration_minutes": 2.5
            }
        }

class BatchProgressResponse(BaseModel):
    """Response schema for batch operation progress tracking"""
    batch_id: str = Field(description="Batch operation identifier")
    status: str = Field(description="Current processing status")
    progress: float = Field(ge=0.0, le=100.0, description="Progress percentage (0-100)")
    total_transactions: int = Field(description="Total transactions to process")
    processed_transactions: int = Field(description="Number of transactions processed")
    tagged_transactions: int = Field(description="Number of transactions successfully tagged")
    skipped_low_confidence: int = Field(description="Transactions skipped due to low confidence")
    errors_count: int = Field(default=0, description="Number of processing errors")
    current_operation: Optional[str] = Field(None, description="Current operation being performed")
    estimated_completion: Optional[str] = Field(None, description="Estimated completion time (ISO format)")
    started_at: str = Field(description="Batch start time (ISO format)")
    
    class Config:
        schema_extra = {
            "example": {
                "batch_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "progress": 75.0,
                "total_transactions": 150,
                "processed_transactions": 112,
                "tagged_transactions": 89,
                "skipped_low_confidence": 23,
                "errors_count": 0,
                "current_operation": "Processing transaction 113/150",
                "estimated_completion": "2025-08-12T14:35:00Z",
                "started_at": "2025-08-12T14:30:00Z"
            }
        }

class BatchTransactionResult(BaseModel):
    """Result for individual transaction processing"""
    transaction_id: int = Field(description="Transaction ID")
    original_label: str = Field(description="Original transaction label")
    suggested_tag: Optional[str] = Field(None, description="AI-suggested tag")
    tag_confidence: Optional[float] = Field(None, description="Tag suggestion confidence")
    expense_type: Optional[str] = Field(None, description="Suggested expense type (FIXED/VARIABLE)")
    expense_type_confidence: Optional[float] = Field(None, description="Expense type confidence")
    action_taken: str = Field(description="Action taken (tagged, skipped, error)")
    skipped_reason: Optional[str] = Field(None, description="Reason for skipping")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    processing_time_ms: int = Field(description="Processing time in milliseconds")
    web_research_used: bool = Field(default=False, description="Whether web research was used")
    
    class Config:
        schema_extra = {
            "example": {
                "transaction_id": 1234,
                "original_label": "NETFLIX SARL 12.99",
                "suggested_tag": "streaming",
                "tag_confidence": 0.92,
                "expense_type": "FIXED",
                "expense_type_confidence": 0.85,
                "action_taken": "tagged",
                "skipped_reason": None,
                "error_message": None,
                "processing_time_ms": 250,
                "web_research_used": True
            }
        }

class BatchResultsSummary(BaseModel):
    """Summary statistics for batch processing results"""
    total_processed: int = Field(description="Total transactions processed")
    successfully_tagged: int = Field(description="Transactions successfully tagged")
    skipped_low_confidence: int = Field(description="Transactions skipped (low confidence)")
    skipped_already_tagged: int = Field(default=0, description="Transactions skipped (already tagged)")
    errors: int = Field(description="Transactions with processing errors")
    fixed_classified: int = Field(description="Transactions classified as FIXED")
    variable_classified: int = Field(description="Transactions classified as VARIABLE")
    new_tags_created: int = Field(description="Number of new unique tags created")
    web_research_count: int = Field(default=0, description="Number of transactions using web research")
    average_confidence: float = Field(description="Average confidence score")
    processing_time_seconds: float = Field(description="Total processing time in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "total_processed": 150,
                "successfully_tagged": 89,
                "skipped_low_confidence": 23,
                "skipped_already_tagged": 35,
                "errors": 3,
                "fixed_classified": 45,
                "variable_classified": 105,
                "new_tags_created": 12,
                "web_research_count": 15,
                "average_confidence": 0.78,
                "processing_time_seconds": 125.5
            }
        }

class BatchResultsResponse(BaseModel):
    """Complete results response for batch operation"""
    batch_id: str = Field(description="Batch operation identifier")
    status: str = Field(description="Final batch status (completed, failed, partial)")
    completed_at: str = Field(description="Completion time (ISO format)")
    summary: BatchResultsSummary = Field(description="Processing summary statistics")
    transactions: List[BatchTransactionResult] = Field(description="Detailed results for each transaction")
    errors: List[str] = Field(default_factory=list, description="Global processing errors")
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance and timing metrics")
    
    class Config:
        schema_extra = {
            "example": {
                "batch_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "completed_at": "2025-08-12T14:35:30Z",
                "summary": {
                    "total_processed": 150,
                    "successfully_tagged": 89,
                    "skipped_low_confidence": 23,
                    "errors": 3,
                    "fixed_classified": 45,
                    "variable_classified": 105,
                    "new_tags_created": 12,
                    "average_confidence": 0.78,
                    "processing_time_seconds": 125.5
                },
                "transactions": [],
                "errors": [],
                "performance_metrics": {
                    "avg_transaction_time_ms": 150,
                    "peak_memory_mb": 45,
                    "cache_hit_rate": 0.65
                }
            }
        }

class BatchOperationStatus:
    """Enumeration of possible batch operation statuses"""
    INITIATED: str = "initiated"
    PROCESSING: str = "processing"
    COMPLETED: str = "completed"
    FAILED: str = "failed"
    CANCELLED: str = "cancelled"
    PARTIAL: str = "partial"

class BatchErrorResponse(BaseModel):
    """Error response for batch operations"""
    batch_id: Optional[str] = Field(None, description="Batch ID if available")
    error_code: str = Field(description="Error code for programmatic handling")
    error_message: str = Field(description="Human-readable error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    timestamp: str = Field(description="Error timestamp (ISO format)")
    
    class Config:
        schema_extra = {
            "example": {
                "batch_id": "550e8400-e29b-41d4-a716-446655440000",
                "error_code": "INSUFFICIENT_TRANSACTIONS",
                "error_message": "No transactions found for the specified month",
                "details": {
                    "month": "2025-07",
                    "transaction_count": 0
                },
                "timestamp": "2025-08-12T14:30:00Z"
            }
        }


# ML Feedback Schemas

class MLFeedbackCreate(BaseModel):
    """Schema for creating ML feedback records"""
    transaction_id: int = Field(description="ID de la transaction concernée")
    original_tag: Optional[str] = Field(None, max_length=100, description="Tag suggéré par le ML")
    corrected_tag: Optional[str] = Field(None, max_length=100, description="Tag corrigé par l'utilisateur")
    original_expense_type: Optional[str] = Field(None, pattern="^(FIXED|VARIABLE|PROVISION)$", description="Type suggéré par le ML")
    corrected_expense_type: Optional[str] = Field(None, pattern="^(FIXED|VARIABLE|PROVISION)$", description="Type corrigé par l'utilisateur")
    feedback_type: str = Field(pattern="^(correction|acceptance|manual)$", description="Type de feedback")
    confidence_before: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confiance ML avant correction")
    
    class Config:
        schema_extra = {
            "example": {
                "transaction_id": 1234,
                "original_tag": "divers",
                "corrected_tag": "restaurant",
                "original_expense_type": "VARIABLE",
                "corrected_expense_type": "VARIABLE",
                "feedback_type": "correction",
                "confidence_before": 0.3
            }
        }


class MLFeedbackResponse(BaseModel):
    """Schema for ML feedback responses"""
    id: int
    transaction_id: int
    original_tag: Optional[str]
    corrected_tag: Optional[str]
    original_expense_type: Optional[str]
    corrected_expense_type: Optional[str]
    merchant_pattern: Optional[str]
    transaction_amount: Optional[float]
    transaction_description: Optional[str]
    feedback_type: str
    confidence_before: Optional[float]
    user_id: Optional[str]
    created_at: dt.datetime
    applied_at: Optional[dt.datetime]
    pattern_learned: bool
    times_pattern_used: int
    pattern_success_rate: float
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "transaction_id": 1234,
                "original_tag": "divers",
                "corrected_tag": "restaurant",
                "original_expense_type": "VARIABLE",
                "corrected_expense_type": "VARIABLE",
                "merchant_pattern": "chez paul",
                "transaction_amount": 35.50,
                "transaction_description": "CB CHEZ PAUL RESTAURANT",
                "feedback_type": "correction",
                "confidence_before": 0.3,
                "user_id": "admin",
                "created_at": "2025-08-12T14:30:00Z",
                "applied_at": None,
                "pattern_learned": False,
                "times_pattern_used": 0,
                "pattern_success_rate": 0.0
            }
        }


class TransactionTagUpdate(BaseModel):
    """Schema for updating transaction tags"""
    tags: str = Field(description="Tags séparés par des virgules")
    
    @validator('tags', pre=True)
    def clean_tags(cls, v):
        if isinstance(v, str):
            # Clean and normalize tags
            tags = [tag.strip().lower() for tag in v.split(',') if tag.strip()]
            return ','.join(tags)
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "tags": "restaurant,sortie"
            }
        }


class TransactionExpenseTypeUpdate(BaseModel):
    """Schema for updating transaction expense type"""
    expense_type: str = Field(pattern="^(FIXED|VARIABLE|PROVISION)$", description="Type de dépense")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Score de confiance de la classification")
    
    class Config:
        schema_extra = {
            "example": {
                "expense_type": "FIXED",
                "confidence_score": 0.95
            }
        }


class MLTaggingResult(BaseModel):
    """Schema for ML tagging results with enhanced confidence scoring"""
    suggested_tag: str = Field(description="Tag suggéré par le ML")
    confidence: float = Field(ge=0.0, le=1.0, description="Confiance totale (0-1)")
    expense_type: str = Field(pattern="^(FIXED|VARIABLE|PROVISION)$", description="Type de dépense classifié")
    explanation: str = Field(description="Explication du choix du ML")
    
    # Confidence factors breakdown
    pattern_match_confidence: float = Field(ge=0.0, le=1.0, description="Confiance basée sur les patterns")
    web_research_confidence: float = Field(ge=0.0, le=1.0, description="Confiance basée sur la recherche web")
    user_feedback_confidence: float = Field(ge=0.0, le=1.0, description="Confiance basée sur l'apprentissage utilisateur")
    context_confidence: float = Field(ge=0.0, le=1.0, description="Confiance basée sur le contexte")
    
    # Additional info
    merchant_category: Optional[str] = Field(None, description="Catégorie de marchand identifiée")
    merchant_name_clean: Optional[str] = Field(None, description="Nom de marchand nettoyé")
    alternative_tags: List[str] = Field(default_factory=list, description="Tags alternatifs suggérés")
    data_sources: List[str] = Field(default_factory=list, description="Sources de données utilisées")
    processing_time_ms: int = Field(description="Temps de traitement en millisecondes")
    web_research_performed: bool = Field(default=False, description="Recherche web effectuée")
    user_correction_applied: bool = Field(default=False, description="Correction utilisateur appliquée")
    
    class Config:
        schema_extra = {
            "example": {
                "suggested_tag": "restaurant",
                "confidence": 0.85,
                "expense_type": "VARIABLE",
                "explanation": "Haute confiance (85%): chez paul identifié comme restaurant",
                "pattern_match_confidence": 0.95,
                "web_research_confidence": 0.0,
                "user_feedback_confidence": 0.0,
                "context_confidence": 0.3,
                "merchant_category": "restaurant",
                "merchant_name_clean": "chez paul",
                "alternative_tags": ["repas", "sortie"],
                "data_sources": ["pattern_matching"],
                "processing_time_ms": 125,
                "web_research_performed": False,
                "user_correction_applied": False
            }
        }


class MLFeedbackStats(BaseModel):
    """Schema for ML feedback statistics"""
    total_feedback_entries: int = Field(description="Nombre total d'entrées de feedback")
    corrections_count: int = Field(description="Nombre de corrections")
    acceptances_count: int = Field(description="Nombre d'acceptations")
    manual_entries_count: int = Field(description="Nombre d'entrées manuelles")
    patterns_learned: int = Field(description="Nombre de patterns appris")
    average_confidence_improvement: float = Field(description="Amélioration moyenne de confiance")
    most_corrected_tags: List[Dict[str, Any]] = Field(description="Tags les plus corrigés")
    learning_success_rate: float = Field(description="Taux de succès de l'apprentissage")
    
    class Config:
        schema_extra = {
            "example": {
                "total_feedback_entries": 156,
                "corrections_count": 89,
                "acceptances_count": 45,
                "manual_entries_count": 22,
                "patterns_learned": 34,
                "average_confidence_improvement": 0.15,
                "most_corrected_tags": [
                    {"tag": "divers", "corrections": 23},
                    {"tag": "shopping", "corrections": 12}
                ],
                "learning_success_rate": 0.78
            }
        }


class MLLearningPattern(BaseModel):
    """Schema for learned ML patterns"""
    merchant_pattern: str = Field(description="Pattern de marchand")
    learned_tag: str = Field(description="Tag appris")
    learned_expense_type: str = Field(description="Type de dépense appris")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Score de confiance du pattern")
    usage_count: int = Field(description="Nombre d'utilisations")
    success_rate: float = Field(ge=0.0, le=1.0, description="Taux de succès")
    last_used: Optional[dt.datetime] = Field(None, description="Dernière utilisation")
    created_from_feedback: dt.datetime = Field(description="Créé à partir du feedback")
    
    class Config:
        schema_extra = {
            "example": {
                "merchant_pattern": "chez paul",
                "learned_tag": "restaurant",
                "learned_expense_type": "VARIABLE",
                "confidence_score": 0.92,
                "usage_count": 8,
                "success_rate": 0.875,
                "last_used": "2025-08-12T14:30:00Z",
                "created_from_feedback": "2025-08-01T10:15:00Z"
            }
        }