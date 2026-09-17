# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ClinicProcedureHistory(models.Model):
    _name = "clinic.procedure.history"
    _description = "Patient Procedure (planned / performed)"
    _order = "planned_date desc, procedure_date desc, id desc"

    partner_id = fields.Many2one(
        "res.partner", string="Patient", ondelete="cascade", index=True,
    )
    # Link to the visit that produced this procedure (auto-filled on Done).
    appointment_id = fields.Many2one(
        "calendar.event", string="Appointment", ondelete="set null", index=True,
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
        default="done",
        required=True,
    )
    qty = fields.Float(string="Qty", default=1.0)
    planned_date = fields.Date(string="Planned Date")
    procedure_date = fields.Date(string="Done Date")
    # Who performed the procedure (doctor).
    doctor_id = fields.Many2one("res.users", string="Performed By")
    tooth = fields.Char(string="Tooth (FDI)")
    note = fields.Text(string="Notes")
    # D3 — Dentos chain: tooth → ICD-10 diagnosis → procedure, priced.
    icd10_id = fields.Many2one("clinic.icd10", string="ICD-10 Diagnosis")
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id.id,
    )
    price_unit = fields.Monetary(
        string="Price", currency_field="currency_id",
        help="Unit price; defaults to the procedure product's sale price.",
    )
    discount_percent = fields.Float(string="Discount (%)")
    amount_total = fields.Monetary(
        string="Total", currency_field="currency_id",
        compute="_compute_amount_total", store=True,
    )

    @api.depends("qty", "price_unit", "discount_percent")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = (
                rec.qty * rec.price_unit * (1 - (rec.discount_percent or 0.0) / 100.0)
            )

    @api.onchange("procedure_id")
    def _onchange_procedure_price(self):
        if self.procedure_id and not self.price_unit:
            self.price_unit = self.procedure_id.lst_price

    @api.onchange("procedure_id")
    def _onchange_procedure_id(self):
        if self.procedure_id and not self.name:
            self.name = self.procedure_id.name

    @api.onchange("appointment_id")
    def _onchange_appointment_id(self):
        if self.appointment_id and self.appointment_id.patient_id and not self.partner_id:
            self.partner_id = self.appointment_id.patient_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("appointment_id") and not vals.get("partner_id"):
                appt = self.env["calendar.event"].browse(vals["appointment_id"])
                if appt.patient_id:
                    vals["partner_id"] = appt.patient_id.id
        return super().create(vals_list)
