# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ClinicPaymentWizard(models.TransientModel):
    _name = "clinic.payment.wizard"
    _description = "Clinic Visit Payment"

    appointment_id = fields.Many2one("calendar.event", required=True)
    partner_id = fields.Many2one(
        related="appointment_id.patient_id", string="Patient", readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id.id,
    )
    amount_total = fields.Monetary(
        string="Amount", compute="_compute_amount", currency_field="currency_id",
    )
    summary = fields.Html(string="Procedures", compute="_compute_amount", sanitize=False)
    payment_method = fields.Selection(
        [
            ("cash", "Cash"),
            ("card", "Card"),
            ("transfer", "Bank Transfer"),
            ("insurance", "Insurance"),
            ("mixed", "Mixed"),
        ],
        string="Payment Method",
        required=True,
        default="cash",
    )
    note = fields.Char(string="Note")

    @api.depends("appointment_id")
    def _compute_amount(self):
        for wiz in self:
            lines = wiz.appointment_id.procedure_line_ids.filtered(lambda l: l.procedure_id)
            total = 0.0
            rows = ""
            for line in lines:
                price = line.procedure_id.list_price
                qty = line.qty or 1.0
                sub = price * qty
                total += sub
                rows += (
                    "<tr>"
                    f"<td>{line.procedure_id.display_name}</td>"
                    f"<td style='text-align:right'>{qty:g}</td>"
                    f"<td style='text-align:right'>{price:.2f}</td>"
                    f"<td style='text-align:right'>{sub:.2f}</td>"
                    "</tr>"
                )
            wiz.amount_total = total
            if rows:
                wiz.summary = (
                    "<table class='table table-sm'>"
                    "<thead><tr><th>Procedure</th>"
                    "<th style='text-align:right'>Qty</th>"
                    "<th style='text-align:right'>Price</th>"
                    "<th style='text-align:right'>Subtotal</th></tr></thead>"
                    f"<tbody>{rows}</tbody></table>"
                )
            else:
                wiz.summary = "<p class='text-muted'>No procedures recorded.</p>"

    def action_confirm(self):
        self.ensure_one()
        appt = self.appointment_id
        appt.payment_method = self.payment_method
        appt._create_invoice_from_procedures()
        appt.write({"clinic_state": "paid"})
        return {"type": "ir.actions.act_window_close"}
