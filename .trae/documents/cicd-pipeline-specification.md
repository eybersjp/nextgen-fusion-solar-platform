# CI/CD Pipeline Implementation Specification
## NextGen Fusion Commercial Solar Platform

### Executive Summary

This document provides comprehensive specifications for implementing an enterprise-grade CI/CD pipeline for the NextGen Fusion Commercial Solar Platform. The pipeline addresses the **critical gap** identified in Phase 1 Foundation Stabilization analysis and establishes automated testing, building, deployment, and monitoring capabilities across all microservices.

**Priority**: Critical (Immediate Action Required)
**Timeline**: 2-3 weeks implementation
**Impact**: Enables production deployment and automated quality assurance

---

## 1. GitHub Actions Workflow Specifications

### 1.1 Core Workflow Architecture

#### Main CI/CD Workflow (`.github/workflows/main.yml`)
```yaml
name: NextGen Fusion CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # Code Quality & Security
  code-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          npm ci
          pip install -r requirements.txt
      - name: ESLint (Frontend)
        run: npm run lint
      - name: Ruff & Black (Backend)
        run: |
          ruff check .
          black --check .
      - name: Security Scan (Snyk)
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}

  # Frontend Testing
  frontend-tests:
    runs-on: ubuntu-latest
    needs: code-quality
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - name: Install dependencies
        run: npm ci
      - name: Unit Tests (Vitest)
        run: npm run test:unit
      - name: Component Tests
        run: npm run test:component
      - name: Build Frontend
        run: npm run build
      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: frontend-build
          path: dist/

  # Backend Testing
  backend-tests:
    runs-on: ubuntu-latest
    needs: code-quality
    strategy:
      matrix:
        service: [svc-design, svc-project, svc-currency, svc-compliance]
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd ${{ matrix.service }}
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run Tests
        run: |
          cd ${{ matrix.service }}
          pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ${{ matrix.service }}/coverage.xml

  # E2E Testing
  e2e-tests:
    runs-on: ubuntu-latest
    needs: [frontend-tests, backend-tests]
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install Playwright
        run: |
          npm ci
          npx playwright install
      - name: Start services
        run: docker-compose -f docker-compose.test.yml up -d
      - name: Run E2E tests
        run: npm run test:e2e
      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: playwright-report/

  # Build & Push Images
  build-images:
    runs-on: ubuntu-latest
    needs: [frontend-tests, backend-tests]
    if: github.ref == 'refs/heads/main'
    strategy:
      matrix:
        service: [frontend, svc-design, svc-project, svc-currency, svc-compliance, api-gateway]
    steps:
      - uses: actions/checkout@v4
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/${{ matrix.service }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ${{ matrix.service == 'frontend' && '.' || matrix.service }}
          file: ${{ matrix.service == 'frontend' && 'Dockerfile.frontend' || format('{0}/Dockerfile', matrix.service) }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}

  # Deploy to Staging
  deploy-staging:
    runs-on: ubuntu-latest
    needs: [build-images, e2e-tests]
    if: github.ref == 'refs/heads/main'
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Setup kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: 'v1.28.0'
      - name: Configure kubectl
        run: |
          echo "${{ secrets.KUBE_CONFIG_STAGING }}" | base64 -d > kubeconfig
          export KUBECONFIG=kubeconfig
      - name: Deploy with Helm
        run: |
          helm upgrade --install nextgen-fusion ./helm/nextgen-fusion \
            --namespace staging \
            --set image.tag=${{ github.sha }} \
            --set environment=staging \
            --values ./helm/values-staging.yaml
      - name: Verify deployment
        run: |
          kubectl rollout status deployment/nextgen-fusion-frontend -n staging
          kubectl rollout status deployment/nextgen-fusion-backend -n staging

  # Production Deployment (Manual Approval)
  deploy-production:
    runs-on: ubuntu-latest
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - uses: actions/checkout@v4
      - name: Setup kubectl
        uses: azure/setup-kubectl@v3
      - name: Configure kubectl
        run: |
          echo "${{ secrets.KUBE_CONFIG_PROD }}" | base64 -d > kubeconfig
          export KUBECONFIG=kubeconfig
      - name: Deploy with Helm
        run: |
          helm upgrade --install nextgen-fusion ./helm/nextgen-fusion \
            --namespace production \
            --set image.tag=${{ github.sha }} \
            --set environment=production \
            --values ./helm/values-production.yaml
      - name: Verify deployment
        run: |
          kubectl rollout status deployment/nextgen-fusion-frontend -n production
          kubectl rollout status deployment/nextgen-fusion-backend -n production
      - name: Run smoke tests
        run: npm run test:smoke:prod
```

### 1.2 Specialized Workflows

#### Security Scanning Workflow (`.github/workflows/security.yml`)
```yaml
name: Security Scanning

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
      - name: OWASP ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.7.0
        with:
          target: 'https://staging.nextgen-fusion.com'
```

#### Performance Testing Workflow (`.github/workflows/performance.yml`)
```yaml
name: Performance Testing

on:
  schedule:
    - cron: '0 4 * * *'  # Daily at 4 AM
  workflow_dispatch:

jobs:
  k6-load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run K6 load test
        uses: grafana/k6-action@v0.3.0
        with:
          filename: tests/performance/load-test.js
        env:
          K6_CLOUD_TOKEN: ${{ secrets.K6_CLOUD_TOKEN }}
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: k6-results
          path: results/
```

---

## 2. Docker Configuration Requirements

### 2.1 Frontend Dockerfile

#### Production Frontend Dockerfile (`Dockerfile.frontend`)
```dockerfile
# Multi-stage build for React frontend
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine AS production

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 2.2 Backend Service Dockerfiles

#### Python Service Dockerfile Template (`svc-*/Dockerfile`)
```dockerfile
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.3 Docker Compose Configuration

#### Development Environment (`docker-compose.dev.yml`)
```yaml
version: '3.8'

services:
  # Frontend
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
      target: development
    ports:
      - "3000:3000"
    volumes:
      - ./src:/app/src
      - ./public:/app/public
    environment:
      - NODE_ENV=development
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - api-gateway

  # API Gateway
  api-gateway:
    build: ./api-gateway
    ports:
      - "8000:8000"
    environment:
      - NODE_ENV=development
      - JWT_SECRET=${JWT_SECRET}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - svc-design
      - svc-project

  # Microservices
  svc-design:
    build: ./svc-design
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/nextgen_design
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  svc-project:
    build: ./svc-project
    ports:
      - "8002:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/nextgen_project
    depends_on:
      - postgres
