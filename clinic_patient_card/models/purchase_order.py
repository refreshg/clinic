# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    # Marks RFQs created from the clinic Supply Shop (drives the notify flow).
    is_clinic_order = fields.Boolean(string="Clinic Order", copy=False)
    # The mirror sales order created on the supplier's side.
    clinic_sale_id = fields.Many2one("sale.order", string="Supplier Sales Order", copy=False)
    # The purchase request this RFQ was generated from (batch #2 pipeline).
    clinic_request_id = fields.Many2one(
        "clinic.purchase.request", string="Clinic Purchase Request", copy=False)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        res = super().button_validate()
        receipts = self.filtered(
            lambda p: p.state == "done" and p.picking_type_code == "incoming")
        if receipts:
            # request pipeline: receipt validation = the "Received" moment
            requests = receipts.mapped("purchase_id.clinic_request_id")
            requests._clinic_on_receipt_validated()
            receipts._clinic_notify_deficit_arrivals()
        return res

    def _clinic_notify_deficit_arrivals(self):
        """Reviewer item 29: a product that was in deficit and could NOT be
        ordered (its request got rejected) just arrived — tell the managers."""
        products = self.mapped("move_ids.product_id")
        if not products:
            return
        lines = self.env["clinic.purchase.request.line"].sudo().search([
            ("product_id", "in", products.ids),
            ("request_id.state", "=", "rejected"),
        ])
        if not lines:
            return
        admin_group = self.env.ref(
            "clinic_patient_card.group_clinic_admin", raise_if_not_found=False)
        if not admin_group:
            return
        admins = self.env["res.users"].search(
            [("all_group_ids", "in", admin_group.id)])
        names = ", ".join(lines.mapped("product_id.display_name"))
        for user in admins:
            if user.partner_id:
                self.env["bus.bus"]._sendone(
                    user.partner_id, "clinic_low_stock",
                    {"count": len(lines), "items":
                     [_("Back in stock (was in deficit): %s") % names]})
        for req in lines.mapped("request_id"):
            req.message_post(body=_(
                "Requested product(s) arrived with another receipt: %s") % names)

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
            # Mirror the order onto the supplier's side as a sales order, so the
            # chain is modelled correctly (clinic buys via PO, supplier sells via SO).
            po._clinic_create_supplier_sale(lines)
            po._clinic_notify_vendor()
            po_ids.append(po.id)
        return po_ids

    def _clinic_create_supplier_sale(self, lines):
        """Create the supplier's sale.order that mirrors this clinic RFQ.

        The customer is the clinic company; the sale order is tagged with the
        supplier partner so the supplier's record rule can scope it.
        """
        self.ensure_one()
        clinic_partner = self.env.company.partner_id
        so_lines = []
        for line in lines:
            product = self.env["product.product"].browse(int(line["product_id"]))
            if not product.exists():
                continue
            so_lines.append((0, 0, {
                "product_id": product.id,
                "product_uom_qty": line.get("qty") or 1.0,
                "price_unit": line.get("price") or product.list_price or 0.0,
            }))
        if not so_lines:
            return self.env["sale.order"]
        so = self.env["sale.order"].sudo().create({
            "partner_id": clinic_partner.id,
            "order_line": so_lines,
            "is_clinic_order": True,
            "clinic_supplier_id": self.partner_id.id,
            "clinic_purchase_id": self.id,
        })
        self.clinic_sale_id = so.id
        return so

    # ------------------------------------------------------------------
    # Business process notifications
    # ------------------------------------------------------------------
    def _clinic_admin_users(self):
        group = self.env.ref("clinic_patient_card.group_clinic_admin", raise_if_not_found=False)
        if not group:
            return self.env["res.users"]
        return self.env["res.users"].search([("all_group_ids", "in", group.id)])

    def _clinic_notify_vendor(self):
        """Order placed by the clinic -> tell the supplier to confirm.

        The supplier works on the mirror sale.order (their own document), so
        the to-do activity and the live toast point at that sales order.
        """
        self.ensure_one()
        # RFQ is now sent to the supplier.
        if self.state == "draft":
            self.write({"state": "sent"})
        self.message_post(body=_("New order sent by the clinic — please confirm."))
        # Keep clinic admins in the loop.
        admin_partners = self._clinic_admin_users().partner_id
        if admin_partners:
            self.message_subscribe(partner_ids=admin_partners.ids)
        # Notify the supplier's user(s): activity on the SALES ORDER + live toast.
        vendor_partner = self.partner_id.commercial_partner_id
        vendor_users = self.env["res.users"].search([
            ("partner_id.commercial_partner_id", "=", vendor_partner.id)
        ])
        so = self.clinic_sale_id
        todo = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        so_model_id = self.env["ir.model"]._get_id("sale.order")
        for user in vendor_users:
            if todo and so:
                self.env["mail.activity"].sudo().create({
                    "res_model_id": so_model_id,
                    "res_id": so.id,
                    "activity_type_id": todo.id,
                    "summary": _("Confirm clinic order %s") % so.name,
                    "date_deadline": fields.Date.context_today(self),
                    "user_id": user.id,
                })
            if user.partner_id:
                self.env["bus.bus"]._sendone(user.partner_id, "clinic_new_order", {
                    "name": so.name if so else self.name,
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
