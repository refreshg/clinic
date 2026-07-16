# -*- coding: utf-8 -*-
from odoo import fields, models


class ClinicPatientDocument(models.Model):
    _name = "clinic.patient.document"
    _description = "Patient Document"
    _order = "date desc, id desc"

    partner_id = fields.Many2one(
        "res.partner", string="Patient", required=True, ondelete="cascade", index=True,
    )
    doc_type = fields.Selection(
        [
            ("id_scan", "ID Scan"),
            ("consent", "Consent Form"),
            ("xray", "X-ray / Diagnostic"),
            ("insurance", "Insurance Document"),
            ("other", "Other"),
        ],
        string="Document Type",
        required=True,
        default="other",
    )
    name = fields.Char(string="Title", required=True)
    date = fields.Date(string="Date", default=fields.Date.context_today)
    attachment = fields.Binary(string="File", attachment=True)
    filename = fields.Char(string="Filename")
    # Drawn signature for consent forms (standard signature widget, Community).
    signature = fields.Binary(string="Signature")
    note = fields.Char(string="Note")
