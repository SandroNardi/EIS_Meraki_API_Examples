"""
Script 2: List Meraki organizations with a Rich-formatted table.

Usage:
    export MK_CSM_KEY=your_api_key   # optional
    python 02_list_orgs_rich.py
"""

import os
import getpass
import meraki
from rich.console import Console
from rich.table import Table


def get_api_key() -> str:
    key = os.environ.get("MK_CSM_KEY")
    if not key:
        key = getpass.getpass("Enter your Meraki API key: ").strip()
    return key


def main() -> None:
    console = Console()
    dashboard = meraki.DashboardAPI(get_api_key(), suppress_logging=True)

    with console.status("[bold green]Fetching organizations..."):
        orgs = dashboard.organizations.getOrganizations()

    table = Table(title=f"Meraki Organizations ({len(orgs)})", show_lines=False)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("ID", style="magenta")
    table.add_column("URL", style="blue")
    table.add_column("API", justify="center")
    table.add_column("Licensing", style="yellow")

    for org in orgs:
        api_enabled = "✅" if org.get("api", {}).get("enabled") else "❌"
        table.add_row(
            org.get("name", ""),
            org.get("id", ""),
            org.get("url", ""),
            api_enabled,
            org.get("licensing", {}).get("model", "—"),
        )

    console.print(table)


if __name__ == "__main__":
    main()