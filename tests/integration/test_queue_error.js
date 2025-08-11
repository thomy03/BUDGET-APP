/**
 * Specific test for "Should have a queue" React error
 * This error typically occurs during hydration mismatches in React hooks
 * 
 * We'll test the specific conditions that cause this error:
 * 1. useGlobalMonth initialization during SSR
 * 2. localStorage access during server rendering
 * 3. State synchronization between server and client
 */

const axios = require('axios');
const fs = require('fs');

class QueueErrorValidator {
  constructor() {
    this.baseURL = 'http://localhost:45678';
    this.findings = {
      ssrAnalysis: null,
      hydrationProtection: null,
      monthHookImplementation: null,
      conclusion: null
    };
  }

  async analyzeSSRHTML() {
    console.log('🔍 Analyzing SSR HTML for hydration risks...');
    
    try {
      const response = await axios.get(`${this.baseURL}/`, {
        headers: {
          'User-Agent': 'SSR-Analysis-Bot/1.0'
        }
      });
      
      const html = response.data;
      
      // Look for signs of hydration mismatch risks
      const analysis = {
        hasLoadingState: html.includes('animate-spin') || html.includes('loading'),
        hasMountedCheck: html.includes('mounted') || html.includes('hydration'),
        hasMonthPicker: html.includes('type="month"'),
        hasLocalStorageReferences: html.includes('localStorage'),
        hasUserAgentChecks: html.includes('navigator') || html.includes('window'),
        htmlLength: html.length,
        timestamp: new Date().toISOString()
      };
      
      console.log('📊 SSR Analysis Results:');
      console.log(`   Has loading state: ${analysis.hasLoadingState}`);
      console.log(`   Has mounted check: ${analysis.hasMountedCheck}`);
      console.log(`   Has month picker: ${analysis.hasMonthPicker}`);
      console.log(`   Has localStorage refs: ${analysis.hasLocalStorageReferences}`);
      console.log(`   Has user agent checks: ${analysis.hasUserAgentChecks}`);
      
      this.findings.ssrAnalysis = analysis;
      
      // The key finding: if mounted check is working, month picker shouldn't appear in SSR
      const isProtectedCorrectly = analysis.hasLoadingState && !analysis.hasMonthPicker;
      
      if (isProtectedCorrectly) {
        console.log('✅ Hydration protection appears to be working correctly');
      } else {
        console.log('⚠️  Potential hydration mismatch risk detected');
      }
      
      return analysis;
      
    } catch (error) {
      console.error('❌ SSR HTML analysis failed:', error.message);
      return null;
    }
  }

  analyzeCodeImplementation() {
    console.log('🔍 Analyzing code implementation for queue error patterns...');
    
    try {
      // Read month.ts
      const monthFile = fs.readFileSync(
        '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/frontend/lib/month.ts',
        'utf8'
      );
      
      // Read layout.tsx
      const layoutFile = fs.readFileSync(
        '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/frontend/app/layout.tsx',
        'utf8'
      );
      
      const implementation = {
        monthHook: {
          hasUseClient: monthFile.includes("'use client'"),
          hasWindowCheck: monthFile.includes('typeof window !== \'undefined\''),
          hasProperInitialization: monthFile.includes('useState<string>(() =>'),
          hasLocalStorageAccess: monthFile.includes('localStorage.getItem'),
          usesCallback: monthFile.includes('useCallback'),
          usesEffect: monthFile.includes('useEffect')
        },
        layout: {
          hasUseClient: layoutFile.includes("'use client'"),
          hasMountedState: layoutFile.includes('const [mounted, setMounted] = useState(false)'),
          hasHydrationGuard: layoutFile.includes('if (!mounted)'),
          hasProperEffect: layoutFile.includes('useEffect(() => {\n    setMounted(true);'),
          returnsLoadingState: layoutFile.includes('animate-spin')
        }
      };
      
      console.log('📊 Implementation Analysis:');
      console.log('   Month Hook:');
      console.log(`     - 'use client' directive: ${implementation.monthHook.hasUseClient}`);
      console.log(`     - Window check: ${implementation.monthHook.hasWindowCheck}`);
      console.log(`     - Proper initialization: ${implementation.monthHook.hasProperInitialization}`);
      console.log(`     - localStorage access: ${implementation.monthHook.hasLocalStorageAccess}`);
      
      console.log('   Layout:');
      console.log(`     - 'use client' directive: ${implementation.layout.hasUseClient}`);
      console.log(`     - Mounted state: ${implementation.layout.hasMountedState}`);
      console.log(`     - Hydration guard: ${implementation.layout.hasHydrationGuard}`);
      console.log(`     - Proper effect: ${implementation.layout.hasProperEffect}`);
      
      this.findings.monthHookImplementation = implementation;
      
      // Check for potential "Should have a queue" error patterns
      const riskFactors = [];
      
      if (!implementation.monthHook.hasWindowCheck) {
        riskFactors.push('Month hook accesses localStorage without window check');
      }
      
      if (!implementation.layout.hasHydrationGuard) {
        riskFactors.push('Layout missing hydration protection');
      }
      
      if (!implementation.monthHook.hasUseClient && implementation.monthHook.hasLocalStorageAccess) {
        riskFactors.push('localStorage access in server component');
      }
      
      this.findings.hydrationProtection = {
        riskFactors,
        protectionLevel: riskFactors.length === 0 ? 'GOOD' : riskFactors.length <= 2 ? 'MODERATE' : 'HIGH_RISK'
      };
      
      console.log('🚨 Risk Assessment:');
      console.log(`   Protection Level: ${this.findings.hydrationProtection.protectionLevel}`);
      if (riskFactors.length > 0) {
        console.log('   Risk Factors:');
        riskFactors.forEach((factor, i) => {
          console.log(`     ${i + 1}. ${factor}`);
        });
      } else {
        console.log('   No significant risk factors found');
      }
      
      return implementation;
      
    } catch (error) {
      console.error('❌ Code implementation analysis failed:', error.message);
      return null;
    }
  }

  async testSpecificQueueError() {
    console.log('🧪 Testing for "Should have a queue" error conditions...');
    
    // This error typically happens when:
    // 1. useState is called during SSR with different initial values than client
    // 2. useEffect dependencies cause mismatched renders
    // 3. localStorage is accessed during server rendering
    
    const conditions = {
      serverClientMismatch: false,
      localStorageSSRAccess: false,
      stateInitializationIssue: false,
      effectDependencyIssue: false
    };
    
    // Check if localStorage is properly protected
    const monthHookCode = fs.readFileSync(
      '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/frontend/lib/month.ts',
      'utf8'
    );
    
    // Look for problematic patterns
    const hasUnguardedLocalStorage = monthHookCode.includes('localStorage') && 
                                   !monthHookCode.includes('typeof window');
    
    const hasProperInitializer = monthHookCode.includes('useState<string>(() =>');
    
    const hasEffectDependencies = monthHookCode.match(/useEffect\(.*\[(.*)\]/);
    
    conditions.localStorageSSRAccess = hasUnguardedLocalStorage;
    conditions.stateInitializationIssue = !hasProperInitializer;
    
    if (hasEffectDependencies) {
      const dependencies = hasEffectDependencies[1];
      // Complex dependency arrays can cause queue errors
      conditions.effectDependencyIssue = dependencies.includes('router') || 
                                        dependencies.includes('searchParams');
    }
    
    console.log('🔍 Queue Error Condition Analysis:');
    console.log(`   Unguarded localStorage: ${conditions.localStorageSSRAccess}`);
    console.log(`   State initialization issue: ${conditions.stateInitializationIssue}`);
    console.log(`   Effect dependency issue: ${conditions.effectDependencyIssue}`);
    
    const errorRisk = Object.values(conditions).some(Boolean);
    
    if (errorRisk) {
      console.log('⚠️  Potential "Should have a queue" error conditions found');
    } else {
      console.log('✅ No "Should have a queue" error conditions detected');
    }
    
    return {
      conditions,
      errorRisk,
      recommendation: errorRisk ? 
        'Review hook implementation and add proper hydration protection' :
        'Implementation appears safe for SSR hydration'
    };
  }

  generateQueueErrorReport() {
    const hasRisks = this.findings.hydrationProtection?.riskFactors?.length > 0;
    const protectionLevel = this.findings.hydrationProtection?.protectionLevel || 'UNKNOWN';
    
    const report = {
      timestamp: new Date().toISOString(),
      testSuite: 'Queue Error Validation',
      findings: this.findings,
      riskAssessment: {
        level: protectionLevel,
        hasHydrationRisks: hasRisks,
        criticalIssues: this.findings.hydrationProtection?.riskFactors || []
      },
      recommendations: this.generateRecommendations(),
      conclusion: hasRisks ? 'NEEDS_REVIEW' : 'PROTECTED'
    };
    
    console.log('\n📋 QUEUE ERROR VALIDATION REPORT');
    console.log('==================================');
    console.log(`Risk Level: ${report.riskAssessment.level}`);
    console.log(`Has Hydration Risks: ${report.riskAssessment.hasHydrationRisks}`);
    console.log(`Critical Issues: ${report.riskAssessment.criticalIssues.length}`);
    console.log(`Conclusion: ${report.conclusion}`);
    
    if (report.recommendations.length > 0) {
      console.log('\n🔧 Recommendations:');
      report.recommendations.forEach((rec, i) => {
        console.log(`   ${i + 1}. ${rec}`);
      });
    }
    
    return report;
  }

  generateRecommendations() {
    const recommendations = [];
    
    if (!this.findings.monthHookImplementation?.monthHook?.hasWindowCheck) {
      recommendations.push('Add window checks before localStorage access in useGlobalMonth');
    }
    
    if (!this.findings.monthHookImplementation?.layout?.hasHydrationGuard) {
      recommendations.push('Implement hydration guard in layout component');
    }
    
    if (this.findings.hydrationProtection?.protectionLevel === 'HIGH_RISK') {
      recommendations.push('Critical: Review all client-side hooks for SSR compatibility');
    }
    
    if (recommendations.length === 0) {
      recommendations.push('Current implementation follows React SSR best practices');
    }
    
    return recommendations;
  }

  async runValidation() {
    try {
      console.log('🚀 Starting Queue Error Validation...\n');
      
      await this.analyzeSSRHTML();
      this.analyzeCodeImplementation();
      await this.testSpecificQueueError();
      
      const report = this.generateQueueErrorReport();
      
      // Save report
      fs.writeFileSync('queue_error_validation.json', JSON.stringify(report, null, 2));
      console.log('\n📄 Report saved to queue_error_validation.json');
      
      return report;
      
    } catch (error) {
      console.error('💥 Queue error validation failed:', error.message);
      throw error;
    }
  }
}

// Execute validation
if (require.main === module) {
  const validator = new QueueErrorValidator();
  
  validator.runValidation()
    .then((report) => {
      process.exit(report.conclusion === 'PROTECTED' ? 0 : 1);
    })
    .catch((error) => {
      console.error('Validation execution failed:', error);
      process.exit(1);
    });
}

module.exports = QueueErrorValidator;