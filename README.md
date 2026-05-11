
# Meraki API Examples

A collection of Python scripts demonstrating how to interact with the 
Cisco Meraki Dashboard API. Each folder covers a specific topic or 
use case and is designed to be easy to read, run, and modify.

These examples are intended for **learning and demonstration purposes only**.  
They are not production-ready code.

---

## What is in this repository

Each sub-folder is a self-contained set of scripts focused on one topic.
Every folder has its own `README.md` with specific setup and usage instructions.

| Folder | What it covers |
|--------|---------------|
| `Session_1_Examples/` | Organization listing, network creation, device claiming |
| `Session_2_Examples/` | Various Cisco Workflows examples |

More folders will be added over time.

---

## Getting started Session_1_Examples

### 1. Install Python

You need Python **3.11 or newer**.  
Download it from [python.org](https://www.python.org/downloads/).

### 2. Get a Meraki API key

1. Log in to [dashboard.meraki.com](https://dashboard.meraki.com)
2. Go to your profile (top right) → **My profile**
3. Scroll to **API access** → **Generate new API key**
4. Copy and save the key somewhere safe — you will not be able to see it again

### 3. Set up a virtual environment (recommended)

A virtual environment keeps dependencies for this project separate from 
the rest of your system.

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows
```

### 4. Install dependencies

Each sub-folder has its own `requirements.txt`.  
Navigate into the folder you want to run and install from there:

```bash
cd Session_1_Examples
pip install -r requirements.txt
```

### 5. Set your API key

The recommended way to provide your API key is via an environment variable:

```bash
export MK_CSM_KEY=your_api_key_here      # macOS / Linux
set MK_CSM_KEY=your_api_key_here         # Windows CMD
$env:MK_CSM_KEY="your_api_key_here"      # Windows PowerShell
```

If you do not set the variable, each script will prompt you to enter 
the key when it starts.

---

## ⚠ API key safety — please read

Your Meraki API key provides **full programmatic access** to your 
Meraki dashboard. Treat it like a password.

**Never do any of the following:**

- Hard-code your API key directly in a script
- Commit your API key to Git or any version control system
- Share your API key in screenshots, chat messages, or emails
- Upload scripts to GitHub, GitLab, or any public platform while 
  your API key is still in the file

**Safe practices:**

- Always use environment variables (see Step 5 above) or a secrets 
  manager to supply the key at runtime
- Add `.env` and any file containing secrets to your `.gitignore`
- If you accidentally expose a key, revoke it immediately in the 
  Meraki Dashboard and generate a new one
- Use read-only API keys where possible when only reading data

---

## ⚠ Production use disclaimer

The scripts in this repository are **demos and learning examples**.  
They are intentionally simplified to make them easy to read and follow.

**They should not be used in production environments as-is** because:

- There is minimal error handling
- There are no retry strategies beyond what the SDK provides by default
- There is no logging to file
- There is no input validation beyond basic checks
- No automated tests are included

If you want to build on these examples for real-world use, treat them 
as a starting point and add appropriate hardening before deployment.

---

## License

MIT License

Copyright (c) 2025 Cisco Systems

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```