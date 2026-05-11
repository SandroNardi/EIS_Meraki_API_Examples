"""
Script 2: CLI — Create a network and claim devices into it.

Steps:
    1. Authenticate
    2. Pick an organisation
    3. Enter a name for the new network
    4. Pick a security appliance (MX / Z series) from inventory
    5. Pick one or more access points (MR series) from inventory
    6. Create the network
    7. Claim the selected devices into it

Usage:
    export MK_CSM_KEY=your_api_key   # optional
    python 02_create_network_cli.py
"""

import os
import json
import getpass
import meraki


# =============================================================================
# STEP 1 — Authenticate
# =============================================================================

def get_api_key():
    key = os.environ.get("MK_CSM_KEY")
    if not key:
        key = getpass.getpass("Enter your Meraki API key: ").strip()
    return key


# =============================================================================
# HELPER — Print a numbered list and ask the user to pick one item
# =============================================================================

def pick_one(label, items):
    """
    Print a numbered list of dicts and return the one the user picks.
    'label' is the dict key used as the display name.
    """
    print()
    for i, item in enumerate(items, start=1):
        print(f"  [{i}] {item[label]}")
    print()

    while True:
        choice = input(f"Enter a number [1-{len(items)}]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(items):
            return items[int(choice) - 1]
        print("  Invalid choice, please try again.")


# =============================================================================
# HELPER — Same as above but the user can pick multiple items
# =============================================================================

def pick_many(label, items):
    """
    Print a numbered list and return one or more items.
    The user can type  '1'  or  '1,3'  or  '2-4'  or any mix.
    """
    print()
    for i, item in enumerate(items, start=1):
        print(f"  [{i}] {item[label]}")
    print()
    print("  You can select multiple items, e.g.:  1,3   or   2-4   or   1,3-5")

    while True:
        raw = input(f"Enter selection [1-{len(items)}]: ").strip()

        chosen_indices = set()
        valid = True

        for part in raw.split(","):
            part = part.strip()

            # Range like "2-4"
            if "-" in part:
                bounds = part.split("-", 1)
                if bounds[0].isdigit() and bounds[1].isdigit():
                    lo, hi = int(bounds[0]), int(bounds[1])
                    if 1 <= lo <= hi <= len(items):
                        chosen_indices.update(range(lo, hi + 1))
                    else:
                        valid = False
                else:
                    valid = False

            # Single number like "1"
            elif part.isdigit() and 1 <= int(part) <= len(items):
                chosen_indices.add(int(part))

            else:
                valid = False

        if valid and chosen_indices:
            return [items[i - 1] for i in sorted(chosen_indices)]

        print("  Invalid selection, please try again.")


# =============================================================================
# MAIN
# =============================================================================

def main():

    # -------------------------------------------------------------------------
    # Step 1 — Connect to the Meraki dashboard
    # -------------------------------------------------------------------------
    api_key   = get_api_key()
    dashboard = meraki.DashboardAPI(api_key, suppress_logging=True)


    # -------------------------------------------------------------------------
    # Step 2 — Pick an organisation
    # -------------------------------------------------------------------------
    print("\n--- Step 2: Select an Organisation ---")

    orgs = dashboard.organizations.getOrganizations()

    # Add a display label to each org for pick_one()
    for org in orgs:
        org["label"] = f"{org['name']}  (id: {org['id']})"

    chosen_org = pick_one("label", orgs)
    org_id     = chosen_org["id"]
    print(f"\n  Selected: {chosen_org['name']}")


    # -------------------------------------------------------------------------
    # Step 3 — Enter a name for the new network
    # -------------------------------------------------------------------------
    print("\n--- Step 3: Name the New Network ---")

    while True:
        net_name = input("  Network name: ").strip()
        if net_name:
            break
        print("  Name cannot be empty, please try again.")


    # -------------------------------------------------------------------------
    # Step 4 — Pick a security appliance from inventory
    #
    # We only show devices that:
    #   - are MX or Z series  (security appliances / teleworker gateways)
    #   - are NOT already assigned to a network  (networkId is None)
    # -------------------------------------------------------------------------
    print("\n--- Step 4: Select a Security Appliance ---")
    print("  Fetching inventory …")

    inventory = dashboard.organizations.getOrganizationInventoryDevices(
        org_id, total_pages="all"
    )

    appliances = [
        d for d in inventory
        if d.get("networkId") is None
        and d.get("productType") == "appliance"
    ]

    if not appliances:
        print("  No unclaimed security appliances found. Exiting.")
        return

    # Add a display label to each device
    for d in appliances:
        d["label"] = f"{d['model']}  —  serial: {d['serial']}"

    chosen_appliance = pick_one("label", appliances)
    print(f"\n  Selected: {chosen_appliance['label']}")


    # -------------------------------------------------------------------------
    # Step 5 — Pick one or more access points from inventory
    #
    # We only show devices that:
    #   - are MR series  (wireless access points)
    #   - are NOT already assigned to a network  (networkId is None)
    # -------------------------------------------------------------------------
    print("\n--- Step 5: Select Access Point(s) ---")

    aps = [
            d for d in inventory
            if d.get("networkId") is None
            and d.get("productType") == "wireless"
        ]

    if not aps:
        print("  No unclaimed access points found. Exiting.")
        return

    for d in aps:
        d["label"] = f"{d['model']}  —  serial: {d['serial']}"

    chosen_aps = pick_many("label", aps)
    print(f"\n  Selected {len(chosen_aps)} access point(s).")


    # -------------------------------------------------------------------------
    # Step 6 — Confirm before making any changes
    # -------------------------------------------------------------------------
    print("\n--- Step 6: Confirm ---")
    print(f"  Organisation : {chosen_org['name']}")
    print(f"  Network name : {net_name}")
    print(f"  Appliance    : {chosen_appliance['label']}")
    print(f"  Access points: {', '.join(d['serial'] for d in chosen_aps)}")
    print()

    confirm = input("  Create network and claim devices? [y/N]: ").strip().lower()
    if confirm != "y":
        print("  Cancelled.")
        return


    # -------------------------------------------------------------------------
    # Step 7 — Create the network
    #
    # productTypes tells Meraki which feature sets to enable.
    # We use both 'appliance' and 'wireless' because we are claiming
    # an MX and MR devices into the same network.
    # -------------------------------------------------------------------------
    print("\n--- Step 7: Creating Network ---")

    new_network = dashboard.organizations.createOrganizationNetwork(
        org_id,
        name=net_name,
        productTypes=["appliance", "wireless"],
    )
    net_id = new_network["id"]
    print(f"  Network created  —  id: {net_id}")


    # -------------------------------------------------------------------------
    # Step 8 — Claim all selected devices into the new network
    # -------------------------------------------------------------------------
    print("\n--- Step 8: Claiming Devices ---")

    serials_to_claim = [chosen_appliance["serial"]] + [d["serial"] for d in chosen_aps]

    dashboard.networks.claimNetworkDevices(net_id, serials=serials_to_claim)

    print(f"  Claimed {len(serials_to_claim)} device(s) into '{net_name}'.")
    print("\n  Done!")
    print(json.dumps(new_network, indent=2))


if __name__ == "__main__":
    main()