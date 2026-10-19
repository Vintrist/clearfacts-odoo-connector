# Clearfacts ↔ Odoo Connector

Python client for the [Clearfacts GraphQL API](https://developer.clearfacts.be) plus an Odoo bridge module that syncs administrations, journals, customers and uploaded documents into Odoo accounting.

## What it does

**Clearfacts client** (`clearfacts/`)
- Authenticates with a personal access token (80-char, non-expiring) or OpenID Connect authorization-code flow
- Queries: accountant, associates, associate groups, administrations, a single administration, journals, customers (paginated, 100/page), company statistics (AIR / processing), archive categories, and individual documents by UUID
- Mutations: upload invoice/purchase files to an administration inbox, upload archive files, add/edit associates, update app info (badge, icon, image)
- File uploads go as `multipart/form-data` with the file field named `file`, matching Clearfacts' own curl examples
- Supported upload types: PDF, JPEG, XML (Peppol Billing 3.0 / UBL.BE / legacy E-FFF)

**Odoo module** (`odoo_addon/clearfacts_connector/`)
- Settings page to store the Clearfacts token or OIDC client credentials
- One-way sync: pull administrations → `res.partner` (companies), customers → `res.partner`, journals → `account.journal`
- Push path: attach a PDF/XML on an Odoo `account.move` and the module uploads it to the matching Clearfacts administration inbox via `uploadFile`
- Cron-friendly: each sync method is a plain Python call you can schedule

## Quick start (client only)

```bash
pip install -r requirements.txt
```

```python
from clearfacts import ClearfactsClient

cf = ClearfactsClient(token="your-80-char-personal-access-token")

for admin in cf.administrations():
    print(admin.name, admin.company_number)

for journal in cf.journals(company_number="0123123123"):
    print(journal.id, journal.name, "credit note" if journal.credit_note else "")

for page in cf.customers(company_number="0123123123"):  # yields pages of <=100
    for c in page:
        print(c.id, c.name)
```

Upload a purchase invoice:

```python
result = cf upload_file(
    vat_number="0123123123",
    filename="invoice.pdf",
    invoice_type="PURCHASE",
    file_path="/path/to/invoice.pdf",
)
print(result.uuid, result.amount_of_pages)
```

## OIDC instead of a personal token

1. In Clearfacts: profile → Integrations → Create new application, set a redirect URI, copy the client ID and secret (shown once).
2. Scopes map to what you need: `read_administrations`, `journal_read`, `contact_read`, `upload_document`, `archive`, `accountant`, `statistics`, `associate_read` / `associate_actions`.
3. The client handles the authorization-code flow and stores the resulting 80-char access token (the JWT itself is also a valid Bearer token).

```python
cf = ClearfactsClient.from_oidc(
    client_id="...", client_secret="...", redirect_uri="https://your.app/callback"
)
```

## Odoo install

1. Copy `odoo_addon/clearfacts_connector` into your addons path.
2. Update the app list, install **Clearfacts Connector**.
3. Settings → Clearfacts: paste your token (or OIDC credentials) and save.
4. Open Accounting → Configuration → Clearfacts and run **Sync now**, or let the daily cron do it.

The module targets Odoo 16/17/18. It depends on `account` and `base_setup`.

## Notes & limits

- There is no "list all documents" query in Clearfacts' API — document IDs only come back from uploads. The Odoo module therefore tracks uploaded UUIDs on `account.move` rather than polling.
- `customers` is capped at 100 per request; the client paginates with `offset` automatically.
- Statistics `type` accepts `AIR` (auto-recognised invoices) or `processing` (documents booked into the ledger).
- Clearfacts was acquired by Wolters Kluwer in September 2024; the API is still public and documented, but direction may shift.
- Dev support: dev-support@clearfacts.be. Status page: https://status.clearfacts.be

## License

MIT.