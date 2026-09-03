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

    # Retail sale to a patient started from the patient card (batch #2: a
    # doctor may draft one — the admin approves it into billing).
    is_clinic_retail = fields.Boolean(string="Clinic Retail Sale", copy=False)

    @api.model
    def default_get(self, fields_list):
        # sale_pdf_quote_builder's default for quotation_document_ids searches
        # on a salesman-gated field, crashing a doctor's retail-request create.
        # Non-salesmen simply skip that default (no PDF headers/footers).
        if ("quotation_document_ids" in fields_list
                and not self.env.user.has_group("sales_team.group_sale_salesman")):
            fields_list = [f for f in fields_list if f != "quotation_document_ids"]
        return super().default_get(fields_list)

    def _compute_available_quotation_document_ids(self):
        # sale_pdf_quote_builder reads quotation.document.quotation_template_ids,
        # a field group-gated to salesmen — a doctor drafting a retail sale
        # request would crash on create. Run the lookup as sudo; the result
        # field itself carries no groups.
        sudo_self = self.sudo()
        super(SaleOrder, sudo_self)._compute_available_quotation_document_ids()
        for rec, srec in zip(self, sudo_self):
            rec.available_quotation_document_ids = srec.available_quotation_document_ids

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("is_clinic_retail"):
                # the request belongs to its creator — otherwise the partner's
                # salesperson takes over user_id and the doctor's own-drafts
                # record rule locks them out of their own request
                vals.setdefault("user_id", self.env.uid)
        orders = super().create(vals_list)
        doctor_group = self.env.ref(
            "clinic_patient_card.group_clinic_doctor", raise_if_not_found=False)
        admin_group = self.env.ref(
            "clinic_patient_card.group_clinic_admin", raise_if_not_found=False)
        user = self.env.user
        is_plain_doctor = (
            doctor_group and doctor_group in user.all_group_ids
            and not (admin_group and admin_group in user.all_group_ids))
        for order in orders:
            if order.is_clinic_retail and is_plain_doctor:
                # doctor's request: keep them in the loop + ping the admins
                order.message_subscribe(partner_ids=user.partner_id.ids)
                order._clinic_notify_sale_request()
        return orders

    def _clinic_notify_sale_request(self):
        self.ensure_one()
        admin_group = self.env.ref(
            "clinic_patient_card.group_clinic_admin", raise_if_not_found=False)
        if not admin_group:
            return
        admins = self.env["res.users"].search(
            [("all_group_ids", "in", admin_group.id)])
        todo = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        model_id = self.env["ir.model"]._get_id("sale.order")
        for user in admins:
            if todo:
                self.env["mail.activity"].sudo().create({
                    "res_model_id": model_id,
                    "res_id": self.id,
                    "activity_type_id": todo.id,
                    "summary": _("Doctor sale request: %(order)s (%(patient)s)",
                                 order=self.name,
                                 patient=self.partner_id.name or ""),
                    "date_deadline": fields.Date.context_today(self),
                    "user_id": user.id,
                })
            if user.partner_id:
                self.env["bus.bus"]._sendone(user.partner_id, "clinic_sale_request", {
                    "order": self.name,
                    "patient": self.partner_id.name or "",
                    "doctor": self.env.user.name,
                })

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if order.is_clinic_order:
                order._clinic_notify_clinic_confirmed()
            if order.is_clinic_retail:
                # approval drops it straight into billing (draft invoice);
                # the doctor (follower) sees the confirmation in the chatter
                order.message_post(body=_("Sale approved by the administration."))
                if not order.invoice_ids:
                    order.sudo()._create_invoices()
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
