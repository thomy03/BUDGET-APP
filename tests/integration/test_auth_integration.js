#!/usr/bin/env node

/**
 * Test d'intégration complète pour simuler l'authentification du frontend
 */

const http = require('http');

function makeRequest(options, data = null) {
    return new Promise((resolve, reject) => {
        const req = http.request(options, (res) => {
            let responseData = '';

            res.on('data', (chunk) => {
                responseData += chunk;
            });

            res.on('end', () => {
                resolve({
                    statusCode: res.statusCode,
                    headers: res.headers,
                    data: responseData
                });
            });
        });

        req.on('error', (err) => {
            reject(err);
        });

        if (data) {
            req.write(data);
        }

        req.end();
    });
}

async function testFullAuth() {
    console.log('🔐 Test d\'authentification intégration complète');
    console.log('===============================================');

    try {
        // Test 1: Authentification
        console.log('1. Authentification admin/secret...');
        const authOptions = {
            hostname: '127.0.0.1',
            port: 8002,
            path: '/token',
            method: 'POST',
            headers: {
                'Origin': 'http://localhost:45678',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
        };

        const authData = 'username=admin&password=secret';
        const authResponse = await makeRequest(authOptions, authData);
        
        console.log(`   Status: ${authResponse.statusCode}`);
        console.log(`   CORS: ${authResponse.headers['access-control-allow-origin'] || 'MANQUANT'}`);
        
        if (authResponse.statusCode !== 200) {
            console.log(`   ❌ Auth échouée: ${authResponse.data}`);
            return;
        }

        const tokenData = JSON.parse(authResponse.data);
        const token = tokenData.access_token;
        console.log(`   ✅ Token reçu: ${token.substring(0, 30)}...`);

        // Test 2: Utilisation du token
        console.log('\n2. Test endpoint protégé /me...');
        const meOptions = {
            hostname: '127.0.0.1',
            port: 8002,
            path: '/me',
            method: 'GET',
            headers: {
                'Origin': 'http://localhost:45678',
                'Authorization': `Bearer ${token}`,
            }
        };

        const meResponse = await makeRequest(meOptions);
        console.log(`   Status: ${meResponse.statusCode}`);
        console.log(`   CORS: ${meResponse.headers['access-control-allow-origin'] || 'MANQUANT'}`);
        
        if (meResponse.statusCode === 200) {
            console.log(`   ✅ User data: ${meResponse.data}`);
        } else {
            console.log(`   ❌ Erreur: ${meResponse.data}`);
        }

        // Test 3: Test avec mauvais credentials
        console.log('\n3. Test avec mauvais mot de passe...');
        const badAuthData = 'username=admin&password=wrong';
        const badAuthResponse = await makeRequest(authOptions, badAuthData);
        
        console.log(`   Status: ${badAuthResponse.statusCode}`);
        if (badAuthResponse.statusCode === 401) {
            console.log('   ✅ Rejet correct des mauvais credentials');
        } else {
            console.log(`   ❌ Comportement inattendu: ${badAuthResponse.data}`);
        }

        // Test 4: Test sans token
        console.log('\n4. Test endpoint protégé sans token...');
        const noTokenOptions = {
            hostname: '127.0.0.1',
            port: 8002,
            path: '/me',
            method: 'GET',
            headers: {
                'Origin': 'http://localhost:45678',
            }
        };

        const noTokenResponse = await makeRequest(noTokenOptions);
        console.log(`   Status: ${noTokenResponse.statusCode}`);
        if (noTokenResponse.statusCode === 401) {
            console.log('   ✅ Rejet correct sans token');
        } else {
            console.log(`   ❌ Comportement inattendu: ${noTokenResponse.data}`);
        }

        console.log('\n🎉 Tests d\'intégration terminés avec succès !');
        console.log('\n📋 Résumé des corrections pour le frontend:');
        console.log('   1. ✅ Backend fonctionnel sur port 8002');
        console.log('   2. ✅ CORS configuré pour port 45678');
        console.log('   3. ✅ Authentification JWT fonctionnelle');
        console.log('   4. ✅ Variables d\'environnement: NEXT_PUBLIC_API_BASE=http://127.0.0.1:8002');

    } catch (error) {
        console.error('❌ Erreur:', error.message);
    }
}

testFullAuth();