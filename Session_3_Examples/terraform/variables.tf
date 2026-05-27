# ═══════════════════════════════════════════════════════════════════════
# variables.tf — Declares all inputs the user must (or may) provide
#
# Each `variable` block is one input. Three things matter:
#   - type        → enforces correctness (string, list, etc.)
#   - description → shown in error messages and `terraform plan`
#   - default     → if present, the variable is OPTIONAL
# ═══════════════════════════════════════════════════════════════════════


# ───── REQUIRED inputs (no default → user MUST provide) ────────────────

variable "organization_id" {
  type        = string
  description = "Your Meraki Organization ID (find it in Dashboard URL or via API)"
}

variable "network_name" {
  type        = string
  description = "Name of the network to create (e.g., 'milan-branch')"
}

variable "device_serials" {
  type        = list(string)
  description = "List of device serial numbers to claim into the network"
  # Example: ["Q2XX-XXXX-XXXX", "Q2YY-YYYY-YYYY"]

  # Validation: serials must be uppercase Q2-prefixed format
  validation {
    condition = alltrue([
      for s in var.device_serials : can(regex("^Q[0-9A-Z]{3}-[0-9A-Z]{4}-[0-9A-Z]{4}$", s))
    ])
    error_message = "Each serial must look like Q2XX-XXXX-XXXX (Meraki format)."
  }
}


# ───── OPTIONAL inputs (have defaults → user may override) ─────────────

variable "product_types" {
  type        = list(string)
  description = "Meraki product families this network will host"
  default     = ["appliance", "wireless"]   # MX + MR is a common combo
}

variable "timezone" {
  type        = string
  description = "IANA timezone for the network (affects logs/schedules)"
  default     = "Etc/UTC"
}

variable "tags" {
  type        = list(string)
  description = "Tags applied to the network (used for grouping/policies)"
  default     = ["terraform-managed"]
}