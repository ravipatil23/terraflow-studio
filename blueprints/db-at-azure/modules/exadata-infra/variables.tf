variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "name" {
  type = string
}

variable "display_name" {
  type = string
}

variable "shape" {
  type    = string
  default = "Exadata.X11M"
}

variable "compute_count" {
  type    = number
  default = 2
}

variable "storage_count" {
  type    = number
  default = 3
}

variable "zone" {
  description = "Availability zone for the infrastructure, e.g. \"2\"."
  type        = string
}

variable "mw_preference" {
  type    = string
  default = "NoPreference"
}

variable "mw_patching_mode" {
  type    = string
  default = "Rolling"
}

variable "mw_lead_time_in_weeks" {
  type    = number
  default = 0
}

variable "mw_days_of_week" {
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

variable "mw_months" {
  type    = list(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
