# PRAXIS InterviewOS — Terraform Infrastructure Management

This directory contains the root Terraform configuration for orchestrating Google Cloud Platform resources for PRAXIS InterviewOS.

## Architecture & Module Topology
- **Root Module**: `infra/terraform/` (wraps and parameterizes `infra/gcp/`)
- **Child Modules**:
  - `infra/gcp/`: Cloud Run (`praxis-api`, `praxis-realtime`, `praxis-worker`), Memorystore Redis 7, Serverless VPC Access connector, Artifact Registry, Secret Manager, Cloud Logging, and Cloud Monitoring.
  - `infra/bootstrap/`: KMS keys and remote GCS state bucket provisioning.

## Directory Layout
```text
infra/terraform/
├── main.tf                 # Root module invoking infra/gcp
├── variables.tf            # Parameter definitions
├── outputs.tf              # Service URLs, Redis host, LB IP, WIF provider
├── README.md               # Operational instructions
└── environments/
    ├── staging/
    │   └── terraform.tfvars # Staging sizing (scale-to-zero API, 1GB Redis)
    └── production/
        └── terraform.tfvars # Production sizing (min 1 instance, 2GB Redis)
```

## Standard Operations
```bash
# Initialize with remote state
terraform init -backend-config=backend.conf

# Plan changes for staging
terraform plan -var-file=environments/staging/terraform.tfvars

# Apply approved plan
terraform apply -var-file=environments/staging/terraform.tfvars
```
