// Environment Variable Validation Service
// Validates and sanitizes environment configuration for NFL Predictor

import { z } from 'zod';

// Environment schema with strict validation
const envSchema = z.object({
  // Server Configuration
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().min(1000).max(65535).default(3001),
  API_VERSION: z.string().default('v1'),

  // Database Configuration
  DATABASE_URL: z.string().url().refine(
    (url) => url.startsWith('postgresql://') || url.startsWith('postgres://'),
    { message: 'DATABASE_URL must be a valid PostgreSQL connection string' }
  ),
  POSTGRES_SSL: z.enum(['true', 'false']).default('false').transform(val => val === 'true'),
  POSTGRES_MAX_CONNECTIONS: z.coerce.number().min(1).max(100).default(10),

  // Redis Configuration
  REDIS_URL: z.string().url().refine(
    (url) => url.startsWith('redis://') || url.startsWith('rediss://'),
    { message: 'REDIS_URL must be a valid Redis connection string' }
  ),
  REDIS_PASSWORD: z.string().optional(),
  REDIS_CLUSTER_MODE: z.enum(['true', 'false']).default('false').transform(val => val === 'true'),
  REDIS_TLS: z.enum(['true', 'false']).default('false').transform(val => val === 'true'),

  // Security Configuration
  JWT_SECRET: z.string().min(32),
  CORS_ORIGINS: z.string().transform(val => val.split(',').map(origin => origin.trim())),
  RATE_LIMIT_WINDOW: z.coerce.number().min(60000).default(900000), // 15 minutes
  RATE_LIMIT_MAX: z.coerce.number().min(10).max(1000).default(100),

  // ML Service Configuration
  ML_SERVICE_URL: z.string().url().optional(),
  ML_SERVICE_TIMEOUT: z.coerce.number().min(5000).max(120000).default(30000),
  ML_CACHE_TTL: z.coerce.number().min(300).max(86400).default(3600),

  // External APIs
  NFL_API_KEY: z.string().optional(),
  WEATHER_API_KEY: z.string().optional(),
  SENTRY_DSN: z.string().optional().refine(
    (dsn) => !dsn || dsn.startsWith('https://'),
    { message: 'SENTRY_DSN must be a valid HTTPS URL or empty' }
  ),

  // Performance Configuration
  CACHE_DEFAULT_TTL: z.coerce.number().min(60).max(86400).default(1800),
  DATABASE_QUERY_TIMEOUT: z.coerce.number().min(1000).max(60000).default(10000),
  API_RESPONSE_TIMEOUT: z.coerce.number().min(5000).max(120000).default(30000),

  // Monitoring Configuration
  ENABLE_METRICS: z.enum(['true', 'false']).default('true').transform(val => val === 'true'),
  METRICS_PORT: z.coerce.number().min(1000).max(65535).default(9090),
  LOG_LEVEL: z.enum(['error', 'warn', 'info', 'debug']).default('info'),

  // Feature Flags
  ENABLE_ML_PROJECTIONS: z.enum(['true', 'false']).default('true').transform(val => val === 'true'),
  ENABLE_INJURY_ANALYSIS: z.enum(['true', 'false']).default('true').transform(val => val === 'true'),
  ENABLE_WEATHER_INTEGRATION: z.enum(['true', 'false']).default('false').transform(val => val === 'true'),
});

// Production-specific validation
const productionSchema = envSchema.extend({
  NODE_ENV: z.literal('production'),
  JWT_SECRET: z.string().min(64).refine(
    (secret) => {
      // Must be cryptographically secure for production
      const hasUppercase = /[A-Z]/.test(secret);
      const hasLowercase = /[a-z]/.test(secret);
      const hasNumbers = /\d/.test(secret);
      const hasSpecialChars = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(secret);
      return hasUppercase && hasLowercase && hasNumbers && hasSpecialChars;
    },
    { message: 'JWT_SECRET must contain uppercase, lowercase, numbers, and special characters in production' }
  ),
  DATABASE_URL: z.string().url().refine(
    (url) => !url.includes('localhost') && !url.includes('127.0.0.1'),
    { message: 'DATABASE_URL cannot use localhost in production' }
  ),
  REDIS_URL: z.string().url().refine(
    (url) => !url.includes('localhost') && !url.includes('127.0.0.1'),
    { message: 'REDIS_URL cannot use localhost in production' }
  ),
  POSTGRES_SSL: z.literal(true),
  SENTRY_DSN: z.string().url().min(1), // Required in production
});

export type EnvConfig = z.infer<typeof envSchema>;
export type ProductionEnvConfig = z.infer<typeof productionSchema>;

class EnvironmentValidator {
  private config: EnvConfig | null = null;
  private validationErrors: string[] = [];

  /**
   * Validate and parse environment variables
   */
  validateEnvironment(env: Record<string, string | undefined> = process.env): EnvConfig {
    try {
      // Use production schema if NODE_ENV is production
      const schema = env.NODE_ENV === 'production' ? productionSchema : envSchema;
      
      this.config = schema.parse(env);
      this.validationErrors = [];
      
      // Additional custom validations
      this.performCustomValidations(this.config);
      
      if (this.validationErrors.length > 0) {
        throw new Error(`Environment validation failed:\n${this.validationErrors.join('\n')}`);
      }

      console.log(`✅ Environment validation successful (${this.config.NODE_ENV} mode)`);
      return this.config;
    } catch (error) {
      if (error instanceof z.ZodError) {
        const errorMessages = error.errors.map(err => `${err.path.join('.')}: ${err.message}`);
        throw new Error(`Environment validation failed:\n${errorMessages.join('\n')}`);
      }
      throw error;
    }
  }

  /**
   * Get validated configuration
   */
  getConfig(): EnvConfig {
    if (!this.config) {
      throw new Error('Environment not validated. Call validateEnvironment() first.');
    }
    return this.config;
  }

  /**
   * Check if running in production
   */
  isProduction(): boolean {
    return this.getConfig().NODE_ENV === 'production';
  }

  /**
   * Check if running in development
   */
  isDevelopment(): boolean {
    return this.getConfig().NODE_ENV === 'development';
  }

  /**
   * Check if running in test mode
   */
  isTest(): boolean {
    return this.getConfig().NODE_ENV === 'test';
  }

  /**
   * Get database configuration
   */
  getDatabaseConfig() {
    const config = this.getConfig();
    return {
      url: config.DATABASE_URL,
      ssl: config.POSTGRES_SSL,
      maxConnections: config.POSTGRES_MAX_CONNECTIONS
    };
  }

  /**
   * Get Redis configuration
   */
  getRedisConfig() {
    const config = this.getConfig();
    return {
      url: config.REDIS_URL,
      password: config.REDIS_PASSWORD,
      clusterMode: config.REDIS_CLUSTER_MODE,
      tls: config.REDIS_TLS
    };
  }

  /**
   * Get security configuration
   */
  getSecurityConfig() {
    const config = this.getConfig();
    return {
      jwtSecret: config.JWT_SECRET,
      corsOrigins: config.CORS_ORIGINS,
      rateLimit: {
        windowMs: config.RATE_LIMIT_WINDOW,
        max: config.RATE_LIMIT_MAX
      }
    };
  }

  /**
   * Perform custom validations
   */
  private performCustomValidations(config: EnvConfig): void {
    // Check for common insecure patterns
    if (config.JWT_SECRET.includes('secret') || config.JWT_SECRET.includes('password')) {
      this.validationErrors.push('JWT_SECRET should not contain common words like "secret" or "password"');
    }

    // Check CORS origins format
    try {
      config.CORS_ORIGINS.forEach(origin => {
        if (origin !== '*' && !origin.startsWith('http://') && !origin.startsWith('https://')) {
          this.validationErrors.push(`Invalid CORS origin: ${origin}. Must start with http:// or https://`);
        }
      });
    } catch (error) {
      this.validationErrors.push('Invalid CORS_ORIGINS format');
    }

    // Check production-specific requirements
    if (config.NODE_ENV === 'production') {
      if (config.CORS_ORIGINS.includes('*')) {
        this.validationErrors.push('CORS_ORIGINS cannot include "*" in production');
      }

      if (config.CORS_ORIGINS.some(origin => origin.includes('localhost'))) {
        this.validationErrors.push('CORS_ORIGINS cannot include localhost in production');
      }

      if (!config.SENTRY_DSN) {
        this.validationErrors.push('SENTRY_DSN is required in production for error monitoring');
      }
    }
  }

  /**
   * Generate environment template
   */
  generateTemplate(environment: 'development' | 'production' | 'test'): string {
    const templates = {
      development: this.generateDevelopmentTemplate(),
      production: this.generateProductionTemplate(),
      test: this.generateTestTemplate()
    };

    return templates[environment];
  }

  private generateDevelopmentTemplate(): string {
    return `# NFL Predictor Backend - Development Environment
# This file contains development-specific configuration

# Server Configuration
NODE_ENV=development
PORT=3001
API_VERSION=v1

# Database Configuration
DATABASE_URL="postgresql://username:password@localhost:5432/nfl_predictor_dev"
POSTGRES_SSL=false
POSTGRES_MAX_CONNECTIONS=10

# Redis Configuration
REDIS_URL="redis://localhost:6379"
REDIS_PASSWORD=""
REDIS_CLUSTER_MODE=false
REDIS_TLS=false

# Security Configuration (DEVELOPMENT ONLY)
JWT_SECRET="dev-jwt-secret-min-32-chars-replace-in-production"
CORS_ORIGINS="http://localhost:3000,http://localhost:5173"
RATE_LIMIT_WINDOW=900000
RATE_LIMIT_MAX=100

# ML Service Configuration
ML_SERVICE_URL="http://localhost:5000"
ML_SERVICE_TIMEOUT=30000
ML_CACHE_TTL=3600

# External APIs (Optional)
NFL_API_KEY=""
WEATHER_API_KEY=""
SENTRY_DSN=""

# Performance Configuration
CACHE_DEFAULT_TTL=1800
DATABASE_QUERY_TIMEOUT=10000
API_RESPONSE_TIMEOUT=30000

# Monitoring Configuration
ENABLE_METRICS=true
METRICS_PORT=9090
LOG_LEVEL=debug

# Feature Flags
ENABLE_ML_PROJECTIONS=true
ENABLE_INJURY_ANALYSIS=true
ENABLE_WEATHER_INTEGRATION=false
`;
  }

  private generateProductionTemplate(): string {
    return `# NFL Predictor Backend - Production Environment
# SECURITY WARNING: This file contains production secrets
# Store sensitive values in your secrets management system

# Server Configuration
NODE_ENV=production
PORT=3001
API_VERSION=v1

# Database Configuration
DATABASE_URL="\${DATABASE_URL_FROM_SECRETS_MANAGER}"
POSTGRES_SSL=true
POSTGRES_MAX_CONNECTIONS=20

# Redis Configuration
REDIS_URL="\${REDIS_URL_FROM_SECRETS_MANAGER}"
REDIS_PASSWORD="\${REDIS_PASSWORD_FROM_SECRETS_MANAGER}"
REDIS_CLUSTER_MODE=true
REDIS_TLS=true

# Security Configuration
JWT_SECRET="\${JWT_SECRET_FROM_SECRETS_MANAGER}"
CORS_ORIGINS="https://nflpredictor.com,https://www.nflpredictor.com"
RATE_LIMIT_WINDOW=900000
RATE_LIMIT_MAX=100

# ML Service Configuration
ML_SERVICE_URL="http://ml-service:5000"
ML_SERVICE_TIMEOUT=30000
ML_CACHE_TTL=3600

# External APIs
NFL_API_KEY="\${NFL_API_KEY_FROM_SECRETS_MANAGER}"
WEATHER_API_KEY="\${WEATHER_API_KEY_FROM_SECRETS_MANAGER}"
SENTRY_DSN="\${SENTRY_DSN_FROM_SECRETS_MANAGER}"

# Performance Configuration
CACHE_DEFAULT_TTL=1800
DATABASE_QUERY_TIMEOUT=10000
API_RESPONSE_TIMEOUT=30000

# Monitoring Configuration
ENABLE_METRICS=true
METRICS_PORT=9090
LOG_LEVEL=info

# Feature Flags
ENABLE_ML_PROJECTIONS=true
ENABLE_INJURY_ANALYSIS=true
ENABLE_WEATHER_INTEGRATION=true
`;
  }

  private generateTestTemplate(): string {
    return `# NFL Predictor Backend - Test Environment

# Server Configuration
NODE_ENV=test
PORT=3002
API_VERSION=v1

# Database Configuration (Test DB)
DATABASE_URL="postgresql://test_user:test_pass@localhost:5432/nfl_predictor_test"
POSTGRES_SSL=false
POSTGRES_MAX_CONNECTIONS=5

# Redis Configuration (Test Redis)
REDIS_URL="redis://localhost:6380"
REDIS_PASSWORD=""
REDIS_CLUSTER_MODE=false
REDIS_TLS=false

# Security Configuration (TEST ONLY)
JWT_SECRET="test-jwt-secret-32-chars-minimum-length"
CORS_ORIGINS="http://localhost:3000"
RATE_LIMIT_WINDOW=60000
RATE_LIMIT_MAX=1000

# ML Service Configuration
ML_SERVICE_URL="http://localhost:5001"
ML_SERVICE_TIMEOUT=5000
ML_CACHE_TTL=300

# External APIs (Mock/Test)
NFL_API_KEY="test_api_key"
WEATHER_API_KEY="test_weather_key"
SENTRY_DSN=""

# Performance Configuration
CACHE_DEFAULT_TTL=300
DATABASE_QUERY_TIMEOUT=5000
API_RESPONSE_TIMEOUT=10000

# Monitoring Configuration
ENABLE_METRICS=false
METRICS_PORT=9091
LOG_LEVEL=error

# Feature Flags
ENABLE_ML_PROJECTIONS=false
ENABLE_INJURY_ANALYSIS=false
ENABLE_WEATHER_INTEGRATION=false
`;
  }
}

// Export singleton instance
export const envValidator = new EnvironmentValidator();