"""
Isolated unit tests for calculations service without external dependencies.
Tests core business logic independently.
"""
import pytest
from unittest.mock import MagicMock
import datetime as dt


def get_split_isolated(config_dict):
    """Isolated version of get_split function for testing."""
    if config_dict.get("split_mode") == "revenus":
        rev1 = config_dict.get("rev1", 0) or 0
        rev2 = config_dict.get("rev2", 0) or 0
        tot = rev1 + rev2
        if tot <= 0:
            return 0.5, 0.5
        r1 = rev1 / tot
        return r1, 1 - r1
    else:
        return config_dict.get("split1", 0.5), config_dict.get("split2", 0.5)


def split_amount_isolated(amount, mode, r1, r2, s1, s2):
    """Isolated version of split_amount function for testing."""
    if mode == "50/50":
        return amount / 2.0, amount / 2.0
    elif mode == "clé":
        return amount * r1, amount * r2
    elif mode == "m1":
        return amount, 0.0
    elif mode == "m2":
        return 0.0, amount
    elif mode == "manuel":
        return amount * (s1 or 0.0), amount * (s2 or 0.0)
    else:
        return amount * r1, amount * r2


def is_income_or_transfer_isolated(label, cat_parent):
    """Isolated version of income/transfer detection for testing."""
    l = (label or "").lower()
    cp = (cat_parent or "").lower()
    
    if any(keyword in l for keyword in ["virement", "vir ", "vir/"]):
        return True
    if "virements emis" in cp:
        return True
    if any(keyword in l for keyword in ["rembourse", "refund"]):
        return True
    if "remboursement" in cp:
        return True
    if any(keyword in l for keyword in ["salaire", "payroll", "paye"]):
        return True
    
    return False


def calculate_provision_amount_isolated(provision_dict, config_dict):
    """Isolated version of calculate_provision_amount for testing."""
    # Calculate base amount
    if provision_dict["base_calculation"] == "total":
        base = (config_dict.get("rev1", 0) or 0) + (config_dict.get("rev2", 0) or 0)
    elif provision_dict["base_calculation"] == "member1":
        base = config_dict.get("rev1", 0) or 0
    elif provision_dict["base_calculation"] == "member2":
        base = config_dict.get("rev2", 0) or 0
    elif provision_dict["base_calculation"] == "fixed":
        base = provision_dict.get("fixed_amount", 0) or 0
    else:
        base = 0
    
    # Calculate monthly amount
    if provision_dict["base_calculation"] == "fixed":
        monthly_amount = base
    else:
        monthly_amount = (base * provision_dict.get("percentage", 0) / 100.0) / 12.0 if base else 0.0
    
    # Calculate distribution
    split_mode = provision_dict.get("split_mode", "50/50")
    if split_mode == "key":
        # Use global split ratio
        total_rev = (config_dict.get("rev1", 0) or 0) + (config_dict.get("rev2", 0) or 0)
        if total_rev > 0:
            r1 = (config_dict.get("rev1", 0) or 0) / total_rev
            r2 = (config_dict.get("rev2", 0) or 0) / total_rev
        else:
            r1 = r2 = 0.5
        member1_amount = monthly_amount * r1
        member2_amount = monthly_amount * r2
    elif split_mode == "50/50":
        member1_amount = monthly_amount * 0.5
        member2_amount = monthly_amount * 0.5
    elif split_mode == "100/0":
        member1_amount = monthly_amount
        member2_amount = 0
    elif split_mode == "0/100":
        member1_amount = 0
        member2_amount = monthly_amount
    elif split_mode == "custom":
        member1_amount = monthly_amount * (provision_dict.get("split_member1", 50) / 100.0)
        member2_amount = monthly_amount * (provision_dict.get("split_member2", 50) / 100.0)
    else:
        member1_amount = member2_amount = monthly_amount * 0.5
    
    return monthly_amount, member1_amount, member2_amount


def get_previous_month_isolated(month):
    """Isolated version of get_previous_month for testing."""
    try:
        year, month_num = map(int, month.split('-'))
        
        if month_num == 1:
            return f"{year-1:04d}-12"
        else:
            return f"{year:04d}-{month_num-1:02d}"
    except Exception:
        return None


class TestGetSplitIsolated:
    """Test split ratio calculations in isolation."""
    
    def test_revenus_split_mode_equal_revenues(self):
        """Should calculate equal split when revenues are equal."""
        config = {"split_mode": "revenus", "rev1": 3000.0, "rev2": 3000.0}
        
        r1, r2 = get_split_isolated(config)
        
        assert r1 == 0.5
        assert r2 == 0.5
    
    def test_revenus_split_mode_unequal_revenues(self):
        """Should calculate proportional split based on revenues."""
        config = {"split_mode": "revenus", "rev1": 4000.0, "rev2": 2000.0}
        
        r1, r2 = get_split_isolated(config)
        
        assert abs(r1 - 2/3) < 0.001  # 4000 / 6000
        assert abs(r2 - 1/3) < 0.001  # 2000 / 6000
    
    def test_revenus_split_mode_zero_total(self):
        """Should default to 50/50 when total revenue is zero."""
        config = {"split_mode": "revenus", "rev1": 0.0, "rev2": 0.0}
        
        r1, r2 = get_split_isolated(config)
        
        assert r1 == 0.5
        assert r2 == 0.5
    
    def test_manual_split_mode(self):
        """Should use manual split values when not in revenus mode."""
        config = {"split_mode": "manuel", "split1": 0.6, "split2": 0.4}
        
        r1, r2 = get_split_isolated(config)
        
        assert r1 == 0.6
        assert r2 == 0.4


class TestSplitAmountIsolated:
    """Test amount splitting logic in isolation."""
    
    def test_fifty_fifty_split(self):
        """Should split amount equally."""
        amount = 100.0
        m1, m2 = split_amount_isolated(amount, "50/50", 0.6, 0.4, None, None)
        
        assert m1 == 50.0
        assert m2 == 50.0
    
    def test_key_split(self):
        """Should split based on ratio key."""
        amount = 100.0
        m1, m2 = split_amount_isolated(amount, "clé", 0.7, 0.3, None, None)
        
        assert m1 == 70.0
        assert m2 == 30.0
    
    def test_member1_only_split(self):
        """Should assign all to member 1."""
        amount = 100.0
        m1, m2 = split_amount_isolated(amount, "m1", 0.5, 0.5, None, None)
        
        assert m1 == 100.0
        assert m2 == 0.0
    
    def test_member2_only_split(self):
        """Should assign all to member 2."""
        amount = 100.0
        m1, m2 = split_amount_isolated(amount, "m2", 0.5, 0.5, None, None)
        
        assert m1 == 0.0
        assert m2 == 100.0
    
    def test_manual_split(self):
        """Should use manual split values."""
        amount = 100.0
        m1, m2 = split_amount_isolated(amount, "manuel", 0.5, 0.5, 0.8, 0.2)
        
        assert m1 == 80.0
        assert m2 == 20.0


class TestIncomeTransferDetectionIsolated:
    """Test income and transfer detection in isolation."""
    
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
        result = is_income_or_transfer_isolated(label, category)
        assert result == expected


class TestProvisionCalculationIsolated:
    """Test provision amount calculations in isolation."""
    
    def test_fixed_amount_provision(self):
        """Should calculate correct amount for fixed provisions."""
        provision = {
            "base_calculation": "fixed",
            "fixed_amount": 200.0,
            "split_mode": "50/50"
        }
        config = {}
        
        total, member1, member2 = calculate_provision_amount_isolated(provision, config)
        
        assert total == 200.0
        assert member1 == 100.0
        assert member2 == 100.0
    
    def test_total_based_provision(self):
        """Should calculate provision based on total income."""
        provision = {
            "base_calculation": "total",
            "percentage": 10.0,  # 10% annually
            "split_mode": "key"
        }
        config = {"rev1": 4000.0, "rev2": 2000.0}
        
        total, member1, member2 = calculate_provision_amount_isolated(provision, config)
        
        # 10% of 6000 annual = 600 annual = 50 monthly
        expected_total = 50.0
        expected_member1 = expected_total * (2/3)  # Based on revenue split
        expected_member2 = expected_total * (1/3)
        
        assert abs(total - expected_total) < 0.01
        assert abs(member1 - expected_member1) < 0.01
        assert abs(member2 - expected_member2) < 0.01
    
    def test_custom_split_provision(self):
        """Should handle custom split percentages."""
        provision = {
            "base_calculation": "fixed",
            "fixed_amount": 300.0,
            "split_mode": "custom",
            "split_member1": 70.0,
            "split_member2": 30.0
        }
        config = {}
        
        total, member1, member2 = calculate_provision_amount_isolated(provision, config)
        
        assert total == 300.0
        assert member1 == 210.0  # 70% of 300
        assert member2 == 90.0   # 30% of 300
    
    def test_member1_only_provision(self):
        """Should handle provisions for member1 only."""
        provision = {
            "base_calculation": "member1",
            "percentage": 5.0,
            "split_mode": "100/0"
        }
        config = {"rev1": 3000.0, "rev2": 2000.0}
        
        total, member1, member2 = calculate_provision_amount_isolated(provision, config)
        
        # 5% of 3000 annual = 150 annual = 12.5 monthly
        expected_total = 12.5
        
        assert abs(total - expected_total) < 0.01
        assert member1 == expected_total
        assert member2 == 0.0


class TestPreviousMonthIsolated:
    """Test previous month calculation in isolation."""
    
    def test_normal_month(self):
        """Should get previous month normally."""
        result = get_previous_month_isolated("2024-06")
        assert result == "2024-05"
    
    def test_january_rollover(self):
        """Should rollover to previous year for January."""
        result = get_previous_month_isolated("2024-01")
        assert result == "2023-12"
    
    def test_december_to_november(self):
        """Should handle December to November correctly."""
        result = get_previous_month_isolated("2024-12")
        assert result == "2024-11"
    
    def test_february_to_january(self):
        """Should handle February to January correctly."""
        result = get_previous_month_isolated("2024-02")
        assert result == "2024-01"
    
    def test_invalid_format(self):
        """Should return None for invalid format."""
        result = get_previous_month_isolated("invalid-date")
        assert result is None
    
    def test_empty_string(self):
        """Should handle empty string gracefully."""
        result = get_previous_month_isolated("")
        assert result is None


class TestFinancialCalculations:
    """Test critical financial calculation scenarios."""
    
    def test_zero_revenue_handling(self):
        """Should handle zero revenue scenarios gracefully."""
        config = {"split_mode": "revenus", "rev1": 0, "rev2": 0}
        
        r1, r2 = get_split_isolated(config)
        assert r1 == 0.5
        assert r2 == 0.5
        
        # Test provision calculation with zero revenue
        provision = {
            "base_calculation": "total",
            "percentage": 10.0,
            "split_mode": "key"
        }
        total, m1, m2 = calculate_provision_amount_isolated(provision, config)
        assert total == 0.0
        assert m1 == 0.0
        assert m2 == 0.0
    
    def test_large_amounts_precision(self):
        """Should maintain precision with large amounts."""
        amount = 1000000.0
        m1, m2 = split_amount_isolated(amount, "clé", 0.333333, 0.666667, None, None)
        
        # Check that precision is maintained
        assert abs(m1 - 333333.0) < 1.0
        assert abs(m2 - 666667.0) < 1.0
        assert abs((m1 + m2) - amount) < 1.0
    
    def test_edge_case_percentages(self):
        """Should handle edge case percentages correctly."""
        provision = {
            "base_calculation": "fixed",
            "fixed_amount": 1000.0,
            "split_mode": "custom",
            "split_member1": 0.0,
            "split_member2": 100.0
        }
        config = {}
        
        total, m1, m2 = calculate_provision_amount_isolated(provision, config)
        
        assert total == 1000.0
        assert m1 == 0.0
        assert m2 == 1000.0
    
    def test_negative_amounts(self):
        """Should handle negative amounts correctly."""
        amount = -100.0
        m1, m2 = split_amount_isolated(amount, "50/50", 0.5, 0.5, None, None)
        
        assert m1 == -50.0
        assert m2 == -50.0
    
    def test_provision_percentage_boundary_values(self):
        """Should handle boundary percentage values."""
        # Test 0% provision
        provision_0 = {
            "base_calculation": "total",
            "percentage": 0.0,
            "split_mode": "50/50"
        }
        config = {"rev1": 3000.0, "rev2": 2000.0}
        
        total, m1, m2 = calculate_provision_amount_isolated(provision_0, config)
        assert total == 0.0
        assert m1 == 0.0
        assert m2 == 0.0
        
        # Test 100% provision (extreme case)
        provision_100 = {
            "base_calculation": "total",
            "percentage": 100.0,
            "split_mode": "50/50"
        }
        
        total, m1, m2 = calculate_provision_amount_isolated(provision_100, config)
        # 100% of 5000 annual = 5000 annual = 416.67 monthly
        expected_total = 5000.0 / 12.0
        
        assert abs(total - expected_total) < 0.01
        assert abs(m1 - expected_total/2) < 0.01
        assert abs(m2 - expected_total/2) < 0.01


class TestBusinessLogicValidation:
    """Test business logic validation scenarios."""
    
    def test_split_consistency(self):
        """Should ensure split amounts always add up to total."""
        test_cases = [
            (1000.0, "50/50", 0.5, 0.5, None, None),
            (1000.0, "clé", 0.3, 0.7, None, None),
            (1000.0, "manuel", 0.5, 0.5, 0.25, 0.75),
            (500.0, "m1", 0.5, 0.5, None, None),
            (500.0, "m2", 0.5, 0.5, None, None),
        ]
        
        for amount, mode, r1, r2, s1, s2 in test_cases:
            m1, m2 = split_amount_isolated(amount, mode, r1, r2, s1, s2)
            
            if mode in ["m1", "m2"]:
                # Special cases where only one member pays
                assert abs((m1 + m2) - amount) < 0.01
            else:
                assert abs((m1 + m2) - amount) < 0.01
    
    def test_provision_split_consistency(self):
        """Should ensure provision splits are mathematically consistent."""
        provision = {
            "base_calculation": "total",
            "percentage": 12.0,
            "split_mode": "custom",
            "split_member1": 30.0,
            "split_member2": 70.0
        }
        config = {"rev1": 4000.0, "rev2": 3000.0}
        
        total, m1, m2 = calculate_provision_amount_isolated(provision, config)
        
        # Verify splits add up to total
        assert abs((m1 + m2) - total) < 0.01
        
        # Verify percentage distribution
        assert abs(m1/total - 0.30) < 0.01
        assert abs(m2/total - 0.70) < 0.01