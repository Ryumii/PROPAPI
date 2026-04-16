###############################################################################
# PropAPI – Azure Infrastructure (TASK-050)
#
# Resources:
#   - Resource Group
#   - Log Analytics Workspace
#   - Container Apps Environment
#   - Container App (API)
#   - PostgreSQL Flexible Server (Burstable B1ms)
#   - Azure Cache for Redis (Basic C0)
#   - Container Registry (Basic)
#   - Key Vault
#
# Budget target: ≤ $150 / month
# Web frontend: GitHub Pages (outside Terraform)
###############################################################################

terraform {
  required_version = ">= 1.5"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

# ── Random suffix for globally unique names ──────────────────
resource "random_id" "suffix" {
  byte_length = 4
}

# Dedicated secret for JWT signing — NOT derived from resource naming
resource "random_password" "api_secret" {
  length  = 48
  special = false
}

locals {
  suffix = random_id.suffix.hex
  tags = {
    project     = "propapi"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# ── Resource Group ───────────────────────────────────────────
resource "azurerm_resource_group" "main" {
  name     = "rg-propapi-${var.environment}"
  location = var.location
  tags     = local.tags
}

# ── Log Analytics ────────────────────────────────────────────
resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-propapi-${local.suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

# ── Container Registry (Basic – $5/month) ────────────────────
resource "azurerm_container_registry" "main" {
  name                = "crpropapi${local.suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Basic"
  admin_enabled       = true
  tags                = local.tags
}

# ── Container Apps Environment ───────────────────────────────
resource "azurerm_container_app_environment" "main" {
  name                       = "cae-propapi-${var.environment}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  tags                       = local.tags
}

# ── PostgreSQL Flexible Server ───────────────────────────────
resource "random_password" "pg_password" {
  length  = 24
  special = true
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                          = "pg-propapi-${local.suffix}"
  location                      = azurerm_resource_group.main.location
  resource_group_name           = azurerm_resource_group.main.name
  administrator_login           = "propadmin"
  administrator_password        = random_password.pg_password.result
  sku_name                      = "B_Standard_B1ms"
  version                       = "16"
  storage_mb                    = 32768
  backup_retention_days         = 7
  geo_redundant_backup_enabled  = false
  public_network_access_enabled = true
  zone                          = "1"
  tags                          = local.tags
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "propapi"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "ja_JP.utf8"
}

# Allow Azure services (Container Apps) to connect
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name      = "AllowAzureServices"
  server_id = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# PostGIS extension
resource "azurerm_postgresql_flexible_server_configuration" "extensions" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "POSTGIS"
}

# ── Azure Cache for Redis ────────────────────────────────────
resource "azurerm_redis_cache" "main" {
  name                          = "redis-propapi-${local.suffix}"
  location                      = azurerm_resource_group.main.location
  resource_group_name           = azurerm_resource_group.main.name
  capacity                      = 0
  family                        = "C"
  sku_name                      = "Basic"
  non_ssl_port_enabled          = false
  minimum_tls_version           = "1.2"
  public_network_access_enabled = true
  tags                          = local.tags
}

# ── Key Vault ────────────────────────────────────────────────
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                       = "kv-propapi-${local.suffix}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id
    secret_permissions = ["Get", "List", "Set", "Delete", "Purge"]
  }

  tags = local.tags
}

# Store secrets in Key Vault
resource "azurerm_key_vault_secret" "pg_password" {
  name         = "pg-admin-password"
  value        = random_password.pg_password.result
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "pg_connection" {
  name         = "database-url"
  value        = "postgresql+asyncpg://propadmin:${random_password.pg_password.result}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/propapi?ssl=require"
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "redis_connection" {
  name         = "redis-url"
  value        = "rediss://:${azurerm_redis_cache.main.primary_access_key}@${azurerm_redis_cache.main.hostname}:${azurerm_redis_cache.main.ssl_port}/0"
  key_vault_id = azurerm_key_vault.main.id
}

# ── Container App (API) ──────────────────────────────────────
resource "azurerm_container_app" "api" {
  name                         = "ca-propapi-api"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.tags

  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.main.admin_password
  }

  secret {
    name  = "database-url"
    value = "postgresql+asyncpg://propadmin:${random_password.pg_password.result}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/propapi?ssl=require"
  }

  secret {
    name  = "redis-url"
    value = "rediss://:${azurerm_redis_cache.main.primary_access_key}@${azurerm_redis_cache.main.hostname}:${azurerm_redis_cache.main.ssl_port}/0"
  }

  secret {
    name  = "api-secret-key"
    value = random_password.api_secret.result
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = 0
    max_replicas = 3

    container {
      name   = "api"
      image  = "${azurerm_container_registry.main.login_server}/propapi-api:latest"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name        = "REDIS_URL"
        secret_name = "redis-url"
      }
      env {
        name        = "API_SECRET_KEY"
        secret_name = "api-secret-key"
      }
      env {
        name  = "API_ENV"
        value = var.environment
      }
      env {
        name  = "CORS_ORIGINS"
        value = "https://propapi.jp"
      }
    }
  }
}

# ── Azure Data Factory + Managed Airflow (TASK-061) ──────────
# Uncomment when ready to deploy (~$350-400/month additional cost).
# For lower-cost alternative, consider Container Apps Jobs.
#
# module "airflow" {
#   source = "./modules/airflow"
#
#   resource_group_name        = azurerm_resource_group.main.name
#   location                   = azurerm_resource_group.main.location
#   suffix                     = local.suffix
#   tags                       = local.tags
#   log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
#   database_url_sync          = "postgresql://propadmin:${random_password.pg_password.result}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/propapi?sslmode=require"
# }
