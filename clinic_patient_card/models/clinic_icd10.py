# Part of clinic_patient_card. LGPL-3.
"""ICD-10 diagnosis catalog (D3).

A tiny local catalog — the dental K00–K14 subset is seeded from data/
(admins can extend it under Configuration). A procedure row on a visit
references one code, Dentos-style (tooth → ICD-10 → procedure).
"""

from odoo import api, fields, models


class ClinicIcd10(models.Model):
    _name = "clinic.icd10"
    _description = "ICD-10 Diagnosis"
    _order = "code"

    code = fields.Char(string="Code", required=True, index=True)
    name = fields.Char(string="Name", required=True, translate=True)
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        "unique(code)", "This ICD-10 code already exists.",
    )

    @api.depends("code", "name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.code} - {rec.name}"
