# ── Connection info ────────────────────────────────────────────
output "resource_group" {
  value = azurerm_resource_group.main.name
}

output "api_fqdn" {
  value       = azurerm_container_app.api.ingress[0].fqdn
  description = "Container App の FQDN（api.propapi.jp の CNAME 先）"
}

output "acr_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "pg_fqdn" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

output "redis_hostname" {
  value = azurerm_redis_cache.main.hostname
}

output "key_vault_name" {
  value = azurerm_key_vault.main.name
}

# ── Cost estimate ────────────────────────────────────────────
output "estimated_monthly_cost" {
  value = <<-EOT
    PostgreSQL B1ms:     ~$15
    Redis Basic C0:      ~$16
    Container Registry:  ~$5
    Container Apps:      ~$10-30 (consumption)
    Key Vault:           ~$1
    Log Analytics:       ~$2
    ─────────────────────
    Total:               ~$49-69/month
  EOT
}
