# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    clearfacts_document_uuid = fields.Char(
        string="Clearfacts Document ID",
        copy=False,
        readonly=True,
        help="UUID returned by Clearfacts after uploading this document.",
    )
    clearfacts_pushed = fields.Boolean(default=False, copy=False)

    def action_push_to_clearfacts(self):
        """Upload this move's PDF/XML attachment to the matching Clearfacts inbox."""
        self.ensure_one()
        if self.move_type not in ("in_invoice", "in_refund"):
            raise ValueError(_("Only vendor bills and refunds can be pushed to Clearfacts."))
        conf = self.env["clearfacts.config"].get_config()
        client = conf._get_client()

        partner_vat = self.commercial_partner_id.vat or ""
        if not partner_vat:
            raise ValueError(_("The vendor has no VAT number; cannot match a Clearfacts administration."))
        vat = partner_vat.upper().replace("BE", "")

        try:
            admin = client.administration(company_number=vat)
        except Exception:
            admin = client.administration(company_number="BE" + vat)

        att = self._get_clearfacts_attachment()
        if not att:
            raise ValueError(_("No PDF or XML attachment found on this bill."))

        result = client.upload_file(
            vat_number=admin.vat_number,
            filename=att.name,
            invoice_type="PURCHASE",
            file_bytes=att.raw,
            content_type=att.mimetype or "application/pdf",
        )
        self.write(
            {
                "clearfacts_document_uuid": result.uuid,
                "clearfacts_pushed": True,
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Pushed to Clearfacts"),
                "message": _("Document %s, %d page(s).")
                % (result.uuid, result.amount_of_pages),
                "type": "success",
            },
        }

    def _get_clearfacts_attachment(self):
        for att in self.attachment_ids:
            name = (att.name or "").lower()
            if name.endswith((".pdf", ".xml", ".jpg", ".jpeg")):
                return att
        return self.attachment_ids[:1] or None
