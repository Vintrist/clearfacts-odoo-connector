# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ClearfactsSync(models.TransientModel):
    _name = "clearfacts.sync"
    _description = "Clearfacts data synchronisation"

    def run_all(self, config):
        client = config._get_client()
        parts = []
        parts.append("admins: %d" % self._sync_administrations(client))
        parts.append("journals: %d" % self._sync_journals(client))
        parts.append("customers: %d" % self._sync_customers(client))
        return ", ".join(parts)

    def _sync_administrations(self, client):
        Partner = self.env["res.partner"].sudo()
        count = 0
        for admin in client.administrations():
            vat = admin.vat_number
            partner = Partner.search([("vat", "ilike", vat)], limit=1) or Partner.search(
                [("company_registry", "=", admin.company_number)], limit=1
            )
            vals = {
                "name": admin.name,
                "is_company": True,
                "company_type": "company",
                "vat": vat,
                "company_registry": admin.company_number,
                "customer_rank": 1,
            }
            if admin.address:
                vals["street"] = admin.address.street_address
                if admin.address.country and admin.address.country.iso2:
                    country = self.env["res.country"].search(
                        [("code", "=", admin.address.country.iso2)], limit=1
                    )
                    if country:
                        vals["country_id"] = country.id
            if partner:
                partner.write(vals)
            else:
                Partner.create(vals)
            count += 1
        return count

    def _sync_journals(self, client):
        Journal = self.env["account.journal"].sudo()
        Company = self.env["res.company"].sudo()
        count = 0
        for admin in client.administrations():
            company = Company.search(
                [("partner_id.vat", "ilike", admin.vat_number)], limit=1
            ) or Company.search(
                [("partner_id.company_registry", "=", admin.company_number)], limit=1
            )
            if not company:
                _logger.info(
                    "Clearfacts: no Odoo company for %s, skipping journals",
                    admin.company_number,
                )
                continue
            for j in client.journals(admin.company_number):
                existing = Journal.search(
                    [("code", "=", j.id), ("company_id", "=", company.id)], limit=1
                )
                vals = {
                    "name": j.name,
                    "code": j.id,
                    "type": "purchase" if not j.credit_note else "general",
                    "company_id": company.id,
                }
                if existing:
                    existing.write(vals)
                else:
                    Journal.create(vals)
                count += 1
        return count

    def _sync_customers(self, client):
        Partner = self.env["res.partner"].sudo()
        count = 0
        for admin in client.administrations():
            for page in client.customers(admin.company_number):
                for c in page:
                    partner = Partner.search(
                        [("ref", "=", "CF-%s-%s" % (admin.company_number, c.id))],
                        limit=1,
                    )
                    vals = {
                        "name": c.name,
                        "ref": "CF-%s-%s" % (admin.company_number, c.id),
                        "is_company": True,
                        "customer_rank": 1,
                        "supplier_rank": 1,
                    }
                    if partner:
                        partner.write(vals)
                    else:
                        Partner.create(vals)
                    count += 1
        return count
