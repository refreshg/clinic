# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    # Marks RFQs created from the clinic Supply Shop (drives the notify flow).
    is_clinic_order = fields.Boolean(string="Clinic Order", copy=False)

    # ------------------------------------------------------------------
    # Shop -> RFQs
    # ------------------------------------------------------------------
    @api.model
    def clinic_create_rfqs(self, cart):
        """Create one RFQ per vendor from a shop cart and notify each vendor.

        cart = [{'product_id', 'vendor_id', 'qty', 'price'}] -> [po ids]
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
                "is_clinic_order": True,
            })
            po._clinic_notify_vendor()
            po_ids.append(po.id)
        return po_ids

    # ------------------------------------------------------------------
    # Business process notifications
    # ------------------------------------------------------------------
    def _clinic_admin_users(self):
        group = self.env.ref("clinic_patient_card.group_clinic_admin", raise_if_not_found=False)
        if not group:
            return self.env["res.users"]
        return self.env["res.users"].search([("all_group_ids", "in", group.id)])

    def _clinic_notify_vendor(self):
        """Order placed by the clinic -> tell the supplier to confirm."""
        self.ensure_one()
        # RFQ is now sent to the supplier.
        if self.state == "draft":
            self.write({"state": "sent"})
        self.message_post(body=_("New order sent by the clinic — please confirm."))
        # Keep clinic admins in the loop.
        admin_partners = self._clinic_admin_users().partner_id
        if admin_partners:
            self.message_subscribe(partner_ids=admin_partners.ids)
        # Notify the supplier's user(s): activity + live toast.
        vendor_users = self.env["res.users"].search([("partner_id", "=", self.partner_id.id)])
        todo = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        po_model_id = self.env["ir.model"]._get_id("purchase.order")
        for user in vendor_users:
            if todo:
                self.env["mail.activity"].create({
                    "res_model_id": po_model_id,
                    "res_id": self.id,
                    "activity_type_id": todo.id,
                    "summary": _("Confirm clinic order %s") % self.name,
                    "date_deadline": fields.Date.context_today(self),
                    "user_id": user.id,
                })
            if user.partner_id:
                self.env["bus.bus"]._sendone(user.partner_id, "clinic_new_order", {
                    "name": self.name,
                    "amount": self.amount_total,
                })

    def _clinic_notify_confirmed(self):
        """Supplier confirmed -> tell the clinic (with delivery date)."""
        self.ensure_one()
        arrival = self.date_planned and fields.Datetime.to_string(self.date_planned) or ""
        self.message_post(body=_("Supplier confirmed the order. Expected arrival: %s") % (arrival or "-"))
        for user in self._clinic_admin_users():
            if user.partner_id:
                self.env["bus.bus"]._sendone(user.partner_id, "clinic_order_confirmed", {
                    "name": self.name,
                    "vendor": self.partner_id.name or "",
                    "arrival": arrival,
                })

    def button_confirm(self):
        res = super().button_confirm()
        for po in self:
            if po.is_clinic_order:
                po._clinic_notify_confirmed()
        return res
