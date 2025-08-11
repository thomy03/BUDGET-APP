// Script de diagnostic pour tester l'authentification
const API_BASE = "http://127.0.0.1:5000";

console.log("🔍 DIAGNOSTIC AUTHENTIFICATION");
console.log("API_BASE:", API_BASE);

async function testAuth() {
    try {
        console.log("📡 Test 1: Health check...");
        const healthResponse = await fetch(`${API_BASE}/health`);
        console.log("Health Status:", healthResponse.status, await healthResponse.text());

        console.log("📡 Test 2: Login attempt...");
        const loginResponse = await fetch(`${API_BASE}/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': window.location.origin
            },
            body: new URLSearchParams({
                username: 'admin',
                password: 'secret'
            })
        });

        console.log("Login Status:", loginResponse.status);
        console.log("Login Headers:", Object.fromEntries(loginResponse.headers.entries()));
        
        if (loginResponse.ok) {
            const data = await loginResponse.json();
            console.log("✅ Login successful:", data);
            
            // Test endpoint protégé
            console.log("📡 Test 3: Protected endpoint...");
            const configResponse = await fetch(`${API_BASE}/config`, {
                headers: {
                    'Authorization': `Bearer ${data.access_token}`
                }
            });
            console.log("Config Status:", configResponse.status);
            if (configResponse.ok) {
                console.log("✅ Protected endpoint accessible");
            }
        } else {
            const errorData = await loginResponse.text();
            console.log("❌ Login failed:", errorData);
        }
    } catch (error) {
        console.error("❌ Network error:", error);
        console.log("Error details:", {
            message: error.message,
            code: error.code,
            name: error.name
        });
    }
}

testAuth();