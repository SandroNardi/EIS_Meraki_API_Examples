"""
Script 3: Flask GUI — Create a network and claim devices into it.

Same workflow as Script 2 but in a minimal browser-based wizard:
    Page 1 — Authenticate (env key or paste)
    Page 2 — Pick an organisation
    Page 3 — Name the network, pick appliance and APs
    Page 4 — Confirm summary
    Page 5 — Result

Run:
    python 03_create_network_gui.py
    Browser opens at http://localhost:8001
"""

import os
import json
import secrets
import webbrowser

import meraki
from flask import Flask, redirect, request, render_template_string, session, url_for


# =============================================================================
# APP SETUP
# =============================================================================

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)


# =============================================================================
# SHARED CSS — used on every page
# =============================================================================

CSS = """
<style>
  body  { font-family: -apple-system, Segoe UI, sans-serif; max-width: 800px;
          margin: 2em auto; padding: 0 1em; background: #f7f8fa; color: #222; }
  h1    { color: #1ba0d7; border-bottom: 2px solid #1ba0d7; padding-bottom: .3em; }
  .card { background: white; border-radius: 8px; padding: 1.5em;
          box-shadow: 0 2px 8px rgba(0,0,0,.07); margin-bottom: 1em; }
  .btn  { display: inline-block; padding: .55em 1.2em; border-radius: 6px;
          font-weight: 600; border: none; cursor: pointer;
          text-decoration: none; font-size: .95em; margin-right: .4em; }
  .primary   { background: #1ba0d7; color: white; }
  .secondary { background: #6c757d; color: white; }
  .success   { background: #2b8a3e; color: white; }
  .btn:hover { opacity: .85; }
  input[type=text], input[type=password], select {
          width: 100%; padding: .55em; border: 1px solid #ccc;
          border-radius: 4px; box-sizing: border-box; font-size: .95em; }
  select[multiple] { min-height: 9em; }
  label { font-weight: 600; display: block; margin-top: .9em; }
  .hint { font-size: .85em; color: #666; margin-top: .25em; }
  .ok   { color: #2b8a3e; font-weight: 600; }
  .err  { color: #c92a2a; font-weight: 600; }
  code  { background: #f1f3f5; padding: .15em .4em; border-radius: 3px; }
  pre   { background: #1e1e1e; color: #d4d4d4; padding: 1em;
          border-radius: 6px; overflow-x: auto; font-size: .85em; }
  ul    { line-height: 2; }
</style>
"""

# Small breadcrumb shown on every page after login
NAV = '<p style="margin-bottom:1.5em"><a href="/">🏠 Home / logout</a></p>'


# =============================================================================
# PAGE 1 — Authentication
# =============================================================================

PAGE_AUTH = CSS + """
<h1>🔧 Create Network &amp; Claim Devices</h1>
<div class="card">
  <h2>Authenticate</h2>

  {% if env_key %}
  <form method="post" action="/auth/env">
    <p>✅ Environment variable <code>MK_CSM_KEY</code> detected.</p>
    <button class="btn primary">Use stored key</button>
  </form>
  <hr style="margin:1.2em 0">
  {% endif %}

  <form method="post" action="/auth/manual">
    <label>Paste an API key:</label>
    <input type="password" name="api_key" placeholder="Meraki Dashboard API key">
    <br><br>
    <button class="btn secondary">Use this key</button>
  </form>
</div>
"""

# =============================================================================
# PAGE 2 — Pick organisation
# =============================================================================

PAGE_ORGS = CSS + NAV + """
<h1>Step 1 — Select an Organisation</h1>
<div class="card">
  <form method="post" action="/orgs">
    <label>Organisation:</label>
    <select name="org_id">
      {% for o in orgs %}
      <option value="{{ o.id }}">{{ o.name }}  ({{ o.id }})</option>
      {% endfor %}
    </select>
    <br><br>
    <button class="btn primary">Next →</button>
  </form>
</div>
"""

# =============================================================================
# PAGE 3 — Name network, pick appliance and APs
# =============================================================================

PAGE_DEVICES = CSS + NAV + """
<h1>Step 2 — Configure Network</h1>
<div class="card">
  <form method="post" action="/devices">

    <label>Network name:</label>
    <input type="text" name="net_name" placeholder="e.g. Branch-Rome" required>

    <label>Security Appliance:</label>
    {% if appliances %}
      <select name="appliance_serial">
        {% for d in appliances %}
        <option value="{{ d.serial }}">{{ d.model }} — {{ d.serial }}</option>
        {% endfor %}
      </select>
    {% else %}
      <p class="err">No unclaimed security appliances in inventory.</p>
    {% endif %}

    <label>Access Points:</label>
    {% if aps %}
      <select name="ap_serials" multiple required>
        {% for d in aps %}
        <option value="{{ d.serial }}">{{ d.model }} — {{ d.serial }}</option>
        {% endfor %}
      </select>
      <p class="hint">Hold Ctrl (Windows) or ⌘ (Mac) to select more than one.</p>
    {% else %}
      <p class="err">No unclaimed access points in inventory.</p>
    {% endif %}

    <br>
    {% if appliances and aps %}
    <button class="btn primary">Review →</button>
    {% endif %}
    <a href="/orgs" class="btn secondary">← Back</a>
  </form>
</div>
"""

# =============================================================================
# PAGE 4 — Confirm summary before writing anything
# =============================================================================

PAGE_CONFIRM = CSS + NAV + """
<h1>Step 3 — Confirm</h1>
<div class="card">
  <ul>
    <li><b>Organisation:</b>  {{ org_name }}</li>
    <li><b>Network name:</b>  {{ net_name }}</li>
    <li><b>Appliance:</b>     {{ appliance_serial }}</li>
    <li><b>Access points:</b> {{ ap_serials | join(', ') }}</li>
  </ul>

  <form method="post" action="/create">
    <!-- Pass all values as hidden fields so we do not need another DB/session key -->
    <input type="hidden" name="net_name"         value="{{ net_name }}">
    <input type="hidden" name="appliance_serial" value="{{ appliance_serial }}">
    {% for s in ap_serials %}
    <input type="hidden" name="ap_serials" value="{{ s }}">
    {% endfor %}
    <button class="btn success">✅ Create &amp; Claim</button>
    <a href="/devices" class="btn secondary">← Back</a>
  </form>
</div>
"""

# =============================================================================
# PAGE 5 — Success
# =============================================================================

PAGE_DONE = CSS + NAV + """
<h1>✅ Done!</h1>
<div class="card">
  <p class="ok">Network <b>{{ net_name }}</b> created and
     {{ device_count }} device(s) claimed.</p>
  <pre>{{ net_json }}</pre>
  <a href="/orgs" class="btn primary">Create another</a>
</div>
"""

# =============================================================================
# PAGE — Error (reused for any failure)
# =============================================================================

PAGE_ERROR = CSS + NAV + """
<h1>⚠ Something went wrong</h1>
<div class="card">
  <p class="err">{{ message }}</p>
  {% if detail %}<pre>{{ detail }}</pre>{% endif %}
  <a href="/" class="btn secondary">Home</a>
</div>
"""


# =============================================================================
# ROUTE HELPERS
# =============================================================================

def dashboard():
    """Return a Meraki SDK client using the API key stored in the session."""
    return meraki.DashboardAPI(session["api_key"], suppress_logging=True)


def error(message, detail=""):
    return render_template_string(PAGE_ERROR, message=message, detail=detail)


# =============================================================================
# ROUTES
# =============================================================================

# --- Authentication ---

@app.route("/")
def home():
    session.clear()
    return render_template_string(PAGE_AUTH, env_key=bool(os.environ.get("MK_CSM_KEY")))


@app.post("/auth/env")
def auth_env():
    session["api_key"] = os.environ.get("MK_CSM_KEY", "")
    return redirect(url_for("orgs_get"))


@app.post("/auth/manual")
def auth_manual():
    session["api_key"] = request.form.get("api_key", "").strip()
    return redirect(url_for("orgs_get"))


# --- Step 1: Organisation ---

@app.route("/orgs")
def orgs_get():
    if "api_key" not in session:
        return redirect(url_for("home"))
    try:
        orgs = dashboard().organizations.getOrganizations()
    except Exception as exc:
        return error("Could not fetch organisations.", str(exc))
    return render_template_string(PAGE_ORGS, orgs=orgs)


@app.post("/orgs")
def orgs_post():
    session["org_id"] = request.form["org_id"]
    return redirect(url_for("devices_get"))


# --- Step 2: Devices ---

@app.route("/devices")
def devices_get():
    if "org_id" not in session:
        return redirect(url_for("orgs_get"))

    org_id = session["org_id"]
    try:
        inventory = dashboard().organizations.getOrganizationInventoryDevices(
            org_id, total_pages="all"
        )
    except Exception as exc:
        return error("Could not fetch inventory.", str(exc))

    # Filter: unclaimed security appliances (MX / Z series)
    appliances = [
        d for d in inventory
        if d.get("networkId") is None
        and d.get("productType") == "appliance"
    ]

    # Filter: unclaimed access points (MR series)
    aps = [
        d for d in inventory
        if d.get("networkId") is None
        and d.get("productType") == "wireless"
    ]

    return render_template_string(PAGE_DEVICES, appliances=appliances, aps=aps)


@app.post("/devices")
def devices_post():
    net_name         = request.form.get("net_name", "").strip()
    appliance_serial = request.form.get("appliance_serial", "").strip()
    ap_serials       = request.form.getlist("ap_serials")

    if not net_name or not appliance_serial or not ap_serials:
        return error("Please fill in all fields and select at least one AP.")

    # Store in session so the confirm page can display them,
    # and the back button from /create works correctly
    session["net_name"]         = net_name
    session["appliance_serial"] = appliance_serial
    session["ap_serials"]       = ap_serials

    # Look up the org name for the summary page
    try:
        orgs     = dashboard().organizations.getOrganizations()
        org_name = next((o["name"] for o in orgs if o["id"] == session["org_id"]), session["org_id"])
    except Exception:
        org_name = session["org_id"]

    return render_template_string(
        PAGE_CONFIRM,
        org_name=org_name,
        net_name=net_name,
        appliance_serial=appliance_serial,
        ap_serials=ap_serials,
    )


# --- Step 3: Create ---

@app.post("/create")
def create():
    org_id           = session.get("org_id")
    net_name         = request.form.get("net_name", "").strip()
    appliance_serial = request.form.get("appliance_serial", "").strip()
    ap_serials       = request.form.getlist("ap_serials")

    if not all([org_id, net_name, appliance_serial, ap_serials]):
        return error("Session data is missing. Please start again.")

    db = dashboard()

    # Create the network with both appliance and wireless product types
    try:
        new_network = db.organizations.createOrganizationNetwork(
            org_id,
            name=net_name,
            productTypes=["appliance", "wireless"],
        )
    except Exception as exc:
        return error("Failed to create network.", str(exc))

    # Claim all devices: appliance first, then APs
    serials = [appliance_serial] + ap_serials
    try:
        db.networks.claimNetworkDevices(new_network["id"], serials=serials)
    except Exception as exc:
        return error(f"Network created (id: {new_network['id']}) but device claim failed.", str(exc))

    return render_template_string(
        PAGE_DONE,
        net_name=net_name,
        device_count=len(serials),
        net_json=json.dumps(new_network, indent=2),
    )


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("Open http://localhost:8001 in your browser")
    webbrowser.open("http://localhost:8001")
    app.run(host="127.0.0.1", port=8001, debug=False)