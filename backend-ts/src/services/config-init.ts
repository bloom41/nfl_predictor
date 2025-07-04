// Configuration Initialization Service
// Securely initializes application configuration and validates environment

import dotenv from 'dotenv';
import path from 'path';
import { envValidator, type EnvConfig } from './env-validation';
import { secretsManager } from './secrets-manager';

export interface AppConfig {
  server: {
    port: number;
    environment: string;
    apiVersion: string;
  };
  database: {
    url: string;
    ssl: boolean;
    maxConnections: number;
  };
  redis: {
    url: string;
    password?: string;
    clusterMode: boolean;
    tls: boolean;
  };
  security: {
    jwtSecret: string;
    corsOrigins: string[];
    rateLimit: {
      windowMs: number;
      max: number;
    };
  };
  services: {
    mlServiceUrl?: string;
    mlServiceTimeout: number;
    mlCacheTtl: number;
  };
  monitoring: {
    enableMetrics: boolean;
    metricsPort: number;
    logLevel: string;
    sentryDsn?: string;
  };
  features: {
    enableMLProjections: boolean;
    enableInjuryAnalysis: boolean;
    enableWeatherIntegration: boolean;
  };
  performance: {
    cacheDefaultTtl: number;
    databaseQueryTimeout: number;
    apiResponseTimeout: number;
  };
}

class ConfigurationService {
  private config: AppConfig | null = null;
  private envConfig: EnvConfig | null = null;

  /**
   * Initialize configuration from environment
   */
  async initialize(): Promise<AppConfig> {
    try {
      console.log('🔧 Initializing application configuration...');

      // Load environment file based on NODE_ENV
      this.loadEnvironmentFile();

      // Validate environment variables
      this.envConfig = envValidator.validateEnvironment();

      // Load secrets in production
      if (this.envConfig.NODE_ENV === 'production') {
        await this.loadProductionSecrets();
      }

      // Build application configuration
      this.config = await this.buildConfiguration(this.envConfig);

      // Validate configuration
      this.validateConfiguration(this.config);

      console.log(`✅ Configuration initialized successfully (${this.config.server.environment})`);
      return this.config;

    } catch (error) {
      console.error('❌ Configuration initialization failed:', error);
      throw error;
    }
  }

  /**
   * Get current configuration
   */
  getConfig(): AppConfig {
    if (!this.config) {
      throw new Error('Configuration not initialized. Call initialize() first.');
    }
    return this.config;
  }

  /**
   * Check if configuration is ready
   */
  isReady(): boolean {
    return this.config !== null;
  }

  /**
   * Get database configuration for Prisma
   */
  getDatabaseConfig() {
    const config = this.getConfig();
    return {
      url: config.database.url,
      ssl: config.database.ssl ? { rejectUnauthorized: false } : false,
      maxConnections: config.database.maxConnections
    };
  }

  /**
   * Load appropriate environment file
   */
  private loadEnvironmentFile(): void {
    const nodeEnv = process.env.NODE_ENV || 'development';
    const envFiles = [
      `.env.${nodeEnv}.local`,
      `.env.${nodeEnv}`,
      '.env.local',
      '.env'
    ];

    for (const envFile of envFiles) {
      const envPath = path.resolve(process.cwd(), envFile);
      const result = dotenv.config({ path: envPath });
      
      if (!result.error) {
        console.log(`📁 Loaded environment from: ${envFile}`);
        break;
      }
    }
  }

  /**
   * Load production secrets from secrets manager
   */
  private async loadProductionSecrets(): Promise<void> {
    try {
      console.log('🔐 Loading production secrets...');
      
      const secrets = await secretsManager.getProductionSecrets();
      
      // Override environment variables with secrets
      process.env.DATABASE_URL = secrets.databaseUrl;
      process.env.JWT_SECRET = secrets.jwtSecret;
      process.env.REDIS_URL = secrets.redisUrl;
      process.env.SENTRY_DSN = secrets.sentryDsn;
      
      if (secrets.redisPassword) {
        process.env.REDIS_PASSWORD = secrets.redisPassword;
      }
      if (secrets.nflApiKey) {
        process.env.NFL_API_KEY = secrets.nflApiKey;
      }
      if (secrets.weatherApiKey) {
        process.env.WEATHER_API_KEY = secrets.weatherApiKey;
      }

      console.log('✅ Production secrets loaded successfully');
    } catch (error) {
      console.error('❌ Failed to load production secrets:', error);
      throw new Error('Production secrets loading failed. Check your secrets manager configuration.');
    }
  }

  /**
   * Build application configuration from environment
   */
  private async buildConfiguration(envConfig: EnvConfig): Promise<AppConfig> {
    return {
      server: {
        port: envConfig.PORT,
        environment: envConfig.NODE_ENV,
        apiVersion: envConfig.API_VERSION
      },
      database: {
        url: envConfig.DATABASE_URL,
        ssl: envConfig.POSTGRES_SSL,
        maxConnections: envConfig.POSTGRES_MAX_CONNECTIONS
      },
      redis: {
        url: envConfig.REDIS_URL,
        ...(envConfig.REDIS_PASSWORD && { password: envConfig.REDIS_PASSWORD }),
        clusterMode: envConfig.REDIS_CLUSTER_MODE,
        tls: envConfig.REDIS_TLS
      },
      security: {
        jwtSecret: envConfig.JWT_SECRET,
        corsOrigins: envConfig.CORS_ORIGINS,
        rateLimit: {
          windowMs: envConfig.RATE_LIMIT_WINDOW,
          max: envConfig.RATE_LIMIT_MAX
        }
      },
      services: {
        ...(envConfig.ML_SERVICE_URL && { mlServiceUrl: envConfig.ML_SERVICE_URL }),
        mlServiceTimeout: envConfig.ML_SERVICE_TIMEOUT,
        mlCacheTtl: envConfig.ML_CACHE_TTL
      },
      monitoring: {
        enableMetrics: envConfig.ENABLE_METRICS,
        metricsPort: envConfig.METRICS_PORT,
        logLevel: envConfig.LOG_LEVEL,
        ...(envConfig.SENTRY_DSN && { sentryDsn: envConfig.SENTRY_DSN })
      },
      features: {
        enableMLProjections: envConfig.ENABLE_ML_PROJECTIONS,
        enableInjuryAnalysis: envConfig.ENABLE_INJURY_ANALYSIS,
        enableWeatherIntegration: envConfig.ENABLE_WEATHER_INTEGRATION
      },
      performance: {
        cacheDefaultTtl: envConfig.CACHE_DEFAULT_TTL,
        databaseQueryTimeout: envConfig.DATABASE_QUERY_TIMEOUT,
        apiResponseTimeout: envConfig.API_RESPONSE_TIMEOUT
      }
    };
  }

  /**
   * Validate final configuration
   */
  private validateConfiguration(config: AppConfig): void {
    const errors: string[] = [];

    // Production-specific validations
    if (config.server.environment === 'production') {
      if (!config.monitoring.sentryDsn) {
        errors.push('Sentry DSN is required in production');
      }

      if (config.security.corsOrigins.includes('*')) {
        errors.push('CORS origins cannot include "*" in production');
      }

      if (config.security.corsOrigins.some(origin => origin.includes('localhost'))) {
        errors.push('CORS origins cannot include localhost in production');
      }

      if (!config.database.ssl) {
        errors.push('Database SSL must be enabled in production');
      }
    }

    // General validations
    if (config.server.port < 1000 || config.server.port > 65535) {
      errors.push('Server port must be between 1000 and 65535');
    }

    if (config.security.jwtSecret.length < 32) {
      errors.push('JWT secret must be at least 32 characters long');
    }

    if (errors.length > 0) {
      throw new Error(`Configuration validation failed:\n${errors.join('\n')}`);
    }
  }

  /**
   * Print configuration summary (safe for logging)
   */
  printConfigSummary(): void {
    const config = this.getConfig();
    
    console.log('\n📋 Configuration Summary:');
    console.log(`Environment: ${config.server.environment}`);
    console.log(`Server Port: ${config.server.port}`);
    console.log(`API Version: ${config.server.apiVersion}`);
    console.log(`Database SSL: ${config.database.ssl ? 'Enabled' : 'Disabled'}`);
    console.log(`Redis TLS: ${config.redis.tls ? 'Enabled' : 'Disabled'}`);
    console.log(`Metrics: ${config.monitoring.enableMetrics ? 'Enabled' : 'Disabled'}`);
    console.log(`Log Level: ${config.monitoring.logLevel}`);
    console.log(`ML Projections: ${config.features.enableMLProjections ? 'Enabled' : 'Disabled'}`);
    console.log(`CORS Origins: ${config.security.corsOrigins.length} configured`);
    
    if (config.server.environment === 'production') {
      console.log(`Sentry: ${config.monitoring.sentryDsn ? 'Configured' : 'Not configured'}`);
    }
    console.log('');
  }

  /**
   * Export configuration for external tools
   */
  exportForDeployment(): {
    environment: string;
    requiredSecrets: string[];
    optionalSecrets: string[];
    configValidation: {
      isValid: boolean;
      errors: string[];
    };
  } {
    const config = this.getConfig();
    
    const requiredSecrets = config.server.environment === 'production' 
      ? [
          'DATABASE_URL_FROM_SECRETS_MANAGER',
          'JWT_SECRET_FROM_SECRETS_MANAGER',
          'REDIS_URL_FROM_SECRETS_MANAGER',
          'SENTRY_DSN_FROM_SECRETS_MANAGER'
        ]
      : [];

    const optionalSecrets = [
      'REDIS_PASSWORD_FROM_SECRETS_MANAGER',
      'NFL_API_KEY_FROM_SECRETS_MANAGER',
      'WEATHER_API_KEY_FROM_SECRETS_MANAGER'
    ];

    try {
      this.validateConfiguration(config);
      return {
        environment: config.server.environment,
        requiredSecrets,
        optionalSecrets,
        configValidation: {
          isValid: true,
          errors: []
        }
      };
    } catch (error) {
      return {
        environment: config.server.environment,
        requiredSecrets,
        optionalSecrets,
        configValidation: {
          isValid: false,
          errors: [error instanceof Error ? error.message : 'Unknown validation error']
        }
      };
    }
  }
}

// Export singleton instance
export const configService = new ConfigurationService();