#!/usr/bin/env python3
"""
Test script for couple balance endpoints
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.orm import Session
from models.database import SessionLocal, Config, FixedLine, CustomProvision, Transaction
from routers.couple_balance import calculate_member_provisions, get_couple_balance
from utils.core_functions import ensure_default_config
from datetime import datetime

def test_couple_balance():
    """Test the couple balance calculation"""
    db = SessionLocal()
    
    try:
        # Setup test configuration
        config = ensure_default_config(db)
        config.member1 = "Diana"
        config.member2 = "Thomas"
        config.rev1 = 3000.0  # Diana's gross income
        config.rev2 = 4000.0  # Thomas's gross income
        config.tax_rate1 = 15.0  # Diana's tax rate
        config.tax_rate2 = 20.0  # Thomas's tax rate
        config.split_mode = "revenus"  # Proportional to income
        db.commit()
        
        # Add some test fixed expenses
        test_fixed = [
            FixedLine(label="Loyer", amount=1200, freq="mensuelle", active=True),
            FixedLine(label="Internet", amount=40, freq="mensuelle", active=True),
            FixedLine(label="Assurance", amount=300, freq="trimestrielle", active=True),
        ]
        
        for fixed in test_fixed:
            existing = db.query(FixedLine).filter_by(label=fixed.label).first()
            if not existing:
                db.add(fixed)
        db.commit()
        
        # Add test provisions
        test_provisions = [
            CustomProvision(
                name="Épargne vacances",
                percentage=10,
                base_calculation="revenue_net",
                is_active=True,
                created_by="admin",
                split_mode="proportionnel"
            ),
            CustomProvision(
                name="Épargne urgence",
                percentage=0,  # Required field even for fixed amounts
                fixed_amount=200,
                base_calculation="fixed",
                is_active=True,
                created_by="admin",
                split_mode="proportionnel"
            )
        ]
        
        for provision in test_provisions:
            existing = db.query(CustomProvision).filter_by(name=provision.name).first()
            if not existing:
                db.add(provision)
        db.commit()
        
        # Calculate fixed charges total
        fixed_lines = db.query(FixedLine).filter(FixedLine.active == True).all()
        fixed_charges_total = sum(
            line.amount / (1 if line.freq == "mensuelle" else 3 if line.freq == "trimestrielle" else 12)
            for line in fixed_lines
        )
        print(f"Total fixed charges: {fixed_charges_total:.2f}€/month")
        
        # Calculate custom provisions total
        custom_provisions = db.query(CustomProvision).filter(
            CustomProvision.is_active == True
        ).all()
        
        custom_provisions_total = 0
        for provision in custom_provisions:
            if provision.base_calculation == "fixed":
                monthly_amount = provision.fixed_amount or 0
            elif provision.base_calculation == "revenue_net":
                total_net = (config.rev1 * (1 - config.tax_rate1 / 100) + 
                           config.rev2 * (1 - config.tax_rate2 / 100))
                monthly_amount = total_net * (provision.percentage / 100)
            else:
                monthly_amount = 0
            custom_provisions_total += monthly_amount
        print(f"Total custom provisions: {custom_provisions_total:.2f}€/month")
        
        # Calculate member provisions
        distribution_mode = "proportionnel" if config.split_mode == "revenus" else config.split_mode
        
        member1_data = calculate_member_provisions(
            config, 1, fixed_charges_total, custom_provisions_total, distribution_mode
        )
        member2_data = calculate_member_provisions(
            config, 2, fixed_charges_total, custom_provisions_total, distribution_mode
        )
        
        print("\n=== COUPLE BALANCE CALCULATION ===")
        print(f"\n{config.member1}:")
        print(f"  Gross income: {member1_data['gross_income']:.2f}€")
        print(f"  Tax rate: {member1_data['tax_rate']:.2f}%")
        print(f"  Net income: {member1_data['net_income']:.2f}€")
        print(f"  Fixed charges share: {member1_data['fixed_charges_share']:.2f}€")
        print(f"  Provisions share: {member1_data['custom_provisions_share']:.2f}€")
        print(f"  Total to provision: {member1_data['total_provision_required']:.2f}€")
        print(f"  % of net income: {member1_data['provision_percentage']:.2f}%")
        
        print(f"\n{config.member2}:")
        print(f"  Gross income: {member2_data['gross_income']:.2f}€")
        print(f"  Tax rate: {member2_data['tax_rate']:.2f}%")
        print(f"  Net income: {member2_data['net_income']:.2f}€")
        print(f"  Fixed charges share: {member2_data['fixed_charges_share']:.2f}€")
        print(f"  Provisions share: {member2_data['custom_provisions_share']:.2f}€")
        print(f"  Total to provision: {member2_data['total_provision_required']:.2f}€")
        print(f"  % of net income: {member2_data['provision_percentage']:.2f}%")
        
        print(f"\nDistribution mode: {distribution_mode}")
        print(f"Total net income: {member1_data['net_income'] + member2_data['net_income']:.2f}€")
        print(f"Total provisions required: {member1_data['total_provision_required'] + member2_data['total_provision_required']:.2f}€")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_couple_balance()
    sys.exit(0 if success else 1)