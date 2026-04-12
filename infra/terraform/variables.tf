variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
  default     = "6e305fc4-34de-476a-a49d-3c85c36c09f1"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "japaneast"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}
