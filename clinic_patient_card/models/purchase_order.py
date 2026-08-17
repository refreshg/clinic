# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model
    def clinic_create_rfqs(self, cart):
        """Create one RFQ (purchase.order) per vendor from a shop cart.

        cart = [{'product_id': int, 'vendor_id': int, 'qty': float,
                 'price': float}]  -> returns list of created purchase.order ids.
        """
        by_vendor = {}
        for line in cart or []:
            vendor = line.get("vendor_id")
            if not vendor or not line.get("product_id"):
                continue
            by_vendor.setdefault(vendor, []).append(line)

        po_ids = []
        for vendor_id, lines in by_vendor.items():
            order_lines = []
            for line in lines:
                product = self.env["product.product"].browse(int(line["product_id"]))
                if not product.exists():
                    continue
                order_lines.append((0, 0, {
                    "product_id": product.id,
                    "product_qty": line.get("qty") or 1.0,
                    "price_unit": line.get("price") or product.standard_price or 0.0,
                }))
            if not order_lines:
                continue
            po = self.env["purchase.order"].create({
                "partner_id": int(vendor_id),
                "order_line": order_lines,
            })
            po_ids.append(po.id)
        return po_ids
