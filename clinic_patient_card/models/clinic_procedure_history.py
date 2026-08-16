# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ClinicProcedureHistory(models.Model):
    _name = "clinic.procedure.history"
    _description = "Patient Procedure (planned / performed)"
    _order = "planned_date desc, procedure_date desc, id desc"

    partner_id = fields.Many2one(
        "res.partner", string="Patient", required=True, ondelete="cascade", index=True,
    )
    # Procedure = a standard service product; `name` is a free-text label/fallback.
    procedure_id = fields.Many2one(
        "product.product", string="Procedure",
        domain="[('is_clinic_procedure', '=', True)]",
    )
    name = fields.Char(string="Procedure (label)")
    # Planned vs performed — one list shows both, distinguished by status.
    status = fields.Selection(
        [
            ("planned", "Planned"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("postponed", "Postponed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="planned",
        required=True,
    )
    planned_date = fields.Date(string="Planned Date")
    procedure_date = fields.Date(string="Done Date")
    # Who performed the procedure (doctor).
    doctor_id = fields.Many2one("res.users", string="Performed By")
    tooth = fields.Char(string="Tooth (FDI)")
    note = fields.Text(string="Notes")

    @api.onchange("procedure_id")
    def _onchange_procedure_id(self):
        if self.procedure_id and not self.name:
            self.name = self.procedure_id.name
