output "resource_group_name" {
  description = "Name of the created resource group"
  value       = azurerm_resource_group.main.name
}

output "search_service_name" {
  description = "Azure AI Search service name"
  value       = azurerm_search_service.main.name
}

output "search_service_endpoint" {
  description = "Azure AI Search HTTPS endpoint"
  value       = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "openai_endpoint" {
  description = "Azure OpenAI endpoint"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "openai_resource_name" {
  description = "Azure OpenAI resource name"
  value       = azurerm_cognitive_account.openai.name
}

output "key_vault_uri" {
  description = "Key Vault URI (used by MCP server and CI to retrieve secrets)"
  value       = azurerm_key_vault.main.vault_uri
}

output "env_file_hint" {
  description = "Copy these values to scripts/.env (never commit .env)"
  value = <<-EOT
    AZURE_SEARCH_ENDPOINT=https://${azurerm_search_service.main.name}.search.windows.net
    AZURE_SEARCH_INDEX_NAME=neural-memory
    AZURE_OPENAI_ENDPOINT=${azurerm_cognitive_account.openai.endpoint}
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
    AZURE_KEY_VAULT_URI=${azurerm_key_vault.main.vault_uri}
  EOT
  sensitive = false
}
