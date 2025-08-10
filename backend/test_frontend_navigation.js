#!/usr/bin/env node

/**
 * Frontend Navigation Test for Budget Famille v2.3
 * Tests MonthPicker synchronization and navigation fixes
 */

const fs = require('fs');
const path = require('path');

function testFrontendStructure() {
    console.log('🧪 Testing Frontend Navigation Structure');
    
    const frontendPath = '../frontend';
    const results = [];
    
    // Test 1: Check MonthPicker component
    const monthPickerPath = path.join(frontendPath, 'components/MonthPicker.tsx');
    if (fs.existsSync(monthPickerPath)) {
        const content = fs.readFileSync(monthPickerPath, 'utf8');
        
        // Check for synchronization logic
        if (content.includes('useGlobalMonthWithUrl') && content.includes('isTransactionsPage')) {
            results.push({test: 'MonthPicker Sync Logic', status: 'PASS', details: 'Conditional URL sync implemented'});
        } else {
            results.push({test: 'MonthPicker Sync Logic', status: 'FAIL', error: 'Missing synchronization logic'});
        }
        
        // Check for navigation functions
        if (content.includes('navigateMonth') && content.includes('setMonth')) {
            results.push({test: 'MonthPicker Navigation', status: 'PASS', details: 'Navigation functions present'});
        } else {
            results.push({test: 'MonthPicker Navigation', status: 'FAIL', error: 'Missing navigation functions'});
        }
    } else {
        results.push({test: 'MonthPicker Component', status: 'FAIL', error: 'MonthPicker.tsx not found'});
    }
    
    // Test 2: Check month synchronization hooks
    const monthLibPath = path.join(frontendPath, 'lib/month.ts');
    if (fs.existsSync(monthLibPath)) {
        const content = fs.readFileSync(monthLibPath, 'utf8');
        
        // Check for both hooks
        if (content.includes('useGlobalMonth') && content.includes('useGlobalMonthWithUrl')) {
            results.push({test: 'Month Sync Hooks', status: 'PASS', details: 'Both sync hooks available'});
        } else {
            results.push({test: 'Month Sync Hooks', status: 'FAIL', error: 'Missing synchronization hooks'});
        }
        
        // Check URL synchronization logic
        if (content.includes('router.replace') && content.includes('searchParams')) {
            results.push({test: 'URL Synchronization', status: 'PASS', details: 'URL sync logic implemented'});
        } else {
            results.push({test: 'URL Synchronization', status: 'FAIL', error: 'Missing URL sync logic'});
        }
    } else {
        results.push({test: 'Month Library', status: 'FAIL', error: 'month.ts not found'});
    }
    
    // Test 3: Check upload page navigation
    const uploadPagePath = path.join(frontendPath, 'app/upload/page.tsx');
    if (fs.existsSync(uploadPagePath)) {
        const content = fs.readFileSync(uploadPagePath, 'utf8');
        
        // Check for redirect logic after import
        if (content.includes('router.replace') && content.includes('buildTransactionUrl')) {
            results.push({test: 'CSV Import Redirect', status: 'PASS', details: 'Navigation after import implemented'});
        } else {
            results.push({test: 'CSV Import Redirect', status: 'FAIL', error: 'Missing import redirect logic'});
        }
        
        // Check for month state management
        if (content.includes('setGlobalMonth') && content.includes('targetMonth')) {
            results.push({test: 'Import Month Sync', status: 'PASS', details: 'Month state updated before navigation'});
        } else {
            results.push({test: 'Import Month Sync', status: 'FAIL', error: 'Missing month state sync'});
        }
    } else {
        results.push({test: 'Upload Page', status: 'FAIL', error: 'upload/page.tsx not found'});
    }
    
    // Test 4: Check transactions page import handling
    const transactionsPagePath = path.join(frontendPath, 'app/transactions/page.tsx');
    if (fs.existsSync(transactionsPagePath)) {
        const content = fs.readFileSync(transactionsPagePath, 'utf8');
        
        // Check for import ID handling
        if (content.includes('importId') && content.includes('searchParams.get')) {
            results.push({test: 'Transaction Import Handling', status: 'PASS', details: 'Import ID parameter handled'});
        } else {
            results.push({test: 'Transaction Import Handling', status: 'FAIL', error: 'Missing import ID handling'});
        }
        
        // Check for URL sync usage
        if (content.includes('useGlobalMonthWithUrl')) {
            results.push({test: 'Transaction Month Sync', status: 'PASS', details: 'URL month sync in transactions'});
        } else {
            results.push({test: 'Transaction Month Sync', status: 'FAIL', error: 'Missing URL month sync'});
        }
    } else {
        results.push({test: 'Transactions Page', status: 'FAIL', error: 'transactions/page.tsx not found'});
    }
    
    // Test 5: Check ImportSuccessBanner component
    const bannerPath = path.join(frontendPath, 'components/ImportSuccessBanner.tsx');
    if (fs.existsSync(bannerPath)) {
        results.push({test: 'Import Success Banner', status: 'PASS', details: 'Import success component available'});
    } else {
        results.push({test: 'Import Success Banner', status: 'WARNING', warning: 'Import success banner not found'});
    }
    
    return results;
}

function generateReport(results) {
    const passed = results.filter(r => r.status === 'PASS').length;
    const failed = results.filter(r => r.status === 'FAIL').length;
    const warnings = results.filter(r => r.status === 'WARNING').length;
    
    console.log('\n' + '='.repeat(60));
    console.log('📊 FRONTEND NAVIGATION TEST REPORT');
    console.log('='.repeat(60));
    
    results.forEach(result => {
        if (result.status === 'PASS') {
            console.log(`✅ ${result.test} - ${result.details}`);
        } else if (result.status === 'FAIL') {
            console.log(`❌ ${result.test} - ${result.error}`);
        } else if (result.status === 'WARNING') {
            console.log(`⚠️  ${result.test} - ${result.warning}`);
        }
    });
    
    console.log('='.repeat(60));
    console.log(`Total Tests: ${results.length}`);
    console.log(`✅ Passed: ${passed}`);
    console.log(`❌ Failed: ${failed}`);
    console.log(`⚠️  Warnings: ${warnings}`);
    console.log('='.repeat(60));
    
    if (failed === 0) {
        console.log('🎉 ALL FRONTEND NAVIGATION TESTS PASSED');
        return 0;
    } else {
        console.log('🚨 FRONTEND NAVIGATION ISSUES DETECTED');
        return 1;
    }
}

// Main execution
console.log('🚀 Starting Frontend Navigation Tests for Budget Famille v2.3');
console.log('Testing: MonthPicker sync, CSV import redirect, Navigation flow');
console.log('-'.repeat(80));

const results = testFrontendStructure();
const exitCode = generateReport(results);

// Save detailed results
const reportData = {
    summary: {
        total: results.length,
        passed: results.filter(r => r.status === 'PASS').length,
        failed: results.filter(r => r.status === 'FAIL').length,
        warnings: results.filter(r => r.status === 'WARNING').length
    },
    details: results,
    timestamp: new Date().toISOString(),
    version: 'v2.3'
};

fs.writeFileSync('frontend_navigation_test_results.json', JSON.stringify(reportData, null, 2));
console.log('\n📄 Detailed results saved to: frontend_navigation_test_results.json');

process.exit(exitCode);