"""
Script 5: SSID RADIUS audit with a minimal Flask GUI.

Authentication options (all selectable from the browser):
  - Stored API key (env var MK_CSM_KEY)
  - Manually pasted API key
  - OAuth 2.0 — full setup done from the web page

Run:
    python 05_ssid_radius_audit_oauth.py
    Browser opens at http://localhost:8000
"""

import os
import json
import secrets
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import meraki
import requests
from flask import Flask, redirect, request, render_template_string, session, url_for


# =============================================================================
# CONFIGURATION
# =============================================================================

REDIRECT_URI = "http://localhost:8000/callback"
AUTH_URL = "https://as.meraki.com/oauth/authorize"
TOKEN_URL = "https://as.meraki.com/oauth/token"
STATE_FILE = Path(".meraki_oauth.json")

DEFAULT_SCOPES = [
    "dashboard:general:config:read",
    "wireless:config:read",
]

RADIUS_AUTH_MODES = {"8021x-radius", "open-with-radius", "wpa-eap", "8021x-meraki"}


# =============================================================================
# DEBUG LOG
# In-memory ring buffer that captures every OAuth step. Visible at /debug
# and also printed to the terminal.
# =============================================================================

DEBUG_LOG: list[dict] = []
DEBUG_MAX = 100


def mask(value: str | None, keep: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}...{value[-keep:]} (len={len(value)})"


def log_debug(label: str, payload: dict) -> None:
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "label": label,
        "payload": payload,
    }
    DEBUG_LOG.append(entry)
    if len(DEBUG_LOG) > DEBUG_MAX:
        DEBUG_LOG.pop(0)
    # Also print to terminal so users running the script see it live
    print(f"\n=== [{entry['ts']}] {label} ===")
    print(json.dumps(payload, indent=2, default=str))


# =============================================================================
# STATE PERSISTENCE
# =============================================================================

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))
    try:
        os.chmod(STATE_FILE, 0o600)
    except OSError:
        pass


def update_state(**fields) -> dict:
    state = load_state()
    for k, v in fields.items():
        if v is not None:
            state[k] = v
    save_state(state)
    return state


def wipe_state() -> None:
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def get_scopes() -> list[str]:
    return load_state().get("scopes") or DEFAULT_SCOPES


# =============================================================================
# OAUTH HELPERS  (with full debug logging)
# =============================================================================

def exchange_code(code: str, client_id: str, client_secret: str, scopes: list[str]) -> dict:
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(scopes),
    }
    log_debug("OAuth: token-exchange request", {
        "url": TOKEN_URL,
        "auth_basic_user": mask(client_id),
        "auth_basic_pass": mask(client_secret),
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "form_data": {**payload, "code": mask(payload["code"])},
        "scope_repr": [repr(s) for s in scopes],
    })
    r = requests.post(
        TOKEN_URL,
        auth=(client_id, client_secret),
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    log_debug("OAuth: token-exchange response", {
        "status_code": r.status_code,
        "response_headers": dict(r.headers),
        "response_body": _safe_json(r),
    })
    r.raise_for_status()
    return r.json()


def refresh_access_token(refresh_token: str, client_id: str, client_secret: str) -> dict:
    log_debug("OAuth: refresh-token request", {
        "url": TOKEN_URL,
        "auth_basic_user": mask(client_id),
        "auth_basic_pass": mask(client_secret),
        "form_data": {"grant_type": "refresh_token", "refresh_token": mask(refresh_token)},
    })
    r = requests.post(
        TOKEN_URL,
        auth=(client_id, client_secret),
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    log_debug("OAuth: refresh-token response", {
        "status_code": r.status_code,
        "response_body": _safe_json(r),
    })
    r.raise_for_status()
    return r.json()


def _safe_json(r: requests.Response):
    try:
        return r.json()
    except ValueError:
        return r.text


# =============================================================================
# MERAKI API CLIENTS
# =============================================================================

class BearerClient:
    BASE = "https://api.meraki.com/api/v1"

    def __init__(self, token: str):
        self.headers = {"Authorization": f"Bearer {token}"}

    def get(self, path: str, **params):
        out = []
        url = f"{self.BASE}{path}"
        while url:
            r = requests.get(url, headers=self.headers, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list):
                return data
            out.extend(data)
            url = None
            for part in r.headers.get("Link", "").split(","):
                if 'rel="next"' in part:
                    url = part[part.find("<") + 1:part.find(">")]
                    params = {}
        return out


class ApiKeyClient:
    def __init__(self, api_key: str):
        self.d = meraki.DashboardAPI(api_key, suppress_logging=True)

    def get(self, path: str, **params):
        if path == "/organizations":
            return self.d.organizations.getOrganizations()
        if path.endswith("/networks"):
            org = path.split("/")[2]
            return self.d.organizations.getOrganizationNetworks(org, total_pages="all")
        if path.endswith("/configTemplates"):
            org = path.split("/")[2]
            return self.d.organizations.getOrganizationConfigTemplates(org)
        if path.endswith("/wireless/ssids"):
            net = path.split("/")[2]
            return self.d.wireless.getNetworkWirelessSsids(net)
        raise ValueError(f"Unsupported path: {path}")


# =============================================================================
# AUDIT LOGIC
# =============================================================================

def is_radius_ssid(ssid: dict) -> bool:
    if not ssid.get("enabled"):
        return False
    mode = ssid.get("authMode", "")
    return mode in RADIUS_AUTH_MODES or mode.endswith("-radius")


def run_audit(client, org_id_filter: str | None) -> tuple[list[dict], int]:
    orgs = client.get("/organizations")
    if org_id_filter:
        orgs = [o for o in orgs if o["id"] == org_id_filter]

    findings, total_active = [], 0

    for org in orgs:
        try:
            nets = client.get(f"/organizations/{org['id']}/networks")
        except Exception:
            nets = []
        try:
            tpls = client.get(f"/organizations/{org['id']}/configTemplates")
        except Exception:
            tpls = []

        bindings = {}
        for n in nets:
            tpl_id = n.get("configTemplateId")
            if tpl_id:
                bindings[tpl_id] = bindings.get(tpl_id, 0) + 1

        wireless_nets = [
            n for n in nets
            if "wireless" in n.get("productTypes", []) and not n.get("configTemplateId")
        ]
        wireless_tpls = [t for t in tpls if "wireless" in t.get("productTypes", [])]

        for n in wireless_nets:
            try:
                ssids = client.get(f"/networks/{n['id']}/wireless/ssids")
            except Exception:
                continue
            for s in ssids:
                if s.get("enabled"):
                    total_active += 1
                if is_radius_ssid(s):
                    findings.append({
                        "kind": "Network", "org": org["name"], "scope": n["name"],
                        "bound": "—", "num": s.get("number"), "name": s.get("name", ""),
                        "auth": s.get("authMode", ""),
                        "servers": s.get("radiusServers", []) or [],
                    })

        for t in wireless_tpls:
            try:
                ssids = client.get(f"/networks/{t['id']}/wireless/ssids")
            except Exception:
                continue
            for s in ssids:
                if s.get("enabled"):
                    total_active += 1
                if is_radius_ssid(s):
                    findings.append({
                        "kind": "Template", "org": org["name"], "scope": t["name"],
                        "bound": str(bindings.get(t["id"], 0)),
                        "num": s.get("number"), "name": s.get("name", ""),
                        "auth": s.get("authMode", ""),
                        "servers": s.get("radiusServers", []) or [],
                    })

    return findings, total_active


def make_client_from_session():
    if session.get("access_token"):
        return BearerClient(session["access_token"])
    if session.get("api_key"):
        return ApiKeyClient(session["api_key"])
    return None


# =============================================================================
# FLASK ROUTES
# =============================================================================

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)


@app.route("/")
def index():
    state = load_state()
    return render_template_string(
        TPL_INDEX,
        env_key=bool(os.environ.get("MK_CSM_KEY")),
        scopes=get_scopes(),
        redirect_uri=REDIRECT_URI,
        client_id=state.get("client_id", ""),
        has_secret=bool(state.get("client_secret")),
        has_refresh=bool(state.get("refresh_token")),
    )


@app.post("/use_env")
def use_env():
    session["api_key"] = os.environ.get("MK_CSM_KEY", "")
    return redirect(url_for("orgs"))


@app.post("/use_manual")
def use_manual():
    session["api_key"] = request.form.get("api_key", "").strip()
    return redirect(url_for("orgs"))


@app.post("/save_oauth_creds")
def save_oauth_creds():
    cid = request.form.get("client_id", "").strip()
    csec = request.form.get("client_secret", "").strip()
    scopes_raw = request.form.get("scopes", "").strip()
    # split() with no arg splits on any whitespace and discards empties — safe
    scopes = scopes_raw.split() or None

    log_debug("OAuth: saving credentials", {
        "client_id": mask(cid),
        "client_secret_provided": bool(csec),
        "scopes_raw_repr": repr(scopes_raw),
        "scopes_parsed": scopes,
    })

    fields = {"client_id": cid or None, "scopes": scopes}
    if csec:
        fields["client_secret"] = csec
    update_state(**fields)
    return redirect(url_for("index"))


@app.post("/oauth_start")
def oauth_start():
    state_data = load_state()
    if not state_data.get("client_id") or not state_data.get("client_secret"):
        return redirect(url_for("index"))

    nonce = secrets.token_urlsafe(16)
    session["oauth_state"] = nonce
    scopes = get_scopes()
    session["oauth_scopes"] = scopes

    params = {
        "response_type": "code",
        "client_id": state_data["client_id"],
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(scopes),
        "state": nonce,
    }
    full_url = f"{AUTH_URL}?{urlencode(params)}"

    log_debug("OAuth: authorize redirect", {
        "authorize_endpoint": AUTH_URL,
        "params_sent": {**params, "client_id": mask(params["client_id"])},
        "scope_repr": [repr(s) for s in scopes],
        "scope_string_sent": params["scope"],
        "full_url_masked": full_url.replace(state_data["client_id"], mask(state_data["client_id"])),
    })
    return redirect(full_url)


@app.route("/callback")
def callback():
    log_debug("OAuth: callback received", {
        "query_args": dict(request.args),
    })

    if request.args.get("state") != session.get("oauth_state"):
        return render_template_string(
            TPL_ERROR,
            error="State mismatch",
            description="The 'state' parameter returned by Meraki does not match the one we sent. "
                        "This is usually a session/cookie issue — try again from /.",
        ), 400

    code = request.args.get("code")
    if not code:
        err = request.args.get("error", "missing code")
        desc = request.args.get("error_description", "")
        hints = _hints_for_oauth_error(err)
        return render_template_string(
            TPL_ERROR, error=f"OAuth error: {err}", description=desc, hints=hints,
        ), 400

    state_data = load_state()
    scopes = session.get("oauth_scopes") or get_scopes()

    try:
        tokens = exchange_code(
            code, state_data["client_id"], state_data["client_secret"], scopes
        )
    except requests.HTTPError as e:
        return render_template_string(
            TPL_ERROR,
            error="Token exchange failed",
            description=e.response.text,
            hints=_hints_for_oauth_error("invalid_scope"),
        ), 400

    update_state(refresh_token=tokens.get("refresh_token"))
    session["access_token"] = tokens["access_token"]
    return redirect(url_for("orgs"))


@app.post("/use_refresh")
def use_refresh():
    state_data = load_state()
    if not state_data.get("refresh_token"):
        return redirect(url_for("index"))
    try:
        new = refresh_access_token(
            state_data["refresh_token"],
            state_data["client_id"],
            state_data["client_secret"],
        )
    except requests.HTTPError as e:
        return render_template_string(
            TPL_ERROR, error="Refresh failed", description=e.response.text
        ), 400

    update_state(refresh_token=new.get("refresh_token"))
    session["access_token"] = new["access_token"]
    return redirect(url_for("orgs"))


@app.post("/drop_refresh")
def drop_refresh():
    state_data = load_state()
    state_data.pop("refresh_token", None)
    save_state(state_data)
    session.clear()
    return redirect(url_for("index"))


@app.post("/reset_oauth")
def reset_oauth():
    wipe_state()
    session.clear()
    return redirect(url_for("index"))


@app.route("/orgs")
def orgs():
    client = make_client_from_session()
    if client is None:
        return redirect(url_for("index"))
    try:
        orgs_list = client.get("/organizations")
    except requests.HTTPError as e:
        return render_template_string(
            TPL_ERROR, error="API error", description=str(e)
        ), 400
    return render_template_string(TPL_ORGS, orgs=orgs_list)


@app.post("/run")
def run():
    client = make_client_from_session()
    if client is None:
        return redirect(url_for("index"))
    org_id = request.form.get("org_id") or None
    findings, total = run_audit(client, org_id)
    return render_template_string(TPL_RESULTS, findings=findings, total_active=total)


# ---------- Debug routes ----------

@app.route("/debug")
def debug():
    state = load_state()
    scopes = get_scopes()
    preview_params = {
        "response_type": "code",
        "client_id": state.get("client_id", "<missing>"),
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(scopes),
        "state": "<generated-at-runtime>",
    }
    preview_url = f"{AUTH_URL}?{urlencode(preview_params)}"

    return render_template_string(
        TPL_DEBUG,
        state_view={
            "client_id": mask(state.get("client_id", "")),
            "client_secret": mask(state.get("client_secret", "")),
            "scopes": state.get("scopes"),
            "refresh_token": mask(state.get("refresh_token", "")),
        },
        active_scopes=scopes,
        active_scopes_repr=[repr(s) for s in scopes],
        preview_params=preview_params,
        preview_url=preview_url.replace(
            state.get("client_id") or "###", mask(state.get("client_id", ""))
        ),
        log=list(reversed(DEBUG_LOG)),
    )


@app.post("/debug/clear")
def debug_clear():
    DEBUG_LOG.clear()
    return redirect(url_for("debug"))


def _hints_for_oauth_error(err: str) -> list[str]:
    if err == "invalid_scope":
        return [
            "The scope string in the request contains a name not enabled on this integration.",
            "Open integrate.cisco.com → your application → check the EXACT scope names ticked.",
            "Copy them character-by-character into the 'Scopes' field on the home page.",
            "Watch out for typos: 'config:read' (correct) vs 'configread' or 'read' (wrong).",
            "Watch out for invisible whitespace when copy/pasting.",
            "If the integration is in 'Pending approval' state, scopes may be rejected.",
            "Visit /debug to see exactly what was sent.",
        ]
    if err == "invalid_client":
        return [
            "The client_id or client_secret is wrong.",
            "Re-check at integrate.cisco.com and re-paste them on the home page.",
        ]
    if err == "redirect_uri_mismatch":
        return [
            f"Make sure the integration has redirect URI '{REDIRECT_URI}' registered exactly.",
        ]
    return ["Visit /debug to see the full request/response details."]


# =============================================================================
# HTML TEMPLATES
# =============================================================================

TPL_BASE_CSS = """
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 960px;
         margin: 2em auto; padding: 0 1em; color: #222; background: #f7f8fa; }
  h1 { color: #1ba0d7; border-bottom: 2px solid #1ba0d7; padding-bottom: .3em; }
  h2 { color: #333; margin-top: 0; }
  .card { background: white; border-radius: 8px; padding: 1.5em;
          box-shadow: 0 2px 8px rgba(0,0,0,.06); margin-bottom: 1em; }
  .btn { display: inline-block; padding: .6em 1.2em; border-radius: 6px;
         text-decoration: none; font-weight: 600; border: none; cursor: pointer;
         margin-right: .5em; font-size: .95em; }
  .btn-primary { background: #1ba0d7; color: white; }
  .btn-secondary { background: #6c757d; color: white; }
  .btn-danger { background: #dc3545; color: white; }
  .btn:hover { opacity: .85; }
  input[type=text], input[type=password], select {
         width: 100%; padding: .6em; border: 1px solid #ccc;
         border-radius: 4px; box-sizing: border-box; font-size: .95em; }
  label { font-weight: 600; display: block; margin-top: .8em; }
  table { width: 100%; border-collapse: collapse; background: white; }
  th, td { padding: .6em; text-align: left; border-bottom: 1px solid #eee; font-size: .9em; }
  th { background: #1ba0d7; color: white; }
  tr:hover { background: #f0f8ff; }
  .badge { display: inline-block; padding: .2em .6em; border-radius: 4px;
           font-size: .8em; font-weight: 600; }
  .badge-net { background: #e7f5ff; color: #1971c2; }
  .badge-tpl { background: #fff4e6; color: #e8590c; }
  .scope { background: #f1f3f5; padding: .4em .8em; border-radius: 4px;
           font-family: monospace; display: inline-block; margin: .2em 0; }
  .muted { color: #888; font-size: .9em; }
  .ok { color: #2b8a3e; font-weight: 600; }
  .warn { color: #e8590c; font-weight: 600; }
  .err { color: #c92a2a; font-weight: 600; }
  code { background: #f1f3f5; padding: .15em .4em; border-radius: 3px; }
  hr { border: none; border-top: 1px solid #e9ecef; margin: 1.5em 0; }
  pre { background: #1e1e1e; color: #d4d4d4; padding: 1em; border-radius: 4px;
        overflow-x: auto; font-size: .85em; }
  .nav { margin-bottom: 1em; }
  .nav a { margin-right: 1em; }
</style>
"""

TPL_NAV = """
<div class="nav">
  <a href="/">🏠 Home</a>
  <a href="/debug">🐞 Debug</a>
</div>
"""

TPL_INDEX = TPL_BASE_CSS + TPL_NAV + """
<h1>🌐 Meraki SSID RADIUS Auditor</h1>

<div class="card">
  <h2>Option 1 — API key</h2>
  {% if env_key %}
    <form method="post" action="/use_env">
      <p>✅ Detected env var <code>MK_CSM_KEY</code>.</p>
      <button class="btn btn-primary">Use stored API key</button>
    </form>
  {% else %}
    <p class="muted">No <code>MK_CSM_KEY</code> environment variable detected.</p>
  {% endif %}
  <form method="post" action="/use_manual">
    <label>Or paste an API key:</label>
    <input type="password" name="api_key" placeholder="Meraki API key">
    <br><br>
    <button class="btn btn-secondary">Use this key</button>
  </form>
</div>

<div class="card">
  <h2>Option 2 — OAuth 2.0</h2>

  <p><b>Redirect URI to register at integrate.cisco.com:</b></p>
  <p><code>{{ redirect_uri }}</code></p>

  <form method="post" action="/save_oauth_creds">
    <label>Client ID</label>
    <input type="text" name="client_id" value="{{ client_id }}"
           placeholder="from integrate.cisco.com">

    <label>Client Secret</label>
    <input type="password" name="client_secret"
           placeholder="{{ 'leave blank to keep existing' if has_secret else 'from integrate.cisco.com' }}">

    <label>Scopes (space-separated, must match the portal exactly)</label>
    <input type="text" name="scopes" value="{{ scopes|join(' ') }}">

    <br><br>
    <button class="btn btn-secondary">Save credentials & scopes</button>
  </form>

  <hr>

  <p><b>Currently configured scopes:</b></p>
  {% for s in scopes %}<div class="scope">{{ s }}</div>{% endfor %}

  <hr>

  {% if not client_id or not has_secret %}
    <p class="warn">⚠ Save your Client ID and Client Secret above before authorizing.</p>
  {% else %}
    <p class="ok">✅ Client credentials saved.</p>

    {% if has_refresh %}
      <form method="post" action="/use_refresh" style="display:inline">
        <button class="btn btn-primary">Use stored refresh token</button>
      </form>
      <form method="post" action="/drop_refresh" style="display:inline">
        <button class="btn btn-danger">Drop refresh token & re-authorize</button>
      </form>
    {% else %}
      <form method="post" action="/oauth_start">
        <button class="btn btn-primary">Authorize via OAuth</button>
      </form>
    {% endif %}

    <form method="post" action="/reset_oauth" style="display:inline; margin-left:1em;">
      <button class="btn btn-danger">Reset OAuth setup (wipe everything)</button>
    </form>
  {% endif %}
</div>
"""

TPL_ORGS = TPL_BASE_CSS + TPL_NAV + """
<h1>Select scope</h1>
<div class="card">
  <form method="post" action="/run">
    <label>Organization:</label>
    <select name="org_id">
      <option value="">— ALL organizations —</option>
      {% for o in orgs %}
      <option value="{{ o.id }}">{{ o.name }} ({{ o.id }})</option>
      {% endfor %}
    </select>
    <br><br>
    <button class="btn btn-primary">Run audit</button>
    <a href="/" class="btn btn-secondary">Back</a>
  </form>
</div>
"""

TPL_RESULTS = TPL_BASE_CSS + TPL_NAV + """
<h1>Audit results</h1>
<div class="card">
  <p><b>Total active SSIDs scanned:</b> {{ total_active }}</p>
  <p><b>RADIUS-enabled SSIDs:</b> {{ findings|length }}</p>
  <a href="/orgs" class="btn btn-secondary">↩ Back</a>
  <a href="/" class="btn btn-secondary">Logout / change auth</a>
</div>

<table>
  <tr>
    <th>Source</th><th>Organization</th><th>Network / Template</th>
    <th>Bound nets</th><th>SSID #</th><th>SSID name</th>
    <th>Auth mode</th><th>RADIUS servers</th>
  </tr>
  {% for f in findings %}
  <tr>
    <td>
      {% if f.kind == 'Template' %}
        <span class="badge badge-tpl">Template</span>
      {% else %}
        <span class="badge badge-net">Network</span>
      {% endif %}
    </td>
    <td>{{ f.org }}</td><td>{{ f.scope }}</td>
    <td>{{ f.bound }}</td><td>{{ f.num }}</td><td>{{ f.name }}</td>
    <td>{{ f.auth }}</td>
    <td>
      {% for s in f.servers %}{{ s.host }}:{{ s.port }}<br>{% endfor %}
    </td>
  </tr>
  {% endfor %}
</table>
"""

TPL_ERROR = TPL_BASE_CSS + TPL_NAV + """
<h1>OAuth / API error</h1>
<div class="card">
  <p class="err">{{ error }}</p>
  {% if description %}<pre>{{ description }}</pre>{% endif %}

  {% if hints %}
  <h2>Possible causes</h2>
  <ul>
    {% for h in hints %}<li>{{ h }}</li>{% endfor %}
  </ul>
  {% endif %}

  <a href="/debug" class="btn btn-primary">Open debug page</a>
  <a href="/" class="btn btn-secondary">Back to home</a>
</div>
"""

TPL_DEBUG = TPL_BASE_CSS + TPL_NAV + """
<h1>🐞 OAuth Debug</h1>

<div class="card">
  <h2>Persisted state (.meraki_oauth.json)</h2>
  <pre>{{ state_view | tojson(indent=2) }}</pre>
</div>

<div class="card">
  <h2>Active scopes</h2>
  <p><b>List:</b></p>
  {% for s in active_scopes %}<div class="scope">{{ s }}</div>{% endfor %}
  <p><b>Python repr (use this to spot hidden whitespace or invisible chars):</b></p>
  <pre>{{ active_scopes_repr | tojson(indent=2) }}</pre>
</div>

<div class="card">
  <h2>Preview of NEXT authorize request</h2>
  <p><b>Endpoint:</b> <code>https://as.meraki.com/oauth/authorize</code></p>
  <p><b>Parameters that will be sent:</b></p>
  <pre>{{ preview_params | tojson(indent=2) }}</pre>
  <p><b>Resulting URL (client_id masked):</b></p>
  <pre>{{ preview_url }}</pre>
</div>

<div class="card">
  <h2>Recent OAuth events ({{ log|length }})</h2>
  <form method="post" action="/debug/clear" style="display:inline">
    <button class="btn btn-danger">Clear log</button>
  </form>
  <br><br>
  {% for entry in log %}
    <p><b>[{{ entry.ts }}]</b> {{ entry.label }}</p>
    <pre>{{ entry.payload | tojson(indent=2) }}</pre>
  {% else %}
    <p class="muted">No events logged yet.</p>
  {% endfor %}
</div>
"""


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("Open http://localhost:8000 in your browser")
    print("Debug page available at http://localhost:8000/debug")
    webbrowser.open("http://localhost:8000")
    app.run(host="127.0.0.1", port=8000, debug=False)