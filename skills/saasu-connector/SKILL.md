---
name: saasu-connector
description: "Connect Saasu accounting (now part of erly) to Claude by installing its bundled MCP server and authenticating with the user's own Saasu file credentials. Use when the user asks to set up or connect Saasu, or wants Saasu work (invoices, contacts, payments, bank balances, profit and loss, items, payroll) and Saasu isn't connected yet. Once connected, Saasu runs directly through the mcp__saasu__* tools."
allowed-tools: Bash,Read,Write,Edit,mcp__saasu__*,mcp__plugin_playwright_playwright__*,mcp__playwright__*
metadata:
  category: Productivity & Integrations
  tags:
    - saasu
    - erly
    - accounting
    - invoices
    - bookkeeping
    - australia
    - rest-api
    - mcp
  pairs-with:
    - skill: xero-connector
      reason: Sibling AU accounting connector. Attendees on Xero go there; Saasu is the smaller AU player, popular with sole traders and e-commerce.
    - skill: myob-connector
      reason: Sibling direct-REST accounting connector, same credentials-file and plain-English install shape.
    - skill: superpowers:systematic-debugging
      reason: Use when Saasu returns unclear 400/401 errors or the daily request cap is hit.
---

# Saasu Connector

## Overview

Saasu is Australian cloud accounting (invoicing, expenses, bank feeds, inventory, Single Touch Payroll), owned by erly since 2022. It publishes **no MCP server, no CLI and no maintained SDK**, so this connector ships its own: one dependency-free Python file that speaks MCP over stdio and talks to Saasu's REST API at `https://api.saasu.com`. Python 3 is already on every Mac that has git installed; Windows needs Python 3 from the Microsoft Store or `winget install Python.Python.3.12`.

**Whose credentials?** The user's. Saasu authorises the API per file, per user. There is no developer program, no app registration and nothing the workshop pays for. The two values Claude needs come out of the user's own Saasu account (Settings > Web Services), or from their normal Saasu login. Free 30-day trials work the same as paid files.

Three ways in, tried in this order:

| Route | What Claude captures | User's moment | When to use |
|---|---|---|---|
| **A. Web Services key** (default) | FileId + access key from the Settings > Web Services page, via the Playwright browser | Sign in to Saasu | Always first. No password ever leaves Saasu's page. |
| **B. Saasu login** | A long-lived refresh token, minted by Saasu's OAuth password grant | Type email + password (+ SMS code if 2FA is on) into a small prompt window Claude opens | Web Services page is missing, or the user's role can't see it |
| **C. Paste** | The same FileId + key, pasted by the user into the chat | Copy two values | Browser tool unavailable. Accepted transcript-leak trade-off; say so. |

Whichever route, the result is the same file on disk, `~/.config/saasu/credentials.env` (mode 600), read by the server at call time. Nothing secret goes into `~/.claude.json`.

**Two phases:**

- **Phase 1, Install and Connect.** Capture credentials, write the file, register the server, verify with a live safe read of the file's name.
- **Phase 2, Use.** `mcp__saasu__*` tools (23 of them: contacts, invoices, payments, items, accounts, bank balances, tax codes, P&L, sales summary, journals, payroll employees, search, PDF download, invoice email, and a raw escape hatch). Reads are free; every write tool says WRITE in its description and needs the user's go-ahead first.

**Which phase to run.** Before any Saasu action run Phase 0. If the credentials file exists and the ping succeeds, go to Phase 2.

---

## Safety gate, before Phase 1

This skill is for people who **already use Saasu**. Do not pitch Saasu, do not create a Saasu account for them, and do not sign them up for a trial.

Ask once:

> "Quick check before we start: do you already run your books in Saasu (it may say erly now), with your own login?"

- **Yes** → continue.
- **They use Xero / MYOB / QuickBooks** → route to that connector. Do not come back to Saasu.
- **Only their bookkeeper has the login** → they need a login on the file, or their bookkeeper's help for the two-minute key step. Wait for that before continuing.
- **Not sure / shopping around** → stop. "Saasu only makes sense to connect if you already use it. What does your business run its accounts on today?"

Money data is sensitive. In Phase 2, read freely, but **confirm before creating, changing, emailing or deleting anything**, and never bulk-dump a whole ledger into the chat.

---

## Communication rules (both phases)

The user is a non-technical business owner.

- **One step per message.** Say what is about to happen before it happens.
- **Plain English.** Never say API, token, MCP, JSON, curl, env, terminal, script or file path to the user. Say "the connection", "your Saasu account", "the small browser window", "the access details".
- **Never echo the access key or FileId** into a reply, a narration line or a log. Never screenshot the Web Services page.
- **Never type the user's password.** Route B hands the typing to the user.
- **Warm and short.** Maximum 8 lines per message in Phase 1. Translate errors; never paste them.
- **Say what needs a restart.** The new tools appear after the user closes and reopens Claude Code once. Say that plainly at the end of Phase 1.

---

## PHASE 0, resume check

```bash
CRED="$HOME/.config/saasu/credentials.env"
SKILL="$HOME/.claude/skills/saasu-connector"
if [ -f "$CRED" ] && grep -q '^SAASU_FILE_ID=.\+' "$CRED"; then python3 "$SKILL/scripts/saasu_mcp.py" ping; else echo not-configured; fi
```

- Prints `{"ok": true, ... "file_name": "..."}` → already connected. Check `claude mcp get saasu` shows the server; if missing, run only Step 5 below. Then Phase 2.
- `FAIL ... 401` → credentials revoked or expired. Re-run Phase 1 from Step 2.
- `not-configured` → Phase 1.

`ping` is a real read of `GET FileIdentity` for the stored FileId. A tool listing is not proof; this is.

---

## PHASE 1, Install and Connect

### Step 1, Check the tools

```bash
python3 --version && claude --version
```

Python missing on Windows → `winget install Python.Python.3.12`, then reopen the chat. Playwright tools missing (`mcp__plugin_playwright_playwright__*` or `mcp__playwright__*` absent) → install per `skills/CLAUDE.md`:

```bash
claude mcp add playwright --scope user -- npx -y @playwright/mcp@latest --user-data-dir "$HOME/.cache/playwright-mcp-profile"
```

Ask the user to close and reopen Claude Code, then continue. If Playwright still cannot be had, go to Route C.

### Step 2, Sign in (user step)

Tell the user: *"I'm opening Saasu's sign-in page in a small browser window. Sign in like normal, including any code Saasu texts you."*

```
browser_navigate({ url: "https://secure.saasu.com/" })
```

**Never snapshot the sign-in page** (password fields can land in the accessibility tree). Poll for the dashboard:

```
browser_wait_for({ text: "Dashboard", time: 60 })
```

If the user has several Saasu files, ask which business to connect and switch to it in the file picker before Step 3.

### Step 3, Route A: read the Web Services page

Saasu's own docs say the values live under **Settings > Web Services** in the web app. The legacy deep link is `https://secure.saasu.com/a/net/webservicessettings.aspx`; it has not been re-verified on the current UI, so try it, and if it 404s or redirects, open the Settings menu from the top navigation and click **Web Services** (snapshot the nav, match by label; Saasu re-renders, so re-query rather than caching refs).

On the page, read the two values through `browser_evaluate` **returning only metadata**, and copy the key to the clipboard:

```js
async () => {
  const text = document.body.innerText;
  const fileId = (text.match(/File\s*(?:Id|ID|UID)\D{0,40}?(\d{3,8})/i) || [])[1] || null;
  const key = (text.match(/\b[0-9A-F]{32}\b/) || [])[0] || null;   // wsAccessKey is a 32-hex string
  if (!key || !fileId) return { ok: false, haveKey: !!key, haveFileId: !!fileId };
  try { await navigator.clipboard.writeText(key); return { ok: true, fileId, keyLen: key.length }; }
  catch (e) { return { ok: false, reason: "clipboard", fileId }; }
}
```

- `ok: true` → Step 4 with `fileId` from the result and the key on the clipboard.
- Page shows a **Generate** / **Create access key** button and no key yet → click it, re-run the read.
- Page not reachable for this user (role lacks Settings) → Route B (Step 3b).

### Step 3b, Route B: Saasu login (fallback)

Saasu's OAuth supports only the password grant, so there is no consent page to drive. Claude opens a prompt window the **user** types into; the password is used once and not stored, and a 12-month refresh token is written instead.

macOS:

```bash
osascript -e 'tell application "Terminal" to do script "python3 \"$HOME/.claude/skills/saasu-connector/scripts/saasu_mcp.py\" login; exit"' -e 'tell application "Terminal" to activate'
```

Windows (PowerShell): `Start-Process powershell -ArgumentList "-NoExit","python `"$HOME\.claude\skills\saasu-connector\scripts\saasu_mcp.py`" login"`.

Tell the user: *"A small window just opened asking for your Saasu email and password, and a code if Saasu texts one. Type them there; I never see them. Tell me when it says Saved."* If the login can see several files it lists them and asks which one; the user answers in that window. Then skip to Step 5.

### Step 3c, Route C: paste (last resort)

Ask the user to open Settings > Web Services in their own browser and paste the File Id and the access key into the chat. Say plainly that the key will sit in this conversation's history and they can regenerate it in Saasu afterwards. Then Step 4 with the pasted values instead of the clipboard.

### Step 4, Store the credentials (silent)

```bash
install -d -m 700 "$HOME/.config/saasu"
KEY="$( pbpaste 2>/dev/null || powershell.exe -c Get-Clipboard 2>/dev/null | tr -d '\r' )"
FILE_ID="<fileId from Step 3>"
umask 077
cat > "$HOME/.config/saasu/credentials.env" <<EOF
# Saasu API credentials - DO NOT COMMIT, DO NOT SHARE
SAASU_FILE_ID=${FILE_ID}
SAASU_ACCESS_KEY=${KEY}
EOF
chmod 600 "$HOME/.config/saasu/credentials.env"
printf '' | pbcopy 2>/dev/null; rm -rf .playwright-mcp 2>/dev/null; unset KEY FILE_ID
```

Never grep the transcript or disk for the key substring afterwards; clear the clipboard and the Playwright snapshot folder wholesale, as above.

### Step 5, Register the server

```bash
claude mcp add saasu --scope user -- python3 "$HOME/.claude/skills/saasu-connector/scripts/saasu_mcp.py" serve
claude mcp get saasu
```

Expect `Status: ✔ Connected`. The server reads the credentials file itself; no secrets go on the command line or into `~/.claude.json`. If `claude mcp add` fails, merge this into `mcpServers` in `~/.claude.json` by hand:

```jsonc
"saasu": { "command": "python3", "args": ["/Users/<user>/.claude/skills/saasu-connector/scripts/saasu_mcp.py", "serve"] }
```

### Step 6, Verify with a real read and report

```bash
python3 "$HOME/.claude/skills/saasu-connector/scripts/saasu_mcp.py" ping
```

Expect `{"ok": true, "route": "access_key" | "oauth", "file_id": "...", "file_name": "<their business>"}`. Say: *"Connected to `<file_name>` in Saasu. Close and reopen Claude Code once so the new Saasu tools show up, then ask me things like 'who owes me money?', 'show last month's sales', or 'what's in the bank?'"*

`FAIL ... 401` → the key or FileId is wrong for this file (a key belongs to one user on one file). Re-run Step 3 on the right file. `429` → the file's daily request cap is hit; Saasu blocks for 24 hours, nothing to do but wait or upgrade the plan.

---

## PHASE 2, Use the connector

Once `mcp__saasu__*` tools are visible, use them directly. Start most sessions with `mcp__saasu__saasu_status` (safe read).

| Ask | Tool |
|---|---|
| Who owes me money? | `saasu_list_invoices(transaction_type="S", payment_status="U")` |
| Bills I still have to pay | `saasu_list_invoices(transaction_type="P", payment_status="U")` |
| Sales this month / quarter | `saasu_sales_summary(from_date, to_date)` or `saasu_list_invoices` with dates |
| What's in the bank? | `saasu_bank_balances()` |
| Profit and loss | `saasu_profit_and_loss(from_date, to_date)` |
| Find a customer | `saasu_list_contacts(search_name=...)` or `saasu_search(text)` |
| Send / download an invoice | `saasu_invoice_pdf(id)`, `saasu_email_invoice(id)` (WRITE, outward-facing, confirm first) |
| Create an invoice | `saasu_tax_codes()` + `saasu_list_accounts(account_type="Income")` first, then `saasu_create_invoice` (WRITE, confirm first) |
| Record a payment | `saasu_list_accounts(bank_accounts_only=True)` then `saasu_create_payment` (WRITE) |
| Anything else | `saasu_raw_request(method, path, params, body)`; full map in `references/api-map.md` |

**Before the tools appear** (user has not reopened Claude Code yet), or if the server fails to start, the same credentials work from the shell:

```bash
set -a; . "$HOME/.config/saasu/credentials.env"; set +a
curl -s -H "Accept: application/json" -H "X-Api-Version: 1.0" \
  "https://api.saasu.com/Invoices?TransactionType=S&PaymentStatus=U&FileId=$SAASU_FILE_ID&wsAccessKey=$SAASU_ACCESS_KEY"
```

Keep to **one request per second**; the server throttles for you, curl does not.

---

## Gotchas

- **One key = one user on one file.** Switching business files in Saasu means a different FileId and key.
- **Updates need `LastUpdatedId`.** Saasu uses optimistic concurrency. `saasu_update_*` must include the current `LastUpdatedId` from a fresh get, or Saasu returns 400.
- **Date windows come in pairs.** `LastModifiedFromDate` needs `LastModifiedToDate`; the server fills the missing end with tomorrow.
- **Daily caps are real.** Small plan 4,000 requests/day, Medium 6,000, Large 8,000; over the cap = 24-hour block. Don't loop through history one record at a time; use the list filters.
- **No webhooks.** Anything "when a new invoice arrives" is a poll on `modified_since`.
- **Route A is marked "to be phased out" by Saasu** with no date. If a key stops working, Route B still will.
- **Refresh tokens (Route B) last 12 months**, then `ping` reports 401 and Route B is re-run.
- **Payroll tools need a plan with payroll**; others return 403 on that call only.

## Credential handling

`~/.config/saasu/credentials.env`, mode 600, outside any repo. Contains `SAASU_FILE_ID` plus either `SAASU_ACCESS_KEY` (Route A) or `SAASU_REFRESH_TOKEN` + rotating `SAASU_ACCESS_TOKEN` (Route B, rewritten atomically on refresh). Add `**/credentials.env` to any nearby `.gitignore`. To disconnect: delete the file, and in Saasu regenerate the Web Services key.

## See also

- `references/api-map.md`: every endpoint, payload shapes, limits, verified 2026-09-10 against `https://api.saasu.com`.
- `scripts/saasu_mcp.py`: the server. `selftest` runs offline checks (no network) and a live stdio handshake against itself.
- `skills/CLAUDE.md`: connector authoring rules, Playwright contingency.
