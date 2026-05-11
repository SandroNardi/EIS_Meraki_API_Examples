# Cisco Workflow Meraki Examples

A collection of **Cisco Workflow** automation examples for **Cisco Meraki**: AI-driven incident analysis, network provisioning with approvals, organization audits with pagination, and tag-based device operations.

📚 **Documentation:** https://documentation.meraki.com/Platform_Management/Workflows

# Disclaimer
This are intended for educational purposes only, not for production use

---

## 🧩 Workflow Catalog

| Folder | Workflow Name | Trigger | Dependencies (Atomics) | Notes |
|---|---|---|---|---|
| `DeviceUnreachWithAI__` | Device status on unreachable - Webhook trigger_AI_WX | Meraki Webhook (`unreachable`) | Alert JSON Parsing, Get Org Devices, Get Org Config Changes, Get Device LLDP/CDP, Get Devices Availabilities History, Get Network Events, Get Network Firmware Upgrades, Webex - Post Message | Full AI-powered RCA. Parses alert → fetches context in parallel → AI LLM summary → posts to Webex. **Most advanced.** |
| `DeviceUnreachWithAIS1__` | Device status on unreachable - Webhook trigger_Step 1 | Meraki Webhook (`unreachable`) | Same Meraki atomics (no Webex, no AI) | Baseline version. Collects context only. Good starting point. |
| `FetchSSIDWithPagination__` | Fetch Networks and SSIDs with Pagination | Manual | Get Org Networks, Get Network Wireless SSIDs | Demonstrates **pagination loop** with `startingAfter` token. Returns enabled SSIDs only. |
| `NetworkCreate__` | Network Creation with prompt and approvers | Manual | Get Orgs, Get Org Inventory Devices, Create Org Network, Claim Network Devices | Human-in-the-loop: prompt → 2 admin approvals → create network → claim devices. |
| `OrgSecInfowPagniation__` | Audit Organization Settings with pagination | Manual / scheduled | Get Orgs, Get Org SAML, Get Org Login Security | Compliance audit. Iterates all orgs, builds HTML table, emails report via SMTP. |
| `TagDeviceRebootWithApproval__` | Meraki - Reboot Devices with Approval | Manual | Get Orgs, Get Org Networks, Get Org Devices, Reboot Device | Tag-based bulk reboot with admin approval and Markdown status report. |
