# Deployment Guide

## Overview

This guide covers deployment strategies for the NFL Predictor full-stack application across different environments.

## Quick Deployment (Development)

### Prerequisites
- Node.js 18+
- Python 3.8+
- PostgreSQL 13+ (optional, SQLite fallback available)

### 1. Clone and Setup
```bash
git clone <repository>
cd nfl_predictor
```

### 2. Backend Setup (Express TypeScript)
```bash
cd backend-ts
npm install
npm run build
npm start
```
- Starts on: `http://localhost:3001`
- Health check: `http://localhost:3001/api/status`

### 3. Frontend Setup (React)
```bash
cd frontend/client
npm install
npm start
```
- Starts on: `http://localhost:3000`
- Auto-connects to backend at port 3001

### 4. ML Service Setup (Flask Python)
```bash
# Install dependencies
pip install -r requirements.txt

# Start Flask service
python app.py
```
- Starts on: `http://localhost:5000`
- ML endpoints available

## Production Deployment

### Option 1: Docker Compose (Recommended)

#### Full Stack Deployment
```bash
# Use the main docker-compose file
docker-compose up -d

# Services started:
# - Frontend (port 3000)
# - Backend (port 3001) 
# - ML Service (port 5000)
# - PostgreSQL (port 5432)
```

#### Database Only
```bash
# For external service deployment
docker-compose -f docker-postgres-only.yml up -d
```

### Option 2: Container Orchestration

#### Kubernetes Deployment
```yaml
# Example k8s configuration
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nfl-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nfl-backend
  template:
    metadata:
      labels:
        app: nfl-backend
    spec:
      containers:
      - name: backend
        image: nfl-predictor/backend:latest
        ports:
        - containerPort: 3001
        env:
        - name: DATABASE_URL
          value: "postgresql://..."
```

### Option 3: Cloud Platform Deployment

#### AWS Deployment
```bash
# ECS with Fargate
aws ecs create-cluster --cluster-name nfl-predictor

# Deploy services
aws ecs create-service \
  --cluster nfl-predictor \
  --service-name nfl-backend \
  --task-definition nfl-backend:1 \
  --desired-count 2
```

#### Google Cloud Run
```bash
# Build and deploy backend
gcloud builds submit --tag gcr.io/PROJECT-ID/nfl-backend
gcloud run deploy --image gcr.io/PROJECT-ID/nfl-backend --platform managed
```

## Environment Configuration

### Environment Variables

#### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/nfl_predictor
SQLITE_DATABASE=./nfl_predictor.db

# API Configuration
PORT=3001
NODE_ENV=production
API_BASE_URL=http://localhost:3001

# ML Service
PYTHON_ML_SERVICE_URL=http://localhost:5000
PYTHON_ML_SERVICE_TIMEOUT=30000

# Security
JWT_SECRET=your-jwt-secret
CORS_ORIGIN=http://localhost:3000
```

#### Frontend (.env)
```bash
# API Configuration
REACT_APP_API_BASE_URL=http://localhost:3001
REACT_APP_API_TIMEOUT=30000

# Environment
REACT_APP_ENV=production
```

#### ML Service (.env)
```bash
# Django Configuration
DJANGO_SECRET_KEY=your-django-secret
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/nfl_predictor

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False
```

## Database Setup

### PostgreSQL Production Setup
```sql
-- Create database
CREATE DATABASE nfl_predictor;
CREATE USER nfl_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE nfl_predictor TO nfl_user;

-- Run migrations
python manage.py migrate
npm run db:migrate
```

### Database Backup Strategy
```bash
# Automated backups
pg_dump nfl_predictor > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
psql nfl_predictor < backup_file.sql
```

## Monitoring & Health Checks

### Health Check Endpoints
```bash
# Backend health
curl http://localhost:3001/api/status

# ML service health  
curl http://localhost:5000/health

# Database connectivity
curl http://localhost:3001/api/status | jq '.database'
```

### Monitoring Setup
```yaml
# Docker Compose monitoring
version: '3.8'
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3030:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

## Load Balancing & Scaling

### Nginx Configuration
```nginx
upstream backend {
    server backend1:3001;
    server backend2:3001;
    server backend3:3001;
}

server {
    listen 80;
    server_name nfl-predictor.com;

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }
}
```

### Auto-scaling Configuration
```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: nfl-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nfl-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Security Configuration

### SSL/TLS Setup
```bash
# Let's Encrypt certificate
certbot --nginx -d nfl-predictor.com

# Nginx SSL configuration
ssl_certificate /etc/letsencrypt/live/nfl-predictor.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/nfl-predictor.com/privkey.pem;
```

### Firewall Configuration
```bash
# Allow only necessary ports
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw deny 3001   # Block direct backend access
ufw deny 5000   # Block direct ML service access
```

## Backup & Recovery

### Application Backup
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
pg_dump nfl_predictor > /backups/db_$DATE.sql

# Application code backup
tar -czf /backups/app_$DATE.tar.gz /app

# Configuration backup
cp -r /app/config /backups/config_$DATE
```

### Disaster Recovery
```bash
# Recovery procedure
1. Restore database from backup
2. Deploy application from Git
3. Restore configuration files
4. Restart services
5. Verify functionality
```

## Performance Optimization

### Production Optimizations
```bash
# Frontend optimizations
npm run build               # Production React build
gzip -9 build/static/**/*  # Compression

# Backend optimizations
npm run build:production   # Optimized TypeScript build
node --max-old-space-size=4096 dist/index.js  # Memory optimization
```

### Caching Strategy
```yaml
# Redis cache configuration
redis:
  image: redis:alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes
```

## Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Check port usage
lsof -i :3001
netstat -tlnp | grep :3001

# Kill conflicting process
kill -9 <PID>
```

#### Database Connection Issues
```bash
# Test database connectivity
psql -h localhost -p 5432 -U nfl_user -d nfl_predictor

# Check database logs
tail -f /var/log/postgresql/postgresql-13-main.log
```

#### Memory Issues
```bash
# Monitor memory usage
free -h
ps aux --sort=-%mem | head

# Adjust Node.js memory limits
export NODE_OPTIONS="--max-old-space-size=4096"
```

## Deployment Checklist

### Pre-deployment
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] SSL certificates installed
- [ ] Monitoring setup complete
- [ ] Backup strategy implemented

### Post-deployment
- [ ] Health checks passing
- [ ] Performance metrics baseline
- [ ] Error tracking configured
- [ ] Documentation updated
- [ ] Team notified

---

*Last Updated: July 2025*  
*Version: 2.1.3 (Unified ML Engine)*