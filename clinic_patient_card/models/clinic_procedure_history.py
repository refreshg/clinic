# -*- coding: utf-8 -*-
from odoo import fields, models


class ClinicProcedureHistory(models.Model):
    _name = "clinic.procedure.history"
    _description = "Performed Procedure History"
    _order = "procedure_date desc, id desc"

    partner_id = fields.Many2one(
        "res.partner", string="Patient", required=True, ondelete="cascade", index=True,
    )
    procedure_date = fields.Date(string="Date")
    name = fields.Char(string="Procedure", required=True)
    # Who performed the procedure (doctor).
    doctor_id = fields.Many2one("res.users", string="Performed By")
    tooth = fields.Char(string="Tooth (FDI)")
    note = fields.Text(string="Notes")
