terraform {
  required_version = ">= 1.6"

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
}

# ──────────────────────────────────────────────
# Locals
# ──────────────────────────────────────────────

locals {
  suffix = random_string.suffix.result

  tags = {
    project     = "neural-flow-framework"
    environment = var.environment
    managed-by  = "terraform"
  }
}

# ──────────────────────────────────────────────
# Randomness for globally-unique names
# ──────────────────────────────────────────────

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

# ──────────────────────────────────────────────
# Resource Group
# ──────────────────────────────────────────────

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.tags
}

# ──────────────────────────────────────────────
# Azure AI Search
# ──────────────────────────────────────────────

resource "azurerm_search_service" "main" {
  name                = "srch-neuralflow-${local.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.search_sku
  tags                = local.tags

  # Disable public network access for non-free tiers in production
  # public_network_access_enabled = false  # uncomment for standard+

  # Semantic ranking is included in standard+; free tier has limited support
  semantic_search_sku = var.search_sku == "free" ? null : "free"
}

# ──────────────────────────────────────────────
# Azure OpenAI (Cognitive Services)
# Used for: text-embedding-3-small (1536 dims)
# ──────────────────────────────────────────────

resource "azurerm_cognitive_account" "openai" {
  name                = "oai-neuralflow-${local.suffix}"
  location            = var.openai_location
  resource_group_name = azurerm_resource_group.main.name
  kind                = "OpenAI"
  sku_name            = var.openai_sku
  tags                = local.tags

  custom_subdomain_name = "oai-neuralflow-${local.suffix}"
}

resource "azurerm_cognitive_deployment" "embedding" {
  name                 = "text-embedding-3-small"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "text-embedding-3-small"
    version = "1"
  }

  sku {
    name     = "Standard"
    capacity = var.embedding_model_capacity
  }
}

# ──────────────────────────────────────────────
# Key Vault — stores secrets referenced by MCP server and CI
# Aegis Protocol: zero secrets in plaintext, always Key Vault
# ──────────────────────────────────────────────

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                = "kv-neuralflow-${local.suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"
  tags                = local.tags

  purge_protection_enabled   = false # set true before production
  soft_delete_retention_days = 7
}

resource "azurerm_key_vault_access_policy" "deployer" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = ["Get", "List", "Set", "Delete", "Purge"]
}

resource "azurerm_key_vault_secret" "search_admin_key" {
  name         = "search-admin-key"
  value        = azurerm_search_service.main.primary_key
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.deployer]
}

resource "azurerm_key_vault_secret" "openai_key" {
  name         = "openai-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.deployer]
}

# ──────────────────────────────────────────────
# RBAC — acesso keyless (ADR-003)
# ──────────────────────────────────────────────
# O protocolo Aegis prega "zero segredo em prompt, memoria ou artefato"; a admin
# key contradizia isso. Estas atribuicoes sao o que permite `ingest.py`,
# `search.py` e o servidor MCP rodarem com DefaultAzureCredential.
#
# Nao removemos a admin key do Key Vault nem desabilitamos `local_authentication`
# aqui: seria mudanca de comportamento em recurso existente, e este projeto nao
# tem backend remoto nem prevent_destroy. Desativar a chave e passo separado,
# depois de a via keyless estar verificada em execucao.

locals {
  # O principal que roda o Terraform sempre entra: sem ele, quem aplicou fica
  # sem acesso ao que acabou de criar.
  rbac_principals = toset(concat(
    [data.azurerm_client_config.current.object_id],
    var.rbac_principal_ids,
  ))
}

# Escrita no indice — exigido por ingest.py (cria indice e sobe documentos).
resource "azurerm_role_assignment" "search_index_data_contributor" {
  for_each             = local.rbac_principals
  scope                = azurerm_search_service.main.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = each.value
}

# Gerencia a definicao do indice (create/update do schema).
resource "azurerm_role_assignment" "search_service_contributor" {
  for_each             = local.rbac_principals
  scope                = azurerm_search_service.main.id
  role_definition_name = "Search Service Contributor"
  principal_id         = each.value
}

# Embeddings — exigido por search.py e pelo servidor MCP.
resource "azurerm_role_assignment" "openai_user" {
  for_each             = local.rbac_principals
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = each.value
}
