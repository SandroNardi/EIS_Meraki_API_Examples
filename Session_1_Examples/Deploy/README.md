# Meraki API Demo Scripts — Network Provisioning

A collection of Python scripts that demonstrate how to use the Cisco Meraki 
Dashboard API to provision new networks and claim devices into them. Built 
for live customer demonstrations and hands-on learning sessions.

---

## Scripts in this folder

| File | Type | What it does |
|------|------|--------------|
| `00_list_orgs_raw.py` | CLI | Fetch and print all organisations (raw JSON) |
| `01_CLI_network_create.py` | CLI | Create a network and claim devices interactively |
| `02_GUI_network_create.py` | Flask GUI | Same workflow as Script 01 in a browser wizard |

---

## Prerequisites

- Python 3.11 or newer
- A Meraki Dashboard API key  
  *(Dashboard → Admin → API access → Generate key)*
- The API key must have read/write access to the target organisation

---

## Installation

```bash
# 1. Clone or download this folder

# 2. (Recommended) Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Authentication

All scripts support two authentication methods:

**Option A — Environment variable (recommended)**
```bash
export MK_CSM_KEY=your_api_key_here      # macOS / Linux
set MK_CSM_KEY=your_api_key_here         # Windows CMD
$env:MK_CSM_KEY="your_api_key_here"      # Windows PowerShell
```

**Option B — Interactive prompt**  
If the environment variable is not set, the CLI script will ask for the 
key at startup. The GUI script shows a paste field in the browser.

---

### Script 01 — Create a network (CLI)

```bash
python 01_CLI_network_create.py
```

**Interactive steps:**
1. Select an organisation from the list
2. Enter a name for the new network
3. Select one security appliance from the unclaimed inventory
4. Select one or more access points from the unclaimed inventory
5. Confirm the summary
6. Network is created and devices are claimed

**Device selection tips:**
- Only devices not yet assigned to a network are shown
- For access points you can select multiple:
  - Single: `2`
  - Comma list: `1,3,5`
  - Range: `2-4`
  - Mixed: `1,3-5`

---

### Script 02 — Create a network (Flask GUI)

```bash
python 02_GUI_network_create.py
```

Opens `http://localhost:8001` in your browser automatically.

**Wizard steps:**
1. Authenticate with your API key
2. Select an organisation
3. Name the network, pick an appliance and one or more APs
4. Review the summary and confirm
5. View the result

> Hold **Ctrl** (Windows/Linux) or **⌘** (Mac) to select multiple APs.

---

## Notes

- The GUI script runs on port `8001` to avoid conflicts with other local services
- All scripts use `suppress_logging=True` on the Meraki SDK to keep terminal 
  output clean and focused on the demo flow
- Inventory filters use the `productType` field (`"appliance"` / `"wireless"`) 
  rather than model name prefixes, so they remain correct as new hardware SKUs 
  are introduced

---

## Folder structure

```
.
├── requirements.txt
├── README.md
├── prompt.md
├── 00_list_orgs_raw.py
├── 01_CLI_network_create.py
└── 02_GUI_network_create.py
```
