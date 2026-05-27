# Meraki Starter Kit — Terraform + Ansible

A minimal, well-commented example for managing Cisco Meraki with
Infrastructure as Code. **Read every file's comments — they explain why.**

## What you'll build

1. **Terraform** creates a Meraki network and claims your devices into it
2. **Ansible** configures two SSIDs on that network:
   - An **open guest** SSID
   - A **WPA2 password-protected** corporate SSID

## Prerequisites

- Terraform ≥ 1.6
- Ansible ≥ 2.15
- A Meraki Dashboard account with:
  - An API key ([how to generate](https://documentation.meraki.com/General_Administration/Other_Topics/Cisco_Meraki_Dashboard_API))
  - At least one MX and one MR device in your organization inventory

## 5-minute Quickstart

```bash
# 1. Set your API key
cp .env.example .env
nano .env                       # paste your API key
source .env

# 2. Create the network with Terraform
cd terraform
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars           # fill in org ID, network name, serials
terraform init
terraform apply                 # confirm with 'yes'

# 3. Note the network_id from the output, then configure SSIDs
cd ../ansible
ansible-galaxy collection install cisco.meraki
cp group_vars/all.yml.example group_vars/all.yml
nano group_vars/all.yml         # set your corp Wi-Fi password

ansible-playbook -i inventory.yml ssids.yml \
    -e "network_id=<paste-network-id-here>"

## Detecting drift (manual changes in the dashboard)

If someone edits SSID settings directly in the Meraki dashboard, your
desired config in `group_vars/all.yml` no longer matches reality. This
is called **configuration drift**.

To detect it:

```bash
source ../.env
ansible-playbook -i inventory.yml ssids_validate.yml \
    -e "network_id=<your-network-id>"