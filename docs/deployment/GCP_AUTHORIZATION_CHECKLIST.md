# PRAXIS InterviewOS — Google Cloud Authorization Checklist & Gate 3 Review

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  
**Barrier Status:** `READY_FOR_STAGING_AUTHORIZATION` / `BLOCKED_ON_CLOUD_AUTHORIZATION`  

---

## 1. Non-Negotiable Authorization Guardrails

In strict accordance with Rule 0.2:
- *"Do not apply Terraform, create chargeable infrastructure, incur material cloud expenditure, destroy resources or rotate production credentials without explicit authorization."*
- *"Do not invent project IDs, domains, infrastructure IDs, credentials or environment values."*
- *"Phase 3 Gate PASS: All project, billing, IAM, quota, cost and authorization requirements are accounted for. Run read-only discovery and Terraform validation first. Generate a Terraform plan and its change summary. Do not apply it until the user explicitly authorizes the resource creation and associated spend."*

---

## 2. Authorization Checklist

- [x] **Account Authentication Verified:** Authenticated as `amiyachowdhury04@gmail.com`.
- [x] **Billing Account Verified:** `01DE13-945CB6-4911D1` ("My Billing Account") confirmed OPEN.
- [x] **Target Region Selected:** `asia-south1` (Mumbai) configured in `terraform.tfvars`.
- [x] **Terraform Syntax & Format Verified:** `terraform fmt -check -recursive` passed cleanly with code 0.
- [x] **Least-Privilege IAM Scoped:** Dedicated Service Accounts specified in `docs/deployment/GCP_IAM_MATRIX.md`.
- [x] **Cost Estimates & Caps Modeled:** Estimated at ~$72.15/month with scale-to-zero API and hard instance ceilings in `docs/deployment/GCP_COST_AND_RESOURCE_PLAN.md`.
- [ ] **External Action: Project Creation & Billing Link:** Requires user confirmation to execute `gcloud projects create praxis-staging` and link billing account `01DE13-945CB6-4911D1`.
- [ ] **External Action: Live Terraform Apply:** Requires explicit user authorization to provision live infrastructure.

---

## 3. Recommended Manual Command to Authorize

When ready to authorize staging provisioning:
```bash
gcloud projects create praxis-staging --name="PRAXIS Staging"
gcloud billing projects link praxis-staging --billing-account=01DE13-945CB6-4911D1
```
