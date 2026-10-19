# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ClearfactsConfig(models.Model):
    _name = "clearfacts.config"
    _description = "Clearfacts API connection"

    name = fields.Char(default="Clearfacts", required=True)
    active = fields.Boolean(default=True)
    auth_mode = fields.Selection(
        [("token", "Personal Access Token"), ("oidc", "OpenID Connect")],
        default="token", required=True,
    )
    token = fields.Char(help="80-character personal access token from Clearfacts > Integrations.")
    client_id = fields.Char()
    client_secret = fields.Char()
    redirect_uri = fields.Char(default="http://localhost:8765/callback")
    last_sync = fields.Datetime(readonly=True)
    last_error = fields.Text(readonly=True)

    _sql_constraints = [
        ("unique_name", "unique(name)", "Only one Clearfacts config per name.")
    ]

    @api.model
    def get_config(self):
        conf = self.search([], limit=1)
        if not conf:
            conf = self.create({"name": "Clearfacts"})
        return conf

    def _get_client(self):
        from clearfacts import ClearfactsClient

        self.ensure_one()
        if self.auth_mode == "token":
            if not self.token:
                raise ValueError("Clearfacts token is not set.")
            return ClearfactsClient(token=self.token)
        if not (self.client_id and self.client_secret):
            raise ValueError("Clearfacts OIDC client ID and secret are required.")
        return ClearfactsClient.from_oidc(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri or "http://localhost:8765/callback",
            open_browser=False,
        )

    def action_test_connection(self):
        try:
            info = self._get_client().test_token()
            self.last_error = False
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Clearfacts OK",
                    "message": "Connected as %s" % info.get("email", info.get("sub", "?")),
                    "type": "success",
                    "sticky": False,
                },
            }
        except Exception as e:
            self.last_error = str(e)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Clearfacts connection failed",
                    "message": str(e)[:500],
                    "type": "danger",
                    "sticky": True,
                },
            }

    def action_sync_now(self):
        self.ensure_one()
        try:
            summary = self.env["clearfacts.sync"].run_all(self)
            self.last_sync = fields.Datetime.now()
            self.last_error = False
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Clearfacts sync done",
                    "message": summary,
                    "type": "success",
                },
            }
        except Exception as e:
            self.last_error = str(e)
            _logger.exception("Clearfacts sync failed")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Clearfacts sync failed",
                    "message": str(e)[:500],
                    "type": "danger",
                    "sticky": True,
                },
            }
