# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


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
    # Mixed payment split — reviewer: "the mixed method must show terminal and cash".
    amount_cash = fields.Monetary(
        string="Cash Amount", currency_field="currency_id",
    )
    amount_terminal = fields.Monetary(
        string="Terminal Amount", currency_field="currency_id",
    )

    @api.onchange("payment_method", "amount_cash")
    def _onchange_mixed_split(self):
        # Convenience: typing the cash part auto-fills the terminal remainder.
        if self.payment_method == "mixed" and self.amount_total:
            self.amount_terminal = max(0.0, self.amount_total - (self.amount_cash or 0.0))

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
        cash = terminal = 0.0
        if self.payment_method == "mixed":
            cash = self.amount_cash or 0.0
            terminal = self.amount_terminal or 0.0
            rounding = self.currency_id.rounding or 0.01
            if cash < 0 or terminal < 0:
                raise UserError(_("Cash and terminal amounts cannot be negative."))
            if float_compare(cash + terminal, self.amount_total,
                             precision_rounding=rounding) != 0:
                raise UserError(_(
                    "Mixed payment: cash (%(cash).2f) + terminal (%(term).2f) "
                    "must equal the total (%(total).2f).",
                    cash=cash, term=terminal, total=self.amount_total,
                ))
        appt.payment_method = self.payment_method
        appt._create_invoice_from_procedures()
        appt.write({
            "clinic_state": "paid",
            "amount_paid": self.amount_total,
            "amount_cash": cash,
            "amount_terminal": terminal,
        })
        return {"type": "ir.actions.act_window_close"}
