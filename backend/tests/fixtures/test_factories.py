"""
Test data factories for generating realistic test data.
Provides consistent, reusable test data for all tests.
"""
import factory
import factory.fuzzy
from datetime import date, datetime, timedelta
import random
from typing import Dict, List, Any
import uuid


class ConfigFactory(factory.DictFactory):
    """Factory for generating configuration data."""
    
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: n + 1)
    member1 = factory.Faker('first_name', locale='fr_FR')
    member2 = factory.Faker('first_name', locale='fr_FR')
    rev1 = factory.fuzzy.FuzzyFloat(2000.0, 5000.0, precision=2)
    rev2 = factory.fuzzy.FuzzyFloat(2000.0, 5000.0, precision=2)
    split_mode = factory.fuzzy.FuzzyChoice(['revenus', 'manuel'])
    split1 = factory.LazyAttribute(lambda obj: 0.5 if obj.split_mode == 'revenus' else random.uniform(0.3, 0.7))
    split2 = factory.LazyAttribute(lambda obj: 0.5 if obj.split_mode == 'revenus' else 1.0 - obj.split1)
    other_split_mode = factory.fuzzy.FuzzyChoice(['clé', '50/50'])
    var_percent = factory.fuzzy.FuzzyFloat(20.0, 40.0, precision=1)
    max_var = factory.fuzzy.FuzzyFloat(0.0, 1000.0, precision=2)
    min_fixed = factory.fuzzy.FuzzyFloat(0.0, 500.0, precision=2)
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


class TransactionFactory(factory.DictFactory):
    """Factory for generating transaction data."""
    
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: n + 1)
    month = factory.fuzzy.FuzzyChoice([
        '2023-10', '2023-11', '2023-12', 
        '2024-01', '2024-02', '2024-03', '2024-04'
    ])
    date_op = factory.LazyAttribute(lambda obj: _get_date_for_month(obj.month))
    label = factory.Faker('sentence', nb_words=3, locale='fr_FR')
    category = factory.fuzzy.FuzzyChoice([
        'Alimentation', 'Transport', 'Santé', 'Loisirs', 'Services', 
        'Logement', 'Vêtements', 'Éducation', 'Autres'
    ])
    category_parent = factory.LazyAttribute(lambda obj: obj.category)
    amount = factory.LazyAttribute(lambda obj: _get_realistic_amount(obj.category))
    account_label = factory.fuzzy.FuzzyChoice([
        'Compte courant', 'Livret A', 'Compte joint', 'Carte bleue'
    ])
    is_expense = factory.LazyAttribute(lambda obj: obj.amount < 0)
    exclude = factory.fuzzy.FuzzyChoice([True, False], weights=[10, 90])  # 10% excluded
    row_id = factory.LazyFunction(lambda: f"row_{uuid.uuid4().hex[:8]}")
    tags = factory.fuzzy.FuzzyChoice(['', 'urgent', 'récurrent', 'prévu', 'exceptionnel'])
    import_id = factory.LazyFunction(lambda: str(uuid.uuid4()))


class FixedLineFactory(factory.DictFactory):
    """Factory for generating fixed expense data."""
    
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: n + 1)
    label = factory.LazyAttribute(lambda obj: _get_realistic_fixed_expense_name())
    amount = factory.LazyAttribute(lambda obj: _get_realistic_fixed_expense_amount(obj.label))
    freq = factory.fuzzy.FuzzyChoice(['mensuelle', 'trimestrielle', 'annuelle'], weights=[70, 20, 10])
    split_mode = factory.fuzzy.FuzzyChoice(['clé', '50/50', 'm1', 'm2', 'manuel'], weights=[40, 30, 10, 10, 10])
    split1 = factory.LazyAttribute(lambda obj: 0.5 if obj.split_mode in ['clé', '50/50'] else random.uniform(0.3, 0.7))
    split2 = factory.LazyAttribute(lambda obj: 0.5 if obj.split_mode in ['clé', '50/50'] else 1.0 - obj.split1)
    category = factory.LazyAttribute(lambda obj: _get_category_for_fixed_expense(obj.label))
    active = factory.fuzzy.FuzzyChoice([True, False], weights=[90, 10])  # 90% active


class CustomProvisionFactory(factory.DictFactory):
    """Factory for generating custom provision data."""
    
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: n + 1)
    name = factory.LazyFunction(_get_realistic_provision_name)
    description = factory.Faker('text', max_nb_chars=200, locale='fr_FR')
    percentage = factory.fuzzy.FuzzyFloat(1.0, 15.0, precision=1)
    base_calculation = factory.fuzzy.FuzzyChoice(['total', 'member1', 'member2', 'fixed'], weights=[50, 20, 20, 10])
    fixed_amount = factory.LazyAttribute(lambda obj: random.uniform(50.0, 500.0) if obj.base_calculation == 'fixed' else 0)
    split_mode = factory.fuzzy.FuzzyChoice(['key', '50/50', 'custom', '100/0', '0/100'], weights=[40, 30, 20, 5, 5])
    split_member1 = factory.LazyAttribute(lambda obj: random.uniform(30, 70) if obj.split_mode == 'custom' else 50)
    split_member2 = factory.LazyAttribute(lambda obj: 100 - obj.split_member1 if obj.split_mode == 'custom' else 50)
    icon = factory.LazyFunction(_get_provision_icon)
    color = factory.fuzzy.FuzzyChoice(['#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444'])
    display_order = factory.Sequence(lambda n: n)
    is_active = factory.fuzzy.FuzzyChoice([True, False], weights=[85, 15])  # 85% active
    is_temporary = factory.fuzzy.FuzzyChoice([True, False], weights=[20, 80])  # 20% temporary
    start_date = factory.LazyFunction(lambda: datetime.now() - timedelta(days=random.randint(0, 365)))
    end_date = factory.LazyAttribute(lambda obj: obj.start_date + timedelta(days=random.randint(180, 730)) if obj.is_temporary else None)
    target_amount = factory.LazyAttribute(lambda obj: random.uniform(1000, 20000) if random.choice([True, False]) else None)
    current_amount = factory.LazyAttribute(lambda obj: random.uniform(0, obj.target_amount * 0.8) if obj.target_amount else 0)
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)
    created_by = factory.Faker('user_name')
    category = factory.fuzzy.FuzzyChoice(['savings', 'investment', 'project', 'custom'])


class ImportMetadataFactory(factory.DictFactory):
    """Factory for generating import metadata."""
    
    class Meta:
        model = dict
    
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    filename = factory.LazyFunction(_get_realistic_csv_filename)
    created_at = factory.LazyFunction(date.today)
    user_id = factory.Faker('user_name')
    months_detected = factory.LazyFunction(lambda: str([f"2024-{i:02d}" for i in range(1, random.randint(2, 6))]))
    duplicates_count = factory.fuzzy.FuzzyInteger(0, 10)
    warnings = factory.LazyFunction(_get_import_warnings)
    processing_ms = factory.fuzzy.FuzzyInteger(500, 5000)


class UserFactory(factory.DictFactory):
    """Factory for generating user data."""
    
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: n + 1)
    username = factory.Faker('user_name')
    email = factory.Faker('email')
    full_name = factory.Faker('name', locale='fr_FR')
    hashed_password = factory.LazyFunction(lambda: f"hashed_{uuid.uuid4().hex[:16]}")
    is_active = factory.fuzzy.FuzzyChoice([True, False], weights=[95, 5])
    is_admin = factory.fuzzy.FuzzyChoice([True, False], weights=[10, 90])
    last_login = factory.LazyFunction(lambda: datetime.now() - timedelta(days=random.randint(0, 30)))
    failed_login_attempts = factory.fuzzy.FuzzyInteger(0, 3)
    locked_until = None
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


# Helper functions for realistic data generation

def _get_date_for_month(month_str: str) -> date:
    """Generate a realistic date within the given month."""
    year, month = map(int, month_str.split('-'))
    day = random.randint(1, 28)  # Safe for all months
    return date(year, month, day)


def _get_realistic_amount(category: str) -> float:
    """Generate realistic transaction amounts based on category."""
    amounts = {
        'Alimentation': (-150.0, -10.0),
        'Transport': (-100.0, -5.0),
        'Santé': (-200.0, -20.0),
        'Loisirs': (-80.0, -5.0),
        'Services': (-150.0, -15.0),
        'Logement': (-1500.0, -200.0),
        'Vêtements': (-200.0, -15.0),
        'Éducation': (-500.0, -50.0),
        'Autres': (-100.0, -5.0)
    }
    
    min_amount, max_amount = amounts.get(category, (-50.0, -5.0))
    return round(random.uniform(min_amount, max_amount), 2)


def _get_realistic_fixed_expense_name() -> str:
    """Generate realistic fixed expense names."""
    expenses = [
        'Loyer', 'Prêt immobilier', 'Assurance habitation', 'Électricité', 'Gaz',
        'Internet', 'Téléphone', 'Assurance auto', 'Abonnement transport',
        'Salle de sport', 'Netflix', 'Spotify', 'Mutuelle santé',
        'Assurance vie', 'Impôts locaux', 'Charges copropriété'
    ]
    return random.choice(expenses)


def _get_realistic_fixed_expense_amount(label: str) -> float:
    """Generate realistic amounts based on expense type."""
    amounts = {
        'Loyer': (800, 2000),
        'Prêt immobilier': (1000, 2500),
        'Assurance habitation': (20, 80),
        'Électricité': (50, 150),
        'Gaz': (40, 120),
        'Internet': (25, 50),
        'Téléphone': (15, 80),
        'Assurance auto': (50, 150),
        'Abonnement transport': (70, 120),
        'Salle de sport': (25, 60),
        'Netflix': (10, 20),
        'Spotify': (5, 15),
        'Mutuelle santé': (50, 200),
        'Assurance vie': (50, 300),
        'Impôts locaux': (100, 400),
        'Charges copropriété': (100, 300)
    }
    
    min_amount, max_amount = amounts.get(label, (20, 100))
    return round(random.uniform(min_amount, max_amount), 2)


def _get_category_for_fixed_expense(label: str) -> str:
    """Get appropriate category for fixed expense."""
    categories = {
        'Loyer': 'logement',
        'Prêt immobilier': 'logement',
        'Assurance habitation': 'logement',
        'Électricité': 'logement',
        'Gaz': 'logement',
        'Internet': 'services',
        'Téléphone': 'services',
        'Assurance auto': 'transport',
        'Abonnement transport': 'transport',
        'Salle de sport': 'loisirs',
        'Netflix': 'loisirs',
        'Spotify': 'loisirs',
        'Mutuelle santé': 'santé',
        'Assurance vie': 'services',
        'Impôts locaux': 'services',
        'Charges copropriété': 'logement'
    }
    
    return categories.get(label, 'autres')


def _get_realistic_provision_name() -> str:
    """Generate realistic provision names."""
    provisions = [
        'Épargne vacances', 'Fonds d\'urgence', 'Voiture neuve', 'Rénovation cuisine',
        'Mariage', 'Naissance', 'Formation professionnelle', 'Équipement informatique',
        'Électroménager', 'Mobilier', 'Voyage Japon', 'Investissement immobilier',
        'Retraite complémentaire', 'Cadeaux Noël', 'Frais vétérinaire',
        'Réparations auto', 'Matériel sport', 'Instruments musique'
    ]
    return random.choice(provisions)


def _get_provision_icon() -> str:
    """Generate appropriate icons for provisions."""
    icons = ['💰', '🏖️', '🚨', '🚗', '🏠', '💍', '👶', '📚', '💻', '🎁', '✈️', '🏥', '⚽', '🎵']
    return random.choice(icons)


def _get_realistic_csv_filename() -> str:
    """Generate realistic CSV filenames."""
    prefixes = ['export', 'transactions', 'comptes', 'releve', 'historique']
    dates = [f"{random.randint(2023, 2024)}-{random.randint(1, 12):02d}"]
    suffixes = ['csv', 'CSV']
    
    prefix = random.choice(prefixes)
    date_part = random.choice(dates)
    suffix = random.choice(suffixes)
    
    return f"{prefix}_{date_part}.{suffix}"


def _get_import_warnings() -> str:
    """Generate realistic import warnings."""
    warnings = [
        "3 lignes dupliquées détectées",
        "Catégories manquantes pour 5 transactions",
        "Format de date non standard détecté",
        "Caractères spéciaux dans les libellés",
        "Montants négatifs pour les revenus"
    ]
    
    selected_warnings = random.sample(warnings, k=random.randint(0, 3))
    return str(selected_warnings) if selected_warnings else ""


# Preset factory configurations for common test scenarios

class TestScenarios:
    """Predefined test scenarios with realistic data sets."""
    
    @staticmethod
    def create_couple_budget() -> Dict[str, Any]:
        """Create a realistic couple budget scenario."""
        config = ConfigFactory(
            member1='Alice',
            member2='Bob',
            rev1=3500.0,
            rev2=2800.0,
            split_mode='revenus'
        )
        
        provisions = [
            CustomProvisionFactory(
                name='Épargne vacances',
                percentage=8.0,
                base_calculation='total',
                split_mode='50/50'
            ),
            CustomProvisionFactory(
                name='Fonds d\'urgence',
                percentage=5.0,
                base_calculation='total',
                split_mode='key'
            )
        ]
        
        fixed_expenses = [
            FixedLineFactory(
                label='Loyer',
                amount=1200.0,
                freq='mensuelle',
                split_mode='50/50',
                category='logement'
            ),
            FixedLineFactory(
                label='Assurance auto',
                amount=85.0,
                freq='mensuelle',
                split_mode='clé',
                category='transport'
            )
        ]
        
        transactions = TransactionFactory.create_batch(
            20,
            month='2024-01',
            exclude=False
        )
        
        return {
            'config': config,
            'provisions': provisions,
            'fixed_expenses': fixed_expenses,
            'transactions': transactions
        }
    
    @staticmethod
    def create_single_budget() -> Dict[str, Any]:
        """Create a realistic single person budget scenario."""
        config = ConfigFactory(
            member1='Thomas',
            member2='',
            rev1=3200.0,
            rev2=0.0,
            split_mode='manuel',
            split1=1.0,
            split2=0.0
        )
        
        provisions = [
            CustomProvisionFactory(
                name='Voiture neuve',
                fixed_amount=300.0,
                base_calculation='fixed',
                split_mode='100/0'
            )
        ]
        
        fixed_expenses = [
            FixedLineFactory(
                label='Studio',
                amount=650.0,
                freq='mensuelle',
                split_mode='m1',
                category='logement'
            )
        ]
        
        return {
            'config': config,
            'provisions': provisions,
            'fixed_expenses': fixed_expenses
        }
    
    @staticmethod
    def create_high_income_scenario() -> Dict[str, Any]:
        """Create a high-income couple scenario."""
        config = ConfigFactory(
            member1='Diana',
            member2='Thomas',
            rev1=6500.0,
            rev2=5200.0,
            split_mode='revenus'
        )
        
        provisions = [
            CustomProvisionFactory(
                name='Investissement immobilier',
                percentage=12.0,
                base_calculation='total',
                split_mode='key'
            ),
            CustomProvisionFactory(
                name='Retraite complémentaire',
                percentage=8.0,
                base_calculation='total',
                split_mode='key'
            ),
            CustomProvisionFactory(
                name='Voyage annuel',
                fixed_amount=500.0,
                base_calculation='fixed',
                split_mode='50/50'
            )
        ]
        
        fixed_expenses = [
            FixedLineFactory(
                label='Prêt immobilier',
                amount=1800.0,
                freq='mensuelle',
                split_mode='clé',
                category='logement'
            ),
            FixedLineFactory(
                label='Deux assurances auto',
                amount=180.0,
                freq='mensuelle',
                split_mode='50/50',
                category='transport'
            )
        ]
        
        return {
            'config': config,
            'provisions': provisions,
            'fixed_expenses': fixed_expenses
        }


# Utility functions for tests

def create_month_transactions(month: str, count: int = 15) -> List[Dict]:
    """Create a realistic set of transactions for a specific month."""
    return TransactionFactory.create_batch(
        count,
        month=month,
        exclude=False
    )


def create_complete_budget(scenario_name: str = 'couple') -> Dict[str, Any]:
    """Create a complete budget scenario for testing."""
    if scenario_name == 'couple':
        return TestScenarios.create_couple_budget()
    elif scenario_name == 'single':
        return TestScenarios.create_single_budget()
    elif scenario_name == 'high_income':
        return TestScenarios.create_high_income_scenario()
    else:
        return TestScenarios.create_couple_budget()  # Default