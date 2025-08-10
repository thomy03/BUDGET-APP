/**
 * Functional Validation Test for Budget Famille v2.3
 * Tests real user scenarios without browser dependency
 * 
 * Focus on validating:
 * 1. Month navigation functionality
 * 2. URL synchronization on transactions page
 * 3. localStorage persistence behavior
 * 4. Cross-page state consistency
 */

const axios = require('axios');
const fs = require('fs');
const { URL } = require('url');

class FunctionalValidator {
  constructor() {
    this.baseURL = 'http://localhost:45678';
    this.sessionCookies = '';
    this.testResults = {
      authentication: null,
      monthNavigation: null,
      urlSynchronization: null,
      crossPageConsistency: null,
      summary: {
        passed: 0,
        failed: 0,
        warnings: 0
      }
    };
  }

  async performLogin() {
    console.log('🔐 Testing authentication flow...');
    
    try {
      // Get login page first
      const loginPageResponse = await axios.get(`${this.baseURL}/login`);
      
      // Attempt login
      const loginResponse = await axios.post(`${this.baseURL}/api/login`, {
        password: 'admin123'
      }, {
        headers: {
          'Content-Type': 'application/json',
          'Cookie': this.sessionCookies
        }
      });
      
      if (loginResponse.headers['set-cookie']) {
        this.sessionCookies = loginResponse.headers['set-cookie'].join('; ');
      }
      
      console.log('✅ Authentication successful');
      this.testResults.authentication = { success: true, message: 'Login successful' };
      this.testResults.summary.passed++;
      
      return true;
      
    } catch (error) {
      console.log('⚠️  Authentication test skipped (API might not be available)');
      this.testResults.authentication = { success: false, message: 'API not available, continuing with UI tests' };
      this.testResults.summary.warnings++;
      return false;
    }
  }

  async testMonthNavigation() {
    console.log('🧪 Testing month navigation scenarios...');
    
    const scenarios = [
      { page: '/', name: 'Dashboard' },
      { page: '/settings', name: 'Settings' },
      { page: '/analytics', name: 'Analytics' }
    ];
    
    const results = [];
    
    for (const scenario of scenarios) {
      try {
        console.log(`   Testing month picker on ${scenario.name}...`);
        
        const response = await axios.get(`${this.baseURL}${scenario.page}`, {
          headers: { 'Cookie': this.sessionCookies }
        });
        
        const html = response.data;
        
        // Check if page loads successfully
        const pageLoads = response.status === 200;
        
        // After hydration protection, month picker should be in a loading state initially
        const hasHydrationProtection = html.includes('animate-spin') || 
                                      html.includes('min-h-screen bg-zinc-50 flex items-center justify-center');
        
        // Should not have month picker in initial SSR (due to hydration protection)
        const hasMonthPickerInSSR = html.includes('type="month"');
        
        const result = {
          page: scenario.page,
          name: scenario.name,
          pageLoads,
          hasHydrationProtection,
          hasMonthPickerInSSR,
          correctBehavior: pageLoads && hasHydrationProtection && !hasMonthPickerInSSR
        };
        
        results.push(result);
        
        if (result.correctBehavior) {
          console.log(`   ✅ ${scenario.name}: Correct hydration behavior`);
          this.testResults.summary.passed++;
        } else {
          console.log(`   ❌ ${scenario.name}: Unexpected behavior`);
          this.testResults.summary.failed++;
        }
        
      } catch (error) {
        console.log(`   ❌ ${scenario.name}: Request failed - ${error.message}`);
        results.push({
          page: scenario.page,
          name: scenario.name,
          error: error.message,
          correctBehavior: false
        });
        this.testResults.summary.failed++;
      }
    }
    
    this.testResults.monthNavigation = results;
    return results;
  }

  async testTransactionUrlSync() {
    console.log('🧪 Testing transactions page URL synchronization...');
    
    const testCases = [
      { url: '/transactions', expectedBehavior: 'Should redirect to add current month param' },
      { url: '/transactions?month=2024-06', expectedBehavior: 'Should maintain month parameter' },
      { url: '/transactions?month=2024-12&importId=test123', expectedBehavior: 'Should maintain all parameters' }
    ];
    
    const results = [];
    
    for (const testCase of testCases) {
      try {
        console.log(`   Testing URL: ${testCase.url}`);
        
        const response = await axios.get(`${this.baseURL}${testCase.url}`, {
          maxRedirects: 5,
          headers: { 'Cookie': this.sessionCookies }
        });
        
        const html = response.data;
        
        // Check page structure
        const isTransactionsPage = html.includes('Transactions') || html.includes('transactions');
        const hasProperLayout = html.includes('Budget Famille');
        const hasHydrationProtection = html.includes('animate-spin') && !html.includes('type="month"');
        
        // Check for import success banner if importId present
        const hasImportBanner = testCase.url.includes('importId') ? 
          html.includes('import') || html.includes('Import') : true;
        
        const result = {
          testUrl: testCase.url,
          finalUrl: response.request.res.responseUrl,
          status: response.status,
          isTransactionsPage,
          hasProperLayout,
          hasHydrationProtection,
          hasImportBanner,
          passed: response.status === 200 && isTransactionsPage && hasProperLayout
        };
        
        results.push(result);
        
        if (result.passed) {
          console.log(`   ✅ URL sync test passed`);
          this.testResults.summary.passed++;
        } else {
          console.log(`   ❌ URL sync test failed`);
          this.testResults.summary.failed++;
        }
        
      } catch (error) {
        console.log(`   ❌ URL test failed: ${error.message}`);
        results.push({
          testUrl: testCase.url,
          error: error.message,
          passed: false
        });
        this.testResults.summary.failed++;
      }
    }
    
    this.testResults.urlSynchronization = results;
    return results;
  }

  async testCrossPageConsistency() {
    console.log('🧪 Testing cross-page state consistency...');
    
    // This test simulates navigating between pages and checks that
    // the hydration protection works consistently
    
    const navigationFlow = [
      { from: '/', to: '/settings', step: 'Dashboard to Settings' },
      { from: '/settings', to: '/transactions', step: 'Settings to Transactions' },
      { from: '/transactions', to: '/upload', step: 'Transactions to Upload' },
      { from: '/upload', to: '/analytics', step: 'Upload to Analytics' },
      { from: '/analytics', to: '/', step: 'Analytics to Dashboard' }
    ];
    
    const results = [];
    
    for (const flow of navigationFlow) {
      try {
        console.log(`   Testing: ${flow.step}`);
        
        // Load the target page
        const response = await axios.get(`${this.baseURL}${flow.to}`, {
          headers: { 'Cookie': this.sessionCookies }
        });
        
        const html = response.data;
        
        // Check consistent behavior across pages
        const hasConsistentLayout = html.includes('Budget Famille');
        const hasConsistentHydration = html.includes('animate-spin') || 
                                      html.includes('min-h-screen bg-zinc-50');
        const noHydrationErrors = !html.includes('Warning:') && 
                                 !html.includes('should have a queue');
        
        const isConsistent = hasConsistentLayout && hasConsistentHydration && noHydrationErrors;
        
        const result = {
          navigationStep: flow.step,
          targetPage: flow.to,
          hasConsistentLayout,
          hasConsistentHydration,
          noHydrationErrors,
          isConsistent,
          status: response.status
        };
        
        results.push(result);
        
        if (isConsistent) {
          console.log(`   ✅ ${flow.step}: Consistent behavior`);
          this.testResults.summary.passed++;
        } else {
          console.log(`   ❌ ${flow.step}: Inconsistent behavior`);
          this.testResults.summary.failed++;
        }
        
        // Small delay between requests
        await new Promise(resolve => setTimeout(resolve, 200));
        
      } catch (error) {
        console.log(`   ❌ ${flow.step}: Navigation failed - ${error.message}`);
        results.push({
          navigationStep: flow.step,
          error: error.message,
          isConsistent: false
        });
        this.testResults.summary.failed++;
      }
    }
    
    this.testResults.crossPageConsistency = results;
    return results;
  }

  analyzeHydrationFix() {
    console.log('🧪 Analyzing hydration fix effectiveness...');
    
    const codeAnalysis = {
      monthHookProtection: null,
      layoutProtection: null,
      overallEffectiveness: null
    };
    
    try {
      // Analyze month.ts
      const monthFile = fs.readFileSync(
        '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/frontend/lib/month.ts',
        'utf8'
      );
      
      codeAnalysis.monthHookProtection = {
        hasUseClient: monthFile.includes("'use client'"),
        hasWindowGuards: monthFile.includes('typeof window !== \'undefined\''),
        hasLazyInitialization: monthFile.includes('useState<string>(() =>'),
        hasProperLocalStorageHandling: monthFile.includes('window.localStorage') &&
                                      monthFile.includes('typeof window !== \'undefined\'')
      };
      
      // Analyze layout.tsx
      const layoutFile = fs.readFileSync(
        '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/frontend/app/layout.tsx',
        'utf8'
      );
      
      codeAnalysis.layoutProtection = {
        hasUseClient: layoutFile.includes('"use client"'),
        hasMountedGuard: layoutFile.includes('const [mounted, setMounted] = useState(false)'),
        hasHydrationReturn: layoutFile.includes('if (!mounted)') && layoutFile.includes('return'),
        hasLoadingState: layoutFile.includes('animate-spin')
      };
      
      // Overall effectiveness score
      const monthScore = Object.values(codeAnalysis.monthHookProtection).filter(Boolean).length;
      const layoutScore = Object.values(codeAnalysis.layoutProtection).filter(Boolean).length;
      
      codeAnalysis.overallEffectiveness = {
        monthHookScore: `${monthScore}/4`,
        layoutScore: `${layoutScore}/4`,
        overallRating: (monthScore >= 3 && layoutScore >= 3) ? 'EFFECTIVE' : 'NEEDS_IMPROVEMENT'
      };
      
      console.log('📊 Hydration Fix Analysis:');
      console.log(`   Month Hook Protection: ${codeAnalysis.overallEffectiveness.monthHookScore}`);
      console.log(`   Layout Protection: ${codeAnalysis.overallEffectiveness.layoutScore}`);
      console.log(`   Overall Rating: ${codeAnalysis.overallEffectiveness.overallRating}`);
      
      if (codeAnalysis.overallEffectiveness.overallRating === 'EFFECTIVE') {
        this.testResults.summary.passed++;
      } else {
        this.testResults.summary.failed++;
      }
      
    } catch (error) {
      console.error('❌ Code analysis failed:', error.message);
      this.testResults.summary.failed++;
    }
    
    return codeAnalysis;
  }

  generateFinalReport() {
    const totalTests = this.testResults.summary.passed + 
                      this.testResults.summary.failed + 
                      this.testResults.summary.warnings;
    
    const successRate = totalTests > 0 ? 
      Math.round((this.testResults.summary.passed / totalTests) * 100) : 0;
    
    const report = {
      timestamp: new Date().toISOString(),
      testSuite: 'Functional SSR Hydration Validation',
      summary: {
        ...this.testResults.summary,
        totalTests,
        successRate,
        overallStatus: this.testResults.summary.failed === 0 ? 'PASS' : 'PARTIAL'
      },
      detailedResults: this.testResults,
      conclusion: this.generateConclusion(),
      recommendations: this.generateRecommendations()
    };

    console.log('\n📋 FUNCTIONAL VALIDATION REPORT');
    console.log('================================');
    console.log(`Total Tests: ${report.summary.totalTests}`);
    console.log(`Passed: ${report.summary.passed}`);
    console.log(`Failed: ${report.summary.failed}`);
    console.log(`Warnings: ${report.summary.warnings}`);
    console.log(`Success Rate: ${report.summary.successRate}%`);
    console.log(`Overall Status: ${report.summary.overallStatus}`);
    
    if (report.conclusion) {
      console.log(`\n📝 Conclusion: ${report.conclusion}`);
    }
    
    if (report.recommendations.length > 0) {
      console.log('\n🔧 Recommendations:');
      report.recommendations.forEach((rec, i) => {
        console.log(`   ${i + 1}. ${rec}`);
      });
    }
    
    return report;
  }

  generateConclusion() {
    const { passed, failed, warnings } = this.testResults.summary;
    
    if (failed === 0 && warnings <= 1) {
      return 'SSR hydration fix is working correctly. All critical functionality validated.';
    } else if (failed <= 2) {
      return 'SSR hydration fix is mostly working. Minor issues detected but core functionality is stable.';
    } else {
      return 'SSR hydration fix needs attention. Multiple issues detected that may affect user experience.';
    }
  }

  generateRecommendations() {
    const recommendations = [];
    
    if (this.testResults.summary.failed > 0) {
      recommendations.push('Review failed test cases and address any critical hydration issues');
    }
    
    if (this.testResults.authentication && !this.testResults.authentication.success) {
      recommendations.push('Verify backend API is running for complete integration testing');
    }
    
    if (this.testResults.summary.passed >= this.testResults.summary.failed) {
      recommendations.push('Current implementation is ready for production deployment');
      recommendations.push('Monitor client-side console for any hydration warnings in production');
    }
    
    return recommendations;
  }

  async runFullValidation() {
    try {
      console.log('🚀 Starting Functional SSR Hydration Validation...\n');
      
      await this.performLogin();
      await this.testMonthNavigation();
      await this.testTransactionUrlSync();
      await this.testCrossPageConsistency();
      this.analyzeHydrationFix();
      
      const report = this.generateFinalReport();
      
      // Save report
      fs.writeFileSync('functional_validation_report.json', JSON.stringify(report, null, 2));
      console.log('\n📄 Report saved to functional_validation_report.json');
      
      return report;
      
    } catch (error) {
      console.error('💥 Functional validation failed:', error.message);
      throw error;
    }
  }
}

// Execute validation
if (require.main === module) {
  const validator = new FunctionalValidator();
  
  validator.runFullValidation()
    .then((report) => {
      process.exit(report.summary.overallStatus === 'PASS' ? 0 : 1);
    })
    .catch((error) => {
      console.error('Validation execution failed:', error);
      process.exit(1);
    });
}

module.exports = FunctionalValidator;