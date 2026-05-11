"""
Script 3: List inventory devices with published End-of-Sale / End-of-Support
dates, sorted by the closest upcoming event first.

Usage:
    export MK_CSM_KEY=your_api_key   # optional
    python 03_inventory_eol.py
"""

import os
import getpass
from datetime import datetime, timezone
import meraki
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt


def get_api_key() -> str:
    key = os.environ.get("MK_CSM_KEY")
    if not key:
        key = getpass.getpass("Enter your Meraki API key: ").strip()
    return key


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def closest_event(device: dict) -> datetime:
    """Return the earliest EoS/EoSupport date for sorting; far future if none."""
    eox = device.get("eox") or {}
    dates = [parse_date(eox.get("endOfSaleAt")), parse_date(eox.get("endOfSupportAt"))]
    dates = [d for d in dates if d]
    return min(dates) if dates else datetime.max.replace(tzinfo=timezone.utc)


def select_org(console: Console, orgs: list) -> list:
    console.print("\n[bold]Select an organization:[/bold]")
    console.print("  [cyan]0[/cyan]: ALL organizations")
    for i, org in enumerate(orgs, 1):
        console.print(f"  [cyan]{i}[/cyan]: {org['name']} ({org['id']})")
    choice = Prompt.ask("Enter number", default="0")
    idx = int(choice)
    return orgs if idx == 0 else [orgs[idx - 1]]


def main() -> None:
    console = Console()
    dashboard = meraki.DashboardAPI(get_api_key(), suppress_logging=True)

    orgs = dashboard.organizations.getOrganizations()
    selected = select_org(console, orgs)

    rows = []
    for org in selected:
        with console.status(f"[green]Fetching inventory for {org['name']}..."):
            try:
                devices = dashboard.organizations.getOrganizationInventoryDevices(
                    org["id"], total_pages="all"
                )
            except meraki.APIError as e:
                console.print(f"[red]Error for {org['name']}: {e}[/red]")
                continue

        for d in devices:
            eox = d.get("eox") or {}
            if not eox:
                continue
            rows.append({
                "org": org["name"],
                "serial": d.get("serial", ""),
                "model": d.get("model", ""),
                "name": d.get("name") or "—",
                "status": eox.get("status", ""),
                "eos": eox.get("endOfSaleAt", "") or "—",
                "eosup": eox.get("endOfSupportAt", "") or "—",
                "_sort": closest_event(d),
            })

    rows.sort(key=lambda r: r["_sort"])

    table = Table(title=f"Devices with EoL data ({len(rows)})", show_lines=False)
    table.add_column("Closest event", style="bold red")
    table.add_column("Organization", style="cyan")
    table.add_column("Name")
    table.add_column("Model", style="magenta")
    table.add_column("Serial")
    table.add_column("Status", style="yellow")
    table.add_column("End of Sale")
    table.add_column("End of Support")

    now = datetime.now(timezone.utc)
    for r in rows:
        delta_days = (r["_sort"] - now).days if r["_sort"] != datetime.max.replace(tzinfo=timezone.utc) else None
        closest = f"{delta_days}d" if delta_days is not None else "—"
        table.add_row(
            closest, r["org"], r["name"], r["model"],
            r["serial"], r["status"], r["eos"], r["eosup"],
        )

    Console().print(table)


if __name__ == "__main__":
    main()