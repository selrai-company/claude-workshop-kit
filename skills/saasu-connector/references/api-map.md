# Saasu API map (verified against https://api.saasu.com on 2026-09-10)

Base URL `https://api.saasu.com/`. JSON in and out. Send `X-Api-Version: 1.0`.
Every call carries `?FileId=<id>` plus either `&wsAccessKey=<key>` (route A) or an
`Authorization: Bearer <token>` header (route B). Self-documenting help lives at the
base URL: `/Help/Authentication`, `/Help/Versioning`, `/Help/Api/<METHOD>-<Resource>`.

## Authentication

| Route | How | Where the values come from | Notes |
|---|---|---|---|
| A. Access key | `wsAccessKey` + `FileId` query params | Saasu web app: Settings > Web Services | Saasu says it will be phased out "sometime in the future"; still works |
| B. OAuth2 password grant | `POST /authorisation/token` body `{grant_type:"password", username, password, scope:"full", verification_code?}` | The user's Saasu login | Only grant Saasu supports. No app registration, no client id. Access token 10800 s, refresh token 12 months. `verification_code` = SMS 2FA code when 2FA is on |
| B refresh | `POST /authorisation/refresh` body `{grant_type:"refresh_token", refresh_token, scope:""}` | | Returns a new pair |

`scope` in the token response lists every file the login can see: `full fileid:15431 fileid:14078`.

## Limits (saasu.com/help/api-limits)

- 1 request per second, hard.
- Daily requests by plan: Small 4,000 · Growing 3,000 · Medium 6,000 · Large 8,000 · X-Large 20,000.
- Exceeding the daily cap blocks the file for 24 hours.
- Sync work: use `LastModifiedFromDate` + `LastModifiedToDate` (both required together), max 50 items per request.
- `PageSize` max 100, default 25.

## Endpoints

| Area | Calls |
|---|---|
| Accounts | `GET Accounts` (IsActive, IsBankAccount, AccountType, IncludeBuiltIn) · `GET Accounts/BankAccountBalances` · `GET/POST/PUT/DELETE Account/{id}` |
| Activities | `GET Activities` · `GET/POST/PUT/DELETE Activity/{id}` |
| Attachments | `POST InvoiceAttachment` · `GET/DELETE InvoiceAttachment/{id}` · `GET InvoiceAttachments/{invoiceId}` |
| Company | `GET Companies` · `GET/POST/PUT/DELETE Company/{id}` |
| Contacts | `GET Contacts` (GivenName, FamilyName, CompanyName, CompanyId, Email, IsCustomer, IsSupplier, IsContractor, IsPartner, Tags, ContactId) · `GET/POST/PUT/DELETE Contact/{id}` · `GET Contact/{id}/generate-pdf?GenerateType=Statement` · `GET/POST/PUT ContactAggregate/{id}` |
| DeletedEntities | `GET DeletedEntities?EntityType=Sale|Purchase|SalePayment|PurchasePayment|Item|Contact|Journal` |
| FileIdentity | `GET FileIdentity` (the smoke read) · `GET FileIdentities` · `PUT FileIdentity` |
| Invoices | `GET Invoices` (InvoiceNumber, PurchaseOrderNumber, TransactionType S/P, InvoiceStatus I/Q/O, PaymentStatus P/U/A, ContactId, date windows, Tags) · `GET/POST/PUT/DELETE Invoice/{id}` · `GET Invoices/SalesStatsSummary` · `GET Invoice/{id}/generate-pdf` · `POST Invoice/{id}/email` body `{"EmailTo": "..."}` · `POST Invoice/{id}/email-contact` |
| Items | `GET Items` (SearchText, SearchMethod, ItemType I/C, IsActive) · `GET/POST/PUT/DELETE Item/{id}` · `POST Item/{id}/build` · ItemAdjustments · ItemTransfers |
| Journals | `GET Journals` · `GET/POST/PUT/DELETE Journal/{id}` |
| LookupData | Countries, Currencies, DateFormats, IndustryTypes, NumberFormats, Zones |
| Payments | `GET Payments` (TransactionType SP/PP, ForInvoiceId, ClearedFromDate+ClearedToDate, LastModified window) · `GET/POST/PUT/DELETE Payment/{id}` |
| Payroll | `GET Payroll/Employees` · `GET Payroll/Employee/{id}` · Entitlements · PayrollEntries · Timesheet CRUD · LeaveRequest CRUD · `GET Payroll/Payslip/{id}/generate-pdf` |
| Reports | `GET Reports/ProfitAndLoss/Summary?FromDate&ToDate` · `GET Reports/ProfitAndLoss/SummaryByAccountType` |
| Search | `GET Search?Keywords=&Scope=All|Transactions|Contacts|InventoryItems` |
| TaxCodes | `GET TaxCodes` · `GET TaxCode/{id}` |
| User | `GET User` · `PUT User` · 2FA opt-in/out · reset-password |

No webhooks. Poll with the LastModified window and DeletedEntities for sync.

## Payload shapes that matter

**Invoice (POST Invoice)**: `TransactionType` S/P, `Layout` S (service) or I (item), `BillingContactId`,
`TransactionDate`, `InvoiceType` "Tax Invoice", `Currency` "AUD", `IsTaxInc`, `LineItems[]`.
Service line: `Description`, `AccountId`, `TaxCode` (e.g. G1), `TotalAmount`.
Item line: `InventoryId`, `Quantity`, `UnitPrice`, `TaxCode`. Optional `Terms {Type, Interval, IntervalType}`,
`Summary`, `NotesInternal`, `NotesExternal`, `QuickPayment`, `SendEmailToContact`.
Updates (PUT) must include the current `LastUpdatedId` from a fresh GET (optimistic concurrency).

**Payment (POST Payment)**: `TransactionType` SP/PP, `TransactionDate`, `PaymentAccountId` (bank account),
`Reference`, `Currency`, `PaymentItems[{InvoiceTransactionId, AmountPaid}]`.

**Contact (POST Contact)**: `GivenName`, `FamilyName`, `EmailAddress`, `PrimaryPhone`, `MobilePhone`,
`CompanyId` (link to a Company record, not a name), `IsCustomer`, `IsSupplier`, `IsActive`,
`PostalAddress {Street, City, State, Postcode, Country}`, `Tags[]`.

## Errors

- 401: bad key / FileId / expired token. 403: user lacks permission for that record. 429: rate limit.
- 400 on write: validation; body carries the reason. Common cause: missing `LastUpdatedId` on PUT.

## Old SDKs worth reading for shapes (none maintained)

- `saasu/api-sdk-dotnet` (official C#, NuGet `Saasu.API.Dotnet.Sdk`, last push 2023)
- `saasu/api-sdk-ruby` (official Ruby, gem `saasu2`, 2020)
- `aleahy/saasu-connect` (PHP, 2022, has the 1 req/s limiter)
