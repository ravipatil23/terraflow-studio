variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "vnet_name" {
  type = string
}

variable "address_space" {
  description = "VNet address space, e.g. 10.0.0.0/16."
  type        = string
}

variable "subnet_name" {
  type = string
}

variable "subnet_address_prefix" {
  description = "Delegated subnet prefix, e.g. 10.0.1.0/24."
  type        = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
