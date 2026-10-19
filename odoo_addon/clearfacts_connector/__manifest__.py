{
    "name": "Clearfacts Connector",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Sync Clearfacts pre-accounting data into Odoo and push documents back.",
    "description": """
Connects Odoo to the Clearfacts GraphQL API (api.clearfacts.be).

* Pull administrations, journals and customers from Clearfacts into Odoo
  (res.partner / account.journal).
* Push PDF or UBL XML attachments from account.move bills to the matching
  Clearfacts administration inbox via uploadFile.
* Store a personal access token or OIDC client credentials in settings.
* No document-list polling: Clearfacts has no 'list documents' query, so
  uploaded UUIDs are tracked on the move itself.
    """,
    "author": "Vintrist",
    "website": "https://github.com/Vintrist/clearfacts-odoo-connector",
    "license": "LGPL-3",
    "depends": ["account", "base_setup"],
    "data": [
        "security/ir.model.access.csv",
        "views/clearfacts_config_views.xml",
        "views/account_move_views.xml",
        "data/cron.xml",
    ],
    "installable": True,
    "application": False,
}
