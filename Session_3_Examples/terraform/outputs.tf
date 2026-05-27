# ═══════════════════════════════════════════════════════════════════════
# outputs.tf — Values exposed after `terraform apply` finishes
#
# Outputs are useful for:
#   - Showing the user what was created (network ID, etc.)
#   - Feeding values into other tools (Ansible, scripts)
#   - Quick reference without digging through state
# ═══════════════════════════════════════════════════════════════════════

output "network_id" {
  description = "Meraki Network ID — feed this to Ansible or other tools"
  value       = meraki_network.this.id
}

output "network_name" {
  description = "The name of the created network"
  value       = meraki_network.this.name
}

output "claimed_serials" {
  description = "Devices that were claimed into the network"
  value       = var.device_serials
}

output "next_steps" {
  description = "What to do after this Terraform run"
  value = <<-EOT

    ✓ Network created: ${meraki_network.this.name}
    ✓ Network ID:      ${meraki_network.this.id}

    Next: configure SSIDs with Ansible
      cd ../ansible
      ansible-playbook -i inventory.yml ssids.yml \
          -e "network_id=${meraki_network.this.id}"

  EOT
}