# Meraki API Learning Journey

A series of short, self-contained Python scripts that progressively introduce
the Meraki Dashboard API. Each script lives in **one file** and is meant to be
read top-to-bottom by attendees and (later) fed to AI assistants as a starting
template for their own projects.

---

## What each script does

| # | File | What it teaches |
|---|------|-----------------|
| 1 | `01_list_orgs_raw.py` | Authenticate and fetch organizations — raw JSON output |
| 2 | `02_list_orgs_rich.py` | Same call, presented in a Rich console table |
| 3 | `03_inventory_eol.py` | List inventory devices with End-of-Sale / End-of-Support data, sorted by closest event |
| 4 | `04_ssid_radius_audit.py` | Audit SSIDs across networks **and** configuration templates; find those using RADIUS |
| 5 | `05_ssid_radius_audit_oauth.py` | Same audit as #4, exposed through a small Flask web UI that supports API key, manual key, **and OAuth 2.0** |

---

## How to use — step-by-step (zero prior experience required)

### 1. Install Python 3.10 or newer

- **Windows / macOS:** download from <https://www.python.org/downloads/>
- **Linux:** `sudo apt install python3 python3-venv` (Debian/Ubuntu)

Verify:
```bash
python3 --version
```

### 2. Get the project files

Download or clone this folder so all scripts sit in the same directory.

### 3. Create a virtual environment (recommended)

```bash
cd path/to/this/folder
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\activate             # Windows PowerShell
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Get a Meraki API key

1. Log into <https://dashboard.meraki.com>.
2. Click your profile → **My profile**.
3. Scroll to **API access** and generate a key.
4. Copy it somewhere safe — you'll only see it once.

### 6. Provide the API key to the scripts

You have two options:

**Option A — environment variable (recommended)**

macOS / Linux:
```bash
export MK_CSM_KEY="paste_your_key_here"
```

Windows PowerShell:
```powershell
$env:MK_CSM_KEY = "paste_your_key_here"
```

**Option B — paste at runtime**

Just run a script without setting the variable — it will prompt you.

### 7. Run scripts 1 to 4

```bash
python 01_list_orgs_raw.py
python 02_list_orgs_rich.py
python 03_inventory_eol.py
python 04_ssid_radius_audit.py
```

Scripts 3 and 4 will ask you to pick an organization (or `0` for all).

---

## Script 5 — using OAuth 2.0 from the browser

Script 5 launches a local web app at <http://localhost:8000>. You can
authenticate three ways: **stored API key**, **manual API key**, or **OAuth**.
**Everything for OAuth — including the first-time setup — is done from the
web page itself.** No environment variables are needed.

### Step 1 — Register an OAuth integration (one time)

1. Go to <https://integrate.cisco.com> and sign in with your Cisco.com account.
2. Click **Create new application**.
3. Fill in:
   - **Name:** anything, e.g. "Meraki Demo Auditor"
   - **Redirect URI:** `http://localhost:8000/callback`
   - **Scopes:** select
     - `dashboard:general:config:read`
     - `wireless:config:read`
4. Save. Copy the **Client ID** and **Client Secret** (the secret is shown only once).

> ⚠ **Important — scope name pitfall**
>
> The Meraki authorization server rejects unknown scope names with
> `invalid_scope` and an opaque error message. The names that actually work
> are exactly those listed above:
>
> - `dashboard:general:config:read`
> - `wireless:config:read`
>
> Names like `dashboard:wireless:config:read` (with `dashboard:` as a prefix
> on the wireless scope) are **not** recognized and will fail. If you see
> `invalid_scope`, verify that the scope strings you ticked at
> integrate.cisco.com match the strings in the form on the home page —
> character by character.

### Step 2 — Launch the script

```bash
python 05_ssid_radius_audit_oauth.py
```

The browser opens at <http://localhost:8000>. The terminal will start
printing every OAuth-related event live, which is helpful while you learn.

### Step 3 — Configure OAuth from the web page

1. Scroll to the **OAuth 2.0** card.
2. Paste your **Client ID** and **Client Secret** in the form.
3. Verify the **Scopes** field contains exactly the scopes you registered at
   integrate.cisco.com. Defaults are pre-filled, but you can edit the field.
4. Click **Save credentials & scopes**.
5. Click **Authorize via OAuth**. You will be redirected to Meraki to grant
   access, then back to the app.
6. The app stores your refresh token automatically. Next time you launch the
   script, click **Use stored refresh token** to skip re-authorization.

### Buttons explained

| Button | What it does |
|--------|--------------|
| **Save credentials & scopes** | Stores Client ID / Secret / scopes in `.meraki_oauth.json` |
| **Authorize via OAuth** | Starts a fresh OAuth grant flow |
| **Use stored refresh token** | Gets a new access token using the saved refresh token |
| **Drop refresh token & re-authorize** | Forces a fresh OAuth flow, keeps client credentials |
| **Reset OAuth setup** | Deletes everything (client credentials, scopes, refresh token) |

### Where is everything stored?

A single local file: `.meraki_oauth.json` next to the script (file mode `600`
on Unix). It can contain:

```json
{
  "client_id": "...",
  "client_secret": "...",
  "scopes": ["dashboard:general:config:read", "wireless:config:read"],
  "refresh_token": "..."
}
```

> ⚠ **Note:** Refresh tokens are auto-revoked by Meraki after **90 days of
> inactivity**. Access tokens expire after **60 minutes** and are refreshed
> automatically by the script.

---

## Troubleshooting OAuth — the `/debug` page

Script 5 ships with a built-in debug page available at
<http://localhost:8000/debug>. It shows:

- **Persisted state** — the contents of `.meraki_oauth.json` with secrets
  masked.
- **Active scopes** — both as a clean list and as Python `repr()` so you can
  spot hidden whitespace or invisible Unicode characters from copy-paste.
- **Preview of the next authorize request** — the exact parameters that
  *would* be sent if you clicked **Authorize via OAuth** right now.
- **Recent OAuth events** — a ring buffer of the last 100 OAuth steps:
  authorize redirect, callback, token exchange request and response,
  refresh-token request and response. Secrets are masked.

If something fails, the error page links directly to `/debug`. The same
information is also printed live to the terminal where the script is running.

### Most common OAuth errors

| Error | Likely cause | Fix |
|-------|--------------|-----|
| `invalid_scope` | A scope name you sent is not enabled (or doesn't exist) on the integration | Compare the **Active scopes** on `/debug` with the scopes ticked on integrate.cisco.com. Update the **Scopes** field on the home page if needed. |
| `invalid_client` | Wrong Client ID or Client Secret | Re-paste both on the home page. |
| `redirect_uri_mismatch` | The redirect URI registered at integrate.cisco.com is not exactly `http://localhost:8000/callback` | Update the integration to use that exact URI. |
| `state mismatch` | Browser session lost between authorize and callback (e.g. cookie blocked) | Start over from the home page. |

---

## Common questions

**Q: Can I run script 3 without seeing EoL data?**
EoL data comes from Meraki's `getOrganizationInventoryDevices` endpoint inside
the `eox` field. If your devices have not yet been declared end-of-sale, the
table will simply be empty.

**Q: Why does script 4 list templates separately from networks?**
Networks bound to a configuration template inherit their SSIDs from the
template. To avoid duplicates, the script reads SSIDs from the template
itself and tells you how many networks are bound to it.

**Q: I get a `403` or `401` error from a Meraki API call.**
Check that your API key is correct, that API access is enabled on the
organization (Organization → Settings → Dashboard API access), and that the
OAuth integration is authorized on the org you are querying.

**Q: My OAuth flow returns `invalid_scope` even though my scopes look right.**
Open <http://localhost:8000/debug> and look at the **Python repr** of the
active scopes. Trailing spaces, non-breaking spaces, or extra characters from
copy-paste are common causes. Re-type the scopes by hand if in doubt.

---

## File layout

```
.
├── 01_list_orgs_raw.py
├── 02_list_orgs_rich.py
├── 03_inventory_eol.py
├── 04_ssid_radius_audit.py
├── 05_ssid_radius_audit_oauth.py
├── requirements.txt
├── README.md
└── PROMPT.md
```

---

## License & disclaimer

These scripts are educational examples shared for a workshop. They favour
readability over completeness. Use them as a starting point, not as a
production-ready tool.