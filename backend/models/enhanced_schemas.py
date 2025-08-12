"""
Enhanced Pydantic schemas for Budget Famille v2.3 API Documentation
Comprehensive data models with examples and detailed descriptions
"""
import datetime as dt
from typing import List, Optional, Dict, Union, Any
from pydantic import BaseModel, validator, Field
from email_validator import validate_email, EmailNotValidError
from enum import Enum

# Enums for better API documentation
class CalculationMode(str, Enum):
    EQUAL = "égalitaire"
    PROPORTIONAL = "proportionnel"

class SplitMode(str, Enum):
    EQUAL = "égalitaire"
    PROPORTIONAL = "proportionnel" 
    CUSTOM = "custom"

class Frequency(str, Enum):
    MONTHLY = "mensuelle"
    QUARTERLY = "trimestrielle"
    YEARLY = "annuelle"

class ExpenseCategory(str, Enum):
    HOUSING = "logement"
    TRANSPORT = "transport"
    SERVICES = "services"
    LEISURE = "loisirs"
    HEALTH = "santé"
    OTHER = "autres"

class BaseCalculation(str, Enum):
    NET_INCOME = "net_income"
    GROSS_INCOME = "gross_income"
    TOTAL_INCOME = "total_income"
    FIXED_AMOUNT = "fixed_amount"

class ImportStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"

class ExportFormat(str, Enum):
    CSV = "csv"
    PDF = "pdf"
    EXCEL = "xlsx"

# Error Response Schemas
class ErrorDetail(BaseModel):
    """Standard error detail schema"""
    type: str = Field(description="Type d'erreur", example="validation_error")
    msg: str = Field(description="Message d'erreur détaillé", example="Le champ est requis")
    ctx: Optional[Dict[str, Any]] = Field(description="Contexte additionnel", example={})

class ErrorResponse(BaseModel):
    """Standard error response schema"""
    detail: Union[str, List[ErrorDetail]] = Field(
        description="Détails de l'erreur",
        example="Données de requête invalides"
    )
    error_code: Optional[str] = Field(
        description="Code d'erreur unique pour le debugging",
        example="INVALID_CONFIG_001"
    )
    timestamp: Optional[str] = Field(
        description="Timestamp de l'erreur",
        example="2024-01-15T10:30:00Z"
    )

# Authentication Schemas
class TokenResponse(BaseModel):
    """JWT Token response schema"""
    access_token: str = Field(
        description="JWT access token pour l'authentification",
        example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    )
    token_type: str = Field(
        description="Type du token",
        example="bearer"
    )
    expires_in: int = Field(
        description="Durée de validité du token en secondes",
        example=3600
    )

class UserInfo(BaseModel):
    """User information schema"""
    username: str = Field(
        description="Nom d'utilisateur",
        example="admin"
    )
    email: Optional[str] = Field(
        description="Adresse email",
        example="admin@famille.com"
    )
    full_name: Optional[str] = Field(
        description="Nom complet",
        example="Administrateur Budget"
    )
    disabled: Optional[bool] = Field(
        description="Indique si le compte est désactivé",
        example=False
    )

# Enhanced Configuration Schemas
class ConfigurationInput(BaseModel):
    """
    Configuration input schema for budget settings.
    
    This schema defines the core financial parameters for budget calculations
    including salaries, fixed charges, provisions, and distribution ratios.
    
    **Key Features:**
    - Automatic validation of percentage distributions (must sum to 100%)
    - Support for both equal and proportional calculation modes
    - Monthly amounts in EUR
    - Adjustment factors for personalized spending patterns
    """
    
    salaire1: float = Field(
        default=2500.0,
        ge=0,
        description="Salaire mensuel net du membre 1 en euros",
        example=2500.0
    )
    salaire2: float = Field(
        default=2200.0,
        ge=0,
        description="Salaire mensuel net du membre 2 en euros",
        example=2200.0
    )
    charges_fixes: float = Field(
        default=1200.0,
        ge=0,
        description="Montant total des charges fixes mensuelles (loyer, assurances, abonnements) en euros",
        example=1200.0
    )
    provision_vacances: float = Field(
        default=200.0,
        ge=0,
        description="Provision mensuelle dédiée aux vacances et loisirs en euros",
        example=200.0
    )
    provision_voiture: float = Field(
        default=150.0,
        ge=0,
        description="Provision mensuelle pour véhicule (entretien, réparations, carburant) en euros",
        example=150.0
    )
    provision_travaux: float = Field(
        default=100.0,
        ge=0,
        description="Provision mensuelle pour travaux et amélioration du logement en euros",
        example=100.0
    )
    r1: float = Field(
        default=60.0,
        ge=0,
        le=100,
        description="Pourcentage de répartition des dépenses communes pour le membre 1 (0-100%)",
        example=60.0
    )
    r2: float = Field(
        default=40.0,
        ge=0,
        le=100,
        description="Pourcentage de répartition des dépenses communes pour le membre 2 (0-100%)",
        example=40.0
    )
    s1: float = Field(
        default=1.2,
        gt=0,
        description="Facteur d'ajustement personnel des dépenses pour le membre 1 (multiplicateur)",
        example=1.2
    )
    s2: float = Field(
        default=0.8,
        gt=0,
        description="Facteur d'ajustement personnel des dépenses pour le membre 2 (multiplicateur)",
        example=0.8
    )
    mode: CalculationMode = Field(
        default=CalculationMode.PROPORTIONAL,
        description="Mode de calcul des répartitions: 'égalitaire' (50/50) ou 'proportionnel' (selon revenus)",
        example=CalculationMode.PROPORTIONAL
    )

    @validator('r2')
    def validate_percentages_sum(cls, v, values):
        """Validate that r1 + r2 = 100%"""
        r1 = values.get('r1', 0)
        if abs(r1 + v - 100) > 0.1:  # Allow small float errors
            raise ValueError('Les répartitions r1 et r2 doivent totaliser 100%')
        return v

    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "salaire1": 2500.0,
                "salaire2": 2200.0,
                "charges_fixes": 1200.0,
                "provision_vacances": 200.0,
                "provision_voiture": 150.0,
                "provision_travaux": 100.0,
                "r1": 60.0,
                "r2": 40.0,
                "s1": 1.2,
                "s2": 0.8,
                "mode": "proportionnel"
            }
        }

class ConfigurationOutput(ConfigurationInput):
    """
    Configuration output schema with metadata.
    
    Includes creation and update timestamps for audit trail.
    """
    id: int = Field(
        description="Identifiant unique de la configuration",
        example=1
    )
    created_at: dt.datetime = Field(
        description="Date et heure de création de la configuration",
        example="2024-01-15T10:30:00"
    )
    updated_at: dt.datetime = Field(
        description="Date et heure de dernière mise à jour",
        example="2024-01-20T15:45:00"
    )

    class Config:
        orm_mode = True
        use_enum_values = True
        schema_extra = {
            "example": {
                "id": 1,
                "salaire1": 2500.0,
                "salaire2": 2200.0,
                "charges_fixes": 1200.0,
                "provision_vacances": 200.0,
                "provision_voiture": 150.0,
                "provision_travaux": 100.0,
                "r1": 60.0,
                "r2": 40.0,
                "s1": 1.2,
                "s2": 0.8,
                "mode": "proportionnel",
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-20T15:45:00"
            }
        }

# Enhanced Transaction Schemas
class TransactionOutput(BaseModel):
    """
    Transaction output schema with comprehensive details.
    
    Represents a financial transaction with categorization,
    exclusion management, and tagging capabilities.
    """
    id: int = Field(
        description="Identifiant unique de la transaction",
        example=123
    )
    month: Optional[str] = Field(
        description="Mois de la transaction au format YYYY-MM",
        example="2024-01"
    )
    date_op: Optional[dt.date] = Field(
        description="Date d'opération bancaire de la transaction",
        example="2024-01-15"
    )
    date_valeur: Optional[dt.date] = Field(
        description="Date de valeur comptable de la transaction",
        example="2024-01-16"
    )
    amount: Optional[float] = Field(
        description="Montant de la transaction en euros (négatif pour les dépenses, positif pour les revenus)",
        example=-45.67
    )
    label: Optional[str] = Field(
        description="Libellé descriptif de la transaction tel qu'affiché par la banque",
        example="ACHAT CB SUPERMARCHE LECLERC PARIS"
    )
    category: Optional[str] = Field(
        description="Catégorie principale de dépense (automatiquement détectée ou assignée manuellement)",
        example="Alimentation"
    )
    subcategory: Optional[str] = Field(
        description="Sous-catégorie pour une classification plus fine",
        example="Courses alimentaires"
    )
    is_expense: Optional[bool] = Field(
        description="Indique si c'est une dépense (true) ou un revenu/crédit (false)",
        example=True
    )
    exclude: bool = Field(
        description="Indique si la transaction est exclue des calculs budgétaires",
        example=False
    )
    tags: str = Field(
        description="Tags personnalisés associés à la transaction, séparés par des virgules",
        example="urgent,famille,alimentation"
    )

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 123,
                "month": "2024-01",
                "date_op": "2024-01-15",
                "date_valeur": "2024-01-16",
                "amount": -45.67,
                "label": "ACHAT CB SUPERMARCHE LECLERC PARIS 15",
                "category": "Alimentation",
                "subcategory": "Courses alimentaires",
                "is_expense": True,
                "exclude": False,
                "tags": "urgent,famille"
            }
        }

class TransactionExclusionUpdate(BaseModel):
    """Schema for updating transaction exclusion status"""
    exclude: bool = Field(
        description="Nouvelle valeur d'exclusion - true pour exclure la transaction des calculs",
        example=True
    )

    class Config:
        schema_extra = {
            "example": {
                "exclude": True
            }
        }

class TransactionTagsUpdate(BaseModel):
    """Schema for updating transaction tags"""
    tags: str = Field(
        description="Tags à associer à la transaction, séparés par des virgules (max 500 caractères)",
        example="urgent,personnel,impôts",
        max_length=500
    )

    class Config:
        schema_extra = {
            "example": {
                "tags": "urgent,personnel,impôts"
            }
        }

# Enhanced Analytics Schemas
class CategoryBreakdown(BaseModel):
    """
    Detailed breakdown of expenses by category.
    
    Provides comprehensive analytics for a specific spending category
    including totals, averages, and transaction counts.
    """
    category: str = Field(
        description="Nom de la catégorie de dépenses",
        example="Alimentation"
    )
    amount: float = Field(
        description="Montant total des dépenses dans cette catégorie en euros",
        example=387.50
    )
    percentage: float = Field(
        description="Pourcentage que représente cette catégorie dans les dépenses totales",
        example=15.2
    )
    transaction_count: int = Field(
        description="Nombre de transactions dans cette catégorie",
        example=12
    )
    avg_transaction: float = Field(
        description="Montant moyen par transaction dans cette catégorie",
        example=32.29
    )

    class Config:
        schema_extra = {
            "example": {
                "category": "Alimentation",
                "amount": 387.50,
                "percentage": 15.2,
                "transaction_count": 12,
                "avg_transaction": 32.29
            }
        }

class KPISummary(BaseModel):
    """
    Key Performance Indicators summary for financial analysis.
    
    Comprehensive financial KPIs including income, expenses, savings rate,
    and spending trends over the analyzed period.
    """
    total_income: float = Field(
        description="Revenus totaux sur la période analysée en euros",
        example=4700.0
    )
    total_expenses: float = Field(
        description="Dépenses totales sur la période analysée en euros",
        example=2850.0
    )
    net_balance: float = Field(
        description="Solde net (revenus - dépenses) en euros",
        example=1850.0
    )
    savings_rate: float = Field(
        description="Taux d'épargne en pourcentage (solde_net/revenus*100)",
        example=39.4
    )
    avg_monthly_expense: float = Field(
        description="Moyenne mensuelle des dépenses sur la période",
        example=950.0
    )
    expense_trend: float = Field(
        description="Tendance d'évolution des dépenses en pourcentage (positif=hausse, négatif=baisse)",
        example=2.5
    )
    top_categories: List[CategoryBreakdown] = Field(
        description="Top des catégories de dépenses par montant",
        example=[]
    )
    months_analyzed: List[str] = Field(
        description="Liste des mois inclus dans l'analyse",
        example=["2024-01", "2024-02", "2024-03"]
    )

    class Config:
        schema_extra = {
            "example": {
                "total_income": 4700.0,
                "total_expenses": 2850.0,
                "net_balance": 1850.0,
                "savings_rate": 39.4,
                "avg_monthly_expense": 950.0,
                "expense_trend": 2.5,
                "top_categories": [
                    {
                        "category": "Alimentation",
                        "amount": 387.50,
                        "percentage": 13.6,
                        "transaction_count": 12,
                        "avg_transaction": 32.29
                    }
                ],
                "months_analyzed": ["2024-01", "2024-02", "2024-03"]
            }
        }

# Health Check Schema
class HealthCheckResponse(BaseModel):
    """API health check response"""
    status: str = Field(
        description="Status de l'API",
        example="healthy"
    )
    version: str = Field(
        description="Version de l'API",
        example="2.3.0"
    )
    database: str = Field(
        description="Status de la base de données",
        example="connected"
    )
    encryption: str = Field(
        description="Status du chiffrement",
        example="enabled"
    )
    timestamp: str = Field(
        description="Timestamp du check",
        example="2024-01-15T10:30:00"
    )
    architecture: str = Field(
        description="Architecture de l'application",
        example="modular"
    )

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "2.3.0",
                "database": "connected",
                "encryption": "enabled",
                "timestamp": "2024-01-15T10:30:00",
                "architecture": "modular"
            }
        }