# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ClinicPurchaseRequest(models.Model):
    """Reviewer batch #2 — purchase request pipeline in front of the standard
    purchase.order: alert/doctor/manager/planned → review with stock
    recommendations → approve or reject (comment) → RFQ per vendor → the
    stock itself only moves on the standard receipt validation."""
    _name = "clinic.purchase.request"
    _description = "Clinic Purchase Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default=lambda s: _("New"), copy=False, readonly=True)
    source = fields.Selection([
        ("low_stock", "Low-stock Alert"),
        ("doctor", "Doctor / Nurse"),
        ("manager", "Purchase Manager"),
        ("planned", "Planned (Calendar)"),
    ], default="manager", required=True, tracking=True)
    requester_id = fields.Many2one(
        "res.users", string="Requested By",
        default=lambda s: s.env.user, readonly=True)
    date_planned = fields.Date(
        string="Planned Date",
        default=fields.Date.context_today, tracking=True)
    state = fields.Selection([
        ("draft", "Draft"),
        ("requested", "Requested"),
        ("review", "In Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("ordered", "Ordered"),
        ("in_transit", "In Transit"),
        ("delivered", "Delivered"),
        ("received", "Received"),
        ("closed", "Closed"),
    ], default="draft", tracking=True, copy=False)
    reject_reason = fields.Text(readonly=True, copy=False, tracking=True)
    line_ids = fields.One2many(
        "clinic.purchase.request.line", "request_id", copy=True)
    purchase_order_ids = fields.One2many(
        "purchase.order", "clinic_request_id", string="Purchase Orders",
        copy=False)
    purchase_count = fields.Integer(compute="_compute_purchase_count")
    note = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "clinic.purchase.request") or _("New")
        return super().create(vals_list)

    def _compute_purchase_count(self):
        for req in self:
            req.purchase_count = len(req.purchase_order_ids)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def action_submit(self):
        for req in self:
            if not req.line_ids:
                raise UserError(_("Add at least one product line first."))
            req.state = "requested"
            req._notify_admins(_("Purchase request %s awaits review.") % req.name)

    def action_review(self):
        self.write({"state": "review"})

    def action_approve(self):
        self.write({"state": "approved"})
        for req in self:
            req.message_post(body=_("Request approved by the administration."))

    def action_reject(self):
        # opens the reject wizard (comment is mandatory — reviewer item)
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "clinic.request.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def action_place_order(self):
        """Approved → one RFQ per vendor (standard purchase.order)."""
        self.ensure_one()
        if self.state != "approved":
            raise UserError(_("Only an approved request can be ordered."))
        by_vendor = {}
        for line in self.line_ids:
            vendor = line.vendor_id or line.suggested_vendor_id
            if not vendor:
                raise UserError(
                    _("No vendor for %s — set one on the line.")
                    % line.product_id.display_name)
            by_vendor.setdefault(vendor, []).append(line)
        for vendor, lines in by_vendor.items():
            self.env["purchase.order"].create({
                "partner_id": vendor.id,
                "origin": self.name,
                "clinic_request_id": self.id,
                "order_line": [(0, 0, {
                    "product_id": l.product_id.id,
                    "product_qty": l.qty,
                    "price_unit": l.last_price or 0.0,
                }) for l in lines],
            })
        self.state = "ordered"
        return self.action_view_purchases()

    def action_in_transit(self):
        self.write({"state": "in_transit"})

    def action_delivered(self):
        # "მოტანილი ≠ მიღებული": stock stays untouched until the standard
        # receipt is validated, which flips the request to received.
        self.write({"state": "delivered"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_reset_draft(self):
        self.write({"state": "draft", "reject_reason": False})

    def action_view_purchases(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Purchase Orders"),
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("clinic_request_id", "=", self.id)],
        }

    def _notify_admins(self, message):
        admin_group = self.env.ref(
            "clinic_patient_card.group_clinic_admin", raise_if_not_found=False)
        if not admin_group:
            return
        todo = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        model_id = self.env["ir.model"]._get_id(self._name)
        admins = self.env["res.users"].search(
            [("all_group_ids", "in", admin_group.id)])
        for req in self:
            for user in admins:
                if todo:
                    self.env["mail.activity"].sudo().create({
                        "res_model_id": model_id,
                        "res_id": req.id,
                        "activity_type_id": todo.id,
                        "summary": message,
                        "date_deadline": fields.Date.context_today(req),
                        "user_id": user.id,
                    })

    def _clinic_on_receipt_validated(self):
        """Called when a linked PO receipt is validated — the only moment the
        clinic stock actually changes (standard stock.move via the picking)."""
        for req in self:
            pickings = req.purchase_order_ids.mapped("picking_ids")
            if pickings and all(p.state in ("done", "cancel") for p in pickings):
                req.state = "received"
                req.message_post(body=_(
                    "All goods received — clinic stock updated by the receipt."))

    # ------------------------------------------------------------------
    # Low-stock cron hook: auto-create a draft request (source=low_stock)
    # ------------------------------------------------------------------
    @api.model
    def _clinic_auto_request_low_stock(self, orderpoints):
        open_states = ("draft", "requested", "review", "approved", "ordered")
        lines = []
        for op in orderpoints:
            if not op.product_id:
                continue
            already = self.env["clinic.purchase.request.line"].search_count([
                ("product_id", "=", op.product_id.id),
                ("request_id.state", "in", open_states),
            ])
            if already:
                continue
            lines.append((0, 0, {
                "product_id": op.product_id.id,
                "location_id": op.location_id.id,
                "qty": max(op.product_max_qty - op.qty_on_hand, 1.0),
            }))
        if lines:
            return self.create({"source": "low_stock", "line_ids": lines})
        return self.browse()


class ClinicPurchaseRequestLine(models.Model):
    _name = "clinic.purchase.request.line"
    _description = "Clinic Purchase Request Line"

    request_id = fields.Many2one(
        "clinic.purchase.request", required=True, ondelete="cascade")
    product_id = fields.Many2one(
        "product.product", required=True,
        domain=[("is_clinic_supply", "=", True)])
    qty = fields.Float(string="Quantity", default=1.0,
                       digits="Product Unit of Measure")
    location_id = fields.Many2one(
        "stock.location", string="For Location",
        domain=[("usage", "=", "internal")],
        help="Cabinet / zone the goods are needed in.")
    vendor_id = fields.Many2one(
        "res.partner", string="Vendor",
        help="Leave empty to use the suggested (last) vendor.")

    # ---- manager recommendations (reviewer items 77-83) ----
    qty_on_hand = fields.Float(
        compute="_compute_recommendations", string="On Hand (Location)")
    qty_other_cabinets = fields.Float(
        compute="_compute_recommendations", string="In Other Cabinets")
    suggested_vendor_id = fields.Many2one(
        "res.partner", compute="_compute_recommendations",
        string="Suggested Vendor")
    last_price = fields.Float(
        compute="_compute_recommendations", string="Last Price",
        digits="Product Price")
    recommended_qty = fields.Float(
        compute="_compute_recommendations", string="Recommended Qty",
        digits="Product Unit of Measure",
        help="Refill to the max of the location's min/max rule (fallback: "
             "the requested quantity).")

    def _compute_recommendations(self):
        Quant = self.env["stock.quant"].sudo()
        Pol = self.env["purchase.order.line"].sudo()
        Orderpoint = self.env["stock.warehouse.orderpoint"].sudo()
        for line in self:
            product = line.product_id
            if not product:
                line.update({
                    "qty_on_hand": 0, "qty_other_cabinets": 0,
                    "suggested_vendor_id": False, "last_price": 0,
                    "recommended_qty": 0,
                })
                continue
            quants = Quant.search([
                ("product_id", "=", product.id),
                ("location_id.usage", "=", "internal"),
            ])
            here = sum(q.quantity for q in quants
                       if line.location_id and q.location_id == line.location_id)
            line.qty_on_hand = here
            line.qty_other_cabinets = sum(quants.mapped("quantity")) - here
            pol = Pol.search(
                [("product_id", "=", product.id),
                 ("state", "in", ("purchase", "done"))],
                order="date_approve desc, id desc", limit=1)
            line.suggested_vendor_id = (
                pol.order_id.partner_id.id if pol
                else (product.seller_ids[:1].partner_id.id or False))
            line.last_price = pol.price_unit if pol else (
                product.seller_ids[:1].price or 0.0)
            op = Orderpoint.search(
                [("product_id", "=", product.id)] +
                ([("location_id", "=", line.location_id.id)]
                 if line.location_id else []), limit=1)
            line.recommended_qty = (
                max(op.product_max_qty - op.qty_on_hand, 0.0)
                if op else line.qty)

    def action_redistribute(self):
        """Reviewer item 87/29: cover the need from another cabinet — opens a
        prefilled standard internal transfer instead of buying."""
        self.ensure_one()
        if not self.location_id:
            raise UserError(_("Set the destination location on the line first."))
        quant = self.env["stock.quant"].sudo().search([
            ("product_id", "=", self.product_id.id),
            ("location_id.usage", "=", "internal"),
            ("location_id", "!=", self.location_id.id),
            ("quantity", ">", 0),
        ], order="quantity desc", limit=1)
        if not quant:
            raise UserError(_("No stock of this product in any other location."))
        ptype = self.env["stock.picking.type"].search(
            [("code", "=", "internal"),
             ("company_id", "=", self.env.company.id)], limit=1)
        picking = self.env["stock.picking"].create({
            "picking_type_id": ptype.id,
            "location_id": quant.location_id.id,
            "location_dest_id": self.location_id.id,
            "origin": self.request_id.name,
            "move_ids": [(0, 0, {
                "product_id": self.product_id.id,
                "product_uom_qty": min(self.qty, quant.quantity),
                "location_id": quant.location_id.id,
                "location_dest_id": self.location_id.id,
            })],
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "res_id": picking.id,
            "view_mode": "form",
        }
