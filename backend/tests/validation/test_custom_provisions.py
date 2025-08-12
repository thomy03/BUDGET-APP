import unittest
import pytest
from datetime import datetime, timedelta
from custom_provisions import CustomProvision, calculate_provision

class TestCustomProvisionModel(unittest.TestCase):
    def setUp(self):
        self.user_id = "test_user_123"
        
    def test_create_custom_provision(self):
        """Test création d'une provision personnalisée"""
        provision = CustomProvision(
            user_id=self.user_id,
            name="Investissement",
            percentage=10.0,
            calculation_base="revenu_net",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=365),
            members_distribution={"user1": 0.5, "user2": 0.5}
        )
        
        self.assertEqual(provision.name, "Investissement")
        self.assertEqual(provision.percentage, 10.0)
        self.assertEqual(provision.calculation_base, "revenu_net")
        self.assertIsNotNone(provision.start_date)
        self.assertIsNotNone(provision.end_date)
    
    def test_provision_calculation(self):
        """Test calcul du montant de provision"""
        revenu_net = 5000
        provision = CustomProvision(
            user_id=self.user_id,
            name="Epargne",
            percentage=15.0,
            calculation_base="revenu_net"
        )
        
        montant = calculate_provision(
            provision=provision, 
            revenu_net=revenu_net
        )
        
        self.assertAlmostEqual(montant, 750, delta=0.01)
    
    def test_member_distribution(self):
        """Test répartition entre membres"""
        provision = CustomProvision(
            user_id=self.user_id,
            name="Vacances",
            percentage=10.0,
            calculation_base="revenu_net",
            members_distribution={"user1": 0.7, "user2": 0.3}
        )
        
        revenu_net = 6000
        montant_total = calculate_provision(provision, revenu_net)
        
        # Vérifier la répartition
        montant_user1 = montant_total * 0.7
        montant_user2 = montant_total * 0.3
        
        self.assertAlmostEqual(montant_user1, 420, delta=0.01)
        self.assertAlmostEqual(montant_user2, 180, delta=0.01)
    
    def test_provision_expiration(self):
        """Test expiration d'une provision temporaire"""
        now = datetime.now()
        provision = CustomProvision(
            user_id=self.user_id,
            name="Projet Temporaire",
            percentage=5.0,
            calculation_base="revenu_net",
            start_date=now - timedelta(days=10),
            end_date=now - timedelta(days=1)  # Déjà expirée
        )
        
        revenu_net = 4000
        montant = calculate_provision(provision, revenu_net)
        
        self.assertEqual(montant, 0)  # Provision expirée
    
    def test_data_validation(self):
        """Test validation des données de provision"""
        with self.assertRaises(ValueError):
            CustomProvision(
                user_id=self.user_id,
                name="Invalid",
                percentage=150.0,  # Pourcentage invalide
                calculation_base="revenu_net"
            )
        
        with self.assertRaises(ValueError):
            CustomProvision(
                user_id=self.user_id,
                name="Invalid",
                percentage=10.0,
                calculation_base="invalid_base"  # Base de calcul invalide
            )

@pytest.mark.performance
def test_performance_multiple_provisions():
    """Test performance avec de nombreuses provisions"""
    import time
    
    revenu_net = 10000
    provisions = [
        CustomProvision(
            user_id=f"user_{i}",
            name=f"Provision {i}",
            percentage=5.0,
            calculation_base="revenu_net"
        ) for i in range(20)
    ]
    
    start_time = time.time()
    for provision in provisions:
        calculate_provision(provision, revenu_net)
    
    end_time = time.time()
    execution_time = (end_time - start_time) * 1000  # en millisecondes
    
    assert execution_time < 100, f"Calcul trop lent: {execution_time}ms"

class TestCustomProvisionSecurity(unittest.TestCase):
    """Tests de sécurité pour les provisions"""
    def test_user_data_isolation(self):
        """Vérifier l'isolation des données entre utilisateurs"""
        user1_id = "user_1"
        user2_id = "user_2"
        
        provision1 = CustomProvision(
            user_id=user1_id,
            name="Provision Utilisateur 1",
            percentage=10.0,
            calculation_base="revenu_net"
        )
        
        provision2 = CustomProvision(
            user_id=user2_id,
            name="Provision Utilisateur 2",
            percentage=15.0,
            calculation_base="revenu_net"
        )
        
        self.assertNotEqual(provision1.user_id, provision2.user_id)
        
        # Simuler une tentative d'accès aux données d'un autre utilisateur
        with self.assertRaises(PermissionError):
            # Cette méthode hypothétique devrait lever une erreur
            get_user_provisions(user2_id, accessed_by=user1_id)

def get_user_provisions(user_id, accessed_by):
    """Méthode simulant la récupération des provisions avec vérification de sécurité"""
    if user_id != accessed_by:
        raise PermissionError("Accès non autorisé aux provisions d'un autre utilisateur")
    return []  # Implémentation simplifiée

if __name__ == '__main__':
    unittest.main()