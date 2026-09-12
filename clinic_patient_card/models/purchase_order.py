# -*- coding: utf-8 -*-
from datetime import timedelta

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

    # ---- batch #2 B4: supplier status, 48h return window, ratings ----
    clinic_delivery_status = fields.Selection(
        related="clinic_sale_id.clinic_delivery_status", string="Supplier Status")
    clinic_receipt_date = fields.Datetime(
        compute="_compute_clinic_receipt", string="Received On")
    clinic_return_allowed = fields.Boolean(compute="_compute_clinic_receipt")
    clinic_return_ids = fields.One2many(
        "clinic.purchase.return", "purchase_id", string="Returns")
    # item 28: the manager rates the delivered goods and the vendor
    RATING_SEL = [("1", "★"), ("2", "★★"), ("3", "★★★"),
                  ("4", "★★★★"), ("5", "★★★★★")]
    clinic_rating_product = fields.Selection(
        RATING_SEL, string="Products Rating", copy=False, tracking=True)
    clinic_rating_vendor = fields.Selection(
        RATING_SEL, string="Vendor Rating", copy=False, tracking=True)
    clinic_rating_note = fields.Char(string="Rating Note", copy=False)

    def _compute_clinic_receipt(self):
        now = fields.Datetime.now()
        for po in self:
            done = po.picking_ids.filtered(
                lambda p: p.picking_type_code == "incoming"
                and p.state == "done").sorted("date_done", reverse=True)[:1]
            po.clinic_receipt_date = done.date_done if done else False
            # reviewer item 35: the Return button lives for 48 hours only
            po.clinic_return_allowed = bool(
                (po.is_clinic_order or po.clinic_request_id)
                and done and done.date_done
                and (now - done.date_done).total_seconds() <= 48 * 3600
                and not po.clinic_return_ids.filtered(
                    lambda r: r.state not in ("rejected", "closed")))

    def action_clinic_return(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Return / Exchange"),
            "res_model": "clinic.purchase.return",
            "view_mode": "form",
            "target": "new",
            "context": {"default_purchase_id": self.id},
        }

    # ------------------------------------------------------------------
    # Manager dashboard (batch #2 B4, items 102-114) — one RPC
    # ------------------------------------------------------------------
    @api.model
    def clinic_dashboard_data(self):
        env = self.env
        now = fields.Datetime.now()
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        Orderpoint = env["stock.warehouse.orderpoint"].sudo()
        Pol = env["purchase.order.line"].sudo()
        Po = env["purchase.order"].sudo()
        Req = env["clinic.purchase.request"].sudo()

        ops = Orderpoint.search(
            [("product_id.product_tmpl_id.is_clinic_supply", "=", True)])
        low = [{"product": o.product_id.display_name,
                "loc": o.location_id.display_name,
                "qty": o.qty_on_hand, "min": o.product_min_qty}
               for o in ops if o.qty_on_hand < o.product_min_qty]
        excess = [{"product": o.product_id.display_name,
                   "loc": o.location_id.display_name,
                   "qty": o.qty_on_hand, "max": o.product_max_qty}
                  for o in ops if o.product_max_qty and o.qty_on_hand > o.product_max_qty]

        to_approve = Req.search_read(
            [("state", "in", ("requested", "review"))],
            ["name", "source", "state"], limit=8)
        clinic_po_dom = ["|", ("is_clinic_order", "=", True),
                         ("clinic_request_id", "!=", False)]
        open_pos = Po.search(
            clinic_po_dom + [("state", "in", ("draft", "sent", "purchase"))])
        ongoing = [{"name": p.name, "vendor": p.partner_id.name,
                    "status": p.clinic_delivery_status or p.state,
                    "amount": p.amount_total} for p in open_pos
                   if not p.clinic_receipt_date][:10]
        late = [{"name": p.name, "vendor": p.partner_id.name,
                 "planned": str(p.date_planned or "")[:10]}
                for p in open_pos
                if p.date_planned and p.date_planned < now
                and not p.clinic_receipt_date]

        month_pos = Po.search(
            clinic_po_dom + [("state", "in", ("purchase", "done")),
             ("date_approve", ">=", fields.Datetime.to_string(month_start))])
        monthly_spend = sum(month_pos.mapped("amount_total"))

        by_prod = Pol._read_group(
            ["|", ("order_id.is_clinic_order", "=", True),
             ("order_id.clinic_request_id", "!=", False),
             ("order_id.state", "in", ("purchase", "done")),
             ("order_id.date_approve", ">=", now - timedelta(days=90))],
            ["product_id"], ["price_total:sum"])
        categ_amounts = {}
        for prod, amt in by_prod:
            categ = prod.categ_id.display_name if prod else "—"
            categ_amounts[categ] = categ_amounts.get(categ, 0.0) + amt
        spend_by_categ = [{"categ": k, "amount": v}
                          for k, v in categ_amounts.items()]
        spend_by_categ.sort(key=lambda r: r["amount"], reverse=True)

        used = env["stock.move"].sudo()._read_group(
            [("state", "=", "done"), ("date", ">=", now - timedelta(days=90)),
             ("location_id.usage", "=", "internal"),
             ("location_dest_id.usage", "in",
              ("customer", "production", "inventory")),
             ("product_id.product_tmpl_id.is_clinic_supply", "=", True)],
            ["product_id"], ["product_uom_qty:sum"])
        top_used = sorted(
            [{"product": p.display_name, "qty": q} for p, q in used],
            key=lambda r: r["qty"], reverse=True)[:8]

        expiry = []
        Lot = env["stock.lot"].sudo() if "stock.lot" in env else False
        if Lot:
            for lot in Lot.search(
                    [("expiration_date", "!=", False),
                     ("expiration_date", "<=", now + timedelta(days=30)),
                     ("product_qty", ">", 0)], limit=10):
                expiry.append({"product": lot.product_id.display_name,
                               "lot": lot.name,
                               "date": str(lot.expiration_date)[:10],
                               "qty": lot.product_qty})

        vendors = {}
        rated = Po.search(clinic_po_dom)
        for p in rated:
            v = vendors.setdefault(p.partner_id.id, {
                "vendor": p.partner_id.name, "orders": 0,
                "rating_sum": 0, "rating_n": 0, "on_time": 0, "done_n": 0})
            v["orders"] += 1
            if p.clinic_rating_vendor:
                v["rating_sum"] += int(p.clinic_rating_vendor)
                v["rating_n"] += 1
            if p.clinic_receipt_date and p.date_planned:
                v["done_n"] += 1
                if p.clinic_receipt_date <= p.date_planned + timedelta(days=1):
                    v["on_time"] += 1
        vendor_perf = [{
            "vendor": v["vendor"], "orders": v["orders"],
            "rating": round(v["rating_sum"] / v["rating_n"], 1) if v["rating_n"] else 0,
            "on_time_pct": round(100 * v["on_time"] / v["done_n"]) if v["done_n"] else None,
        } for v in vendors.values()]

        planned = Req.search_read(
            [("source", "=", "planned"), ("date_planned", ">=", today),
             ("state", "not in", ("closed", "rejected"))],
            ["name", "date_planned", "state"], limit=8, order="date_planned")

        return {
            "low": low[:10], "excess": excess[:10],
            "to_approve": to_approve, "ongoing": ongoing, "late": late[:10],
            "monthly_spend": monthly_spend, "spend_by_categ": spend_by_categ[:8],
            "top_used": top_used, "expiry": expiry, "vendor_perf": vendor_perf,
            "planned": planned,
            "currency": env.company.currency_id.symbol or "",
        }
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
            # B4 item 16 (user decision): vendor bill drafts itself on
            # receipt; the waybill is attached by hand on the order
            for po in receipts.mapped("purchase_id").filtered(
                    lambda p: (p.is_clinic_order or p.clinic_request_id)
                    and not p.invoice_ids):
                try:
                    po.sudo().action_create_invoice()
                except Exception:
                    pass  # billing must never block a receipt
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
