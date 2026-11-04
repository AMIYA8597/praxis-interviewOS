################################################################################
# PRAXIS InterviewOS — Master Terraform Outputs
################################################################################

output "api_cloud_run_url" {
  description = "Cloud Run service URL for API"
  value       = module.gcp_infrastructure.api_cloud_run_url
}

output "realtime_cloud_run_url" {
  description = "Cloud Run service URL for Realtime agent"
  value       = module.gcp_infrastructure.realtime_cloud_run_url
}

output "api_url" {
  description = "Authoritative public URL for API traffic"
  value       = module.gcp_infrastructure.api_url
}

output "realtime_url" {
  description = "Authoritative public URL for WebSocket realtime traffic"
  value       = module.gcp_infrastructure.realtime_url
}

output "redis_host" {
  description = "Private IP of Memorystore Redis instance"
  value       = module.gcp_infrastructure.redis_host
  sensitive   = true
}

output "load_balancer_ip" {
  description = "Static IP allocated for External HTTPS/WSS Load Balancer"
  value       = module.gcp_infrastructure.load_balancer_ip
}

output "wif_provider_name" {
  description = "Workload Identity Federation Provider resource name"
  value       = module.gcp_infrastructure.wif_provider_name
}

output "deployer_service_account" {
  description = "IAM Service Account email used by CI/CD pipelines"
  value       = module.gcp_infrastructure.deployer_service_account
}
