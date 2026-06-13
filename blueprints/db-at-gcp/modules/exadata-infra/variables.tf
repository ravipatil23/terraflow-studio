variable "cloud_exadata_infrastructure_id" {
  description = "Immutable unique ID for the Exadata Infrastructure."
  type        = string
}

variable "location" {
  description = "GCP region (e.g. us-east4)."
  type        = string
}

variable "display_name" {
  type    = string
  default = null
}

variable "gcp_oracle_zone" {
  description = "Oracle zone within the GCP region (e.g. us-east4-b-r1)."
  type        = string
  default     = null
}

variable "project" {
  description = "GCP project ID. Defaults to provider project if null."
  type        = string
  default     = null
}

variable "deletion_protection" {
  type    = bool
  default = true
}

variable "shape" {
  description = "Exadata shape — Exadata.X9M, Exadata.X10M, or Exadata.X11M."
  type        = string
}

variable "compute_count" {
  description = "Number of compute nodes (2–32)."
  type        = number
}

variable "storage_count" {
  description = "Number of storage servers (3–64)."
  type        = number
}

variable "total_storage_size_gb" {
  description = "Total storage in GB. Leave null/0 to use the default for the shape."
  type        = number
  default     = null
}

variable "customer_contacts" {
  description = "List of email addresses for maintenance notifications."
  type        = list(string)
  default     = []
}

variable "mw_preference" {
  description = "NO_PREFERENCE or CUSTOM_PREFERENCE."
  type        = string
  default     = "NO_PREFERENCE"
}

variable "mw_patching_mode" {
  description = "ROLLING or NONROLLING."
  type        = string
  default     = "ROLLING"
}

variable "mw_is_custom_action_timeout_enabled" {
  type    = bool
  default = false
}

variable "mw_custom_action_timeout_mins" {
  type    = number
  default = 15
}

variable "mw_lead_time_week" {
  type    = number
  default = null
}

variable "mw_days_of_week" {
  type    = list(string)
  default = []
}

variable "mw_months" {
  type    = list(string)
  default = []
}

variable "mw_hours_of_day" {
  type    = list(number)
  default = []
}

variable "mw_weeks_of_month" {
  type    = list(number)
  default = []
}

variable "labels" {
  type    = map(string)
  default = {}
}
