#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="tradebit-396406"
REGION="asia-south1"
IMAGE_TAG="latest"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/praxis"

echo ""
echo "=== Deploying PRAXIS API to Cloud Run ==="
echo ""

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
  --set-env-vars="APP_ENV=staging,STORAGE_BACKEND=local,ENABLE_RATE_LIMIT=true,DB_POOL_SIZE=2,DB_MAX_OVERFLOW=3,DB_POOL_RECYCLE_S=300,LOG_LEVEL=INFO,OPENAI_BASE_URL=https://openrouter.ai/api/v1,OPENAI_MODEL=openai/gpt-3.5-turbo,LLM_PROVIDER=gemini,GEMINI_MODEL=gemini-2.0-flash-lite" \
  --set-secrets="DATABASE_URL=praxis-database-url:latest,REDIS_URL=praxis-redis-url:latest,SUPABASE_URL=praxis-supabase-url:latest,SUPABASE_ANON_KEY=praxis-supabase-anon-key:latest,OPENAI_API_KEY=praxis-openai-api-key:latest,FERNET_KEY=praxis-fernet-key:latest"

API_URL=$(gcloud run services describe praxis-api \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")

echo ""
echo "=== API deployed at: ${API_URL} ==="
echo ""
echo "Smoke testing..."
curl -fsS --max-time 15 "${API_URL}/health/live" && echo " OK" || echo " FAILED"
echo ""

echo "=== Deploying PRAXIS Worker to Cloud Run ==="
echo ""

# Check if worker image exists
if gcloud artifacts docker images describe "${REGISTRY}/praxis-worker:${IMAGE_TAG}" --project="${PROJECT_ID}" &>/dev/null; then
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
    --set-env-vars="APP_ENV=staging,STORAGE_BACKEND=local,DB_POOL_SIZE=2,DB_MAX_OVERFLOW=3,DB_POOL_RECYCLE_S=300,WORKER_MAX_JOBS=5" \
    --set-secrets="DATABASE_URL=praxis-database-url:latest,REDIS_URL=praxis-redis-url:latest,SUPABASE_URL=praxis-supabase-url:latest,SUPABASE_ANON_KEY=praxis-supabase-anon-key:latest,FERNET_KEY=praxis-fernet-key:latest"
  echo ""
  echo "Worker deployed."
else
  echo "Worker image not ready yet. Run this command once the build finishes:"
  echo "  gcloud run deploy praxis-worker --image=${REGISTRY}/praxis-worker:${IMAGE_TAG} --region=${REGION} --project=${PROJECT_ID} --platform=managed --no-allow-unauthenticated --memory=1Gi --cpu=1 --min-instances=0 --max-instances=2 --timeout=600 --set-env-vars='APP_ENV=staging,STORAGE_BACKEND=local,DB_POOL_SIZE=2,DB_MAX_OVERFLOW=3,DB_POOL_RECYCLE_S=300,WORKER_MAX_JOBS=5' --set-secrets='DATABASE_URL=praxis-database-url:latest,REDIS_URL=praxis-redis-url:latest,SUPABASE_URL=praxis-supabase-url:latest,SUPABASE_ANON_KEY=praxis-supabase-anon-key:latest,FERNET_KEY=praxis-fernet-key:latest'"
fi

echo ""
echo "============================================"
echo "  Done! API URL: ${API_URL}"
echo "============================================"
echo ""
echo "Next steps — deploy frontend to Vercel:"
echo "  1. Go to https://vercel.com/new"
echo "  2. Import: AMIYA8597/praxis-interviewOS"
echo "  3. Add Environment Variables:"
echo "     NEXT_PUBLIC_API_BASE_URL    = ${API_URL}"
echo "     NEXT_PUBLIC_REALTIME_URL    = wss://praxis-realtime-url (later)"
echo "     NEXT_PUBLIC_SUPABASE_URL    = https://rqbbfegkqmsvthdgoyqk.supabase.co"
echo "     NEXT_PUBLIC_SUPABASE_ANON_KEY = (your anon key)"
echo "     NEXT_PUBLIC_APP_ENV         = production"
echo "  4. Deploy!"
echo ""
echo "After Vercel deploys, update CORS on the API:"
echo "  gcloud run services update praxis-api \\"
echo "    --update-env-vars='CORS_ALLOW_ORIGINS=https://your-app.vercel.app' \\"
echo "    --region=${REGION} --project=${PROJECT_ID}"
echo ""
