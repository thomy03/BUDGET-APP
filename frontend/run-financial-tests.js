#!/usr/bin/env node

/**
 * Financial Improvements Validation Script
 * 
 * This script validates all the financial improvements implemented:
 * 1. Transaction page total recall and calculations
 * 2. Dashboard key metrics restructuring  
 * 3. API endpoints validation
 * 4. Integration workflow testing
 */

const { spawn } = require('child_process')
const fs = require('fs')
const path = require('path')

console.log('🚀 Starting Financial Improvements Validation Suite')
console.log('================================================\n')

// Test categories to run
const testSuites = [
  {
    name: 'Transaction Page Tests',
    pattern: 'TransactionPage.test.tsx',
    description: 'Validates transaction page total recall and calculations'
  },
  {
    name: 'Dashboard Tests', 
    pattern: 'Dashboard.test.tsx',
    description: 'Validates dashboard key metrics and subtotals'
  },
  {
    name: 'API Endpoint Tests',
    pattern: 'ApiEndpoints.test.ts',
    description: 'Tests new API endpoints for enhanced summary and batch operations'
  },
  {
    name: 'Integration Tests',
    pattern: 'Integration.test.tsx', 
    description: 'End-to-end workflow validation from CSV import to display'
  }
]

// Results tracking
const results = {
  passed: [],
  failed: [],
  skipped: []
}

// Run a test suite
function runTestSuite(suite) {
  return new Promise((resolve) => {
    console.log(`\n📊 Running: ${suite.name}`)
    console.log(`📝 Description: ${suite.description}`)
    console.log('─'.repeat(60))

    const testProcess = spawn('npm', ['test', '--', `--testPathPatterns=${suite.pattern}`, '--verbose', '--no-coverage'], {
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: true,
      cwd: process.cwd()
    })

    let output = ''
    let errorOutput = ''

    testProcess.stdout.on('data', (data) => {
      const text = data.toString()
      output += text
      process.stdout.write(text)
    })

    testProcess.stderr.on('data', (data) => {
      const text = data.toString()
      errorOutput += text
      process.stderr.write(text)
    })

    testProcess.on('close', (code) => {
      const success = code === 0
      const result = {
        name: suite.name,
        pattern: suite.pattern,
        success,
        code,
        output,
        errorOutput
      }

      if (success) {
        results.passed.push(result)
        console.log(`✅ ${suite.name}: PASSED\n`)
      } else {
        results.failed.push(result)
        console.log(`❌ ${suite.name}: FAILED (exit code: ${code})\n`)
      }

      resolve(result)
    })

    testProcess.on('error', (error) => {
      const result = {
        name: suite.name,
        pattern: suite.pattern,
        success: false,
        code: -1,
        output: '',
        errorOutput: error.message
      }
      
      results.failed.push(result)
      console.log(`❌ ${suite.name}: ERROR - ${error.message}\n`)
      resolve(result)
    })
  })
}

// Generate detailed report
function generateReport() {
  console.log('\n📋 VALIDATION REPORT')
  console.log('='.repeat(60))
  
  console.log(`\n📈 SUMMARY:`)
  console.log(`  ✅ Passed: ${results.passed.length}`)
  console.log(`  ❌ Failed: ${results.failed.length}`)
  console.log(`  ⏭️  Skipped: ${results.skipped.length}`)
  console.log(`  📊 Total: ${results.passed.length + results.failed.length + results.skipped.length}`)

  if (results.passed.length > 0) {
    console.log(`\n✅ PASSED TESTS:`)
    results.passed.forEach(test => {
      console.log(`   • ${test.name}`)
    })
  }

  if (results.failed.length > 0) {
    console.log(`\n❌ FAILED TESTS:`)
    results.failed.forEach(test => {
      console.log(`   • ${test.name} (exit code: ${test.code})`)
    })
  }

  // Feature-specific validation summary
  console.log(`\n🎯 FEATURE VALIDATION STATUS:`)
  
  const features = {
    'Transaction Total Recall': results.passed.some(t => t.pattern.includes('TransactionPage')),
    'Dashboard Key Metrics': results.passed.some(t => t.pattern.includes('Dashboard')),
    'Enhanced API Endpoints': results.passed.some(t => t.pattern.includes('ApiEndpoints')),
    'End-to-End Integration': results.passed.some(t => t.pattern.includes('Integration'))
  }

  Object.entries(features).forEach(([feature, passed]) => {
    console.log(`   ${passed ? '✅' : '❌'} ${feature}`)
  })

  // Quality assurance recommendations
  console.log(`\n📋 QA RECOMMENDATIONS:`)
  
  if (results.failed.length === 0) {
    console.log('   🎉 All financial improvements are functioning correctly!')
    console.log('   ✅ Ready for production deployment')
    console.log('   💡 Consider adding performance tests for large datasets')
  } else {
    console.log('   ⚠️  Some tests are failing - review before deployment')
    console.log('   🔍 Check failed test logs for specific issues')
    console.log('   🛠️  Fix failing tests before proceeding to production')
  }

  // Performance notes
  console.log(`\n⚡ PERFORMANCE NOTES:`)
  console.log('   • Transaction calculations should complete within 100ms')
  console.log('   • Dashboard loading should complete within 2 seconds')
  console.log('   • API responses should return within 500ms')
  console.log('   • Large datasets (500+ transactions) should render within 3 seconds')

  console.log('\n' + '='.repeat(60))
  
  const overallSuccess = results.failed.length === 0
  console.log(`🏆 OVERALL RESULT: ${overallSuccess ? 'PASS' : 'FAIL'}`)
  
  return overallSuccess
}

// Main execution
async function main() {
  console.log('⚙️  Validating test environment...')
  
  // Check if test files exist
  const missingTests = testSuites.filter(suite => {
    const testPath = path.join(__dirname, '__tests__', suite.pattern)
    return !fs.existsSync(testPath)
  })

  if (missingTests.length > 0) {
    console.log('❌ Missing test files:')
    missingTests.forEach(test => {
      console.log(`   • ${test.pattern}`)
      results.skipped.push({ name: test.name, reason: 'Test file not found' })
    })
  }

  // Run available test suites
  const availableTests = testSuites.filter(suite => {
    const testPath = path.join(__dirname, '__tests__', suite.pattern)
    return fs.existsSync(testPath)
  })

  if (availableTests.length === 0) {
    console.log('❌ No test files found! Cannot validate financial improvements.')
    process.exit(1)
  }

  console.log(`✅ Found ${availableTests.length} test suites to run\n`)

  // Execute tests sequentially
  for (const suite of availableTests) {
    await runTestSuite(suite)
  }

  // Generate final report
  const success = generateReport()
  
  // Exit with appropriate code
  process.exit(success ? 0 : 1)
}

// Handle interruption gracefully
process.on('SIGINT', () => {
  console.log('\n\n⚠️  Validation interrupted by user')
  console.log('📊 Partial results:')
  generateReport()
  process.exit(130)
})

// Error handling
process.on('uncaughtException', (error) => {
  console.error('\n❌ Unexpected error during validation:', error.message)
  process.exit(1)
})

// Run the validation
main().catch(error => {
  console.error('\n❌ Validation script failed:', error.message)
  process.exit(1)
})