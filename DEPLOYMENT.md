# ContractAI Guardian — Production Deployment Guide

## Architecture Overview

```
                    ┌─────────────────────────────────────────────────────┐
                    │                  CloudFront CDN                      │
                    │        (SSL termination, caching, routing)           │
                    └────────────────┬──────────────────┬─────────────────┘
                                     │                  │
                          /api/*     │                  │  /*  (static)
                                     ▼                  ▼
                    ┌──────────────────────┐   ┌──────────────────┐
                    │   ALB (HTTPS:443)    │   │   S3 (Frontend)  │
                    │   TLS 1.3 only       │   │   React SPA      │
                    └──────────┬───────────┘   └──────────────────┘
                               │
                    ┌──────────▼───────────┐
                    │   ECS Fargate        │
                    │   3 tasks (auto-     │
                    │   scaling 1-10)      │
                    │   FastAPI + Uvicorn  │
                    └──┬──────┬──────┬────┘
                       │      │      │
              ┌────────▼─┐ ┌─▼────┐ ┌▼────────┐
              │ RDS PG   │ │Redis │ │ S3 Docs  │
              │ Multi-AZ │ │Cache │ │ (KMS)    │
              │ Encrypted│ │      │ │          │
              └──────────┘ └──────┘ └──────────┘
```

## Prerequisites

- AWS Account with admin access
- Domain name (e.g., `contractai.com`) with DNS in Route53
- Terraform >= 1.5 installed
- Docker installed
- GitHub repository with Actions enabled
- API keys: Anthropic, Google Gemini

---

## 1. Local Development Setup

```bash
# Clone and configure
git clone <repo-url> && cd contractGuardproject
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# Start everything
docker compose up --build

# Access:
#   Frontend: http://localhost
#   Backend:  http://localhost:8000
#   API docs: http://localhost:8000/docs
```

---

## 2. AWS Infrastructure Setup

### 2.1 Create Terraform State Bucket

```bash
aws s3api create-bucket \
  --bucket contractai-terraform-state \
  --region us-east-1

aws s3api put-bucket-versioning \
  --bucket contractai-terraform-state \
  --versioning-configuration Status=Enabled
```

### 2.2 Create ECR Repository

```bash
aws ecr create-repository \
  --repository-name contractai-backend \
  --image-scanning-configuration scanOnPush=true
```

### 2.3 Deploy Infrastructure

```bash
cd infra/terraform

# Initialize
terraform init

# Plan (review changes)
terraform plan \
  -var="db_password=$(openssl rand -base64 32)" \
  -var="backend_image=<account-id>.dkr.ecr.us-east-1.amazonaws.com/contractai-backend:latest"

# Apply
terraform apply
```

### 2.4 Store Secrets

```bash
aws secretsmanager put-secret-value \
  --secret-id contractai/production/app \
  --secret-string '{
    "DATABASE_URL": "postgresql+asyncpg://contractai:<password>@<rds-endpoint>:5432/contractai",
    "SECRET_KEY": "'$(openssl rand -base64 64)'",
    "ANTHROPIC_API_KEY": "sk-ant-...",
    "GEMINI_API_KEY": "AIza...",
    "AWS_ACCESS_KEY_ID": "...",
    "AWS_SECRET_ACCESS_KEY": "..."
  }'
```

---

## 3. Database Setup

### 3.1 Run Migrations

```bash
# From backend container or locally with DATABASE_URL set
alembic upgrade head
```

### 3.2 RDS Configuration

| Setting | Value |
|---------|-------|
| Engine | PostgreSQL 16 |
| Instance | db.t3.medium (prod: db.r6g.large) |
| Storage | 50GB gp3, auto-scale to 200GB |
| Multi-AZ | Yes (production) |
| Backup | 7 days retention, 03:00-04:00 UTC |
| Encryption | AES-256 (KMS) |
| Performance Insights | Enabled |

### 3.3 Connection Pooling

For production with >50 concurrent connections, add PgBouncer:

```bash
# Add to ECS task definition as sidecar container
# Or use RDS Proxy ($30/month, managed)
aws rds create-db-proxy \
  --db-proxy-name contractai-proxy \
  --engine-family POSTGRESQL \
  --auth SecretArn=<secret-arn>,IAMAuth=DISABLED
```

---

## 4. CI/CD Pipeline

### 4.1 GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `AWS_DEPLOY_ROLE_ARN` | IAM role for GitHub OIDC deployment |
| `DATABASE_URL` | RDS connection string (for migrations) |
| `CLOUDFRONT_DISTRIBUTION_ID` | For cache invalidation |

### 4.2 Pipeline Flow

```
Push to main
  → CI (lint + test + build + security scan)
    → Build Docker image → Push to ECR
      → Run DB migrations
        → Deploy to ECS (rolling update)
          → Health check
            → Deploy frontend to S3
              → Invalidate CloudFront
```

### 4.3 GitHub OIDC Setup (no static credentials)

```bash
# Create OIDC provider for GitHub Actions
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

---

## 5. Frontend Deployment

### 5.1 Build Configuration

```bash
# Production build
VITE_API_URL=https://api.contractai.com npm run build
```

### 5.2 S3 + CloudFront

- Static assets (`*.js`, `*.css`): 1 year cache, immutable
- `index.html`: no-cache (always fresh for SPA routing)
- CloudFront handles HTTPS and SPA 404→index.html fallback

### 5.3 Custom Domain

1. Create ACM certificate for `contractai.com` + `*.contractai.com`
2. Validate via DNS (Route53 CNAME records)
3. Attach to CloudFront distribution
4. Create Route53 A record → CloudFront alias

---

## 6. Security Configuration

### 6.1 Network Security

| Layer | Protection |
|-------|-----------|
| CloudFront | WAF rules, rate limiting, geo-blocking |
| ALB | Security group (443 only from CloudFront) |
| ECS | Private subnets, no public IP |
| RDS | Private subnets, SG allows only ECS |
| Redis | Private subnets, encryption in-transit |
| S3 | No public access, KMS encryption |

### 6.2 Application Security

- **JWT tokens**: Short-lived access (30min) + refresh (7 days)
- **Password hashing**: bcrypt with salt
- **Rate limiting**: 100 req/min per user (Redis-backed)
- **File upload**: Type validation, size limits (50MB), virus scan
- **CORS**: Explicit origin whitelist
- **Headers**: HSTS, X-Frame-Options, CSP, X-Content-Type-Options
- **Input validation**: Pydantic schemas on all endpoints
- **SQL injection**: SQLAlchemy parameterized queries (never raw SQL)
- **Secrets**: AWS Secrets Manager (rotated quarterly)

### 6.3 WAF Rules

```bash
aws wafv2 create-web-acl \
  --name contractai-waf \
  --scope CLOUDFRONT \
  --default-action Allow={} \
  --rules '[
    {"Name":"RateLimit","Priority":1,"Action":{"Block":{}},"Statement":{"RateBasedStatement":{"Limit":2000,"AggregateKeyType":"IP"}},"VisibilityConfig":{"SampledRequestsEnabled":true,"CloudWatchMetricsEnabled":true,"MetricName":"RateLimit"}},
    {"Name":"SQLi","Priority":2,"Action":{"Block":{}},"Statement":{"SqliMatchStatement":{"FieldToMatch":{"Body":{}},"TextTransformations":[{"Priority":0,"Type":"URL_DECODE"}]}},"VisibilityConfig":{"SampledRequestsEnabled":true,"CloudWatchMetricsEnabled":true,"MetricName":"SQLi"}}
  ]'
```

### 6.4 Encryption

| Data | At Rest | In Transit |
|------|---------|-----------|
| Database | AES-256 (KMS) | TLS 1.3 |
| S3 documents | SSE-KMS | HTTPS |
| Redis | AES-256 | TLS |
| Secrets | Secrets Manager (KMS) | HTTPS |
| API traffic | N/A | TLS 1.3 (CloudFront) |

---

## 7. Monitoring & Alerting

### 7.1 CloudWatch Dashboards

```bash
# Key metrics to monitor:
# - ECS CPU/Memory utilization
# - RDS connections, read/write IOPS
# - ALB request count, 5xx errors, latency
# - CloudFront cache hit ratio
# - API response times (p50, p95, p99)
```

### 7.2 Alarms

| Metric | Threshold | Action |
|--------|-----------|--------|
| ECS CPU > 80% | 5min | Auto-scale + alert |
| ALB 5xx > 10/min | 2min | PagerDuty |
| RDS connections > 80% | 5min | Alert |
| API latency p99 > 5s | 5min | Alert |
| Disk usage > 80% | 15min | Alert |

### 7.3 Logging

- **Application logs**: CloudWatch Logs (30-day retention)
- **Access logs**: ALB → S3 (90-day retention)
- **Audit logs**: Application audit table + CloudTrail

---

## 8. Scaling Strategy

| Component | Min | Max | Trigger |
|-----------|-----|-----|---------|
| ECS Tasks | 3 | 10 | CPU > 70% |
| RDS | 1 replica | 3 replicas | Read load |
| Redis | 1 node | 3 nodes | Memory > 80% |

### Cost Estimate (Production)

| Service | Monthly Cost |
|---------|-------------|
| ECS Fargate (3 tasks) | ~$150 |
| RDS db.t3.medium (Multi-AZ) | ~$130 |
| ElastiCache (t3.small) | ~$50 |
| S3 + CloudFront | ~$30 |
| ALB | ~$25 |
| Secrets Manager | ~$5 |
| CloudWatch | ~$20 |
| **Total** | **~$410/month** |

---

## 9. Disaster Recovery

### Backup Strategy

| Data | RPO | RTO | Method |
|------|-----|-----|--------|
| Database | 1 hour | 30 min | Automated snapshots + point-in-time recovery |
| Documents (S3) | 0 | Instant | Versioning + cross-region replication |
| Config | 0 | 5 min | Terraform state in S3 |

### Runbook: Full Recovery

```bash
# 1. Restore RDS from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier contractai-recovery \
  --db-snapshot-identifier <latest-snapshot>

# 2. Update secrets with new RDS endpoint
# 3. Redeploy ECS (picks up new endpoint)
# 4. Verify health checks pass
# 5. Update DNS if needed
```

---

## 10. GCP Alternative

If deploying on GCP instead of AWS:

| AWS Service | GCP Equivalent |
|-------------|---------------|
| ECS Fargate | Cloud Run |
| RDS PostgreSQL | Cloud SQL |
| ElastiCache | Memorystore |
| S3 | Cloud Storage |
| CloudFront | Cloud CDN |
| Secrets Manager | Secret Manager |
| Route53 | Cloud DNS |
| ACM | Certificate Manager |
| ECR | Artifact Registry |
| CloudWatch | Cloud Monitoring |

### GCP Quick Deploy (Cloud Run)

```bash
# Build and push
gcloud builds submit --tag gcr.io/$PROJECT_ID/contractai-backend ./backend

# Deploy
gcloud run deploy contractai-backend \
  --image gcr.io/$PROJECT_ID/contractai-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="ENVIRONMENT=production" \
  --set-secrets="DATABASE_URL=contractai-db-url:latest,SECRET_KEY=contractai-secret:latest" \
  --min-instances=1 \
  --max-instances=10 \
  --cpu=2 \
  --memory=2Gi
```

---

## Quick Commands

```bash
# Local dev
docker compose up --build

# View logs
docker compose logs -f backend

# Run migrations
docker compose exec backend alembic upgrade head

# Production deploy (manual)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check health
curl https://api.contractai.com/health

# Force redeploy
aws ecs update-service --cluster contractai-production --service contractai-backend --force-new-deployment

# Rollback (previous task definition)
aws ecs update-service --cluster contractai-production --service contractai-backend --task-definition contractai-backend:<previous-revision>
```
