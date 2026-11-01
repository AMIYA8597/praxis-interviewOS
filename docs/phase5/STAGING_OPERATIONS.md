# PRAXIS InterviewOS — Staging Operations & Maintenance

**Document ID**: PROD-STAGE-OPS-001  
**Milestone**: Phase 5 — Production Engineering  
**Environment**: Staging Cluster (`asia-south1`)  
**Date**: 2026-11-01  
**Status**: Authoritative Staging Operations Specification  

---

## 1. Staging Maintenance & Operational Controls

The staging environment serves as the pre-production validation sandbox where all PRs, security scans, and E2E journeys are vetted prior to production promotion:

### 1.1 Automated Scale-to-Zero Policy
To minimize cloud infrastructure spend while maintaining deployment readiness:
- `api_min_instances = 0`: Cloud Run automatically scales `praxis-api` to zero instances after 15 minutes of inactivity.
- `realtime_min_instances = 1`: Kept at 1 instance during working hours (08:00–20:00 IST) to facilitate manual and automated testing without cold-start model load delays.
- Monthly Staging Compute Cost: **$\approx \$35.00\text{/month}$**.

---

## 2. Synthetic Test Data Management

To maintain GDPR compliance and prevent storage bloat:
1. **Automated Test Tenant Purging**: Synthetic test candidates (identified by prefix `test_cand_`) are automatically purged after 24 hours by a scheduled ARQ maintenance task (`backend/app/worker_tasks.py`).
2. **Zero Real User Data**: Production database dumps are **strictly forbidden** from being imported into staging. Staging utilizes synthetic mock candidates, synthetic job descriptions, and synthetic resume PDFs exclusively.

---

## 3. Operational Ownership & Escalation

- **Primary SRE Owner**: PRAXIS DevOps Guild
- **Staging URL Status**: Monitored via Cloud Monitoring Uptime Checks with automated Slack notifications to `#eng-staging-alerts`.
- **Maintenance Windows**: Weekly Wednesday 02:00–04:00 IST for non-disruptive infrastructure updates.
