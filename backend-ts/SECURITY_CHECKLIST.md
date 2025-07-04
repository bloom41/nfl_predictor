# Security Configuration Checklist

## 🔒 Environment Security Validation

### ✅ Pre-Production Security Requirements

#### 1. Environment Variables
- [ ] All production secrets stored in secrets manager (not environment files)
- [ ] Development environment files use safe placeholder values
- [ ] No hardcoded credentials in source code
- [ ] JWT secrets are cryptographically secure (64+ characters)
- [ ] Database connections use SSL in production
- [ ] Redis connections use TLS in production

#### 2. CORS Configuration
- [ ] Production CORS origins are specific domains (no wildcards)
- [ ] No localhost origins in production CORS settings
- [ ] Credentials enabled only for trusted origins

#### 3. Rate Limiting
- [ ] Rate limiting enabled for all API endpoints
- [ ] Health check endpoints excluded from rate limiting
- [ ] Production rate limits appropriate for expected load

#### 4. Security Headers
- [ ] HSTS enabled with long max-age in production
- [ ] Content Security Policy configured for production
- [ ] X-Frame-Options, X-Content-Type-Options enabled

#### 5. Secrets Management
- [ ] AWS Secrets Manager or Azure Key Vault configured
- [ ] Secrets rotation policy implemented
- [ ] Secrets cache automatically cleared on shutdown
- [ ] No secrets logged or exposed in error messages

### 🛡️ Production Security Configuration

#### Environment Template Usage
```bash
# 1. Copy production template
cp .env.production.template .env.production

# 2. Replace placeholder values with actual secrets
# Replace ${DATABASE_URL_FROM_SECRETS_MANAGER} with actual URL
# Replace ${JWT_SECRET_FROM_SECRETS_MANAGER} with actual secret
# etc.

# 3. Validate configuration
npm run config:validate
```

#### Secrets Manager Setup (AWS)
```bash
# Create secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name "nfl-predictor/database-url" \
  --description "PostgreSQL database connection URL" \
  --secret-string "postgresql://user:pass@host:5432/db"

aws secretsmanager create-secret \
  --name "nfl-predictor/jwt-secret" \
  --description "JWT signing secret" \
  --secret-string "$(openssl rand -base64 64)"

aws secretsmanager create-secret \
  --name "nfl-predictor/redis-url" \
  --description "Redis connection URL" \
  --secret-string "redis://cache-cluster.aws.com:6379"
```

#### Configuration Validation Commands
```bash
# Validate environment configuration
npm run typecheck
npm run build
npm run config:validate

# Test configuration loading
npm run config:test

# Generate secure JWT secret
node -e "console.log(require('crypto').randomBytes(64).toString('base64'))"
```

### 🔍 Security Validation Tests

#### 1. Environment Validation
- JWT secret strength validation
- Database SSL requirement check
- CORS origins validation
- Rate limiting configuration

#### 2. Secrets Manager Integration
- Connection test to secrets provider
- Secret retrieval validation
- Cache expiration testing
- Fallback mechanism testing

### 📋 Deployment Security Steps

#### Pre-Deployment
1. **Validate Configuration**
   ```bash
   npm run config:validate
   ```

2. **Test Secrets Integration**
   ```bash
   npm run secrets:test
   ```

3. **Security Scan**
   ```bash
   npm audit
   npm run security:scan
   ```

#### During Deployment
1. **Set Environment**
   ```bash
   export NODE_ENV=production
   ```

2. **Initialize Secrets**
   ```bash
   # Secrets manager should auto-load
   npm start
   ```

3. **Verify Security Headers**
   ```bash
   curl -I https://api.nflpredictor.com/api/status
   ```

#### Post-Deployment
1. **Security Health Check**
   ```bash
   curl https://api.nflpredictor.com/api/security/health
   ```

2. **Monitor Security Metrics**
   - Failed authentication attempts
   - Rate limit violations
   - Secrets access patterns

### 🚨 Security Incident Response

#### If Secrets Are Compromised
1. **Immediate Actions**
   ```bash
   # Rotate all affected secrets
   aws secretsmanager update-secret --secret-id nfl-predictor/jwt-secret \
     --secret-string "$(openssl rand -base64 64)"
   
   # Restart all application instances
   kubectl rollout restart deployment/nfl-predictor-backend
   ```

2. **Audit Actions**
   - Review access logs
   - Check for unauthorized API usage
   - Validate database integrity

#### Common Security Issues
1. **Weak JWT Secret**
   - Error: JWT secret validation failed
   - Fix: Generate new cryptographically secure secret

2. **Insecure CORS Configuration**
   - Error: CORS origins validation failed
   - Fix: Remove wildcards and localhost from production

3. **Missing SSL Configuration**
   - Error: Database SSL required in production
   - Fix: Enable SSL in database connection string

### 🔧 Environment Configuration Examples

#### Development (.env.development)
```bash
NODE_ENV=development
DATABASE_URL="postgresql://dev_user:dev_pass@localhost:5432/nfl_dev"
JWT_SECRET="dev-jwt-secret-32-chars-minimum-replace"
CORS_ORIGINS="http://localhost:3000,http://localhost:5173"
```

#### Production (.env.production)
```bash
NODE_ENV=production
DATABASE_URL="${DATABASE_URL_FROM_SECRETS_MANAGER}"
JWT_SECRET="${JWT_SECRET_FROM_SECRETS_MANAGER}"
CORS_ORIGINS="https://nflpredictor.com,https://www.nflpredictor.com"
POSTGRES_SSL=true
REDIS_TLS=true
```

### 📊 Security Metrics Dashboard

Monitor these security metrics in production:
- Authentication failure rate
- Rate limit hit rate
- Secrets access frequency
- SSL/TLS connection success rate
- CORS violation attempts

### 🎯 Security Compliance

This configuration provides:
- ✅ **Encryption in Transit**: HTTPS, Redis TLS, Database SSL
- ✅ **Encryption at Rest**: Secrets Manager encryption
- ✅ **Access Control**: CORS, rate limiting, authentication
- ✅ **Monitoring**: Security event logging
- ✅ **Incident Response**: Automated secret rotation capability

---

**Security Team Contacts:**
- Infrastructure Security: security@nflpredictor.com
- Application Security: appsec@nflpredictor.com
- Incident Response: incident@nflpredictor.com