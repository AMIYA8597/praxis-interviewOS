#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# PRAXIS InterviewOS — Full Deployment Script
# Deploys backend to GCP Cloud Run, then guides Vercel frontend setup.
#
# Prerequisites:
#   - gcloud CLI authenticated (gcloud auth login)
#   - Docker running locally
#   - Supabase project with database URL ready
#   - Redis URL ready (e.g. Upstash free tier)
#
# Usage:
#   bash scripts/deploy.sh
# =============================================================================

PROJECT_ID="tradebit-396406"
REGION="asia-south1"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/praxis"
IMAGE_TAG=$(git rev-parse --short HEAD)

echo ""
echo "============================================"
echo "  PRAXIS InterviewOS Deployment"
echo "  Project: ${PROJECT_ID}"
echo "  Region:  ${REGION}"
echo "  Tag:     ${IMAGE_TAG}"
echo "============================================"
echo ""

# ── Step 1: Collect secrets ──────────────────────────────────────────────────

echo "[1/6] Collecting secrets..."
echo ""

# Database URL (Supabase Postgres)
if [ -z "${DATABASE_URL:-}" ]; then
  echo "Enter your Supabase database URL"
  echo "  Format: postgresql+asyncpg://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres"
  echo "  Find it in: Supabase Dashboard > Settings > Database > Connection string > URI"
  read -rp "  DATABASE_URL: " DATABASE_URL
fi

# Redis URL
if [ -z "${REDIS_URL:-}" ]; then
  echo ""
  echo "Enter your Redis URL (e.g. Upstash: rediss://default:xxx@xxx.upstash.io:6379)"
  read -rp "  REDIS_URL: " REDIS_URL
fi

# Supabase
SUPABASE_URL="${SUPABASE_URL:-https://rqbbfegkqmsvthdgoyqk.supabase.co}"
echo ""
echo "  Using SUPABASE_URL=${SUPABASE_URL}"

if [ -z "${SUPABASE_ANON_KEY:-}" ]; then
  echo "Enter your Supabase anon key (Settings > API > anon/public key)"
  read -rp "  SUPABASE_ANON_KEY: " SUPABASE_ANON_KEY
fi

# AI provider keys
if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo ""
  read -rp "  OPENAI_API_KEY (or press Enter to skip): " OPENAI_API_KEY
fi

if [ -z "${GEMINI_API_KEY:-}" ]; then
  read -rp "  GEMINI_API_KEY (or press Enter to skip): " GEMINI_API_KEY
fi

# Fernet key for encrypting BYO provider secrets
if [ -z "${FERNET_KEY:-}" ]; then
  FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
  echo ""
  echo "  Generated FERNET_KEY=${FERNET_KEY}"
  echo "  (save this — you need it if you redeploy)"
fi

# ── Step 2: Create Secret Manager secrets ────────────────────────────────────

echo ""
echo "[2/6] Creating Secret Manager secrets..."

create_or_update_secret() {
  local name="$1"
  local value="$2"
  if [ -z "$value" ]; then
    echo "  Skipping ${name} (empty value)"
    return
  fi
  if gcloud secrets describe "$name" --project="$PROJECT_ID" &>/dev/null; then
    echo "$value" | gcloud secrets versions add "$name" --data-file=- --project="$PROJECT_ID" 2>/dev/null
    echo "  Updated: ${name}"
  else
    echo "$value" | gcloud secrets create "$name" --data-file=- --replication-policy=automatic --project="$PROJECT_ID" 2>/dev/null
    echo "  Created: ${name}"
  fi
}

create_or_update_secret "praxis-database-url" "$DATABASE_URL"
create_or_update_secret "praxis-redis-url" "$REDIS_URL"
create_or_update_secret "praxis-supabase-url" "$SUPABASE_URL"
create_or_update_secret "praxis-supabase-anon-key" "$SUPABASE_ANON_KEY"
create_or_update_secret "praxis-openai-api-key" "${OPENAI_API_KEY:-}"
create_or_update_secret "praxis-groq-api-key" "${GEMINI_API_KEY:-}"
create_or_update_secret "praxis-fernet-key" "$FERNET_KEY"

# Grant Cloud Run service agent access to secrets
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo ""
echo "  Granting secret access to ${SA}..."
for secret in praxis-database-url praxis-redis-url praxis-supabase-url praxis-supabase-anon-key praxis-openai-api-key praxis-groq-api-key praxis-fernet-key; do
  if gcloud secrets describe "$secret" --project="$PROJECT_ID" &>/dev/null; then
    gcloud secrets add-iam-policy-binding "$secret" \
      --member="serviceAccount:${SA}" \
      --role="roles/secretmanager.secretAccessor" \
      --project="$PROJECT_ID" --quiet 2>/dev/null || true
  fi
done
echo "  Done."

# ── Step 3: Build Docker images ─────────────────────────────────────────────

echo ""
echo "[3/6] Building Docker images (this takes 5-10 minutes)..."
echo ""

docker build -f docker/Dockerfile.api -t "${REGISTRY}/praxis-api:${IMAGE_TAG}" --target production . 2>&1
echo ""
echo "  API image built."

docker build -f docker/Dockerfile.worker -t "${REGISTRY}/praxis-worker:${IMAGE_TAG}" --target production . 2>&1
echo ""
echo "  Worker image built."

echo ""
echo "  Skipping realtime image (requires torch — build separately if needed)."
echo "  To build: docker build -f docker/Dockerfile.realtime -t ${REGISTRY}/praxis-realtime:${IMAGE_TAG} --target production ."

# ── Step 4: Push images ─────────────────────────────────────────────────────

echo ""
echo "[4/6] Pushing images to Artifact Registry..."

docker push "${REGISTRY}/praxis-api:${IMAGE_TAG}" 2>&1
docker push "${REGISTRY}/praxis-worker:${IMAGE_TAG}" 2>&1

echo "  Done."

# ── Step 5: Deploy to Cloud Run ─────────────────────────────────────────────

echo ""
echo "[5/6] Deploying to Cloud Run..."

# Deploy API
gcloud run deploy praxis-api \
  --image="${REGISTRY}/praxis-api:${IMAGE_TAG}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8000 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --timeout=300 \
  --set-env-vars="APP_ENV=production,STORAGE_BACKEND=local,ENABLE_RATE_LIMIT=true,DB_POOL_SIZE=2,DB_MAX_OVERFLOW=3,DB_POOL_RECYCLE_S=300,LOG_LEVEL=INFO" \
  --set-secrets="DATABASE_URL=praxis-database-url:latest,REDIS_URL=praxis-redis-url:latest,SUPABASE_URL=praxis-supabase-url:latest,SUPABASE_ANON_KEY=praxis-supabase-anon-key:latest,OPENAI_API_KEY=praxis-openai-api-key:latest,FERNET_KEY=praxis-fernet-key:latest" \
  --quiet 2>&1

API_URL=$(gcloud run services describe praxis-api \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")

echo ""
echo "  API deployed at: ${API_URL}"

# Deploy Worker
gcloud run deploy praxis-worker \
  --image="${REGISTRY}/praxis-worker:${IMAGE_TAG}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --platform=managed \
  --no-allow-unauthenticated \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=2 \
  --timeout=600 \
  --set-env-vars="APP_ENV=production,STORAGE_BACKEND=local,DB_POOL_SIZE=2,DB_MAX_OVERFLOW=3,DB_POOL_RECYCLE_S=300,WORKER_MAX_JOBS=5" \
  --set-secrets="DATABASE_URL=praxis-database-url:latest,REDIS_URL=praxis-redis-url:latest,SUPABASE_URL=praxis-supabase-url:latest,SUPABASE_ANON_KEY=praxis-supabase-anon-key:latest,FERNET_KEY=praxis-fernet-key:latest" \
  --quiet 2>&1

echo "  Worker deployed."

# ── Step 6: Smoke test ──────────────────────────────────────────────────────

echo ""
echo "[6/6] Smoke testing..."

HTTP_CODE=$(curl -fsS -o /dev/null -w "%{http_code}" --max-time 15 "${API_URL}/health/live" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  echo "  /health/live: OK"
else
  echo "  /health/live: FAILED (HTTP ${HTTP_CODE})"
  echo "  Check logs: gcloud run services logs read praxis-api --region=${REGION} --project=${PROJECT_ID} --limit=20"
fi

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo "============================================"
echo "  Backend Deployment Complete!"
echo "============================================"
echo ""
echo "  API URL: ${API_URL}"
echo ""
echo "  Next: Deploy frontend to Vercel"
echo ""
echo "  1. Go to https://vercel.com/new"
echo "  2. Import: AMIYA8597/praxis-interviewOS"
echo "  3. Framework: Next.js (auto-detected)"
echo "  4. Root directory: . (monorepo — vercel.json handles it)"
echo "  5. Add these Environment Variables:"
echo "     NEXT_PUBLIC_API_BASE_URL    = ${API_URL}"
echo "     NEXT_PUBLIC_REALTIME_URL    = wss://praxis-realtime-url (deploy realtime service first)"
echo "     NEXT_PUBLIC_SUPABASE_URL    = ${SUPABASE_URL}"
echo "     NEXT_PUBLIC_SUPABASE_ANON_KEY = (your anon key)"
echo "     NEXT_PUBLIC_APP_ENV         = production"
echo "  6. Deploy!"
echo ""
echo "  After Vercel deploys, update CORS:"
echo "    gcloud run services update praxis-api \\"
echo "      --update-env-vars='CORS_ALLOW_ORIGINS=https://your-app.vercel.app' \\"
echo "      --region=${REGION} --project=${PROJECT_ID}"
echo ""
