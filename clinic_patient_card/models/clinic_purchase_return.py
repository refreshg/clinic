# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ClinicPurchaseReturn(models.Model):
    """Return/exchange of a delivered clinic order (reviewer batch #2 B4,
    items 34-40). The manager opens it from the order within 48h of the
    receipt; the supplier reviews and approves/rejects; the physical flow is
    a standard reverse picking of the receipt."""
    _name = "clinic.purchase.return"
    _description = "Clinic Purchase Return"
    _inherit = ["mail.thread"]
    _order = "id desc"

    purchase_id = fields.Many2one(
        "purchase.order", required=True, readonly=True, ondelete="cascade")
    vendor_id = fields.Many2one(
        related="purchase_id.partner_id", store=True, string="Vendor")
    reason = fields.Text(string="Return Reason", required=True)
    image = fields.Image(string="Photo", max_width=1600, max_height=1600)
    state = fields.Selection([
        ("requested", "Requested"),
        ("review", "In Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("return_transit", "Return In Transit"),
        ("closed", "Closed"),
    ], default="requested", tracking=True, copy=False)
    decision_note = fields.Text(string="Supplier Comment")
    return_picking_id = fields.Many2one("stock.picking", readonly=True, copy=False)

    def _notify_counterpart(self, body):
        for rec in self:
            rec.message_post(body=body)
            rec.purchase_id.message_post(body=body)

    def action_review(self):
        self.write({"state": "review"})
        self._notify_counterpart(_("Return is being reviewed by the supplier."))

    def action_approve(self):
        for rec in self:
            rec.state = "approved"
            rec._create_reverse_picking()
        self._notify_counterpart(_("Return approved by the supplier."))

    def action_reject(self):
        for rec in self:
            if not rec.decision_note:
                raise UserError(_("A supplier comment is required to reject."))
            rec.state = "rejected"
        self._notify_counterpart(_("Return rejected by the supplier."))

    def action_transit(self):
        self.write({"state": "return_transit"})
        self._notify_counterpart(_("Return shipment is on its way back."))

    def action_close(self):
        self.write({"state": "closed"})
        self._notify_counterpart(_("Return closed."))

    def _create_reverse_picking(self):
        """Reverse transfer of the order's done receipt: goods travel back
        stock → vendor as a standard outgoing picking (the stock.return.picking
        wizard's internals shift between versions — built directly instead)."""
        self.ensure_one()
        picking = self.purchase_id.picking_ids.filtered(
            lambda p: p.picking_type_code == "incoming" and p.state == "done")[:1]
        if not picking:
            return
        Picking = self.env["stock.picking"].sudo()
        ptype = self.env["stock.picking.type"].sudo().search(
            [("code", "=", "outgoing"),
             ("company_id", "=", self.purchase_id.company_id.id)], limit=1)
        supplier_loc = picking.location_id  # the vendor location it came from
        ret = Picking.create({
            "picking_type_id": ptype.id,
            "location_id": picking.location_dest_id.id,
            "location_dest_id": supplier_loc.id,
            "partner_id": self.purchase_id.partner_id.id,
            "origin": _("Return of %s") % self.purchase_id.name,
            "move_ids": [(0, 0, {
                "product_id": m.product_id.id,
                "product_uom_qty": m.quantity,
                "location_id": picking.location_dest_id.id,
                "location_dest_id": supplier_loc.id,
            }) for m in picking.move_ids if m.quantity],
        })
        ret.action_confirm()
        self.return_picking_id = ret.id
        self.message_post(body=_("Reverse transfer %s created.") % ret.name)
