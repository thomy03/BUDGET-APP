#!/usr/bin/env node

/**
 * Test CORS détaillé pour simuler le comportement du browser
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

async function testCORS() {
    console.log('🌐 Test CORS détaillé');
    console.log('===================');

    try {
        // Test preflight OPTIONS pour /token
        console.log('1. Test preflight OPTIONS /token...');
        const preflightOptions = {
            hostname: '127.0.0.1',
            port: 8002,
            path: '/token',
            method: 'OPTIONS',
            headers: {
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'content-type'
            }
        };

        const preflightResponse = await makeRequest(preflightOptions);
        console.log(`   Status: ${preflightResponse.statusCode}`);
        console.log('   Headers CORS:');
        
        const corsHeaders = [
            'access-control-allow-origin',
            'access-control-allow-methods', 
            'access-control-allow-headers',
            'access-control-allow-credentials'
        ];
        
        corsHeaders.forEach(header => {
            if (preflightResponse.headers[header]) {
                console.log(`   ✅ ${header}: ${preflightResponse.headers[header]}`);
            } else {
                console.log(`   ❌ ${header}: MANQUANT`);
            }
        });

        // Test POST /token avec Origin
        console.log('\n2. Test POST /token avec Origin header...');
        const authOptions = {
            hostname: '127.0.0.1',
            port: 8002,
            path: '/token',
            method: 'POST',
            headers: {
                'Origin': 'http://localhost:3000',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
        };

        const authData = 'username=admin&password=secret';
        const authResponse = await makeRequest(authOptions, authData);
        
        console.log(`   Status: ${authResponse.statusCode}`);
        console.log(`   Access-Control-Allow-Origin: ${authResponse.headers['access-control-allow-origin'] || 'MANQUANT'}`);
        
        if (authResponse.statusCode === 200) {
            const tokenData = JSON.parse(authResponse.data);
            console.log(`   ✅ Auth réussie, token: ${tokenData.access_token.substring(0, 20)}...`);
        } else {
            console.log(`   ❌ Auth échouée: ${authResponse.data}`);
        }

        // Test depuis le port frontend Next.js
        console.log('\n3. Test avec Origin Next.js (port 45678)...');
        const nextjsOptions = {
            ...authOptions,
            headers: {
                ...authOptions.headers,
                'Origin': 'http://localhost:45678'
            }
        };

        const nextjsResponse = await makeRequest(nextjsOptions, authData);
        console.log(`   Status: ${nextjsResponse.statusCode}`);
        console.log(`   CORS Header: ${nextjsResponse.headers['access-control-allow-origin'] || 'MANQUANT'}`);

    } catch (error) {
        console.error('❌ Erreur:', error.message);
    }
}

testCORS();