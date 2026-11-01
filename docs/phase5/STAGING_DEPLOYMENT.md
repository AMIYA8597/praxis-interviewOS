# PRAXIS InterviewOS — Staging Deployment Guide

**Document ID**: PROD-STAGE-DEPLOY-001  
**Milestone**: Phase 5 — Production Engineering  
**Staging Project ID**: `praxis-staging`  
**Staging Region**: `asia-south1` (Mumbai)  
**Date**: 2026-11-01  
**Status**: Authoritative Staging Deployment Guide  

---

## 1. Staging Environment Architecture

The Staging environment mirrors the production architecture while optimizing resource costs through scale-to-zero capabilities:

```
========================================================================================
  STAGING DEPLOYMENT PARAMETERS (asia-south1)
========================================================================================
  * GCP Project ID:         praxis-staging
  * API Service:            praxis-api (min: 0, max: 3, memory: 1 GiB)
  * Realtime Service:       praxis-realtime (min: 1, max: 2, memory: 4 GiB)
  * Worker Service:         praxis-worker (count: 1, memory: 2 GiB)
  * Redis:                  Memorystore Redis 7 (1 GiB, VPC private IP)
  * Database:               Supabase Staging Project (Dedicated, non-production)
  * Terraform Workspace:    infra/gcp/environments/staging
========================================================================================
```

---

## 2. Step-by-Step Staging Deployment Procedure

### 2.1 Pre-Deployment Verification
```bash
# 1. Verify all quality gates pass locally
uv run python scripts/final_quality_gate.py
uv run python scripts/check_backend_completeness.py
uv run python scripts/security/security_baseline.py
```

### 2.2 Build & Push Immutable Artifacts
```bash
# 2. Build containers using Git SHA tag (e.g. 0f1e6e5)
export SHA=$(git rev-parse --short HEAD)
export REGISTRY="asia-south1-docker.pkg.dev/praxis-staging/praxis"

docker build -f docker/Dockerfile.api -t ${REGISTRY}/praxis-api:${SHA} .
docker build -f docker/Dockerfile.realtime -t ${REGISTRY}/praxis-realtime:${SHA} .
docker build -f docker/Dockerfile.worker -t ${REGISTRY}/praxis-worker:${SHA} .

docker push ${REGISTRY}/praxis-api:${SHA}
docker push ${REGISTRY}/praxis-realtime:${SHA}
docker push ${REGISTRY}/praxis-worker:${SHA}
```

### 2.3 Terraform Infrastructure Apply
```bash
cd infra/gcp/environments/staging
terraform init -backend-config=backend.conf
terraform apply -var-file=terraform.tfvars -var="image_tag=${SHA}" -auto-approve
```

### 2.4 Staging Post-Deployment Health Check
```bash
# Verify API liveness
curl -fsS https://praxis-api-staging.run.app/health
# {"status":"ok","environment":"staging","database":"connected","redis":"connected"}
```
