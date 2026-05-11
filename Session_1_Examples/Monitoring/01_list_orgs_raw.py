"""
Script 1: Fetch and print the raw list of Meraki organizations.

Usage:
    export MK_CSM_KEY=your_api_key   # optional
    python 01_list_orgs_raw.py
"""

import os
import json
import getpass
import meraki


def get_api_key() -> str:
    key = os.environ.get("MK_CSM_KEY")
    if not key:
        key = getpass.getpass("Enter your Meraki API key: ").strip()
    return key


def main() -> None:
    api_key = get_api_key()
    dashboard = meraki.DashboardAPI(api_key, suppress_logging=True)
    orgs = dashboard.organizations.getOrganizations()
    print(json.dumps(orgs, indent=2))


if __name__ == "__main__":
    main()