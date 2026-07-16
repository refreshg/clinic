# -*- coding: utf-8 -*-
from odoo import fields, models


class ClinicPatientTooth(models.Model):
    _name = "clinic.patient.tooth"
    _description = "Patient Dental Chart (tooth)"
    _order = "tooth_number, id"

    partner_id = fields.Many2one(
        "res.partner", string="Patient", required=True, ondelete="cascade", index=True,
    )
    # FDI two-digit tooth number (e.g. 11-18, 21-28, 31-38, 41-48; 51-85 for milk teeth).
    tooth_number = fields.Char(string="Tooth (FDI)", required=True)
    status = fields.Selection(
        [
            ("healthy", "Healthy"),
            ("caries", "Caries"),
            ("filled", "Filled"),
            ("crown", "Crown"),
            ("root_canal", "Root Canal"),
            ("implant", "Implant"),
            ("missing", "Missing"),
            ("to_extract", "To Extract"),
            ("other", "Other"),
        ],
        string="Status",
        default="healthy",
    )
    note = fields.Char(string="Note")
