# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ClinicSupplierMove(models.TransientModel):
    """Internal move strictly INSIDE the supplier's own warehouse tree."""
    _name = "clinic.supplier.move"
    _description = "Supplier Internal Move"

    product_id = fields.Many2one(
        "product.product", required=True,
        domain=[("is_clinic_supply", "=", True)])
    src_location_id = fields.Many2one(
        "stock.location", string="From", required=True)
    dest_location_id = fields.Many2one(
        "stock.location", string="To", required=True)
    qty = fields.Float(default=1.0, digits="Product Unit of Measure")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        root = self.env.user.partner_id._clinic_supplier_stock_loc()
        if root and "src_location_id" in fields_list:
            res.setdefault("src_location_id", root.id)
        return res

    def action_move(self):
        self.ensure_one()
        vendor = self.env.user.partner_id.commercial_partner_id
        for loc in (self.src_location_id, self.dest_location_id):
            if loc.clinic_supplier_id != vendor or loc.usage != "internal":
                raise UserError(_(
                    "Both locations must belong to YOUR warehouse."))
        if self.src_location_id == self.dest_location_id:
            raise UserError(_("Pick two different locations."))
        if self.qty <= 0:
            raise UserError(_("Quantity must be positive."))
        ptype = self.env["stock.picking.type"].sudo().search(
            [("code", "=", "internal"),
             ("company_id", "=", self.env.company.id)], limit=1)
        pk = self.env["stock.picking"].sudo().create({
            "picking_type_id": ptype.id,
            "location_id": self.src_location_id.id,
            "location_dest_id": self.dest_location_id.id,
            "origin": _("Supplier internal move"),
            "move_ids": [(0, 0, {
                "product_id": self.product_id.id,
                "product_uom_qty": self.qty,
                "location_id": self.src_location_id.id,
                "location_dest_id": self.dest_location_id.id,
            })],
        })
        pk.action_confirm()
        pk.action_assign()
        for move in pk.move_ids:
            if not move.quantity:
                move.quantity = move.product_uom_qty
            move.picked = True
        pk.button_validate()
        return {"type": "ir.actions.act_window_close"}
