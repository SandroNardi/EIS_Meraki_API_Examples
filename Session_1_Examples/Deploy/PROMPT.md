
# AI Prompt — Meraki Network Provisioning Scripts

Use the prompt below to recreate the two demo scripts from scratch using 
any AI coding assistant. Copy and paste the entire block.

---

```
You are an expert Python developer with deep knowledge of the Cisco Meraki 
Dashboard API and the official Meraki Python SDK.

Write two Python scripts that demonstrate network provisioning via the 
Meraki API. The scripts share the same workflow but use different interfaces.
Both scripts must be written to be as simple, readable, and instructional as 
possible — they are teaching material, not production code.

---

## Shared workflow

1. Authenticate using a Meraki Dashboard API key
   - First check for an environment variable called MK_CSM_KEY
   - If not found, prompt the user to enter it

2. Let the user select an organisation from the list returned by
   GET /organizations

3. Ask for a name for the new network

4. Show all unclaimed security appliances in the organisation inventory
   - Use GET /organizations/{orgId}/inventory/devices
   - Filter for:  networkId == null  AND  productType == "appliance"
   - Let the user select exactly one

5. Show all unclaimed access points in the organisation inventory
   - Same endpoint and networkId filter
   - Filter for:  productType == "wireless"
   - Let the user select one or more

6. Show a summary and ask the user to confirm before making any changes

7. Create the network using POST /organizations/{orgId}/networks
   - productTypes must include both "appliance" and "wireless"

8. Claim all selected devices into the new network using
   POST /networks/{networkId}/devices/claim
   - Pass the list of serials in the request body

---

## Script 1 — CLI (file: 01_CLI_network_create.py)

- Pure Python, no GUI framework
- Use the official meraki SDK:  meraki.DashboardAPI(api_key, suppress_logging=True)
- Print a clearly numbered step header before each step,
  e.g. "--- Step 2: Select Organisation ---"
- For single selection: print a numbered list and accept a number input
- For multi selection: accept a comma-separated list, ranges (e.g. 2-4),
  or a mix (e.g. 1,3-5)
- Add an inline comment above every non-obvious line of code
- Do not use type annotations
- Do not use classes
- All logic lives inside a single main() function, called at the bottom with:
  if __name__ == "__main__":
      main()

---

## Script 2 — Flask GUI (file: 02_GUI_network_create.py)

- Use Flask for the web interface
- Use render_template_string (no external template files)
- Run on port 8001
- Open the browser automatically using webbrowser.open()
- Store state between pages using Flask session
- Structure as a linear wizard with these pages:
    Page 1 — Authentication (env key detected or paste manually)
    Page 2 — Select organisation
    Page 3 — Name network, select appliance (dropdown), select APs (multi-select)
    Page 4 — Confirm summary (all values passed as hidden form fields)
    Page 5 — Result showing the new network details
- Include a shared CSS block and a small navigation link on every page after login
- Use a shared error page template for all failure cases
- Add an inline comment above every non-obvious line of code
- Do not use type annotations
- Keep helper functions minimal — only define one if the same logic is needed
  in three or more places

---

## Requirements for both scripts

- Clean, minimal code — no unnecessary abstractions
- No type annotations
- No external template files
- No database or file storage
- Comments explain the WHY, not just the what
- Every Meraki API call must be inside a try/except block
- Use the meraki SDK where possible
- Dependencies: meraki>=1.48.0, flask>=3.0.0
- Compatible with Python 3.11+
