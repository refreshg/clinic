# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class SaleOrder(models.Model):
    """The supplier's side of a clinic order.

    A clinic purchase.order (what the clinic buys) is mirrored into a
    sale.order (what the supplier sells), so the chain is modelled correctly:
    clinic -> purchase.order (RFQ), supplier -> sale.order (to fulfil).
    """
    _inherit = "sale.order"

    is_clinic_order = fields.Boolean(string="Clinic Order", copy=False)
    # The vendor/supplier this sales order belongs to (drives the record rule
    # that limits a supplier to their own sales orders).
    clinic_supplier_id = fields.Many2one("res.partner", string="Clinic Supplier", copy=False)
    clinic_purchase_id = fields.Many2one("purchase.order", string="Clinic Purchase Order", copy=False)

    def _clinic_notify_clinic_confirmed(self):
        """Supplier confirmed the sale order -> tell the clinic + confirm the PO."""
        self.ensure_one()
        po = self.clinic_purchase_id
        # Mirror the confirmation onto the clinic's purchase order.
        if po and po.state in ("draft", "sent"):
            po.button_confirm()  # triggers _clinic_notify_confirmed (clinic toast)
        self.message_post(body=_("Order confirmed by the supplier."))

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if order.is_clinic_order:
                order._clinic_notify_clinic_confirmed()
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _action_launch_stock_rule(self, *, previous_product_uom_qty=False):
        """Clinic mirror sales orders are confirmation documents only — the
        physical goods reach the clinic through the purchase-order receipt, not
        a sale delivery. Skip delivery procurement for these lines so confirming
        the supplier's SO never depends on warehouse route configuration."""
        clinic = self.filtered(lambda l: l.order_id.is_clinic_order)
        other = self - clinic
        if other:
            return super(SaleOrderLine, other)._action_launch_stock_rule(
                previous_product_uom_qty=previous_product_uom_qty
            )
        return True
