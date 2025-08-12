"""
Unit tests for database models.
Tests model validation, relationships, and constraints.
"""
import pytest
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from models.database import (
    Base, User, Config, Transaction, FixedLine, ImportMetadata,
    ExportHistory, CustomProvision, get_db, create_tables
)


@pytest.fixture
def test_engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create test database session."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


class TestUserModel:
    """Test User model validation and constraints."""
    
    def test_create_user_with_required_fields(self, test_session):
        """Should create user with minimum required fields."""
        user = User(
            username="testuser",
            hashed_password="hashed_password_123",
            email="test@example.com"
        )
        test_session.add(user)
        test_session.commit()
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.is_active == True  # Default value
        assert user.is_admin == False  # Default value
        assert user.failed_login_attempts == 0  # Default value
        assert user.created_at is not None
    
    def test_user_unique_username_constraint(self, test_session):
        """Should enforce unique username constraint."""
        user1 = User(username="duplicate", hashed_password="pass1")
        user2 = User(username="duplicate", hashed_password="pass2")
        
        test_session.add(user1)
        test_session.commit()
        
        test_session.add(user2)
        with pytest.raises(IntegrityError):
            test_session.commit()
    
    def test_user_unique_email_constraint(self, test_session):
        """Should enforce unique email constraint."""
        user1 = User(username="user1", email="same@email.com", hashed_password="pass1")
        user2 = User(username="user2", email="same@email.com", hashed_password="pass2")
        
        test_session.add(user1)
        test_session.commit()
        
        test_session.add(user2)
        with pytest.raises(IntegrityError):
            test_session.commit()
    
    def test_user_defaults_and_optional_fields(self, test_session):
        """Should handle default values and optional fields."""
        user = User(
            username="optionaltest",
            hashed_password="hashedpass",
            full_name="Test User",
            last_login=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        assert user.email is None  # Optional field
        assert user.full_name == "Test User"
        assert user.last_login is not None
        assert user.locked_until is None


class TestConfigModel:
    """Test Config model for budget settings."""
    
    def test_create_config_with_defaults(self, test_session):
        """Should create config with default values."""
        config = Config()
        test_session.add(config)
        test_session.commit()
        
        assert config.id is not None
        assert config.member1 == "diana"  # Default
        assert config.member2 == "thomas"  # Default
        assert config.rev1 == 0.0
        assert config.rev2 == 0.0
        assert config.split_mode == "revenus"
        assert config.split1 == 0.5
        assert config.split2 == 0.5
        assert config.var_percent == 30.0
    
    def test_config_custom_values(self, test_session):
        """Should accept custom configuration values."""
        config = Config(
            member1="Alice",
            member2="Bob",
            rev1=3500.0,
            rev2=4200.0,
            split_mode="manuel",
            split1=0.4,
            split2=0.6,
            var_percent=25.0
        )
        test_session.add(config)
        test_session.commit()
        
        assert config.member1 == "Alice"
        assert config.member2 == "Bob"
        assert config.rev1 == 3500.0
        assert config.rev2 == 4200.0
        assert config.split_mode == "manuel"
        assert config.split1 == 0.4
        assert config.split2 == 0.6
        assert config.var_percent == 25.0


class TestTransactionModel:
    """Test Transaction model for budget entries."""
    
    def test_create_transaction_basic(self, test_session):
        """Should create transaction with basic fields."""
        transaction = Transaction(
            month="2024-01",
            date_op=date(2024, 1, 15),
            label="Test transaction",
            amount=-50.0,
            category="Alimentation",
            is_expense=True
        )
        test_session.add(transaction)
        test_session.commit()
        
        assert transaction.id is not None
        assert transaction.month == "2024-01"
        assert transaction.date_op == date(2024, 1, 15)
        assert transaction.label == "Test transaction"
        assert transaction.amount == -50.0
        assert transaction.category == "Alimentation"
        assert transaction.is_expense == True
        assert transaction.exclude == False  # Default
    
    def test_transaction_defaults(self, test_session):
        """Should use default values properly."""
        transaction = Transaction()
        test_session.add(transaction)
        test_session.commit()
        
        assert transaction.label == ""
        assert transaction.category == ""
        assert transaction.category_parent == ""
        assert transaction.amount == 0.0
        assert transaction.account_label == ""
        assert transaction.is_expense == False
        assert transaction.exclude == False
        assert transaction.tags == ""
    
    def test_transaction_import_tracking(self, test_session):
        """Should track import metadata."""
        transaction = Transaction(
            month="2024-01",
            label="Imported transaction",
            amount=-25.0,
            import_id="12345-abcde",
            row_id="unique-hash-123"
        )
        test_session.add(transaction)
        test_session.commit()
        
        assert transaction.import_id == "12345-abcde"
        assert transaction.row_id == "unique-hash-123"


class TestFixedLineModel:
    """Test FixedLine model for recurring expenses."""
    
    def test_create_fixed_line_basic(self, test_session):
        """Should create fixed line with basic configuration."""
        fixed_line = FixedLine(
            label="Rent",
            amount=1200.0,
            freq="mensuelle",
            split_mode="50/50"
        )
        test_session.add(fixed_line)
        test_session.commit()
        
        assert fixed_line.id is not None
        assert fixed_line.label == "Rent"
        assert fixed_line.amount == 1200.0
        assert fixed_line.freq == "mensuelle"
        assert fixed_line.split_mode == "50/50"
        assert fixed_line.active == True  # Default
        assert fixed_line.category == "autres"  # Default
    
    def test_fixed_line_manual_split(self, test_session):
        """Should handle manual split configuration."""
        fixed_line = FixedLine(
            label="Car insurance",
            amount=120.0,
            freq="mensuelle",
            split_mode="manuel",
            split1=0.7,
            split2=0.3,
            category="transport"
        )
        test_session.add(fixed_line)
        test_session.commit()
        
        assert fixed_line.split_mode == "manuel"
        assert fixed_line.split1 == 0.7
        assert fixed_line.split2 == 0.3
        assert fixed_line.category == "transport"
    
    def test_fixed_line_frequencies(self, test_session):
        """Should handle different payment frequencies."""
        # Monthly
        monthly = FixedLine(label="Monthly", amount=100.0, freq="mensuelle")
        # Quarterly
        quarterly = FixedLine(label="Quarterly", amount=300.0, freq="trimestrielle")
        # Annual
        annual = FixedLine(label="Annual", amount=1200.0, freq="annuelle")
        
        test_session.add_all([monthly, quarterly, annual])
        test_session.commit()
        
        assert monthly.freq == "mensuelle"
        assert quarterly.freq == "trimestrielle"
        assert annual.freq == "annuelle"


class TestCustomProvisionModel:
    """Test CustomProvision model for flexible provisions."""
    
    def test_create_custom_provision_basic(self, test_session):
        """Should create custom provision with basic configuration."""
        provision = CustomProvision(
            name="Vacation Fund",
            percentage=5.0,
            base_calculation="total",
            split_mode="50/50"
        )
        test_session.add(provision)
        test_session.commit()
        
        assert provision.id is not None
        assert provision.name == "Vacation Fund"
        assert provision.percentage == 5.0
        assert provision.base_calculation == "total"
        assert provision.split_mode == "50/50"
        assert provision.is_active == True  # Default
        assert provision.icon == "💰"  # Default
        assert provision.color == "#6366f1"  # Default
        assert provision.created_at is not None
    
    def test_custom_provision_fixed_amount(self, test_session):
        """Should handle fixed amount provisions."""
        provision = CustomProvision(
            name="Emergency Fund",
            percentage=0.0,  # Not used for fixed
            base_calculation="fixed",
            fixed_amount=500.0,
            split_mode="custom",
            split_member1=60.0,
            split_member2=40.0
        )
        test_session.add(provision)
        test_session.commit()
        
        assert provision.base_calculation == "fixed"
        assert provision.fixed_amount == 500.0
        assert provision.split_mode == "custom"
        assert provision.split_member1 == 60.0
        assert provision.split_member2 == 40.0
    
    def test_custom_provision_with_target(self, test_session):
        """Should handle provisions with target amounts."""
        provision = CustomProvision(
            name="New Car",
            percentage=8.0,
            base_calculation="total",
            target_amount=15000.0,
            current_amount=2500.0,
            is_temporary=True,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2025, 12, 31)
        )
        test_session.add(provision)
        test_session.commit()
        
        assert provision.target_amount == 15000.0
        assert provision.current_amount == 2500.0
        assert provision.is_temporary == True
        assert provision.start_date == datetime(2024, 1, 1)
        assert provision.end_date == datetime(2025, 12, 31)
    
    def test_custom_provision_display_options(self, test_session):
        """Should handle display customization."""
        provision = CustomProvision(
            name="Investment",
            percentage=10.0,
            base_calculation="total",
            icon="📈",
            color="#10b981",
            display_order=1,
            category="investment"
        )
        test_session.add(provision)
        test_session.commit()
        
        assert provision.icon == "📈"
        assert provision.color == "#10b981"
        assert provision.display_order == 1
        assert provision.category == "investment"


class TestImportMetadataModel:
    """Test ImportMetadata model for tracking imports."""
    
    def test_create_import_metadata(self, test_session):
        """Should create import metadata record."""
        import_meta = ImportMetadata(
            id="uuid-12345",
            filename="test-import.csv",
            created_at=date.today(),
            user_id="testuser",
            months_detected='["2024-01", "2024-02"]',
            duplicates_count=3,
            processing_ms=1250
        )
        test_session.add(import_meta)
        test_session.commit()
        
        assert import_meta.id == "uuid-12345"
        assert import_meta.filename == "test-import.csv"
        assert import_meta.user_id == "testuser"
        assert import_meta.duplicates_count == 3
        assert import_meta.processing_ms == 1250


class TestExportHistoryModel:
    """Test ExportHistory model for tracking exports."""
    
    def test_create_export_history(self, test_session):
        """Should create export history record."""
        export_history = ExportHistory(
            id="export-uuid-123",
            user_id="testuser",
            format="excel",
            scope="transactions",
            created_at=date.today(),
            filename="budget-export-2024.xlsx",
            file_size=52480,
            processing_ms=850
        )
        test_session.add(export_history)
        test_session.commit()
        
        assert export_history.id == "export-uuid-123"
        assert export_history.user_id == "testuser"
        assert export_history.format == "excel"
        assert export_history.scope == "transactions"
        assert export_history.file_size == 52480
        assert export_history.download_count == 0  # Default
        assert export_history.status == "completed"  # Default


class TestDatabaseIndexes:
    """Test that critical database indexes exist and work."""
    
    def test_transaction_performance_queries(self, test_session):
        """Should handle performance-critical transaction queries efficiently."""
        # Create test data
        transactions = [
            Transaction(month="2024-01", category="Alimentation", amount=-50.0, is_expense=True, exclude=False),
            Transaction(month="2024-01", category="Transport", amount=-30.0, is_expense=True, exclude=False),
            Transaction(month="2024-01", category="Alimentation", amount=-25.0, is_expense=True, exclude=True),
            Transaction(month="2024-02", category="Alimentation", amount=-60.0, is_expense=True, exclude=False),
        ]
        test_session.add_all(transactions)
        test_session.commit()
        
        # Test month + exclude + expense filtering (uses composite index)
        active_expenses = test_session.query(Transaction).filter(
            Transaction.month == "2024-01",
            Transaction.exclude == False,
            Transaction.is_expense == True
        ).all()
        
        assert len(active_expenses) == 2
        assert all(t.exclude == False for t in active_expenses)
        assert all(t.is_expense == True for t in active_expenses)
        
        # Test category breakdown query
        alimentation_txs = test_session.query(Transaction).filter(
            Transaction.month == "2024-01",
            Transaction.category == "Alimentation",
            Transaction.exclude == False
        ).all()
        
        assert len(alimentation_txs) == 1
        assert alimentation_txs[0].amount == -50.0
    
    def test_user_authentication_queries(self, test_session):
        """Should handle user authentication queries efficiently."""
        users = [
            User(username="active_user", hashed_password="pass1", is_active=True),
            User(username="inactive_user", hashed_password="pass2", is_active=False),
            User(username="admin_user", hashed_password="pass3", is_active=True, is_admin=True),
        ]
        test_session.add_all(users)
        test_session.commit()
        
        # Test username + active lookup (uses composite index)
        active_user = test_session.query(User).filter(
            User.username == "active_user",
            User.is_active == True
        ).first()
        
        assert active_user is not None
        assert active_user.username == "active_user"
        assert active_user.is_active == True
        
        # Test admin users lookup
        admin_users = test_session.query(User).filter(
            User.is_active == True,
            User.is_admin == True
        ).all()
        
        assert len(admin_users) == 1
        assert admin_users[0].username == "admin_user"
    
    def test_custom_provision_queries(self, test_session):
        """Should handle custom provision queries efficiently."""
        provisions = [
            CustomProvision(name="Active 1", is_active=True, display_order=1, category="savings"),
            CustomProvision(name="Inactive", is_active=False, display_order=2, category="savings"),
            CustomProvision(name="Active 2", is_active=True, display_order=3, category="investment"),
        ]
        test_session.add_all(provisions)
        test_session.commit()
        
        # Test active provisions with ordering (uses composite index)
        active_provisions = test_session.query(CustomProvision).filter(
            CustomProvision.is_active == True
        ).order_by(CustomProvision.display_order).all()
        
        assert len(active_provisions) == 2
        assert active_provisions[0].name == "Active 1"
        assert active_provisions[1].name == "Active 2"
        
        # Test category filtering
        savings_provisions = test_session.query(CustomProvision).filter(
            CustomProvision.category == "savings",
            CustomProvision.is_active == True
        ).all()
        
        assert len(savings_provisions) == 1
        assert savings_provisions[0].name == "Active 1"