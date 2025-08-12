"""
Unit tests for the calculations service module.
Tests critical business logic, financial calculations, and provisions.
"""
import pytest
import datetime as dt
from unittest.mock import MagicMock, patch
from services.calculations import (
    get_split, calculate_provision_amount, calculate_monthly_trends,
    calculate_category_breakdown, calculate_kpi_summary, detect_anomalies,
    split_amount, is_income_or_transfer, get_active_provisions,
    calculate_fixed_lines_total, calculate_provisions_total,
    get_previous_month
)


class TestGetSplit:
    """Test split ratio calculations."""
    
    def test_revenus_split_mode_equal_revenues(self):
        """Should calculate equal split when revenues are equal."""
        config = MagicMock()
        config.split_mode = "revenus"
        config.rev1 = 3000.0
        config.rev2 = 3000.0
        
        r1, r2 = get_split(config)
        
        assert r1 == 0.5
        assert r2 == 0.5
    
    def test_revenus_split_mode_unequal_revenues(self):
        """Should calculate proportional split based on revenues."""
        config = MagicMock()
        config.split_mode = "revenus"
        config.rev1 = 4000.0
        config.rev2 = 2000.0
        
        r1, r2 = get_split(config)
        
        assert r1 == 2/3  # 4000 / 6000
        assert r2 == 1/3  # 2000 / 6000
    
    def test_revenus_split_mode_zero_total(self):
        """Should default to 50/50 when total revenue is zero."""
        config = MagicMock()
        config.split_mode = "revenus"
        config.rev1 = 0.0
        config.rev2 = 0.0
        
        r1, r2 = get_split(config)
        
        assert r1 == 0.5
        assert r2 == 0.5
    
    def test_manual_split_mode(self):
        """Should use manual split values when not in revenus mode."""
        config = MagicMock()
        config.split_mode = "manuel"
        config.split1 = 0.6
        config.split2 = 0.4
        
        r1, r2 = get_split(config)
        
        assert r1 == 0.6
        assert r2 == 0.4


class TestCalculateProvisionAmount:
    """Test provision amount calculations."""
    
    def test_fixed_amount_provision(self):
        """Should calculate correct amount for fixed provisions."""
        provision = MagicMock()
        provision.base_calculation = "fixed"
        provision.fixed_amount = 200.0
        provision.split_mode = "50/50"
        
        config = MagicMock()
        
        total, member1, member2 = calculate_provision_amount(provision, config)
        
        assert total == 200.0
        assert member1 == 100.0
        assert member2 == 100.0
    
    def test_total_based_provision(self):
        """Should calculate provision based on total income."""
        provision = MagicMock()
        provision.base_calculation = "total"
        provision.percentage = 10.0  # 10% annually
        provision.split_mode = "key"
        
        config = MagicMock()
        config.rev1 = 4000.0
        config.rev2 = 2000.0
        
        total, member1, member2 = calculate_provision_amount(provision, config)
        
        # 10% of 6000 annual = 600 annual = 50 monthly
        expected_total = 50.0
        expected_member1 = expected_total * (2/3)  # Based on revenue split
        expected_member2 = expected_total * (1/3)
        
        assert abs(total - expected_total) < 0.01
        assert abs(member1 - expected_member1) < 0.01
        assert abs(member2 - expected_member2) < 0.01
    
    def test_custom_split_provision(self):
        """Should handle custom split percentages."""
        provision = MagicMock()
        provision.base_calculation = "fixed"
        provision.fixed_amount = 300.0
        provision.split_mode = "custom"
        provision.split_member1 = 70.0
        provision.split_member2 = 30.0
        
        config = MagicMock()
        
        total, member1, member2 = calculate_provision_amount(provision, config)
        
        assert total == 300.0
        assert member1 == 210.0  # 70% of 300
        assert member2 == 90.0   # 30% of 300


class TestSplitAmount:
    """Test amount splitting logic."""
    
    def test_fifty_fifty_split(self):
        """Should split amount equally."""
        amount = 100.0
        m1, m2 = split_amount(amount, "50/50", 0.6, 0.4, None, None)
        
        assert m1 == 50.0
        assert m2 == 50.0
    
    def test_key_split(self):
        """Should split based on ratio key."""
        amount = 100.0
        m1, m2 = split_amount(amount, "clé", 0.7, 0.3, None, None)
        
        assert m1 == 70.0
        assert m2 == 30.0
    
    def test_member1_only_split(self):
        """Should assign all to member 1."""
        amount = 100.0
        m1, m2 = split_amount(amount, "m1", 0.5, 0.5, None, None)
        
        assert m1 == 100.0
        assert m2 == 0.0
    
    def test_member2_only_split(self):
        """Should assign all to member 2."""
        amount = 100.0
        m1, m2 = split_amount(amount, "m2", 0.5, 0.5, None, None)
        
        assert m1 == 0.0
        assert m2 == 100.0
    
    def test_manual_split(self):
        """Should use manual split values."""
        amount = 100.0
        m1, m2 = split_amount(amount, "manuel", 0.5, 0.5, 0.8, 0.2)
        
        assert m1 == 80.0
        assert m2 == 20.0


class TestIsIncomeOrTransfer:
    """Test income and transfer detection."""
    
    @pytest.mark.parametrize("label,category,expected", [
        ("Virement compte épargne", "", True),
        ("VIR SALAIRE", "", True),
        ("Salaire mensuel", "", True),
        ("Remboursement frais", "", True),
        ("Achat supermarché", "", False),
        ("", "Virements emis", True),
        ("", "Remboursement", True),
        ("Restaurant", "Sorties", False),
    ])
    def test_income_transfer_detection(self, label, category, expected):
        """Should correctly identify income and transfers."""
        result = is_income_or_transfer(label, category)
        assert result == expected


class TestGetPreviousMonth:
    """Test previous month calculation."""
    
    def test_normal_month(self):
        """Should get previous month normally."""
        result = get_previous_month("2024-06")
        assert result == "2024-05"
    
    def test_january_rollover(self):
        """Should rollover to previous year for January."""
        result = get_previous_month("2024-01")
        assert result == "2023-12"
    
    def test_invalid_format(self):
        """Should return None for invalid format."""
        result = get_previous_month("invalid-date")
        assert result is None


class TestCalculateFixedLinesTotal:
    """Test fixed lines total calculations."""
    
    def test_monthly_fixed_lines(self):
        """Should calculate monthly fixed lines correctly."""
        # Mock database session
        mock_db = MagicMock()
        
        # Mock fixed line
        fixed_line = MagicMock()
        fixed_line.amount = 1200.0
        fixed_line.freq = "mensuelle"
        fixed_line.split_mode = "50/50"
        fixed_line.active = True
        
        mock_db.query().filter().all.return_value = [fixed_line]
        
        # Mock config
        config = MagicMock()
        config.split_mode = "manuel"
        config.split1 = 0.5
        config.split2 = 0.5
        
        total, m1, m2 = calculate_fixed_lines_total(mock_db, config)
        
        assert total == 1200.0
        assert m1 == 600.0
        assert m2 == 600.0
    
    def test_annual_fixed_lines(self):
        """Should convert annual amounts to monthly."""
        mock_db = MagicMock()
        
        fixed_line = MagicMock()
        fixed_line.amount = 1200.0  # Annual
        fixed_line.freq = "annuelle"
        fixed_line.split_mode = "50/50"
        fixed_line.active = True
        
        mock_db.query().filter().all.return_value = [fixed_line]
        
        config = MagicMock()
        config.split_mode = "manuel"
        config.split1 = 0.5
        config.split2 = 0.5
        
        total, m1, m2 = calculate_fixed_lines_total(mock_db, config)
        
        assert total == 100.0  # 1200 / 12
        assert m1 == 50.0
        assert m2 == 50.0


class TestMonthlyTrends:
    """Test monthly trends calculations with caching."""
    
    @patch('services.calculations._get_from_cache')
    @patch('services.calculations._set_to_cache')
    def test_monthly_trends_cache_miss(self, mock_set_cache, mock_get_cache):
        """Should calculate trends when cache miss occurs."""
        mock_get_cache.return_value = None  # Cache miss
        mock_set_cache.return_value = True
        
        mock_db = MagicMock()
        
        # Mock expenses
        expense_tx = MagicMock()
        expense_tx.amount = -100.0
        mock_db.query().filter().all.return_value = [expense_tx]
        
        months = ["2024-01", "2024-02"]
        result = calculate_monthly_trends(mock_db, months)
        
        assert len(result) == 2
        assert all("month" in trend for trend in result)
        assert all("total_expenses" in trend for trend in result)
        mock_set_cache.assert_called_once()
    
    @patch('services.calculations._get_from_cache')
    def test_monthly_trends_cache_hit(self, mock_get_cache):
        """Should return cached data when available."""
        cached_data = [{"month": "2024-01", "total_expenses": 500}]
        mock_get_cache.return_value = cached_data
        
        mock_db = MagicMock()
        months = ["2024-01"]
        
        result = calculate_monthly_trends(mock_db, months)
        
        assert result == cached_data
        # Should not query database when cache hits
        mock_db.query.assert_not_called()


class TestCategoryBreakdown:
    """Test category breakdown calculations."""
    
    @patch('services.calculations._get_from_cache')
    @patch('services.calculations._set_to_cache')
    def test_category_breakdown_calculation(self, mock_set_cache, mock_get_cache):
        """Should calculate category breakdown correctly."""
        mock_get_cache.return_value = None  # Cache miss
        mock_set_cache.return_value = True
        
        mock_db = MagicMock()
        
        # Mock transactions
        tx1 = MagicMock()
        tx1.category = "Alimentation"
        tx1.amount = -50.0
        
        tx2 = MagicMock()
        tx2.category = "Alimentation"
        tx2.amount = -30.0
        
        tx3 = MagicMock()
        tx3.category = "Transport"
        tx3.amount = -20.0
        
        mock_db.query().filter().all.return_value = [tx1, tx2, tx3]
        
        result = calculate_category_breakdown(mock_db, "2024-01")
        
        assert len(result) == 2
        # Should be sorted by amount descending
        assert result[0]["category"] == "Alimentation"
        assert result[0]["amount"] == 80.0
        assert result[0]["percentage"] == 80.0  # 80/100 * 100
        assert result[1]["category"] == "Transport"
        assert result[1]["amount"] == 20.0


class TestKPISummary:
    """Test KPI summary calculations."""
    
    @patch('services.calculations._get_from_cache')
    @patch('services.calculations._set_to_cache')
    def test_kpi_summary_calculation(self, mock_set_cache, mock_get_cache):
        """Should calculate KPI summary correctly."""
        mock_get_cache.return_value = None
        mock_set_cache.return_value = True
        
        mock_db = MagicMock()
        
        # Mock transactions
        expense_tx = MagicMock()
        expense_tx.amount = -100.0
        expense_tx.month = "2024-01"
        
        income_tx = MagicMock()
        income_tx.amount = 3000.0
        income_tx.month = "2024-01"
        
        mock_db.query().filter().all.return_value = [expense_tx, income_tx]
        
        result = calculate_kpi_summary(mock_db, ["2024-01"])
        
        assert result["total_expenses"] == 100.0
        assert result["total_income"] == 3000.0
        assert result["net_balance"] == 2900.0
        assert result["avg_monthly_expenses"] == 100.0
        assert result["avg_monthly_income"] == 3000.0
        assert abs(result["savings_rate"] - 96.67) < 0.01  # (2900/3000)*100
    
    def test_kpi_summary_empty_months(self):
        """Should handle empty months list."""
        mock_db = MagicMock()
        
        result = calculate_kpi_summary(mock_db, [])
        
        assert result["total_expenses"] == 0
        assert result["total_income"] == 0
        assert result["net_balance"] == 0


class TestDetectAnomalies:
    """Test anomaly detection algorithms."""
    
    @patch('services.calculations._get_from_cache')
    @patch('services.calculations._set_to_cache')
    def test_detect_anomalies_with_outlier(self, mock_set_cache, mock_get_cache):
        """Should detect spending anomalies correctly."""
        mock_get_cache.return_value = None
        mock_set_cache.return_value = True
        
        mock_db = MagicMock()
        
        # Current month transaction (anomaly)
        current_tx = MagicMock()
        current_tx.id = 1
        current_tx.amount = -500.0  # Anomalously high
        current_tx.category = "Alimentation"
        current_tx.label = "Expensive restaurant"
        current_tx.date_op = dt.date(2024, 1, 15)
        current_tx.month = "2024-01"
        
        # Historical transactions (normal amounts)
        hist_tx1 = MagicMock()
        hist_tx1.amount = -50.0
        hist_tx1.category = "Alimentation"
        hist_tx1.month = "2023-12"
        
        hist_tx2 = MagicMock()
        hist_tx2.amount = -60.0
        hist_tx2.category = "Alimentation" 
        hist_tx2.month = "2023-11"
        
        # Mock query calls
        def query_side_effect(*args):
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            
            # First call: current month
            # Second call: historical months
            call_count = getattr(query_side_effect, 'call_count', 0)
            query_side_effect.call_count = call_count + 1
            
            if call_count == 0:
                mock_query.all.return_value = [current_tx]
            else:
                mock_query.all.return_value = [hist_tx1, hist_tx2]
            
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        result = detect_anomalies(mock_db, "2024-01")
        
        assert len(result) > 0
        assert result[0]["transaction_id"] == 1
        assert abs(result[0]["z_score"]) > 2  # Should be anomalous
    
    def test_detect_anomalies_empty_data(self):
        """Should handle empty transaction data."""
        mock_db = MagicMock()
        mock_db.query().filter().all.return_value = []
        
        result = detect_anomalies(mock_db, "2024-01")
        
        assert result == []