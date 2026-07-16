# -*- coding: utf-8 -*-
from odoo import fields, models


class ClinicPatientAllergy(models.Model):
    _name = "clinic.patient.allergy"
    _description = "Patient Allergy"
    _order = "severity desc, id"

    partner_id = fields.Many2one(
        "res.partner", string="Patient", required=True, ondelete="cascade", index=True,
    )
    allergy_type = fields.Selection(
        [
            ("medication", "Medication"),
            ("material", "Material (e.g. latex)"),
            ("food", "Food"),
            ("other", "Other"),
        ],
        string="Type",
        required=True,
        default="medication",
    )
    name = fields.Char(string="Substance", required=True)
    reaction = fields.Char(string="Reaction")
    severity = fields.Selection(
        [
            ("mild", "Mild"),
            ("moderate", "Moderate"),
            ("severe", "Severe"),
        ],
        string="Severity",
        default="moderate",
    )
    note = fields.Char(string="Note")
