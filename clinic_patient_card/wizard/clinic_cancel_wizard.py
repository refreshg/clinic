# -*- coding: utf-8 -*-
from odoo import fields, models


class ClinicCancelWizard(models.TransientModel):
    """Cancel a clinic visit with a reason — one popup, no page navigation."""
    _name = "clinic.cancel.wizard"
    _description = "Cancel Clinic Visit"

    event_id = fields.Many2one("calendar.event", required=True)
    reason = fields.Text(string="Cancellation Reason", required=True)

    def action_confirm(self):
        self.ensure_one()
        self.event_id.write({
            "cancel_reason": self.reason,
            "clinic_state": "cancelled",
        })
        return {"type": "ir.actions.act_window_close"}
