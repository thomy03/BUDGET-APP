import unittest
import requests
import json
from datetime import datetime, timedelta

class TestCustomProvisionsE2E(unittest.TestCase):
    BASE_URL = "http://localhost:5000/api"  # Ajustez selon votre configuration
    
    def setUp(self):
        # Authentification et préparation des tests
        self.token = self._login()
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    def _login(self):
        """Authentification pour les tests"""
        login_data = {
            'username': 'test_user',
            'password': 'test_password'
        }
        response = requests.post(f"{self.BASE_URL}/login", json=login_data)
        return response.json()['access_token']
    
    def test_create_investment_provision(self):
        """Scénario: Créer une provision d'investissement à 10%"""
        provision_data = {
            'name': 'Investissement Test',
            'percentage': 10.0,
            'calculation_base': 'revenu_net',
            'members_distribution': {'user1': 1.0}
        }
        
        response = requests.post(
            f"{self.BASE_URL}/custom_provisions", 
            headers=self.headers,
            json=provision_data
        )
        
        self.assertEqual(response.status_code, 201)
        created_provision = response.json()
        self.assertEqual(created_provision['name'], 'Investissement Test')
        self.assertEqual(created_provision['percentage'], 10.0)
    
    def test_modify_existing_provision(self):
        """Scénario: Modifier une provision existante"""
        # D'abord créer une provision
        provision_data = {
            'name': 'Provision à Modifier',
            'percentage': 5.0,
            'calculation_base': 'revenu_total'
        }
        create_response = requests.post(
            f"{self.BASE_URL}/custom_provisions", 
            headers=self.headers,
            json=provision_data
        )
        provision_id = create_response.json()['id']
        
        # Modifier la provision
        update_data = {
            'name': 'Provision Modifiée',
            'percentage': 7.5,
            'calculation_base': 'revenu_net'
        }
        
        response = requests.put(
            f"{self.BASE_URL}/custom_provisions/{provision_id}", 
            headers=self.headers,
            json=update_data
        )
        
        self.assertEqual(response.status_code, 200)
        updated_provision = response.json()
        self.assertEqual(updated_provision['name'], 'Provision Modifiée')
        self.assertEqual(updated_provision['percentage'], 7.5)
    
    def test_delete_provision(self):
        """Scénario: Supprimer une provision"""
        # Créer une provision à supprimer
        provision_data = {
            'name': 'Provision à Supprimer',
            'percentage': 3.0,
            'calculation_base': 'revenu_net'
        }
        create_response = requests.post(
            f"{self.BASE_URL}/custom_provisions", 
            headers=self.headers,
            json=provision_data
        )
        provision_id = create_response.json()['id']
        
        # Supprimer la provision
        response = requests.delete(
            f"{self.BASE_URL}/custom_provisions/{provision_id}", 
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 204)
    
    def test_provisions_in_summary(self):
        """Scénario: Vérifier que les provisions apparaissent dans le summary"""
        # Créer quelques provisions
        provisions_data = [
            {
                'name': 'Investissement Summary',
                'percentage': 10.0,
                'calculation_base': 'revenu_net'
            },
            {
                'name': 'Épargne Summary',
                'percentage': 15.0,
                'calculation_base': 'revenu_total'
            }
        ]
        
        for provision_data in provisions_data:
            requests.post(
                f"{self.BASE_URL}/custom_provisions", 
                headers=self.headers,
                json=provision_data
            )
        
        # Récupérer le summary
        response = requests.get(
            f"{self.BASE_URL}/budget_summary", 
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 200)
        summary = response.json()
        
        # Vérifier que les provisions sont présentes
        provision_names = [p['name'] for p in summary.get('custom_provisions', [])]
        self.assertIn('Investissement Summary', provision_names)
        self.assertIn('Épargne Summary', provision_names)
    
    def test_temporary_provision_expiration(self):
        """Scénario: Provision temporaire qui expire"""
        now = datetime.now()
        provision_data = {
            'name': 'Provision Temporaire',
            'percentage': 5.0,
            'calculation_base': 'revenu_net',
            'start_date': (now - timedelta(days=10)).isoformat(),
            'end_date': (now - timedelta(days=1)).isoformat()
        }
        
        response = requests.post(
            f"{self.BASE_URL}/custom_provisions", 
            headers=self.headers,
            json=provision_data
        )
        
        # Vérifier que la provision n'est plus active
        summary_response = requests.get(
            f"{self.BASE_URL}/budget_summary", 
            headers=self.headers
        )
        
        summary = summary_response.json()
        temporary_provisions = [
            p for p in summary.get('custom_provisions', []) 
            if p['name'] == 'Provision Temporaire'
        ]
        
        self.assertEqual(len(temporary_provisions), 0, "La provision expirée ne devrait pas apparaître")

    def test_goal_tracking(self):
        """Scénario: Atteindre un objectif de provision"""
        provision_data = {
            'name': 'Objectif Vacances',
            'percentage': 20.0,
            'calculation_base': 'revenu_net',
            'goal_amount': 5000,
            'current_amount': 0
        }
        
        # Créer la provision
        create_response = requests.post(
            f"{self.BASE_URL}/custom_provisions", 
            headers=self.headers,
            json=provision_data
        )
        provision_id = create_response.json()['id']
        
        # Simuler des versements
        for _ in range(5):
            # Simuler un revenu et un calcul de provision
            income_data = {
                'revenu_net': 5000,
                'provision_id': provision_id
            }
            requests.post(
                f"{self.BASE_URL}/income_processed", 
                headers=self.headers,
                json=income_data
            )
        
        # Vérifier l'état de l'objectif
        goal_response = requests.get(
            f"{self.BASE_URL}/custom_provisions/{provision_id}/goal", 
            headers=self.headers
        )
        
        goal_status = goal_response.json()
        self.assertTrue(goal_status['goal_reached'])
        self.assertGreaterEqual(goal_status['current_amount'], goal_status['goal_amount'])

if __name__ == '__main__':
    unittest.main()