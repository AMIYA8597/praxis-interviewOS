# PRAXIS Release Process
**Phase 86**

---

## Branch Strategy

```
main          ← production source of truth; protected; requires PR + CI green + review
staging       ← staging environment source; auto-deployed to GCP staging on push
feature/*     ← feature branches; PR targets main
hotfix/*      ← emergency patches; PR targets main; cherry-picked to staging post-deploy
```

## Release Pipeline

```
1. DEVELOPMENT
   ├── Feature branch from main
   ├── Local: ruff, pytest, tsc, pnpm build
   └── Commit with conventional-commits format

2. PULL REQUEST
   ├── PR opened against main
   ├── Auto-assign reviewers
   ├── CI pipeline must be green (all jobs)
   └── At least one approval required

3. CI GATE (GitHub Actions)
   ├── backend-tests (migration, RLS, unit, integration, acceptance)
   ├── frontend-checks (typecheck, lint, build)
   ├── secrets-scan (detect-secrets)
   ├── pip-audit (Python CVE scan)
   └── pnpm-audit (frontend CVE scan)

4. MERGE
   ├── Squash-merge to main
   ├── Delete feature branch
   └── Auto-tag: v{year}.{month}.{patch}

5. STAGING DEPLOYMENT (auto on main push)
   ├── Cloud Build trigger fires
   ├── Builds praxis-api, praxis-realtime, praxis-worker images
   ├── Pushes to Artifact Registry with :staging-{sha} tag
   ├── Deploys to Cloud Run staging (praxis-staging GCP project)
   ├── Runs database migrations (staging Supabase project)
   └── Runs staging smoke tests

6. STAGING ACCEPTANCE
   ├── Manual trigger or automated E2E via Playwright
   ├── Full user journey: signup → resume → JD → interview → debrief
   ├── Must pass all acceptance assertions
   └── Performance: API p95 < 500ms, WS connect < 2s

7. PRODUCTION DEPLOYMENT
   ├── Manual trigger: "Promote staging → production"
   ├── Cloud Build builds production images with :v{tag} immutable tag
   ├── Deploys to Cloud Run production (praxis-production GCP project)
   │   └── Canary: 10% traffic to new revision
   ├── Monitors: 5xx rate, latency, WS errors for 10 minutes
   ├── If metrics healthy: promote to 100%
   └── If metrics degrade: rollback (see below)

8. POST-DEPLOYMENT MONITORING
   ├── Cloud Monitoring dashboard reviewed for 30 minutes
   ├── Error Reporting checked for new error groups
   └── AI budget dashboard checked

9. ROLLBACK
   ├── Cloud Run: gcloud run services update-traffic --to-revisions=PREV=100
   ├── Database: only via expand/contract; never destructive auto-rollback
   └── Vercel: redeploy previous deployment from Vercel dashboard
```

## Tagging Convention

```
v2026.10.1   ← year.month.patch
```

Tag is created after staging acceptance, before production deploy:
```bash
git tag -a v2026.10.1 -m "Release 2026.10.1: phases 85-118 production launch"
git push origin v2026.10.1
```

## Database Migration Safety

Before every production migration:
1. Verify backup exists (Supabase dashboard → Database → Backups)
2. Run migration on staging first
3. Verify idempotency: apply twice, second run must be no-op
4. Check for destructive operations (DROP, TRUNCATE, column removal)
5. Apply to production during low-traffic window
6. Verify schema post-migration
7. Run smoke tests
8. Monitor for 15 minutes

Never run raw SQL against production without this gate.

## Hotfix Process

```
1. Cut hotfix/* from main (not from a feature branch)
2. Fix, test locally
3. PR to main (expedited review)
4. CI must pass
5. Merge to main
6. Deploy via normal staging → production pipeline
7. Monitor
```

## Rollback Decision Matrix

| Symptom | Action |
|---------|--------|
| 5xx rate > 1% for 5min | Roll back Cloud Run revision |
| Latency p95 > 3s for 5min | Roll back Cloud Run revision |
| WebSocket errors > 5% | Roll back realtime revision |
| Worker backlog > 1000 for 10min | Scale up worker pool; do not roll back |
| Database connectivity failure | Check Supabase status; do not roll back app |
| AI provider failure | Automatic fallback; monitor budget |
| Supabase outage | Static maintenance page via Vercel; wait |
