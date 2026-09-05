# -*- coding: utf-8 -*-
from odoo import _, fields, models


class ClinicRequestRejectWizard(models.TransientModel):
    """Rejection of a purchase request requires a comment (reviewer item 88)."""
    _name = "clinic.request.reject.wizard"
    _description = "Reject Purchase Request"

    request_id = fields.Many2one(
        "clinic.purchase.request", required=True, readonly=True)
    reason = fields.Text(string="Rejection Reason", required=True)

    def action_confirm(self):
        self.ensure_one()
        self.request_id.write({
            "state": "rejected",
            "reject_reason": self.reason,
        })
        self.request_id.message_post(
            body=_("Request rejected: %s") % self.reason)
        return {"type": "ir.actions.act_window_close"}
