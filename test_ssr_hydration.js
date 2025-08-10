/**
 * Critical SSR Hydration Test Suite for Budget Famille v2.3
 * Tests the "Should have a queue" error fix in useGlobalMonth hook
 * 
 * This test validates:
 * 1. Month hooks work correctly after SSR fix
 * 2. Navigation between pages without React errors
 * 3. localStorage persistence during SSR
 * 4. Calendar month selection functionality
 * 5. No console errors during page transitions
 */

const puppeteer = require('puppeteer');
const { URL } = require('url');

class SSRHydrationValidator {
  constructor() {
    this.browser = null;
    this.page = null;
    this.baseURL = 'http://localhost:3000';
    this.testResults = {
      hydrationErrors: [],
      consoleErrors: [],
      navigationErrors: [],
      localStorage: {},
      testsPassed: 0,
      testsFailed: 0
    };
  }

  async initialize() {
    console.log('🚀 Initializing SSR Hydration Test Suite...');
    
    this.browser = await puppeteer.launch({
      headless: false, // Keep visible for debugging
      devtools: false,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    this.page = await this.browser.newPage();
    
    // Monitor console messages for hydration errors
    this.page.on('console', (message) => {
      const text = message.text();
      
      // Critical: Look for React hydration errors
      if (text.includes('Should have a queue') || 
          text.includes('Hydration') || 
          text.includes('hydration') ||
          text.includes('Warning: Text content did not match') ||
          text.includes('Warning: Expected server HTML')) {
        this.testResults.hydrationErrors.push({
          timestamp: new Date().toISOString(),
          message: text,
          type: message.type()
        });
        console.error('❌ HYDRATION ERROR:', text);
      }
      
      // Monitor other console errors
      if (message.type() === 'error') {
        this.testResults.consoleErrors.push({
          timestamp: new Date().toISOString(),
          message: text
        });
        console.error('🔍 Console Error:', text);
      }
      
      // Log month-related debug messages
      if (text.includes('Global month') || text.includes('MonthPicker')) {
        console.log('📅 Month Hook:', text);
      }
    });

    // Monitor page errors
    this.page.on('pageerror', (error) => {
      this.testResults.navigationErrors.push({
        timestamp: new Date().toISOString(),
        error: error.message,
        stack: error.stack
      });
      console.error('📄 Page Error:', error.message);
    });

    await this.page.setViewport({ width: 1280, height: 720 });
  }

  async login() {
    console.log('🔐 Performing login...');
    
    await this.page.goto(`${this.baseURL}/login`, { waitUntil: 'networkidle2' });
    
    // Wait for the form to be ready
    await this.page.waitForSelector('input[type="password"]', { timeout: 10000 });
    
    // Fill login form
    await this.page.type('input[type="password"]', 'admin123');
    await this.page.click('button[type="submit"]');
    
    // Wait for authentication redirect
    await this.page.waitForNavigation({ waitUntil: 'networkidle2' });
    
    const currentUrl = this.page.url();
    if (currentUrl.includes('/login')) {
      throw new Error('Login failed - still on login page');
    }
    
    console.log('✅ Login successful');
  }

  async testHydrationProtection() {
    console.log('🧪 Testing SSR Hydration Protection...');
    
    // Test 1: Initial page load should not have hydration errors
    await this.page.goto(`${this.baseURL}/`, { waitUntil: 'networkidle2' });
    await this.page.waitForTimeout(2000); // Give React time to hydrate
    
    const initialHydrationErrors = this.testResults.hydrationErrors.length;
    
    if (initialHydrationErrors === 0) {
      this.testResults.testsPassed++;
      console.log('✅ Initial page load: No hydration errors detected');
    } else {
      this.testResults.testsFailed++;
      console.error('❌ Initial page load: Hydration errors detected');
    }
    
    return initialHydrationErrors === 0;
  }

  async testMonthHooksInitialization() {
    console.log('🧪 Testing Month Hooks Initialization...');
    
    // Wait for MonthPicker to be rendered
    await this.page.waitForSelector('input[type="month"]', { timeout: 10000 });
    
    // Get initial month value
    const initialMonth = await this.page.$eval('input[type="month"]', el => el.value);
    console.log('📅 Initial month value:', initialMonth);
    
    // Validate month format (YYYY-MM)
    const monthRegex = /^\d{4}-\d{2}$/;
    if (monthRegex.test(initialMonth)) {
      this.testResults.testsPassed++;
      console.log('✅ Month format validation: Correct format');
    } else {
      this.testResults.testsFailed++;
      console.error('❌ Month format validation: Invalid format');
      return false;
    }
    
    // Test localStorage persistence
    const storedMonth = await this.page.evaluate(() => {
      return window.localStorage.getItem('selectedMonth');
    });
    
    this.testResults.localStorage.selectedMonth = storedMonth;
    console.log('💾 localStorage selectedMonth:', storedMonth);
    
    if (storedMonth === initialMonth) {
      this.testResults.testsPassed++;
      console.log('✅ localStorage sync: Month value matches');
    } else {
      this.testResults.testsFailed++;
      console.error('❌ localStorage sync: Mismatch detected');
      return false;
    }
    
    return true;
  }

  async testPageNavigation() {
    console.log('🧪 Testing Page Navigation without Hydration Errors...');
    
    const pages = [
      { path: '/', name: 'Dashboard' },
      { path: '/transactions', name: 'Transactions' },
      { path: '/upload', name: 'Upload' },
      { path: '/settings', name: 'Settings' },
      { path: '/analytics', name: 'Analytics' }
    ];
    
    let navigationTestsPassed = 0;
    
    for (const pageInfo of pages) {
      console.log(`🔄 Navigating to ${pageInfo.name}...`);
      
      const errorsBefore = this.testResults.hydrationErrors.length;
      
      await this.page.goto(`${this.baseURL}${pageInfo.path}`, { waitUntil: 'networkidle2' });
      await this.page.waitForTimeout(1500); // Allow React to settle
      
      const errorsAfter = this.testResults.hydrationErrors.length;
      
      if (errorsAfter === errorsBefore) {
        navigationTestsPassed++;
        console.log(`✅ ${pageInfo.name}: No hydration errors`);
      } else {
        console.error(`❌ ${pageInfo.name}: Hydration errors detected`);
      }
    }
    
    if (navigationTestsPassed === pages.length) {
      this.testResults.testsPassed++;
      console.log('✅ Navigation test: All pages passed');
      return true;
    } else {
      this.testResults.testsFailed++;
      console.error(`❌ Navigation test: ${pages.length - navigationTestsPassed} pages failed`);
      return false;
    }
  }

  async testMonthSelection() {
    console.log('🧪 Testing Calendar Month Selection...');
    
    // Go to transactions page (has URL sync)
    await this.page.goto(`${this.baseURL}/transactions`, { waitUntil: 'networkidle2' });
    await this.page.waitForSelector('input[type="month"]', { timeout: 10000 });
    
    const initialErrorCount = this.testResults.hydrationErrors.length;
    
    // Test month input change
    const testMonth = '2024-06';
    await this.page.$eval('input[type="month"]', (el, value) => {
      el.value = value;
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }, testMonth);
    
    await this.page.waitForTimeout(1000);
    
    // Verify URL updated
    const currentUrl = this.page.url();
    if (currentUrl.includes(`month=${testMonth}`)) {
      this.testResults.testsPassed++;
      console.log('✅ Month selection: URL updated correctly');
    } else {
      this.testResults.testsFailed++;
      console.error('❌ Month selection: URL not updated');
    }
    
    // Test navigation buttons
    await this.page.click('button[title="Mois suivant"]');
    await this.page.waitForTimeout(1000);
    
    const finalErrorCount = this.testResults.hydrationErrors.length;
    
    if (finalErrorCount === initialErrorCount) {
      this.testResults.testsPassed++;
      console.log('✅ Month navigation: No hydration errors');
      return true;
    } else {
      this.testResults.testsFailed++;
      console.error('❌ Month navigation: Hydration errors detected');
      return false;
    }
  }

  async testLocalStoragePersistence() {
    console.log('🧪 Testing localStorage Persistence Across Pages...');
    
    // Set a specific month
    const testMonth = '2024-05';
    await this.page.goto(`${this.baseURL}/`, { waitUntil: 'networkidle2' });
    
    await this.page.$eval('input[type="month"]', (el, value) => {
      el.value = value;
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }, testMonth);
    
    await this.page.waitForTimeout(500);
    
    // Navigate to different page
    await this.page.goto(`${this.baseURL}/settings`, { waitUntil: 'networkidle2' });
    await this.page.waitForTimeout(500);
    
    // Go back to dashboard and check if month persisted
    await this.page.goto(`${this.baseURL}/`, { waitUntil: 'networkidle2' });
    await this.page.waitForSelector('input[type="month"]', { timeout: 5000 });
    
    const persistedMonth = await this.page.$eval('input[type="month"]', el => el.value);
    
    if (persistedMonth === testMonth) {
      this.testResults.testsPassed++;
      console.log('✅ localStorage persistence: Month value maintained');
      return true;
    } else {
      this.testResults.testsFailed++;
      console.error('❌ localStorage persistence: Month value lost');
      console.error(`Expected: ${testMonth}, Got: ${persistedMonth}`);
      return false;
    }
  }

  async generateReport() {
    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        totalTests: this.testResults.testsPassed + this.testResults.testsFailed,
        passed: this.testResults.testsPassed,
        failed: this.testResults.testsFailed,
        successRate: Math.round((this.testResults.testsPassed / (this.testResults.testsPassed + this.testResults.testsFailed)) * 100)
      },
      criticalFindings: {
        hydrationErrors: this.testResults.hydrationErrors,
        consoleErrors: this.testResults.consoleErrors,
        navigationErrors: this.testResults.navigationErrors
      },
      localStorage: this.testResults.localStorage,
      conclusion: this.testResults.hydrationErrors.length === 0 ? 'PASS' : 'FAIL'
    };

    console.log('\n📋 SSR HYDRATION TEST REPORT');
    console.log('================================');
    console.log(`Tests Passed: ${report.summary.passed}`);
    console.log(`Tests Failed: ${report.summary.failed}`);
    console.log(`Success Rate: ${report.summary.successRate}%`);
    console.log(`Hydration Errors: ${report.criticalFindings.hydrationErrors.length}`);
    console.log(`Console Errors: ${report.criticalFindings.consoleErrors.length}`);
    console.log(`Navigation Errors: ${report.criticalFindings.navigationErrors.length}`);
    console.log(`Final Result: ${report.conclusion}`);
    
    if (report.criticalFindings.hydrationErrors.length > 0) {
      console.log('\n❌ CRITICAL HYDRATION ERRORS FOUND:');
      report.criticalFindings.hydrationErrors.forEach((error, index) => {
        console.log(`${index + 1}. ${error.message}`);
      });
    }
    
    return report;
  }

  async runAllTests() {
    try {
      await this.initialize();
      await this.login();
      
      // Core SSR hydration tests
      console.log('\n🧪 Starting SSR Hydration Test Suite...\n');
      
      await this.testHydrationProtection();
      await this.testMonthHooksInitialization();
      await this.testPageNavigation();
      await this.testMonthSelection();
      await this.testLocalStoragePersistence();
      
      const report = await this.generateReport();
      
      // Save detailed report
      const fs = require('fs');
      fs.writeFileSync('ssr_hydration_test_report.json', JSON.stringify(report, null, 2));
      console.log('\n📄 Detailed report saved to ssr_hydration_test_report.json');
      
      return report;
      
    } catch (error) {
      console.error('💥 Test suite failed:', error.message);
      throw error;
    } finally {
      if (this.browser) {
        await this.browser.close();
      }
    }
  }
}

// Execute the test suite
if (require.main === module) {
  const validator = new SSRHydrationValidator();
  
  validator.runAllTests()
    .then((report) => {
      process.exit(report.conclusion === 'PASS' ? 0 : 1);
    })
    .catch((error) => {
      console.error('Test execution failed:', error);
      process.exit(1);
    });
}

module.exports = SSRHydrationValidator;