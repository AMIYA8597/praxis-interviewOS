# PRAXIS InterviewOS — CI/CD Pipeline Architecture

**Document ID**: PROD-CICD-001  
**Milestone**: Phase 5 — Production Engineering  
**Orchestration**: GitHub Actions (`.github/workflows/ci.yml`) & Google Cloud Build (`cloudbuild.yaml`)  
**Tagging Policy**: Immutable Git SHA (`${SHORT_SHA}`)  
**Date**: 2026-11-01  
**Status**: Authoritative CI/CD Specification  

---

## 1. Automated Pipeline Stage Flow

The PRAXIS deployment pipeline enforces zero-defect promotions from pull requests to production:

```mermaid
flowchart TD
    PR[Pull Request Opened / Updated] --> Gate[Quality & Security Gates]
    
    subgraph Gate Evaluation
        QG[Final Quality Gate\n15/15 Passed]
        BCG[Backend Completeness Gate\n75/75 Passed]
        SecSuite[Security Regression Suite\n84 Passed Controls]
        UITests[Design System Tests\n28/28 Passed]
        DesktopTests[Desktop Integration Tests\n15/15 Passed]
        BuildWeb[Next.js 15 Build\nExit Code 0]
        BuildDesktop[Desktop tsc Build\nExit Code 0]
        TFVal[Terraform Validate\nExit Code 0]
    end

    Gate --> QG
    Gate --> BCG
    Gate --> SecSuite
    Gate --> UITests
    Gate --> DesktopTests
    Gate --> BuildWeb
    Gate --> BuildDesktop
    Gate --> TFVal

    QG & BCG & SecSuite & UITests & DesktopTests & BuildWeb & BuildDesktop & TFVal --> Merge[Merge to main branch]

    subgraph Build & Staging Pipeline
        Merge --> CloudBuild[Cloud Build Trigger]
        CloudBuild --> ImmBuild[Build Immutable Images\nTag: ${SHORT_SHA}]
        ImmBuild --> ScanSBOM[Scan Images & Update sbom.json]
        ScanSBOM --> StagingDeploy[Deploy to Cloud Run Staging]
        StagingDeploy --> SmokeTest[Execute Staging Smoke Tests]
    end

    subgraph Production Gate
        SmokeTest --> ManualApproval{Release Approval\nLead Architect Sign-off}
        ManualApproval -- Approved --> ProdDeploy[Deploy to Cloud Run Production\nZero-Downtime Traffic Migration]
        ProdDeploy --> PostVerify[Post-Deploy Health Verification]
    end
```

---

## 2. Pull Request Blocking Gates

Every pull request must pass the following automated checks prior to merge authorization:

| Pipeline Check | Command | Enforced Standard | Blocking? |
| :--- | :--- | :--- | :---: |
| **Final Quality Gate** | `uv run python scripts/final_quality_gate.py` | 15/15 checks pass (RLS, ruff, no secrets) | **YES** |
| **Backend Completeness** | `uv run python scripts/check_backend_completeness.py` | 75/75 architectural capabilities pass | **YES** |
| **Security Baseline** | `uv run python scripts/security/security_baseline.py` | Zero secrets, 63 security tests pass | **YES** |
| **UI Component Suite** | `pnpm --filter @praxis/ui test` | 28/28 unit tests pass | **YES** |
| **Desktop Suite** | `pnpm --filter desktop test` | 15/15 integration tests pass | **YES** |
| **Web Production Build** | `pnpm build:web` | Next.js 15 production compile succeeds | **YES** |
| **Desktop Build** | `pnpm build:desktop` | `tsc` clean compilation | **YES** |
| **Terraform Syntax** | `terraform -chdir=infra/gcp validate` | Configuration valid | **YES** |

---

## 3. Deployment Gating & Artifact Promotion

1. **Build Once, Deploy Anywhere**: The identical container image digests (`sha256:...`) validated in Staging are promoted to Production. Rebuilding binaries between staging and production is strictly prohibited.
2. **Production Manual Approval**: Production deployment triggers require explicit human sign-off from the Release Engineering Lead or Security Architect in the GitHub Actions / Cloud Build console.
3. **Automated Rollback Trigger**: If post-deployment smoke tests detect a 5xx response rate $> 1\%$ within 5 minutes of release, Cloud Run automatically rolls back 100% of traffic to the prior healthy revision.
