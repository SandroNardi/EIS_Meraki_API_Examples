# Prompt

I need a series of incremental Python scripts that form a demo learning
journey for the Meraki Dashboard API. Each script must be self-contained in
a single file. The scripts are meant to be published as workshop material:
attendees will read them and feed them to AI assistants as starting templates,
so the code must be as short, bare-bones, and readable as possible. Shorter
code is preferred, as long as it is functional and clear.

Use the official `meraki` Python library (where applicable). The API key
must be loaded from an environment variable named `MK_CSM_KEY`; if it is not
set, the script must prompt the user to paste a key at runtime.

Deliver the following five scripts:

1. Fetch the list of organizations and print the raw response.

2. Same as #1, but render the result as a `rich` console table.

3. Let the user select a single organization or all organizations, then list
   every device in the inventory that has a published End-of-Sale or
   End-of-Support date, sorted by the closest upcoming event first. The data
   source is the `getOrganizationInventoryDevices` endpoint, which returns an
   `eox` field of the form:

       "eox": {
         "status": "endOfSale",
         "endOfSaleAt": "2031-07-29T02:00:00Z",
         "endOfSupportAt": "2032-07-29T02:00:00Z"
       }

4. Let the user select a single organization or all organizations. For each
   organization, walk through every wireless network and every configuration
   template that contains a wireless product type. For every SSID found,
   identify the ones that are enabled and use RADIUS authentication, and
   report:
     - the organization name
     - the network name **or** template name (clearly indicate which one in
       the output)
     - if the row comes from a template, also indicate how many networks are
       bound to that template
     - the SSID number and name
     - the auth mode
     - the list of configured RADIUS servers with host and port

   Also report the total number of enabled SSIDs scanned.

5. Same audit as #4, but exposed through a minimal local web GUI that lets
   the user authenticate via:
     - the stored API key (`MK_CSM_KEY`), if present
     - a manually pasted API key
     - OAuth 2.0

   The entire OAuth setup must be doable from the web page, including the
   very first iteration:
     - The user must be able to paste the OAuth Client ID and Client Secret
       directly into the web form (no environment variables required).
     - The redirect URI to register at integrate.cisco.com must be displayed
       on the page so the user can copy it.
     - The required scopes must be displayed on the page and must be
       editable in the form, so the user can verify and adjust them to match
       what was configured at integrate.cisco.com. The exact scope names that
       work with the Meraki authorization server are:
         - `dashboard:general:config:read`
         - `wireless:config:read`
       (Note: scope names that look like `dashboard:wireless:config:read` are
       NOT recognized by the authorization server and will return
       `invalid_scope`. Always verify the names against integrate.cisco.com.)
     - If a refresh token is already stored locally, offer to reuse it.
     - Provide a button to drop the refresh token and restart from a fresh
       authorization while keeping the client credentials.
     - Provide a separate button to fully reset the OAuth setup (wipe both
       client credentials and refresh token).
     - Persist client credentials, scopes, and the refresh token in a single
       local JSON file (`.meraki_oauth.json`, mode 600 on Unix).
     - The OAuth redirect URI is `http://localhost:8000/callback`.
     - Follow Meraki's OAuth 2.0 spec: authorize endpoint
       `https://as.meraki.com/oauth/authorize`, token endpoint
       `https://as.meraki.com/oauth/token`, HTTP Basic auth with
       `client_id` / `client_secret`, refresh tokens revoked after 90 days
       of inactivity, access tokens valid for 60 minutes.

   The web UI must look professional but stay minimal. UI templates must be
   kept at the bottom of the file in clearly named constants (e.g.
   `TPL_INDEX`, `TPL_ORGS`, `TPL_RESULTS`, `TPL_ERROR`, `TPL_DEBUG`) so
   that workshop attendees can easily separate the Flask routes / business
   logic from the presentation.

   The script must include a built-in **debug page** at `/debug` that shows:
     - the current persisted state with secrets masked
     - the active scopes (both as a list and as Python `repr` to expose any
       hidden whitespace or invisible characters)
     - a preview of the next authorize request that would be sent
     - a ring buffer of the most recent OAuth events (authorize redirect,
       callback, token-exchange request and response, refresh-token request
       and response), with secrets masked
     - a button to clear the log

   All OAuth-related events must also be printed to the terminal so the
   workshop attendee can follow them live without opening the debug page.

   When the OAuth flow returns an error, the error page must:
     - display the `error` and `error_description` returned by Meraki
     - include a list of common causes for that specific error code
       (`invalid_scope`, `invalid_client`, `redirect_uri_mismatch`)
     - link to the `/debug` page

Also produce:

- A `README.md` at the folder root with a thorough "How to use" section
  written so that a complete beginner can install Python, set up a virtual
  environment, install dependencies, obtain a Meraki API key, configure the
  OAuth integration at integrate.cisco.com, run every script, and use the
  debug page to troubleshoot OAuth issues.

- A `requirements.txt` listing the Python dependencies.

- A `PROMPT.md` containing this rewritten specification.

Target Python 3.10 or newer. Each file must be delivered separately.