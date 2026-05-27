# ═══════════════════════════════════════════════════════════════════════
# main.tf — Creates a Meraki network and claims devices into it
#
# What this does, top to bottom:
#   1. Tells Terraform which version + provider to use
#   2. Configures the Meraki provider (reads API key from env var)
#   3. Creates a network in your organization
#   4. Claims your devices (MX, MS, MR) into that network
# ═══════════════════════════════════════════════════════════════════════


# ───── 1. Provider requirements ────────────────────────────────────────
# `required_providers` tells Terraform WHICH plugin to download.
# Pin the version so future provider releases don't break your config.
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    meraki = {
      source  = "CiscoDevNet/meraki"   # Official Cisco-maintained provider
      version = "~> 1.0"               # Allow 1.x.y, but not 2.0
    }
  }
}


# ───── 2. Provider configuration ───────────────────────────────────────
# The provider block authenticates to the Meraki Dashboard API.
# We deliberately DO NOT put the API key here — it's read from the
# MERAKI_DASHBOARD_API_KEY environment variable automatically.
provider "meraki" {
  # No arguments needed — the env var is picked up automatically.
  # This is best practice: secrets never live in version control.
}


# ───── 3. Create the network ───────────────────────────────────────────
# A "network" in Meraki is the logical container for devices and config.
# `product_types` declares which device families this network supports.
resource "meraki_network" "this" {
  organization_id = var.organization_id      # which org to create in
  name            = var.network_name         # e.g., "milan-branch"

  # Product types must match the devices you'll claim later.
  # Common combos:
  #   ["appliance"]                         → MX only
  #   ["appliance", "wireless"]             → MX + MR
  #   ["appliance", "wireless", "switch"]   → full stack
  product_types = var.product_types

  time_zone = var.timezone                    # e.g., "Europe/Rome"
  tags     = var.tags                        # ["demo", "starter"]
  notes    = "Created by Terraform starter kit"
}


# ───── 4. Claim devices into the network ───────────────────────────────
# A device must exist in your organization's INVENTORY before it can be
# claimed into a network. Buy/register them in the dashboard first.
#
# This single resource accepts a LIST of serials and claims them all.
resource "meraki_network_device_claim" "devices" {
  network_id = meraki_network.this.id        # <- reference to step 3
  serials    = var.device_serials            # ["Q2XX-XXXX-XXXX", ...]
}