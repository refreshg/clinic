# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

PHONE_RE = re.compile(r"^[0-9+\-\s()]+$")


class ClinicPatientPhone(models.Model):
    _name = "clinic.patient.phone"
    _description = "Patient Phone Number"
    _order = "sequence, id"

    @api.constrains("phone")
    def _check_phone_digits(self):
        for rec in self:
            if rec.phone and not PHONE_RE.match(rec.phone.strip()):
                raise ValidationError(_(
                    "Phone number may contain digits only: %s"
                ) % rec.phone)

    partner_id = fields.Many2one(
        "res.partner", string="Patient", required=True, ondelete="cascade", index=True,
    )
    sequence = fields.Integer(string="Priority", default=10)
    phone = fields.Char(string="Phone", required=True)
    phone_type = fields.Selection(
        [
            ("mobile", "Mobile"),
            ("home", "Home"),
            ("work", "Work"),
            ("parent", "Parent / Guardian"),
            ("other", "Other"),
        ],
        string="Type",
        default="mobile",
    )
    # Preferred communication channel for THIS number.
    channel = fields.Selection(
        [
            ("sms", "SMS"),
            ("call", "Call"),
            ("whatsapp", "WhatsApp"),
            ("email", "Email"),
        ],
        string="Channel",
    )
    # Country dialing code (e.g. +995, +49) — useful for foreign numbers.
    country_code = fields.Char(string="Country Code")
    # Mark the primary Georgian and primary foreign numbers.
    is_primary = fields.Boolean(string="Primary")
    # For minors: the phone may belong to a parent/guardian.
    owner_name = fields.Char(string="Owner / Guardian Name")
    # Emergency contact marked directly on the phone row.
    is_emergency = fields.Boolean(string="Emergency")
    relation = fields.Char(string="Relationship")
    is_foreign_number = fields.Boolean(string="Foreign Number")
    note = fields.Char(string="Note")
