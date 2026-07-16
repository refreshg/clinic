# -*- coding: utf-8 -*-
from odoo import fields, models


class ClinicPatientPhone(models.Model):
    _name = "clinic.patient.phone"
    _description = "Patient Phone Number"
    _order = "sequence, id"

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
        ],
        string="Channel",
    )
    # For minors: the phone may belong to a parent/guardian.
    owner_name = fields.Char(string="Owner / Guardian Name")
    # Emergency contact marked directly on the phone row.
    is_emergency = fields.Boolean(string="Emergency")
    relation = fields.Char(string="Relationship")
    is_foreign_number = fields.Boolean(string="Foreign Number")
    note = fields.Char(string="Note")
