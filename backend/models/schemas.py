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