#!/usr/bin/env bash
# setup-secrets.sh — Create required Secret Manager secrets for a PRAXIS environment.
#
# Usage:
#   ./scripts/setup-secrets.sh staging praxis-staging
#   ./scripts/setup-secrets.sh production praxis-production
#
# This script creates empty secret *shells* in Secret Manager.
# You must add secret versions manually:
#   gcloud secrets versions add praxis-database-url --data-file=- --project=PROJECT <<< "postgresql://..."
#
# NEVER pass secret values as command-line arguments (they appear in shell history and /proc).

set -euo pipefail

ENVIRONMENT="${1:?Usage: $0 <staging|production> <project-id>}"
PROJECT="${2:?Usage: $0 <staging|production> <project-id>}"

if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
  echo "ERROR: environment must be 'staging' or 'production'" >&2
  exit 1
fi

SECRETS=(
  "praxis-database-url"
  "praxis-redis-url"
  "praxis-supabase-url"
  "praxis-supabase-anon-key"
  "praxis-groq-api-key"
  "praxis-openai-api-key"
  "praxis-fernet-key"
)

echo "Creating secrets in project '$PROJECT' for environment '$ENVIRONMENT'..."
echo ""

for secret in "${SECRETS[@]}"; do
  if gcloud secrets describe "$secret" --project="$PROJECT" &>/dev/null; then
    echo "  ✓ $secret (already exists)"
  else
    gcloud secrets create "$secret" \
      --replication-policy="automatic" \
      --labels="environment=$ENVIRONMENT,app=praxis" \
      --project="$PROJECT"
    echo "  + $secret (created)"
  fi
done

echo ""
echo "All secret shells created. Add versions with:"
echo "  echo -n 'value' | gcloud secrets versions add SECRET_NAME --data-file=- --project=$PROJECT"
echo ""
echo "Required values:"
echo "  praxis-database-url      — PostgreSQL connection string"
echo "  praxis-redis-url         — Redis connection string (rediss:// for TLS)"
echo "  praxis-supabase-url      — Supabase project URL"
echo "  praxis-supabase-anon-key — Supabase anon/publishable key"
echo "  praxis-groq-api-key      — Groq API key"
echo "  praxis-openai-api-key    — OpenAI API key"
echo "  praxis-fernet-key        — Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
