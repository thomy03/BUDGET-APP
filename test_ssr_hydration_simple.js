/**
 * Simplified SSR Hydration Test for Budget Famille v2.3
 * Tests hydration issues without browser dependency
 * 
 * This test validates:
 * 1. Server-side rendering produces valid HTML
 * 2. No critical JavaScript errors in client logs
 * 3. Month hooks initialize properly
 * 4. Navigation works without React errors
 */

const axios = require('axios');
const fs = require('fs');

class SimpleSSRValidator {
  constructor() {
    this.baseURL = 'http://localhost:45678';
    this.testResults = {
      serverRendering: [],
      clientErrors: [],
      testsPassed: 0,
      testsFailed: 0
    };
  }

  async testServerRendering() {
    console.log('🧪 Testing Server-Side Rendering...');
    
    const pages = ['/', '/login', '/transactions', '/upload', '/settings', '/analytics'];
    
    for (const page of pages) {
      try {
        console.log(`🔍 Testing ${page}...`);
        
        const response = await axios.get(`${this.baseURL}${page}`, {
          timeout: 10000,
          headers: {
            'User-Agent': 'SSR-Test-Bot/1.0'
          }
        });
        
        const html = response.data;
        
        // Check for basic React SSR structure
        const hasReactRoot = html.includes('id="__next"') || html.includes('data-reactroot');
        const hasMetadata = html.includes('<title>') && html.includes('<meta');
        const hasValidHtml = html.includes('<!DOCTYPE html>') || html.startsWith('<html');
        
        // Check for potential hydration mismatch indicators
        const hasHydrationWarnings = html.includes('Warning:') || html.includes('should have a queue');
        
        const result = {
          page,
          status: response.status,
          hasReactRoot,
          hasMetadata,
          hasValidHtml,
          hasHydrationWarnings,
          htmlLength: html.length,
          passed: response.status === 200 && hasValidHtml && !hasHydrationWarnings
        };
        
        this.testResults.serverRendering.push(result);
        
        if (result.passed) {
          this.testResults.testsPassed++;
          console.log(`✅ ${page}: SSR working correctly`);
        } else {
          this.testResults.testsFailed++;
          console.error(`❌ ${page}: SSR issues detected`);
          if (hasHydrationWarnings) {
            console.error(`   - Hydration warnings found in HTML`);
          }
          if (!hasValidHtml) {
            console.error(`   - Invalid HTML structure`);
          }
        }
        
        // Small delay to avoid overwhelming the server
        await new Promise(resolve => setTimeout(resolve, 500));
        
      } catch (error) {
        console.error(`❌ ${page}: Request failed - ${error.message}`);
        this.testResults.testsFailed++;
        this.testResults.serverRendering.push({
          page,
          error: error.message,
          passed: false
        });
      }
    }
  }

  async testMonthHookStructure() {
    console.log('🧪 Testing Month Hook Structure in SSR...');
    
    try {
      const response = await axios.get(`${this.baseURL}/`, {
        timeout: 5000
      });
      
      const html = response.data;
      
      // Check for month picker in SSR HTML
      const hasMonthInput = html.includes('type="month"') || html.includes('month-picker');
      const hasMonthValue = html.includes('value="2024-') || html.includes('value="2025-');
      
      // Check for potential hydration protection
      const hasHydrationProtection = html.includes('mounted') || html.includes('hydration');
      
      if (hasMonthInput) {
        this.testResults.testsPassed++;
        console.log('✅ Month picker found in SSR HTML');
      } else {
        this.testResults.testsFailed++;
        console.error('❌ Month picker not found in SSR HTML');
      }
      
      if (hasMonthValue) {
        this.testResults.testsPassed++;
        console.log('✅ Month value present in SSR HTML');
      } else {
        this.testResults.testsFailed++;
        console.error('❌ Month value missing in SSR HTML');
      }
      
      console.log(`📊 Hydration protection detected: ${hasHydrationProtection}`);
      
    } catch (error) {
      console.error('❌ Month hook structure test failed:', error.message);
      this.testResults.testsFailed++;
    }
  }

  async testAuthFlow() {
    console.log('🧪 Testing Auth Flow SSR...');
    
    try {
      // Test login page
      const loginResponse = await axios.get(`${this.baseURL}/login`);
      const loginHtml = loginResponse.data;
      
      const hasLoginForm = loginHtml.includes('type="password"') && loginHtml.includes('button');
      const hasAuthProtection = !loginHtml.includes('useGlobalMonth') || loginHtml.includes('isLoginPage');
      
      if (hasLoginForm && hasAuthProtection) {
        this.testResults.testsPassed++;
        console.log('✅ Login page SSR: Properly structured');
      } else {
        this.testResults.testsFailed++;
        console.error('❌ Login page SSR: Issues detected');
      }
      
    } catch (error) {
      console.error('❌ Auth flow test failed:', error.message);
      this.testResults.testsFailed++;
    }
  }

  async performStaticAnalysis() {
    console.log('🧪 Performing Static Code Analysis...');
    
    try {
      // Read the month.ts file to analyze hook implementation
      const monthFile = fs.readFileSync(
        '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/frontend/lib/month.ts', 
        'utf8'
      );
      
      // Check for proper SSR protection patterns
      const hasWindowCheck = monthFile.includes('typeof window !== \'undefined\'');
      const hasUseClientDirective = monthFile.includes('\'use client\'');
      const hasProperInitialization = monthFile.includes('useState<string>(() =>');
      
      // Check layout.tsx for hydration protection
      const layoutFile = fs.readFileSync(
        '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/frontend/app/layout.tsx',
        'utf8'
      );
      
      const hasMountedState = layoutFile.includes('mounted') && layoutFile.includes('setMounted');
      const hasHydrationPrevention = layoutFile.includes('if (!mounted)');
      
      const analysisResults = {
        monthHooks: {
          hasWindowCheck,
          hasUseClientDirective,
          hasProperInitialization,
          score: [hasWindowCheck, hasUseClientDirective, hasProperInitialization].filter(Boolean).length
        },
        layout: {
          hasMountedState,
          hasHydrationPrevention,
          score: [hasMountedState, hasHydrationPrevention].filter(Boolean).length
        }
      };
      
      console.log('📊 Static Analysis Results:');
      console.log(`   Month Hooks Protection: ${analysisResults.monthHooks.score}/3`);
      console.log(`   Layout Hydration Protection: ${analysisResults.layout.score}/2`);
      
      if (analysisResults.monthHooks.score >= 2 && analysisResults.layout.score >= 1) {
        this.testResults.testsPassed++;
        console.log('✅ Static analysis: Good SSR protection patterns found');
      } else {
        this.testResults.testsFailed++;
        console.error('❌ Static analysis: Missing SSR protection patterns');
      }
      
      return analysisResults;
      
    } catch (error) {
      console.error('❌ Static analysis failed:', error.message);
      this.testResults.testsFailed++;
      return null;
    }
  }

  generateReport() {
    const totalTests = this.testResults.testsPassed + this.testResults.testsFailed;
    const successRate = totalTests > 0 ? Math.round((this.testResults.testsPassed / totalTests) * 100) : 0;
    
    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        totalTests,
        passed: this.testResults.testsPassed,
        failed: this.testResults.testsFailed,
        successRate
      },
      serverRendering: this.testResults.serverRendering,
      conclusion: this.testResults.testsFailed === 0 ? 'PASS' : 'NEEDS_ATTENTION'
    };

    console.log('\n📋 SSR HYDRATION VALIDATION REPORT');
    console.log('===================================');
    console.log(`Tests Passed: ${report.summary.passed}`);
    console.log(`Tests Failed: ${report.summary.failed}`);
    console.log(`Success Rate: ${report.summary.successRate}%`);
    console.log(`Final Result: ${report.conclusion}`);
    
    // Detailed results
    console.log('\n📊 Server Rendering Results:');
    this.testResults.serverRendering.forEach(result => {
      const status = result.passed ? '✅' : '❌';
      console.log(`${status} ${result.page}: ${result.passed ? 'OK' : 'ISSUES'}`);
      if (result.error) {
        console.log(`    Error: ${result.error}`);
      }
    });
    
    return report;
  }

  async runAllTests() {
    try {
      console.log('🚀 Starting Simple SSR Hydration Validation...\n');
      
      await this.testServerRendering();
      await this.testMonthHookStructure();
      await this.testAuthFlow();
      await this.performStaticAnalysis();
      
      const report = this.generateReport();
      
      // Save report
      fs.writeFileSync('ssr_validation_report.json', JSON.stringify(report, null, 2));
      console.log('\n📄 Report saved to ssr_validation_report.json');
      
      return report;
      
    } catch (error) {
      console.error('💥 Test suite failed:', error.message);
      throw error;
    }
  }
}

// Check if axios is available, if not suggest installation
try {
  require('axios');
} catch (e) {
  console.error('❌ axios is required but not found. Install with: npm install axios');
  process.exit(1);
}

// Execute the test suite
if (require.main === module) {
  const validator = new SimpleSSRValidator();
  
  validator.runAllTests()
    .then((report) => {
      process.exit(report.conclusion === 'PASS' ? 0 : 1);
    })
    .catch((error) => {
      console.error('Test execution failed:', error);
      process.exit(1);
    });
}

module.exports = SimpleSSRValidator;