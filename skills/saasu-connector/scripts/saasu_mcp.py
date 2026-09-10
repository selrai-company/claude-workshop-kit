#!/usr/bin/env python3
"""Saasu accounting MCP server + setup CLI.

Single file, standard library only (no pip installs): HTTP via urllib, MCP over stdio by hand.

    saasu_mcp.py serve          # stdio MCP server (what `claude mcp add` runs)
    saasu_mcp.py login          # interactive: email + password (+2FA) -> refresh token on disk
    saasu_mcp.py ping           # safe read: confirm the stored credentials reach the file
    saasu_mcp.py selftest       # offline unit checks, no network

Credentials live in ~/.config/saasu/credentials.env (mode 600), never in argv or
the MCP config. Two auth routes are supported and picked automatically:

  A. Access key   SAASU_FILE_ID + SAASU_ACCESS_KEY  (Saasu > Settings > Web Services)
  B. OAuth2       SAASU_FILE_ID + SAASU_REFRESH_TOKEN (from `login`; password grant,
                  the only grant Saasu supports; access tokens last 3h, refresh 12 months)

API reference: https://api.saasu.com  (Help/Authentication, Help/Api/*)
Limits: 1 request/second hard; daily cap by plan (4k-8k). This client throttles to 1/s.
"""
from __future__ import annotations

import getpass
import json
import os
import socket
import stat
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API_BASE = "https://api.saasu.com/"
API_VERSION = "1.0"
CRED_DIR = Path(os.environ.get("SAASU_CONFIG_DIR", Path.home() / ".config" / "saasu"))
CRED_FILE = CRED_DIR / "credentials.env"
USER_AGENT = "selr-saasu-connector/1.0 (+https://loup.academy/connectors)"
MIN_INTERVAL = 1.05  # seconds between requests (Saasu limit is 1/s)

# Force IPv4: Python urllib stalls on some Macs when a host publishes AAAA records.
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(*args, **kwargs):
    return [ai for ai in _orig_getaddrinfo(*args, **kwargs) if ai[0] == socket.AF_INET] or _orig_getaddrinfo(*args, **kwargs)


socket.getaddrinfo = _ipv4_getaddrinfo  # type: ignore[assignment]


# --------------------------------------------------------------------------- credentials
def read_env_file(path: Path = CRED_FILE) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        out[k.strip()] = v
    return out


def write_env_file(values: dict[str, str], path: Path = CRED_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, stat.S_IRWXU)
    lines = [
        "# Saasu API credentials - DO NOT COMMIT, DO NOT SHARE",
        "# Route A: SAASU_FILE_ID + SAASU_ACCESS_KEY (Settings > Web Services)",
        "# Route B: SAASU_FILE_ID + SAASU_REFRESH_TOKEN (written by `saasu_mcp.py login`)",
    ]
    for k, v in values.items():
        if v:
            lines.append(f"{k}={v}")
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    os.replace(tmp, path)
    os.chmod(path, 0o600)


def load_credentials() -> dict[str, str]:
    """Env vars win over the file so a launcher can inject from a secret store."""
    creds = read_env_file()
    for k in ("SAASU_FILE_ID", "SAASU_ACCESS_KEY", "SAASU_REFRESH_TOKEN", "SAASU_ACCESS_TOKEN", "SAASU_TOKEN_EXPIRES"):
        if os.environ.get(k):
            creds[k] = os.environ[k]
    return creds


# --------------------------------------------------------------------------- HTTP client
class SaasuError(RuntimeError):
    pass


class SaasuClient:
    def __init__(self, creds: dict[str, str] | None = None, opener=None):
        self.creds = creds if creds is not None else load_credentials()
        self._opener = opener or urllib.request.build_opener()
        self._lock = threading.Lock()
        self._last = 0.0

    # ---- auth state
    @property
    def file_id(self) -> str:
        return self.creds.get("SAASU_FILE_ID", "")

    @property
    def route(self) -> str:
        if self.creds.get("SAASU_ACCESS_KEY"):
            return "access_key"
        if self.creds.get("SAASU_REFRESH_TOKEN") or self.creds.get("SAASU_ACCESS_TOKEN"):
            return "oauth"
        return "none"

    def configured(self) -> bool:
        return bool(self.file_id) and self.route != "none"

    # ---- throttle
    def _throttle(self) -> None:
        with self._lock:
            wait = MIN_INTERVAL - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()

    # ---- raw transport
    def _send(self, method: str, url: str, body: Any = None, headers: dict[str, str] | None = None, auth: bool = True) -> tuple[int, Any]:
        h = {"Accept": "application/json", "User-Agent": USER_AGENT, "X-Api-Version": API_VERSION}
        if headers:
            h.update(headers)
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        if auth and self.route == "oauth":
            h["Authorization"] = f"Bearer {self._access_token()}"
        req = urllib.request.Request(url, data=data, method=method, headers=h)
        self._throttle()
        try:
            with self._opener.open(req, timeout=60) as resp:
                raw = resp.read()
                ctype = resp.headers.get("Content-Type", "")
                status = resp.status
        except urllib.error.HTTPError as e:
            raw = e.read()
            ctype = e.headers.get("Content-Type", "") if e.headers else ""
            status = e.code
        if "json" in ctype and raw:
            try:
                return status, json.loads(raw)
            except json.JSONDecodeError:
                pass
        if "pdf" in ctype:
            return status, raw
        return status, raw.decode(errors="replace") if raw else None

    def _access_token(self) -> str:
        exp = float(self.creds.get("SAASU_TOKEN_EXPIRES") or 0)
        tok = self.creds.get("SAASU_ACCESS_TOKEN")
        if tok and time.time() < exp - 120:
            return tok
        rt = self.creds.get("SAASU_REFRESH_TOKEN")
        if not rt:
            raise SaasuError("No refresh token on file. Run `saasu_mcp.py login` again.")
        status, data = self._send("POST", API_BASE + "authorisation/refresh", {"grant_type": "refresh_token", "refresh_token": rt, "scope": ""}, auth=False)
        if status != 200 or not isinstance(data, dict) or "access_token" not in data:
            raise SaasuError(f"Token refresh failed (HTTP {status}). Run `saasu_mcp.py login` again.")
        self._store_grant(data)
        return self.creds["SAASU_ACCESS_TOKEN"]

    def _store_grant(self, grant: dict[str, Any]) -> None:
        self.creds["SAASU_ACCESS_TOKEN"] = grant["access_token"]
        self.creds["SAASU_REFRESH_TOKEN"] = grant.get("refresh_token", self.creds.get("SAASU_REFRESH_TOKEN", ""))
        self.creds["SAASU_TOKEN_EXPIRES"] = str(int(time.time() + int(grant.get("expires_in", 10800))))
        if os.environ.get("SAASU_NO_PERSIST") != "1":
            write_env_file({k: v for k, v in self.creds.items() if k.startswith("SAASU_")})

    # ---- public request
    def request(self, method: str, path: str, params: dict[str, Any] | None = None, body: Any = None) -> Any:
        if not self.configured():
            raise SaasuError("Saasu is not connected yet. Add SAASU_FILE_ID plus SAASU_ACCESS_KEY, or run `saasu_mcp.py login`.")
        q = {k: v for k, v in (params or {}).items() if v not in (None, "")}
        q.setdefault("FileId", self.file_id)
        # Saasu requires both ends of a LastModified / Cleared window.
        for a, b in (("LastModifiedFromDate", "LastModifiedToDate"), ("ClearedFromDate", "ClearedToDate")):
            if a in q and b not in q:
                q[b] = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 86400))
        if self.route == "access_key":
            q["wsAccessKey"] = self.creds["SAASU_ACCESS_KEY"]
        url = API_BASE + path.lstrip("/") + "?" + urllib.parse.urlencode(q)
        status, data = self._send(method.upper(), url, body)
        if status == 401:
            raise SaasuError("Saasu rejected the credentials (401). Re-check the access key / FileId or run `login` again.")
        if status == 403:
            raise SaasuError("Saasu refused this action for this user (403).")
        if status == 429:
            raise SaasuError("Saasu rate limit hit (429). Wait a moment; daily plan cap may be reached.")
        if status >= 400:
            raise SaasuError(f"Saasu API error HTTP {status}: {json.dumps(data)[:800] if not isinstance(data, bytes) else '<binary>'}")
        return data

    # ---- login (password grant; the only grant Saasu supports)
    def password_grant(self, username: str, password: str, verification_code: str | None = None) -> dict[str, Any]:
        body = {"grant_type": "password", "username": username, "password": password, "scope": "full"}
        if verification_code:
            body["verification_code"] = verification_code
        status, data = self._send("POST", API_BASE + "authorisation/token", body, auth=False)
        if status != 200 or not isinstance(data, dict) or "access_token" not in data:
            raise SaasuError(f"Login failed (HTTP {status}): {json.dumps(data)[:400]}")
        return data


def file_ids_from_scope(scope: str) -> list[str]:
    return [p.split(":", 1)[1] for p in (scope or "").split() if p.lower().startswith("fileid:")]


def redact(obj: Any) -> Any:
    """Strip secrets from anything that might be echoed."""
    if isinstance(obj, dict):
        return {k: ("***" if k.lower() in {"wsaccesskey", "access_token", "refresh_token", "password"} else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    return obj


# --------------------------------------------------------------------------- MCP server (stdlib JSON-RPC over stdio)
import inspect
import typing

SERVER_INSTRUCTIONS = (
    "Saasu (erly) cloud accounting for one Saasu file. Money data: read freely, but confirm with the user "
    "before creating, updating, emailing or deleting anything. Dates are YYYY-MM-DD. TransactionType S=sale, P=purchase. "
    "InvoiceStatus I=invoice Q=quote O=order. PaymentStatus P=paid U=unpaid A=all. Rate limit is 1 request/second."
)

_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean", dict: "object", list: "array"}


def _schema_for(fn) -> dict[str, Any]:
    hints = typing.get_type_hints(fn)
    props: dict[str, Any] = {}
    required: list[str] = []
    for name, param in inspect.signature(fn).parameters.items():
        t = hints.get(name, str)
        origin = typing.get_origin(t)
        if origin is typing.Union or (origin is not None and origin.__name__ == "UnionType"):
            t = next(a for a in typing.get_args(t) if a is not type(None))
            origin = typing.get_origin(t)
        if origin in (list, dict):
            t = origin
        props[name] = {"type": _JSON_TYPES.get(t, "string")}
        if t is list:
            props[name]["items"] = {"type": "object"}
        if param.default is inspect.Parameter.empty:
            required.append(name)
    return {"type": "object", "properties": props, "required": required}


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, Any] = {}

    def tool(self):
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn
        return deco

    def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": n, "description": inspect.getdoc(f) or "", "inputSchema": _schema_for(f)} for n, f in self.tools.items()]

    def call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        fn = self.tools.get(name)
        if fn is None:
            return {"content": [{"type": "text", "text": f"Unknown tool {name}"}], "isError": True}
        try:
            return {"content": [{"type": "text", "text": str(fn(**(args or {})))}]}
        except (SaasuError, TypeError, ValueError) as e:
            return {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}], "isError": True}

    def serve_stdio(self) -> None:
        out = sys.stdout
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
            if mid is None:  # notification
                continue
            if method == "initialize":
                result: Any = {"protocolVersion": params.get("protocolVersion", "2025-06-18"), "capabilities": {"tools": {}},
                               "serverInfo": {"name": "saasu", "version": "1.0"}, "instructions": SERVER_INSTRUCTIONS}
            elif method == "tools/list":
                result = {"tools": self.list_tools()}
            elif method == "tools/call":
                result = self.call(params.get("name", ""), params.get("arguments") or {})
            elif method == "ping":
                result = {}
            else:
                out.write(json.dumps({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Method not found: {method}"}}) + "\n")
                out.flush()
                continue
            out.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": result}) + "\n")
            out.flush()


def build_server() -> ToolRegistry:
    mcp = ToolRegistry()
    client = SaasuClient()

    def _j(data: Any) -> str:
        if isinstance(data, bytes):
            return f"<binary {len(data)} bytes>"
        return json.dumps(data, indent=1, default=str)

    @mcp.tool()
    def saasu_status() -> str:
        """Check whether Saasu is connected and which file it points at. Safe read, no data changed."""
        if not client.configured():
            return json.dumps({"connected": False, "reason": "no credentials", "credentials_file": str(CRED_FILE)})
        data = client.request("GET", "FileIdentity")
        return _j({"connected": True, "auth_route": client.route, "file_id": client.file_id, "file": redact(data)})

    @mcp.tool()
    def saasu_list_contacts(search_name: str = "", company_name: str = "", email: str = "", is_customer: bool | None = None,
                            is_supplier: bool | None = None, modified_since: str = "", page: int = 1, page_size: int = 50) -> str:
        """List contacts (customers, suppliers). Filters are optional. Paginated, max page_size 100."""
        p: dict[str, Any] = {"Page": page, "PageSize": min(page_size, 100)}
        if search_name:
            p["GivenName"] = search_name
        if company_name:
            p["CompanyName"] = company_name
        if email:
            p["Email"] = email
        if is_customer is not None:
            p["IsCustomer"] = str(is_customer).lower()
        if is_supplier is not None:
            p["IsSupplier"] = str(is_supplier).lower()
        if modified_since:
            p["LastModifiedFromDate"] = modified_since
        return _j(client.request("GET", "Contacts", p))

    @mcp.tool()
    def saasu_get_contact(contact_id: int) -> str:
        """Fetch one contact by Id."""
        return _j(client.request("GET", f"Contact/{contact_id}"))

    @mcp.tool()
    def saasu_create_contact(given_name: str = "", family_name: str = "", email: str = "", phone: str = "",
                             company_id: int | None = None, is_customer: bool = True, is_supplier: bool = False,
                             extra_fields: dict | None = None) -> str:
        """Create a contact. WRITE: confirm with the user first. Saasu links a contact to a business via company_id
        (create the company first with saasu_raw_request POST 'Company' {"Name": ...} if it does not exist)."""
        body: dict[str, Any] = {"GivenName": given_name, "FamilyName": family_name, "EmailAddress": email,
                                "PrimaryPhone": phone, "IsCustomer": is_customer, "IsSupplier": is_supplier, "IsActive": True}
        if company_id:
            body["CompanyId"] = company_id
        body.update(extra_fields or {})
        return _j(client.request("POST", "Contact", body=body))

    @mcp.tool()
    def saasu_update_contact(contact_id: int, fields: dict) -> str:
        """Update a contact. WRITE. Saasu needs the current LastUpdatedId: fetch the contact first and include it in fields."""
        return _j(client.request("PUT", f"Contact/{contact_id}", body=fields))

    @mcp.tool()
    def saasu_list_invoices(transaction_type: str = "S", invoice_from: str = "", invoice_to: str = "", payment_status: str = "A",
                            invoice_status: str = "", contact_id: int | None = None, invoice_number: str = "",
                            modified_since: str = "", page: int = 1, page_size: int = 50) -> str:
        """List sales (S) or purchases (P). payment_status P=paid U=unpaid A=all. invoice_status I=invoice Q=quote O=order."""
        p: dict[str, Any] = {"TransactionType": transaction_type, "PaymentStatus": payment_status, "Page": page, "PageSize": min(page_size, 100)}
        if invoice_from:
            p["InvoiceFromDate"] = invoice_from
        if invoice_to:
            p["InvoiceToDate"] = invoice_to
        if invoice_status:
            p["InvoiceStatus"] = invoice_status
        if contact_id:
            p["ContactId"] = contact_id
        if invoice_number:
            p["InvoiceNumber"] = invoice_number
        if modified_since:
            p["LastModifiedFromDate"] = modified_since
        return _j(client.request("GET", "Invoices", p))

    @mcp.tool()
    def saasu_get_invoice(invoice_id: int) -> str:
        """Fetch one invoice (sale or purchase) with line items."""
        return _j(client.request("GET", f"Invoice/{invoice_id}"))

    @mcp.tool()
    def saasu_create_invoice(contact_id: int, line_items: list[dict], transaction_type: str = "S", transaction_date: str = "",
                             due_date: str = "", layout: str = "S", invoice_number: str = "", summary: str = "", notes: str = "",
                             invoice_type: str = "Tax Invoice", extra_fields: dict | None = None) -> str:
        """Create a sale (S) or purchase (P) invoice. WRITE: confirm with the user first.
        layout S=service (lines need Description, AccountId, TaxCode, TotalAmount) or I=item (lines need ItemId, Quantity, UnitPrice).
        Saasu returns the new InvoiceId and LastUpdatedId."""
        body: dict[str, Any] = {
            "TransactionType": transaction_type, "Layout": layout, "BillingContactId": contact_id,
            "TransactionDate": transaction_date or time.strftime("%Y-%m-%d"), "LineItems": line_items,
            "InvoiceType": invoice_type, "Summary": summary, "Notes": notes, "Currency": "AUD",
        }
        if due_date:
            body["DueDate"] = due_date
        if invoice_number:
            body["InvoiceNumber"] = invoice_number
        body.update(extra_fields or {})
        return _j(client.request("POST", "Invoice", body=body))

    @mcp.tool()
    def saasu_update_invoice(invoice_id: int, fields: dict) -> str:
        """Update an invoice. WRITE. Include the current LastUpdatedId from saasu_get_invoice in fields."""
        return _j(client.request("PUT", f"Invoice/{invoice_id}", body=fields))

    @mcp.tool()
    def saasu_email_invoice(invoice_id: int, to_email: str = "") -> str:
        """Email an invoice from Saasu. WRITE / outward-facing: confirm with the user first. Empty to_email sends to the billing contact."""
        if to_email:
            return _j(client.request("POST", f"Invoice/{invoice_id}/email", body={"EmailTo": to_email}))
        return _j(client.request("POST", f"Invoice/{invoice_id}/email-contact", body={}))

    @mcp.tool()
    def saasu_invoice_pdf(invoice_id: int, save_to: str = "") -> str:
        """Download an invoice as PDF. Saves to save_to (default ~/Downloads/saasu-invoice-<id>.pdf) and returns the path."""
        data = client.request("GET", f"Invoice/{invoice_id}/generate-pdf")
        if not isinstance(data, bytes):
            return _j(data)
        out = Path(save_to) if save_to else Path.home() / "Downloads" / f"saasu-invoice-{invoice_id}.pdf"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        return str(out)

    @mcp.tool()
    def saasu_list_payments(transaction_type: str = "SP", cleared_from: str = "", cleared_to: str = "", for_invoice_id: int | None = None,
                            modified_since: str = "", page: int = 1, page_size: int = 50) -> str:
        """List payments. transaction_type SP=sale payments received, PP=purchase payments made. Filter by cleared date window or invoice."""
        p: dict[str, Any] = {"TransactionType": transaction_type, "Page": page, "PageSize": min(page_size, 100)}
        if cleared_from:
            p["ClearedFromDate"] = cleared_from
        if cleared_to:
            p["ClearedToDate"] = cleared_to
        if for_invoice_id:
            p["ForInvoiceId"] = for_invoice_id
        if modified_since:
            p["LastModifiedFromDate"] = modified_since
        return _j(client.request("GET", "Payments", p))

    @mcp.tool()
    def saasu_create_payment(invoice_id: int, amount: float, paid_into_account_id: int, transaction_date: str = "",
                             transaction_type: str = "SP", reference: str = "") -> str:
        """Record a payment against an invoice. WRITE: confirm with the user first. transaction_type SP=sale payment received, PP=purchase payment made.
        paid_into_account_id = the bank account Id (see saasu_list_accounts with bank_accounts_only)."""
        body = {
            "TransactionType": transaction_type, "TransactionDate": transaction_date or time.strftime("%Y-%m-%d"),
            "PaymentAccountId": paid_into_account_id, "Reference": reference, "Currency": "AUD",
            "PaymentItems": [{"InvoiceTransactionId": invoice_id, "AmountPaid": amount}],
        }
        return _j(client.request("POST", "Payment", body=body))

    @mcp.tool()
    def saasu_list_items(search: str = "", active_only: bool = True, page: int = 1, page_size: int = 50) -> str:
        """List inventory / service items."""
        p: dict[str, Any] = {"IsActive": str(active_only).lower(), "Page": page, "PageSize": min(page_size, 100)}
        if search:
            p["SearchText"] = search
            p["SearchMethod"] = "Contains"
        return _j(client.request("GET", "Items", p))

    @mcp.tool()
    def saasu_list_accounts(account_type: str = "", bank_accounts_only: bool = False) -> str:
        """Chart of accounts. account_type one of Income, Expense, Asset, Equity, Liability, OtherIncome, OtherExpense, CostOfSales."""
        p: dict[str, Any] = {"IsActive": "true", "IncludeBuiltIn": "true"}
        if account_type:
            p["AccountType"] = account_type
        if bank_accounts_only:
            p["IsBankAccount"] = "true"
        return _j(client.request("GET", "Accounts", p))

    @mcp.tool()
    def saasu_bank_balances() -> str:
        """Current balance of every bank account in the file."""
        return _j(client.request("GET", "Accounts/BankAccountBalances"))

    @mcp.tool()
    def saasu_tax_codes() -> str:
        """List tax codes (GST etc.) needed on invoice lines."""
        return _j(client.request("GET", "TaxCodes"))

    @mcp.tool()
    def saasu_profit_and_loss(from_date: str, to_date: str, by_account_type: bool = False) -> str:
        """Profit and loss summary for a date range (YYYY-MM-DD)."""
        path = "Reports/ProfitAndLoss/SummaryByAccountType" if by_account_type else "Reports/ProfitAndLoss/Summary"
        return _j(client.request("GET", path, {"FromDate": from_date, "ToDate": to_date}))

    @mcp.tool()
    def saasu_sales_summary(from_date: str, to_date: str) -> str:
        """Sales statistics summary (totals, counts) for a date range."""
        return _j(client.request("GET", "Invoices/SalesStatsSummary", {"InvoiceFromDate": from_date, "InvoiceToDate": to_date}))

    @mcp.tool()
    def saasu_journals(from_date: str = "", to_date: str = "", page: int = 1, page_size: int = 50) -> str:
        """List general journals."""
        p: dict[str, Any] = {"Page": page, "PageSize": min(page_size, 100)}
        if from_date:
            p["FromDate"] = from_date
        if to_date:
            p["ToDate"] = to_date
        return _j(client.request("GET", "Journals", p))

    @mcp.tool()
    def saasu_payroll_employees() -> str:
        """List payroll employees (needs a plan with payroll)."""
        return _j(client.request("GET", "Payroll/Employees"))

    @mcp.tool()
    def saasu_search(text: str, scope: str = "All") -> str:
        """Free-text search across the file. scope: All, Transactions, Contacts, InventoryItems."""
        return _j(client.request("GET", "Search", {"Keywords": text, "Scope": scope}))

    @mcp.tool()
    def saasu_raw_request(method: str, path: str, params: dict | None = None, body: dict | None = None) -> str:
        """Escape hatch for any endpoint on https://api.saasu.com (e.g. GET 'ItemAdjustments'). Any non-GET is a WRITE: confirm first."""
        return _j(client.request(method, path, params, body))

    return mcp


# --------------------------------------------------------------------------- CLI modes
def cmd_login() -> int:
    print("Saasu sign-in (nothing is echoed; the password is used once and not stored).")
    username = input("Saasu email: ").strip()
    password = getpass.getpass("Saasu password: ")
    client = SaasuClient(creds={})
    try:
        grant = client.password_grant(username, password)
    except SaasuError as e:
        if "2fa" in str(e).lower() or "verification" in str(e).lower() or "400" in str(e):
            code = input("Saasu sent a code to your phone. Enter it: ").strip()
            grant = client.password_grant(username, password, code)
        else:
            raise
    del password
    ids = file_ids_from_scope(grant.get("scope", ""))
    existing = read_env_file()
    file_id = existing.get("SAASU_FILE_ID") or os.environ.get("SAASU_FILE_ID", "")
    if not file_id:
        if len(ids) == 1:
            file_id = ids[0]
        elif ids:
            print("This login can see these Saasu files:", ", ".join(ids))
            file_id = input("Which FileId should Claude use? ").strip()
        else:
            file_id = input("FileId (Settings > Web Services): ").strip()
    values = {"SAASU_FILE_ID": file_id, "SAASU_ACCESS_KEY": existing.get("SAASU_ACCESS_KEY", "")}
    client.creds = dict(values)
    client._store_grant(grant)
    print(f"Saved. Connected to FileId {file_id} via OAuth (refresh token good for 12 months).")
    return 0


def cmd_ping() -> int:
    client = SaasuClient()
    if not client.configured():
        print("not-configured", CRED_FILE)
        return 2
    try:
        data = client.request("GET", "FileIdentity")
    except SaasuError as e:
        print("FAIL", e)
        return 1
    name = data.get("Name") if isinstance(data, dict) else None
    print(json.dumps({"ok": True, "route": client.route, "file_id": client.file_id, "file_name": name}))
    return 0


def cmd_selftest() -> int:
    """Offline checks: env parsing, URL/auth building, throttle, token refresh, tool registration."""
    import tempfile

    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        (print("  ok ", msg) if cond else (failures.append(msg), print("  FAIL", msg)))

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "credentials.env"
        write_env_file({"SAASU_FILE_ID": "123", "SAASU_ACCESS_KEY": "ABC"}, p)
        check(oct(p.stat().st_mode & 0o777) == "0o600", "credentials file is mode 600")
        check(read_env_file(p) == {"SAASU_FILE_ID": "123", "SAASU_ACCESS_KEY": "ABC"}, "env round-trips")

    calls: list[tuple[str, str, dict]] = []

    class FakeResp:
        def __init__(self, status, payload, ctype="application/json"):
            self.status, self._p, self.headers = status, payload, {"Content-Type": ctype}

        def read(self):
            return json.dumps(self._p).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class FakeOpener:
        def open(self, req, timeout=0):
            calls.append((req.get_method(), req.full_url, dict(req.header_items())))
            if req.full_url.endswith("authorisation/refresh"):
                return FakeResp(200, {"access_token": "NEWTOK", "refresh_token": "NEWREF", "expires_in": 10800, "scope": "full fileid:123"})
            if "wsAccessKey=ABC" in req.full_url or req.headers.get("Authorization") == "Bearer NEWTOK":
                return FakeResp(200, {"Name": "Test File"})
            raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)

    os.environ["SAASU_NO_PERSIST"] = "1"
    c = SaasuClient({"SAASU_FILE_ID": "123", "SAASU_ACCESS_KEY": "ABC"}, opener=FakeOpener())
    check(c.route == "access_key", "route A detected")
    t0 = time.monotonic()
    c.request("GET", "FileIdentity")
    c.request("GET", "Contacts", {"Page": 1})
    check(time.monotonic() - t0 >= MIN_INTERVAL * 0.9, "throttle enforces ~1 req/s")
    check("FileId=123" in calls[0][1] and "wsAccessKey=ABC" in calls[0][1], "route A puts FileId + wsAccessKey on the URL")
    hdrs = {k.lower(): v for k, v in calls[0][2].items()}
    check(hdrs.get("x-api-version") == API_VERSION, "X-Api-Version header sent")
    check(hdrs.get("accept") == "application/json", "Accept json")

    calls.clear()
    c2 = SaasuClient({"SAASU_FILE_ID": "123", "SAASU_REFRESH_TOKEN": "OLDREF"}, opener=FakeOpener())
    check(c2.route == "oauth", "route B detected")
    data = c2.request("GET", "FileIdentity")
    check(calls[0][1].endswith("authorisation/refresh"), "expired/missing access token triggers refresh first")
    check(any(h.get("Authorization") == "Bearer NEWTOK" for _, _, h in calls), "bearer header used after refresh")
    check(data == {"Name": "Test File"}, "json body parsed")
    check(c2.creds["SAASU_REFRESH_TOKEN"] == "NEWREF", "rotated refresh token kept")

    c3 = SaasuClient({"SAASU_FILE_ID": "123", "SAASU_ACCESS_KEY": "WRONG"}, opener=FakeOpener())
    try:
        c3.request("GET", "FileIdentity")
        check(False, "401 raises SaasuError")
    except SaasuError as e:
        check("401" in str(e), "401 raises SaasuError")

    c4 = SaasuClient({}, opener=FakeOpener())
    try:
        c4.request("GET", "FileIdentity")
        check(False, "unconfigured client raises")
    except SaasuError:
        check(True, "unconfigured client raises a clear error")

    check(file_ids_from_scope("full fileid:15431 fileid:14078") == ["15431", "14078"], "scope FileId parsing")
    check(redact({"wsAccessKey": "x", "a": [{"access_token": "y"}]}) == {"wsAccessKey": "***", "a": [{"access_token": "***"}]}, "redact() strips secrets")

    srv = build_server()
    names = sorted(srv.tools)
    check(len(names) >= 20 and "saasu_status" in names and "saasu_raw_request" in names, f"server registers {len(names)} tools")
    schema = _schema_for(srv.tools["saasu_create_invoice"])
    check(schema["properties"]["line_items"]["type"] == "array" and "contact_id" in schema["required"], "input schemas derived from signatures")

    import subprocess
    env = dict(os.environ, SAASU_CONFIG_DIR=tempfile.mkdtemp())
    proc = subprocess.Popen([sys.executable, __file__, "serve"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "saasu_status", "arguments": {}}}]
    outp, _ = proc.communicate("\n".join(json.dumps(m) for m in msgs) + "\n", timeout=20)
    replies = {r["id"]: r for r in (json.loads(l) for l in outp.splitlines() if l.strip())}
    check(replies[1]["result"]["serverInfo"]["name"] == "saasu", "stdio initialize handshake")
    check(len(replies[2]["result"]["tools"]) == len(names), "stdio tools/list matches registry")
    check('"connected": false' in replies[3]["result"]["content"][0]["text"], "stdio tools/call saasu_status reports not connected without creds")
    print("SELFTEST", "PASS" if not failures else f"FAIL ({len(failures)})")
    return 0 if not failures else 1


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "serve"
    if mode == "serve":
        build_server().serve_stdio()
        return 0
    if mode == "login":
        return cmd_login()
    if mode == "ping":
        return cmd_ping()
    if mode == "selftest":
        return cmd_selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
