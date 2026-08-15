variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "eastus"
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "rg-neural-flow"
}

variable "environment" {
  description = "Environment tag (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "search_sku" {
  description = "Azure AI Search pricing tier (free | basic | standard)"
  type        = string
  default     = "free"

  validation {
    condition     = contains(["free", "basic", "standard", "standard2", "standard3"], var.search_sku)
    error_message = "search_sku must be one of: free, basic, standard, standard2, standard3"
  }
}

variable "openai_sku" {
  description = "Azure OpenAI (Cognitive Services) SKU"
  type        = string
  default     = "S0"
}

variable "openai_location" {
  description = "Region for Azure OpenAI (must support text-embedding-3-small; prefer eastus or swedencentral)"
  type        = string
  default     = "eastus"
}

variable "embedding_model_capacity" {
  description = "Capacity (TPM units x 1000) for the embedding model deployment"
  type        = number
  default     = 1
}

variable "rbac_principal_ids" {
  description = <<-EOT
    Principals que recebem acesso keyless (Entra ID/RBAC) ao Search e ao OpenAI.
    Vazio = so o principal que roda o Terraform. Ver ADR-003.
  EOT
  type        = list(string)
  default     = []
}
