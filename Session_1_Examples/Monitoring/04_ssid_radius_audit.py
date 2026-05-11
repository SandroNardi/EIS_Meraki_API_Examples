"""
Script 4: Audit SSIDs across networks and configuration templates,
reporting any SSID that uses RADIUS authentication.

Usage:
    export MK_CSM_KEY=your_api_key   # optional
    python 04_ssid_radius_audit.py
"""

import os
import getpass
import meraki
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt


RADIUS_AUTH_MODES = {"8021x-radius", "open-with-radius", "wpa-eap", "8021x-meraki"}


def get_api_key() -> str:
    key = os.environ.get("MK_CSM_KEY")
    if not key:
        key = getpass.getpass("Enter your Meraki API key: ").strip()
    return key


def select_org(console: Console, orgs: list) -> list:
    console.print("\n[bold]Select an organization:[/bold]")
    console.print("  [cyan]0[/cyan]: ALL organizations")
    for i, org in enumerate(orgs, 1):
        console.print(f"  [cyan]{i}[/cyan]: {org['name']} ({org['id']})")
    choice = Prompt.ask("Enter number", default="0")
    idx = int(choice)
    return orgs if idx == 0 else [orgs[idx - 1]]


def is_radius(ssid: dict) -> bool:
    if not ssid.get("enabled"):
        return False
    if ssid.get("authMode") in RADIUS_AUTH_MODES:
        return True
    # WPA2/WPA3 Enterprise variants
    if ssid.get("authMode", "").endswith("-radius"):
        return True
    return False


def collect_ssids(dashboard, net_id: str) -> list:
    try:
        return dashboard.wireless.getNetworkWirelessSsids(net_id)
    except meraki.APIError:
        return []


def main() -> None:
    console = Console()
    dashboard = meraki.DashboardAPI(get_api_key(), suppress_logging=True)

    orgs = dashboard.organizations.getOrganizations()
    selected = select_org(console, orgs)

    findings = []
    total_active_ssids = 0

    for org in selected:
        console.print(f"\n[bold cyan]→ {org['name']}[/bold cyan]")

        # Networks
        try:
            networks = dashboard.organizations.getOrganizationNetworks(
                org["id"], total_pages="all"
            )
        except meraki.APIError as e:
            console.print(f"[red]  Error fetching networks: {e}[/red]")
            networks = []

        wireless_nets = [n for n in networks if "wireless" in n.get("productTypes", [])]

        # Templates
        try:
            templates = dashboard.organizations.getOrganizationConfigTemplates(org["id"])
        except meraki.APIError:
            templates = []

        wireless_templates = [t for t in templates if "wireless" in t.get("productTypes", [])]

        # Count template bindings (network -> template)
        bindings_count = {}
        for n in networks:
            tpl = n.get("configTemplateId")
            if tpl:
                bindings_count[tpl] = bindings_count.get(tpl, 0) + 1

        # Process networks
        for n in wireless_nets:
            if n.get("configTemplateId"):
                continue  # skip bound networks; SSIDs come from the template
            for ssid in collect_ssids(dashboard, n["id"]):
                if ssid.get("enabled"):
                    total_active_ssids += 1
                if is_radius(ssid):
                    findings.append({
                        "kind": "Network",
                        "org": org["name"],
                        "scope": n["name"],
                        "bound_nets": "—",
                        "ssid_num": ssid.get("number"),
                        "ssid_name": ssid.get("name", ""),
                        "auth": ssid.get("authMode", ""),
                        "servers": ssid.get("radiusServers", []) or [],
                    })

        # Process templates
        for t in wireless_templates:
            for ssid in collect_ssids(dashboard, t["id"]):
                if ssid.get("enabled"):
                    total_active_ssids += 1
                if is_radius(ssid):
                    findings.append({
                        "kind": "Template",
                        "org": org["name"],
                        "scope": t["name"],
                        "bound_nets": str(bindings_count.get(t["id"], 0)),
                        "ssid_num": ssid.get("number"),
                        "ssid_name": ssid.get("name", ""),
                        "auth": ssid.get("authMode", ""),
                        "servers": ssid.get("radiusServers", []) or [],
                    })

    # Output
    console.print(f"\n[bold]Total active SSIDs scanned:[/bold] {total_active_ssids}")
    console.print(f"[bold]RADIUS-enabled SSIDs found:[/bold] {len(findings)}\n")

    table = Table(title="RADIUS-enabled SSIDs", show_lines=True)
    table.add_column("Source", style="bold")
    table.add_column("Organization", style="cyan")
    table.add_column("Network / Template")
    table.add_column("Bound nets", justify="right")
    table.add_column("SSID #", justify="right")
    table.add_column("SSID name", style="green")
    table.add_column("Auth mode", style="yellow")
    table.add_column("RADIUS servers (host:port)", style="magenta")

    for f in findings:
        servers = "\n".join(
            f"{s.get('host', '?')}:{s.get('port', '?')}" for s in f["servers"]
        ) or "—"
        kind_style = "[blue]Template[/blue]" if f["kind"] == "Template" else "[white]Network[/white]"
        table.add_row(
            kind_style, f["org"], f["scope"], f["bound_nets"],
            str(f["ssid_num"]), f["ssid_name"], f["auth"], servers,
        )

    console.print(table)


if __name__ == "__main__":
    main()