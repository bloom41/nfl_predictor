# NFL Predictor Production Deployment Plan

*Deployment Plan Date: July 4, 2025*

## 🎯 Deployment Overview

This plan provides step-by-step instructions for deploying the NFL Predictor application to production with high availability, security, and performance.

## 📋 Pre-Deployment Checklist

### ✅ Completed Items
- [x] Database optimization with caching system
- [x] TypeScript compilation fixes
- [x] Test suite validation
- [x] Docker containerization
- [x] Health checks implementation
- [x] Performance monitoring setup
- [x] API documentation complete

### 🔧 Required Before Deployment
- [ ] Production environment variables configuration
- [ ] SSL certificates acquisition
- [ ] Database migration scripts
- [ ] Redis cluster setup
- [ ] CDN configuration
- [ ] Monitoring alerts configuration
- [ ] Backup procedures setup

## 🏗️ Infrastructure Architecture

### Production Environment Stack
```
┌─────────────────────────────────────────────────────────────┐
│                    Production Architecture                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │     CDN      │    │Load Balancer │    │  Monitoring  │  │
│  │ CloudFront   │◄──►│   ALB/nginx  │◄──►│ CloudWatch   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                             │                              │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Application Layer (ECS/EKS)                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │  │
│  │  │  Frontend   │  │   Backend   │  │ ML Service  │     │  │
│  │  │   React     │  │ Express TS  │  │   Flask     │     │  │
│  │  │ (Static S3) │  │  (Docker)   │  │  (Docker)   │     │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │  │
│  └─────────────────────────────────────────────────────────┘  │
│                             │                              │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                  Data Layer                             │  │
│  │  ┌─────────────┐          ┌─────────────┐               │  │
│  │  │ PostgreSQL  │          │    Redis    │               │  │
│  │  │    RDS      │          │ElastiCache  │               │  │
│  │  │  (Primary)  │          │  (Cache)    │               │  │
│  │  └─────────────┘          └─────────────┘               │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Resource Allocation
- **Frontend**: CloudFront + S3 (Static hosting)
- **Backend API**: ECS/EKS with 2-4 instances (auto-scaling)
- **ML Service**: Dedicated compute instances (CPU optimized)
- **Database**: RDS PostgreSQL (Multi-AZ)
- **Cache**: ElastiCache Redis (Cluster mode)
- **Load Balancer**: Application Load Balancer
- **Monitoring**: CloudWatch + Prometheus + Grafana

## 🔧 Environment Configuration

### Production Environment Variables

Create `/backend-ts/.env.production`:
```bash
# Application Configuration
NODE_ENV=production
PORT=3001
API_VERSION=v1

# Database Configuration
DATABASE_URL=postgresql://username:password@prod-db.region.rds.amazonaws.com:5432/nfl_predictor
POSTGRES_SSL=true
POSTGRES_MAX_CONNECTIONS=20

# Redis Configuration
REDIS_URL=redis://prod-redis.region.cache.amazonaws.com:6379
REDIS_CLUSTER_MODE=true
REDIS_TLS=true

# Security Configuration
JWT_SECRET=${SECURE_JWT_SECRET_FROM_SECRETS_MANAGER}
CORS_ORIGINS=https://nflpredictor.com,https://www.nflpredictor.com
RATE_LIMIT_WINDOW=900000
RATE_LIMIT_MAX=100

# ML Service Configuration
ML_SERVICE_URL=http://ml-service:5000
ML_SERVICE_TIMEOUT=30000
ML_CACHE_TTL=3600

# Monitoring Configuration
ENABLE_METRICS=true
METRICS_PORT=9090
SENTRY_DSN=${SENTRY_DSN}
LOG_LEVEL=info

# Performance Configuration
CACHE_DEFAULT_TTL=1800
DATABASE_QUERY_TIMEOUT=10000
API_RESPONSE_TIMEOUT=30000
```

Create `/frontend/client/.env.production`:
```bash
REACT_APP_API_URL=https://api.nflpredictor.com
REACT_APP_VERSION=1.0.0
REACT_APP_ENVIRONMENT=production
REACT_APP_SENTRY_DSN=${FRONTEND_SENTRY_DSN}
REACT_APP_ANALYTICS_ID=${GOOGLE_ANALYTICS_ID}
GENERATE_SOURCEMAP=false
```

### Docker Production Configuration

Create `docker-compose.production.yml`:
```yaml
version: '3.8'

services:
  # Backend API Service
  backend:
    build:
      context: ./backend-ts
      dockerfile: Dockerfile.production
    image: nfl-predictor-backend:${VERSION}
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET=${JWT_SECRET}
    ports:
      - "3001:3001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3001/api/status"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 1G
          cpus: "0.5"
    networks:
      - app-network
    depends_on:
      - redis

  # ML Service
  ml-service:
    build:
      context: .
      dockerfile: Dockerfile.production
    image: nfl-predictor-ml:${VERSION}
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    ports:
      - "5000:5000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/status"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 2G
          cpus: "1"
    networks:
      - app-network

  # Redis Cache (for local testing - use ElastiCache in production)
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "0.25"
    networks:
      - app-network

  # Nginx Load Balancer
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.production.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
      - ml-service
    networks:
      - app-network

networks:
  app-network:
    driver: bridge

volumes:
  redis-data:
```

## 🚀 Deployment Steps

### Phase 1: Infrastructure Setup (Day 1-2)

#### 1.1 AWS/Cloud Infrastructure
```bash
# Create VPC and networking
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=nfl-predictor-vpc}]'

# Create subnets
aws ec2 create-subnet --vpc-id <vpc-id> --cidr-block 10.0.1.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id <vpc-id> --cidr-block 10.0.2.0/24 --availability-zone us-east-1b

# Create security groups
aws ec2 create-security-group --group-name nfl-predictor-sg --description "NFL Predictor Security Group" --vpc-id <vpc-id>
```

#### 1.2 Database Setup
```bash
# Create RDS PostgreSQL instance
aws rds create-db-instance \
  --db-instance-identifier nfl-predictor-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.2 \
  --master-username nfluser \
  --master-user-password <secure-password> \
  --allocated-storage 100 \
  --vpc-security-group-ids <security-group-id> \
  --multi-az \
  --backup-retention-period 7 \
  --storage-encrypted
```

#### 1.3 Redis Cache Setup
```bash
# Create ElastiCache Redis cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id nfl-predictor-cache \
  --cache-node-type cache.r6g.large \
  --engine redis \
  --num-cache-nodes 2 \
  --security-group-ids <security-group-id>
```

### Phase 2: Application Deployment (Day 2-3)

#### 2.1 Container Registry Setup
```bash
# Build and push backend image
cd backend-ts
docker build -f Dockerfile.production -t nfl-predictor-backend:latest .
docker tag nfl-predictor-backend:latest <account-id>.dkr.ecr.<region>.amazonaws.com/nfl-predictor-backend:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/nfl-predictor-backend:latest

# Build and push ML service image
cd ..
docker build -f Dockerfile.production -t nfl-predictor-ml:latest .
docker tag nfl-predictor-ml:latest <account-id>.dkr.ecr.<region>.amazonaws.com/nfl-predictor-ml:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/nfl-predictor-ml:latest
```

#### 2.2 ECS/EKS Deployment
```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name nfl-predictor-cluster

# Create task definitions
aws ecs register-task-definition --cli-input-json file://backend-task-definition.json
aws ecs register-task-definition --cli-input-json file://ml-service-task-definition.json

# Create services
aws ecs create-service \
  --cluster nfl-predictor-cluster \
  --service-name backend-service \
  --task-definition nfl-predictor-backend \
  --desired-count 3 \
  --load-balancers targetGroupArn=<target-group-arn>,containerName=backend,containerPort=3001
```

#### 2.3 Frontend Deployment
```bash
# Build frontend
cd frontend/client
npm run build

# Deploy to S3 with CloudFront
aws s3 sync build/ s3://nfl-predictor-frontend --delete
aws cloudfront create-invalidation --distribution-id <distribution-id> --paths "/*"
```

### Phase 3: Database Migration (Day 3)

#### 3.1 Database Schema Migration
```bash
# Run Prisma migrations
cd backend-ts
npx prisma migrate deploy --schema=./prisma/schema.prisma

# Seed production data if needed
npx prisma db seed
```

#### 3.2 Data Import
```bash
# Import ML models
aws s3 sync models/ s3://nfl-predictor-models/

# Import historical data
python scripts/import_production_data.py
```

### Phase 4: Configuration & Testing (Day 4)

#### 4.1 Load Balancer Configuration
```nginx
# nginx.production.conf
upstream backend {
    server backend-1:3001 max_fails=3 fail_timeout=30s;
    server backend-2:3001 max_fails=3 fail_timeout=30s;
    server backend-3:3001 max_fails=3 fail_timeout=30s;
}

upstream ml-service {
    server ml-service-1:5000 max_fails=3 fail_timeout=30s;
    server ml-service-2:5000 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name api.nflpredictor.com;

    ssl_certificate /etc/nginx/ssl/nflpredictor.com.crt;
    ssl_certificate_key /etc/nginx/ssl/nflpredictor.com.key;

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
        
        # Timeouts
        proxy_connect_timeout 5s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    location /ml/ {
        proxy_pass http://ml-service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 10s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

#### 4.2 SSL Certificate Setup
```bash
# Using Let's Encrypt
certbot --nginx -d nflpredictor.com -d www.nflpredictor.com -d api.nflpredictor.com

# Or using AWS Certificate Manager
aws acm request-certificate \
  --domain-name nflpredictor.com \
  --subject-alternative-names www.nflpredictor.com api.nflpredictor.com \
  --validation-method DNS
```

### Phase 5: Monitoring & Alerting (Day 5)

#### 5.1 CloudWatch Configuration
```bash
# Create log groups
aws logs create-log-group --log-group-name /nfl-predictor/backend
aws logs create-log-group --log-group-name /nfl-predictor/ml-service

# Create alarms
aws cloudwatch put-metric-alarm \
  --alarm-name "NFL-Predictor-High-Error-Rate" \
  --alarm-description "High error rate in API" \
  --metric-name ErrorCount \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

#### 5.2 Health Check Configuration
```typescript
// Enhanced health check endpoint
app.get('/api/status', async (req, res) => {
  const status = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: process.env.API_VERSION || '1.0.0',
    environment: process.env.NODE_ENV,
    uptime: process.uptime(),
    checks: {
      database: await databaseService.healthCheck(),
      cache: await cacheService.healthCheck(),
      mlService: await checkMLServiceHealth(),
      memory: process.memoryUsage(),
      cpu: process.cpuUsage()
    }
  };

  const isHealthy = Object.values(status.checks).every(check => 
    typeof check === 'boolean' ? check : true
  );

  res.status(isHealthy ? 200 : 503).json(status);
});
```

## 📊 Performance Targets & SLAs

### Service Level Objectives (SLOs)
- **Availability**: 99.9% uptime
- **Response Time**: 95% of requests < 200ms
- **Throughput**: Support 1000+ concurrent users
- **Error Rate**: < 0.1% of all requests
- **Cache Hit Rate**: > 85%

### Performance Monitoring
```javascript
// Key metrics to monitor
const metrics = {
  // Application metrics
  'api.response_time': { target: '<200ms', alert: '>500ms' },
  'api.error_rate': { target: '<0.1%', alert: '>1%' },
  'api.throughput': { target: '>100 rps', alert: '<50 rps' },
  
  // Infrastructure metrics
  'db.connection_pool': { target: '<80%', alert: '>90%' },
  'cache.hit_rate': { target: '>85%', alert: '<70%' },
  'memory.usage': { target: '<80%', alert: '>90%' },
  'cpu.usage': { target: '<70%', alert: '>85%' }
};
```

## 🔐 Security Configuration

### Security Headers
```typescript
// Helmet.js security configuration
app.use(helmet({
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true
  },
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
      fontSrc: ["'self'", "https://fonts.gstatic.com"],
      imgSrc: ["'self'", "data:", "https:"],
      scriptSrc: ["'self'"]
    }
  },
  crossOriginEmbedderPolicy: false
}));
```

### Rate Limiting
```typescript
// Production rate limiting
const rateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP',
  standardHeaders: true,
  legacyHeaders: false,
  skip: (req) => {
    // Skip rate limiting for health checks
    return req.path === '/api/status';
  }
});
```

## 💾 Backup & Recovery

### Database Backup Strategy
```bash
# Automated daily backups
aws rds create-db-snapshot \
  --db-instance-identifier nfl-predictor-db \
  --db-snapshot-identifier nfl-predictor-backup-$(date +%Y%m%d)

# Cross-region backup replication
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier nfl-predictor-backup-$(date +%Y%m%d) \
  --target-db-snapshot-identifier nfl-predictor-backup-$(date +%Y%m%d)-replica \
  --source-region us-east-1 \
  --target-region us-west-2
```

### Application Backup
```bash
# Code backup (Git)
git push origin main --tags

# Model backup
aws s3 sync models/ s3://nfl-predictor-backups/models/$(date +%Y%m%d)/

# Configuration backup
aws s3 cp docker-compose.production.yml s3://nfl-predictor-backups/config/$(date +%Y%m%d)/
```

## 🔄 Rollback Procedures

### Zero-Downtime Deployment
```bash
# Blue-green deployment script
#!/bin/bash
VERSION=${1:-latest}

# Deploy to green environment
docker-compose -f docker-compose.green.yml up -d

# Health check green environment
for i in {1..30}; do
  if curl -f http://green-environment:3001/api/status; then
    echo "Green environment healthy"
    break
  fi
  sleep 10
done

# Switch traffic to green
aws elbv2 modify-target-group \
  --target-group-arn $GREEN_TARGET_GROUP_ARN \
  --health-check-path /api/status

# Verify traffic switch
sleep 60

# Stop blue environment
docker-compose -f docker-compose.blue.yml down
```

### Emergency Rollback
```bash
#!/bin/bash
# Emergency rollback script
echo "Initiating emergency rollback..."

# Switch traffic back to previous version
aws elbv2 modify-target-group \
  --target-group-arn $BLUE_TARGET_GROUP_ARN \
  --health-check-path /api/status

# Restart services with previous version
docker-compose -f docker-compose.blue.yml up -d

echo "Rollback completed. Monitor application health."
```

## 📈 Scaling Strategy

### Auto-scaling Configuration
```bash
# Create auto-scaling group
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name nfl-predictor-asg \
  --launch-template LaunchTemplateName=nfl-predictor-template \
  --min-size 2 \
  --max-size 10 \
  --desired-capacity 3 \
  --target-group-arns $TARGET_GROUP_ARN

# Create scaling policies
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name nfl-predictor-asg \
  --policy-name scale-up \
  --scaling-adjustment 2 \
  --adjustment-type ChangeInCapacity
```

### Database Scaling
- **Read Replicas**: Add read replicas for read-heavy workloads
- **Connection Pooling**: PgBouncer for connection management
- **Query Optimization**: Regular query performance analysis

## 🎯 Success Criteria

### Deployment Success Metrics
- [ ] All services passing health checks
- [ ] Database migrations completed successfully
- [ ] Cache hit rate > 80% within 1 hour
- [ ] API response time < 200ms for 95% of requests
- [ ] Zero critical errors in first 24 hours
- [ ] Frontend loading in < 2 seconds
- [ ] SSL certificates installed and working
- [ ] Monitoring alerts configured and testing

### Business Success Metrics
- [ ] Support 1000+ concurrent users
- [ ] 99.9% uptime in first month
- [ ] User satisfaction > 4.5/5
- [ ] API usage growing 20% week-over-week
- [ ] Cost per user < $0.10/month

## 📞 Support & Maintenance

### 24/7 Support Plan
- **Tier 1**: Automated monitoring and alerting
- **Tier 2**: On-call engineer for critical issues
- **Tier 3**: Full development team escalation

### Regular Maintenance
- **Daily**: Automated backups and health checks
- **Weekly**: Performance review and optimization
- **Monthly**: Security patches and updates
- **Quarterly**: Capacity planning and cost optimization

---

## 🎉 Deployment Timeline Summary

| Phase | Duration | Key Activities | Dependencies |
|-------|----------|----------------|--------------|
| **Phase 1** | 1-2 days | Infrastructure setup | AWS account, SSL certs |
| **Phase 2** | 1-2 days | Application deployment | Container images |
| **Phase 3** | 1 day | Database migration | Backup verified |
| **Phase 4** | 1 day | Configuration & testing | All services running |
| **Phase 5** | 1 day | Monitoring setup | Alerting tools |

**Total Estimated Time**: 5-7 days  
**Go-Live Date**: Target within 1 week  
**Success Probability**: 95% (with proper preparation)

---

**Status**: ✅ **READY FOR EXECUTION**  
**Next Action**: Begin Phase 1 infrastructure setup  
**Owner**: DevOps/Infrastructure team