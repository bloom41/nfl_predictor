// Secrets Management Service
// Handles secure retrieval of secrets from various providers (AWS, Azure, etc.)

import { envValidator } from './env-validation';

export interface SecretsProvider {
  getSecret(secretName: string): Promise<string>;
  getSecrets(secretNames: string[]): Promise<Record<string, string>>;
}

// AWS Secrets Manager Provider
export class AWSSecretsProvider implements SecretsProvider {
  constructor(_region: string = 'us-east-1') {
    // Region parameter for future AWS SDK implementation
  }

  async getSecret(secretName: string): Promise<string> {
    try {
      // In a real implementation, use AWS SDK
      // const { SecretsManagerClient, GetSecretValueCommand } = require('@aws-sdk/client-secrets-manager');
      // const client = new SecretsManagerClient({ region: _region });
      // const response = await client.send(new GetSecretValueCommand({ SecretId: secretName }));
      // return response.SecretString;
      
      // For now, return environment variable or throw error
      const value = process.env[secretName];
      if (!value) {
        throw new Error(`Secret ${secretName} not found in AWS Secrets Manager`);
      }
      return value;
    } catch (error) {
      console.error(`Failed to retrieve secret ${secretName} from AWS:`, error);
      throw error;
    }
  }

  async getSecrets(secretNames: string[]): Promise<Record<string, string>> {
    const secrets: Record<string, string> = {};
    for (const secretName of secretNames) {
      secrets[secretName] = await this.getSecret(secretName);
    }
    return secrets;
  }
}

// Azure Key Vault Provider
export class AzureKeyVaultProvider implements SecretsProvider {
  constructor(_vaultUrl: string) {
    // VaultUrl parameter for future Azure SDK implementation
  }

  async getSecret(secretName: string): Promise<string> {
    try {
      // In a real implementation, use Azure SDK
      // const { SecretClient } = require('@azure/keyvault-secrets');
      // const { DefaultAzureCredential } = require('@azure/identity');
      // const credential = new DefaultAzureCredential();
      // const client = new SecretClient(_vaultUrl, credential);
      // const secret = await client.getSecret(secretName);
      // return secret.value;
      
      // For now, return environment variable or throw error
      const value = process.env[secretName];
      if (!value) {
        throw new Error(`Secret ${secretName} not found in Azure Key Vault`);
      }
      return value;
    } catch (error) {
      console.error(`Failed to retrieve secret ${secretName} from Azure:`, error);
      throw error;
    }
  }

  async getSecrets(secretNames: string[]): Promise<Record<string, string>> {
    const secrets: Record<string, string> = {};
    for (const secretName of secretNames) {
      secrets[secretName] = await this.getSecret(secretName);
    }
    return secrets;
  }
}

// Environment Variables Provider (fallback)
export class EnvironmentProvider implements SecretsProvider {
  async getSecret(secretName: string): Promise<string> {
    const value = process.env[secretName];
    if (!value) {
      throw new Error(`Environment variable ${secretName} not found`);
    }
    return value;
  }

  async getSecrets(secretNames: string[]): Promise<Record<string, string>> {
    const secrets: Record<string, string> = {};
    for (const secretName of secretNames) {
      secrets[secretName] = await this.getSecret(secretName);
    }
    return secrets;
  }
}

class SecretsManager {
  private provider: SecretsProvider | null = null;
  private secretsCache: Map<string, { value: string; expiry: number }> = new Map();
  private readonly CACHE_TTL = 300000; // 5 minutes

  constructor() {
    // Initialize provider lazily to avoid circular dependencies
  }

  private getProvider(): SecretsProvider {
    if (!this.provider) {
      const nodeEnv = process.env.NODE_ENV || 'development';
      
      if (nodeEnv === 'production') {
        // Detect cloud provider and use appropriate secrets manager
        if (process.env.AWS_REGION || process.env.AWS_DEFAULT_REGION) {
          console.log('🔐 Using AWS Secrets Manager');
          this.provider = new AWSSecretsProvider(process.env.AWS_REGION || 'us-east-1');
        } else if (process.env.AZURE_KEY_VAULT_URL) {
          console.log('🔐 Using Azure Key Vault');
          this.provider = new AzureKeyVaultProvider(process.env.AZURE_KEY_VAULT_URL);
        } else {
          console.log('🔐 Using Environment Variables (production fallback)');
          this.provider = new EnvironmentProvider();
        }
      } else {
        console.log('🔐 Using Environment Variables (development/fallback)');
        this.provider = new EnvironmentProvider();
      }
    }
    return this.provider;
  }

  /**
   * Get a single secret with caching
   */
  async getSecret(secretName: string): Promise<string> {
    // Check cache first
    const cached = this.secretsCache.get(secretName);
    if (cached && cached.expiry > Date.now()) {
      return cached.value;
    }

    try {
      const value = await this.getProvider().getSecret(secretName);
      
      // Cache the secret
      this.secretsCache.set(secretName, {
        value,
        expiry: Date.now() + this.CACHE_TTL
      });

      return value;
    } catch (error) {
      console.error(`Failed to retrieve secret ${secretName}:`, error);
      throw error;
    }
  }

  /**
   * Get multiple secrets
   */
  async getSecrets(secretNames: string[]): Promise<Record<string, string>> {
    const secrets: Record<string, string> = {};
    
    for (const secretName of secretNames) {
      secrets[secretName] = await this.getSecret(secretName);
    }

    return secrets;
  }

  /**
   * Get production secrets for the application
   */
  async getProductionSecrets(): Promise<{
    databaseUrl: string;
    jwtSecret: string;
    redisUrl: string;
    redisPassword?: string;
    sentryDsn: string;
    nflApiKey?: string;
    weatherApiKey?: string;
  }> {
    const requiredSecrets = [
      'DATABASE_URL_FROM_SECRETS_MANAGER',
      'JWT_SECRET_FROM_SECRETS_MANAGER',
      'REDIS_URL_FROM_SECRETS_MANAGER',
      'SENTRY_DSN_FROM_SECRETS_MANAGER'
    ];

    const optionalSecrets = [
      'REDIS_PASSWORD_FROM_SECRETS_MANAGER',
      'NFL_API_KEY_FROM_SECRETS_MANAGER',
      'WEATHER_API_KEY_FROM_SECRETS_MANAGER'
    ];

    try {
      const secrets = await this.getSecrets([...requiredSecrets, ...optionalSecrets]);

      const result: {
        databaseUrl: string;
        jwtSecret: string;
        redisUrl: string;
        redisPassword?: string;
        sentryDsn: string;
        nflApiKey?: string;
        weatherApiKey?: string;
      } = {
        databaseUrl: secrets.DATABASE_URL_FROM_SECRETS_MANAGER || '',
        jwtSecret: secrets.JWT_SECRET_FROM_SECRETS_MANAGER || '',
        redisUrl: secrets.REDIS_URL_FROM_SECRETS_MANAGER || '',
        sentryDsn: secrets.SENTRY_DSN_FROM_SECRETS_MANAGER || ''
      };

      if (secrets.REDIS_PASSWORD_FROM_SECRETS_MANAGER) {
        result.redisPassword = secrets.REDIS_PASSWORD_FROM_SECRETS_MANAGER;
      }
      if (secrets.NFL_API_KEY_FROM_SECRETS_MANAGER) {
        result.nflApiKey = secrets.NFL_API_KEY_FROM_SECRETS_MANAGER;
      }
      if (secrets.WEATHER_API_KEY_FROM_SECRETS_MANAGER) {
        result.weatherApiKey = secrets.WEATHER_API_KEY_FROM_SECRETS_MANAGER;
      }

      return result;
    } catch (error) {
      console.error('Failed to retrieve production secrets:', error);
      throw new Error('Production secrets retrieval failed. Check your secrets manager configuration.');
    }
  }

  /**
   * Clear secrets cache (for security)
   */
  clearCache(): void {
    this.secretsCache.clear();
    console.log('🧹 Secrets cache cleared');
  }

  /**
   * Health check for secrets provider
   */
  async healthCheck(): Promise<boolean> {
    try {
      // Try to get a test secret or environment variable
      await this.getSecret('NODE_ENV');
      return true;
    } catch (error) {
      console.error('Secrets manager health check failed:', error);
      return false;
    }
  }

  /**
   * Generate secure JWT secret
   */
  static generateJWTSecret(): string {
    const crypto = require('crypto');
    return crypto.randomBytes(64).toString('base64');
  }

  /**
   * Validate secret strength
   */
  static validateSecretStrength(secret: string): {
    isStrong: boolean;
    score: number;
    recommendations: string[];
  } {
    const recommendations: string[] = [];
    let score = 0;

    // Length check
    if (secret.length >= 64) {
      score += 30;
    } else if (secret.length >= 32) {
      score += 20;
    } else {
      recommendations.push('Secret should be at least 32 characters long (64+ recommended)');
    }

    // Character variety
    const hasUppercase = /[A-Z]/.test(secret);
    const hasLowercase = /[a-z]/.test(secret);
    const hasNumbers = /\d/.test(secret);
    const hasSpecialChars = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(secret);

    if (hasUppercase) score += 15;
    else recommendations.push('Include uppercase letters');

    if (hasLowercase) score += 15;
    else recommendations.push('Include lowercase letters');

    if (hasNumbers) score += 15;
    else recommendations.push('Include numbers');

    if (hasSpecialChars) score += 15;
    else recommendations.push('Include special characters');

    // Common patterns check
    const commonPatterns = ['password', 'secret', 'admin', '123', 'abc'];
    const hasCommonPattern = commonPatterns.some(pattern => 
      secret.toLowerCase().includes(pattern)
    );
    
    if (hasCommonPattern) {
      score -= 20;
      recommendations.push('Avoid common words and patterns');
    } else {
      score += 10;
    }

    return {
      isStrong: score >= 80,
      score: Math.max(0, Math.min(100, score)),
      recommendations
    };
  }
}

// Export singleton instance
export const secretsManager = new SecretsManager();