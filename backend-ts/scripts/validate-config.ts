#!/usr/bin/env tsx
// Configuration Validation Script
// Validates environment configuration for deployment readiness

import dotenv from 'dotenv';
import { configService } from '../src/services/config-init';
import { secretsManager } from '../src/services/secrets-manager';
import { envValidator } from '../src/services/env-validation';

async function validateConfiguration() {
  console.log('🔍 Validating NFL Predictor Configuration...\n');

  // Load environment file
  dotenv.config();

  try {
    // 1. Environment Validation
    console.log('1️⃣ Validating Environment Variables...');
    const envConfig = envValidator.validateEnvironment();
    console.log('✅ Environment variables valid');

    // 2. Configuration Initialization
    console.log('\n2️⃣ Initializing Configuration...');
    const config = await configService.initialize();
    console.log('✅ Configuration initialized successfully');

    // 3. Secrets Manager Health Check
    console.log('\n3️⃣ Testing Secrets Manager...');
    const secretsHealthy = await secretsManager.healthCheck();
    if (secretsHealthy) {
      console.log('✅ Secrets manager is healthy');
    } else {
      console.log('⚠️  Secrets manager health check failed (using fallback)');
    }

    // 4. Configuration Summary
    console.log('\n📋 Configuration Summary:');
    configService.printConfigSummary();

    // 5. Security Validation
    console.log('🔒 Security Validation:');
    const securityChecks = [
      {
        name: 'JWT Secret Strength',
        check: () => {
          const validation = secretsManager.constructor.validateSecretStrength(config.security.jwtSecret);
          return validation.isStrong;
        },
        message: 'JWT secret meets security requirements'
      },
      {
        name: 'Database SSL',
        check: () => config.database.ssl || config.server.environment !== 'production',
        message: 'Database SSL properly configured'
      },
      {
        name: 'Redis TLS',
        check: () => config.redis.tls || config.server.environment !== 'production',
        message: 'Redis TLS properly configured'
      },
      {
        name: 'CORS Security',
        check: () => !config.security.corsOrigins.includes('*') || config.server.environment !== 'production',
        message: 'CORS origins are secure'
      },
      {
        name: 'Production Monitoring',
        check: () => config.monitoring.sentryDsn !== undefined || config.server.environment !== 'production',
        message: 'Production monitoring configured'
      }
    ];

    let allSecurityChecksPassed = true;

    for (const check of securityChecks) {
      try {
        if (check.check()) {
          console.log(`  ✅ ${check.message}`);
        } else {
          console.log(`  ❌ ${check.message} - FAILED`);
          allSecurityChecksPassed = false;
        }
      } catch (error) {
        console.log(`  ⚠️  ${check.message} - ERROR: ${error}`);
        allSecurityChecksPassed = false;
      }
    }

    // 6. Deployment Readiness Check
    console.log('\n🚀 Deployment Readiness:');
    const deploymentInfo = configService.exportForDeployment();
    
    if (deploymentInfo.configValidation.isValid && allSecurityChecksPassed) {
      console.log('✅ Configuration is READY for deployment');
      console.log(`Environment: ${deploymentInfo.environment}`);
      console.log(`Required Secrets: ${deploymentInfo.requiredSecrets.length}`);
      console.log(`Optional Secrets: ${deploymentInfo.optionalSecrets.length}`);
    } else {
      console.log('❌ Configuration is NOT ready for deployment');
      if (!deploymentInfo.configValidation.isValid) {
        console.log('Configuration errors:');
        deploymentInfo.configValidation.errors.forEach(error => 
          console.log(`  - ${error}`)
        );
      }
      if (!allSecurityChecksPassed) {
        console.log('Security validation failed - see security checks above');
      }
      process.exit(1);
    }

    // 7. Recommendations
    if (config.server.environment === 'production') {
      console.log('\n💡 Production Recommendations:');
      console.log('  - Rotate secrets every 90 days');
      console.log('  - Monitor configuration access logs');
      console.log('  - Set up automated security scanning');
      console.log('  - Configure backup and disaster recovery');
      console.log('  - Enable detailed application monitoring');
    }

    console.log('\n🎉 Configuration validation completed successfully!');

  } catch (error) {
    console.error('\n❌ Configuration validation failed:');
    console.error(error);
    process.exit(1);
  }
}

// Run validation
if (require.main === module) {
  validateConfiguration();
}