# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    # which supplier company this location belongs to (their own warehouse /
    # their in-transit shelf) — drives the supplier's My Warehouse scoping
    clinic_supplier_id = fields.Many2one(
        "res.partner", string="Clinic Supplier", index=True)


class ResPartnerSupplierStock(models.Model):
    _inherit = "res.partner"

    @api.model
    def _clinic_ensure_supplier_locations(self):
        """Every supplier company gets its own warehouse pair:
        Suppliers/<name> (internal — THEIR stock, managed by them) and
        Suppliers/<name>/In Transit (transit — goods they shipped, not yet
        received by the clinic). The partner's property_stock_supplier points
        at the transit shelf, so clinic receipts pull from it. Idempotent —
        runs on every upgrade."""
        Location = self.env["stock.location"].sudo()
        group = self.env.ref(
            "clinic_patient_card.group_clinic_supplier", raise_if_not_found=False)
        if not group:
            return True
        parent = Location.search([("name", "=", "Suppliers"),
                                  ("usage", "=", "view"),
                                  ("clinic_supplier_id", "=", False)], limit=1)
        if not parent:
            parent = Location.create({"name": "Suppliers", "usage": "view"})
        users = self.env["res.users"].sudo().search(
            [("all_group_ids", "in", group.id)])
        vendors = users.mapped("partner_id.commercial_partner_id")
        for vendor in vendors:
            stock = Location.search([
                ("clinic_supplier_id", "=", vendor.id),
                ("usage", "=", "internal")], limit=1)
            if not stock:
                stock = Location.create({
                    "name": vendor.name, "usage": "internal",
                    "location_id": parent.id,
                    "clinic_supplier_id": vendor.id,
                })
            transit = Location.search([
                ("clinic_supplier_id", "=", vendor.id),
                ("usage", "=", "transit")], limit=1)
            if not transit:
                transit = Location.create({
                    "name": _("In Transit"), "usage": "transit",
                    "location_id": stock.id,
                    "clinic_supplier_id": vendor.id,
                })
            # clinic receipts source from the transit shelf
            vendor.sudo().property_stock_supplier = transit
        return True

    def _clinic_supplier_stock_loc(self):
        self.ensure_one()
        return self.env["stock.location"].sudo().search([
            ("clinic_supplier_id", "=", self.commercial_partner_id.id),
            ("usage", "=", "internal")], limit=1)

    def _clinic_supplier_transit_loc(self):
        self.ensure_one()
        return self.env["stock.location"].sudo().search([
            ("clinic_supplier_id", "=", self.commercial_partner_id.id),
            ("usage", "=", "transit")], limit=1)

    @api.model
    def clinic_my_transfers_action(self):
        """Read-only history of every transfer touching the supplier's own
        locations: shipments to transit, clinic receipts, returns."""
        vendor = self.env.user.partner_id.commercial_partner_id
        return {
            "type": "ir.actions.act_window",
            "name": _("My Transfers"),
            "res_model": "stock.picking",
            "view_mode": "list",
            "view_id": self.env.ref(
                "clinic_patient_card.view_clinic_supplier_picking_list").id,
            "domain": ["|",
                       ("location_id.clinic_supplier_id", "=", vendor.id),
                       ("location_dest_id.clinic_supplier_id", "=", vendor.id)],
        }

    @api.model
    def clinic_my_warehouse_action(self):
        """Server-action entry: the supplier's own quants, inventory-editable."""
        vendor = self.env.user.partner_id.commercial_partner_id
        return {
            "type": "ir.actions.act_window",
            "name": _("My Warehouse"),
            "res_model": "stock.quant",
            "view_mode": "list",
            "view_id": self.env.ref(
                "clinic_patient_card.view_clinic_supplier_quant_list").id,
            # own warehouse AND the In-Transit shelf (reviewer: "გზაშია სად ვნახო")
            "domain": [("location_id.clinic_supplier_id", "=", vendor.id),
                       ("location_id.usage", "in", ("internal", "transit"))],
            "context": {"inventory_mode": True,
                        "default_location_id":
                            self.env.user.partner_id
                                ._clinic_supplier_stock_loc().id},
        }
