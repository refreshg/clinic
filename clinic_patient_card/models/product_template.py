# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    """Dental procedures are standard products (type=service), not a custom
    catalog — so they reuse pricing, taxes and invoicing out of the box.
    """
    _inherit = "product.template"

    is_clinic_procedure = fields.Boolean(string="Clinic Procedure")
    # Consumables / materials the clinic keeps in stock and reorders from vendors.
    is_clinic_supply = fields.Boolean(string="Clinic Supply")

    @api.model
    def _clinic_notify_low_stock(self):
        """Cron — alert clinic admins about clinic supplies below their reordering
        minimum (reuses standard reordering rules). Sends a to-do activity per item
        plus a live bus toast."""
        orderpoints = self.env["stock.warehouse.orderpoint"].search(
            [("product_id.product_tmpl_id.is_clinic_supply", "=", True)]
        )
        low = orderpoints.filtered(lambda o: o.qty_on_hand < o.product_min_qty)
        if not low:
            return
        admin_group = self.env.ref(
            "clinic_patient_card.group_clinic_admin", raise_if_not_found=False
        )
        if not admin_group:
            return
        admins = self.env["res.users"].search(
            [("all_group_ids", "in", admin_group.id)]
        )
        todo = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        # orderpoint has no chatter/activities — attach the to-do to the product.
        prod_model_id = self.env["ir.model"]._get_id("product.product")
        for op in low:
            if todo and op.product_id:
                for user in admins:
                    self.env["mail.activity"].create({
                        "res_model_id": prod_model_id,
                        "res_id": op.product_id.id,
                        "activity_type_id": todo.id,
                        "summary": _("Low stock: %s") % op.product_id.display_name,
                        "date_deadline": fields.Date.context_today(self),
                        "user_id": user.id,
                    })
        items = low.mapped("product_id.display_name")
        for user in admins:
            if user.partner_id:
                self.env["bus.bus"]._sendone(
                    user.partner_id,
                    "clinic_low_stock",
                    {"count": len(low), "items": items[:5]},
                )
