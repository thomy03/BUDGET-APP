#!/usr/bin/env node

/**
 * Script Node.js pour tester la connectivité frontend -> backend
 */

const http = require('http');

function testEndpoint(host, port, path, method = 'GET', data = null) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: host,
            port: port,
            path: path,
            method: method,
            headers: {
                'Content-Type': method === 'POST' ? 'application/x-www-form-urlencoded' : 'application/json',
            }
        };

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

        if (data && method === 'POST') {
            req.write(data);
        }

        req.end();
    });
}

async function runTests() {
    console.log('🔍 Tests de connectivité Frontend -> Backend');
    console.log('===============================================');

    try {
        // Test 1: Health check
        console.log('1. Test /health...');
        const healthResponse = await testEndpoint('127.0.0.1', 8002, '/health');
        console.log(`   ✅ Status: ${healthResponse.statusCode}`);
        console.log(`   📄 Response: ${healthResponse.data}`);

        // Test 2: Root endpoint
        console.log('\n2. Test / (root)...');
        const rootResponse = await testEndpoint('127.0.0.1', 8002, '/');
        console.log(`   ✅ Status: ${rootResponse.statusCode}`);
        console.log(`   📄 Response: ${rootResponse.data}`);

        // Test 3: Authentification
        console.log('\n3. Test /token (auth)...');
        const authData = 'username=admin&password=secret';
        const authResponse = await testEndpoint('127.0.0.1', 8002, '/token', 'POST', authData);
        console.log(`   ✅ Status: ${authResponse.statusCode}`);
        console.log(`   📄 Response: ${authResponse.data}`);

        if (authResponse.statusCode === 200) {
            const tokenData = JSON.parse(authResponse.data);
            console.log(`   🔑 Token reçu: ${tokenData.access_token.substring(0, 20)}...`);
        }

        // Test 4: CORS headers
        console.log('\n4. Vérification CORS headers...');
        const corsHeaders = healthResponse.headers;
        if (corsHeaders['access-control-allow-origin']) {
            console.log(`   ✅ CORS Origin: ${corsHeaders['access-control-allow-origin']}`);
        } else {
            console.log('   ❌ Pas de header CORS Origin trouvé');
        }

    } catch (error) {
        console.error('❌ Erreur:', error.message);
    }
}

runTests();