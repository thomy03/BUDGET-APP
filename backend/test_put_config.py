#!/usr/bin/env python3
"""
Test script for PUT /config endpoint
"""
import requests
import json

def test_put_config():
    # Authentification
    login_data = {'username': 'admin', 'password': 'admin123'}
    response = requests.post('http://localhost:8000/token', data=login_data)
    print(f'Token Response Status: {response.status_code}')
    
    if response.status_code != 200:
        print(f'Erreur authentification: {response.text}')
        return False

    token_data = response.json()
    print(f'Token obtenu: {list(token_data.keys())}')
    token = token_data['access_token']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    # Test de l'endpoint PUT /config
    test_config = {
        'member1': 'diana',
        'member2': 'thomas', 
        'rev1': 2500.0,
        'rev2': 3200.0,
        'split_mode': 'revenus',
        'split1': 0.5,
        'split2': 0.5,
        'other_split_mode': 'clé',
        'var_percent': 30.0,
        'max_var': 1000.0,
        'min_fixed': 500.0
    }

    print('\n=== TEST PUT /config ===')
    response = requests.put('http://localhost:8000/config', json=test_config, headers=headers)
    print(f'Status Code: {response.status_code}')
    
    if response.status_code == 200:
        print('✅ PUT /config fonctionne!')
        result = response.json()
        print(f'Config ID: {result["id"]}')
        print(f'Rev1: {result["rev1"]}, Rev2: {result["rev2"]}')
        print(f'Updated at: {result["updated_at"]}')
    else:
        print(f'❌ Erreur: {response.status_code}')
        print(f'Response: {response.text}')
        return False

    # Vérifier avec GET
    print('\n=== VERIFICATION GET /config ===')
    response = requests.get('http://localhost:8000/config', headers=headers)
    print(f'GET Status Code: {response.status_code}')
    
    if response.status_code == 200:
        result = response.json()
        print(f'Rev1: {result["rev1"]}, Rev2: {result["rev2"]}')
        return True
    else:
        print(f'❌ Erreur GET: {response.text}')
        return False

if __name__ == '__main__':
    success = test_put_config()
    print(f'\n{"✅ SUCCESS" if success else "❌ FAILED"}')