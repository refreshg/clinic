# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    """Dental procedures are standard products (type=service), not a custom
    catalog — so they reuse pricing, taxes and invoicing out of the box.
    """
    _inherit = "product.template"

    is_clinic_procedure = fields.Boolean(string="Clinic Procedure")
    # Consumables / materials the clinic keeps in stock and reorders from vendors.
    is_clinic_supply = fields.Boolean(string="Clinic Supply")

    # ------------------------------------------------------------------
    # Supplier self-service catalogue (OWL "My Products" panel).
    # A supplier user manages only the products they themselves publish;
    # every published product is a clinic supply with a product.supplierinfo
    # line for that vendor, so it automatically appears in the clinic
    # Supply Shop (which lists product.supplierinfo).
    # ------------------------------------------------------------------
    def _clinic_current_vendor(self):
        """The vendor (res.partner) the logged-in supplier user represents."""
        partner = self.env.user.partner_id
        return partner.commercial_partner_id or partner

    @staticmethod
    def _clinic_b64(value):
        """Normalise an image field to a plain base64 string (or False)."""
        if not value:
            return False
        return value.decode() if isinstance(value, bytes) else value

    @api.model
    def clinic_supplier_products(self):
        """Return the current supplier's published products (for the panel)."""
        vendor = self._clinic_current_vendor()
        if not vendor:
            return {"vendor": False, "products": []}
        sis = self.env["product.supplierinfo"].search(
            [("partner_id", "=", vendor.id)]
        )
        rows = []
        seen = set()
        for si in sis:
            tmpl = si.product_tmpl_id
            if not tmpl or tmpl.id in seen or not tmpl.is_clinic_supply:
                continue
            seen.add(tmpl.id)
            rows.append({
                "id": tmpl.id,
                "supplierinfo_id": si.id,
                "name": tmpl.name,
                "price": si.price or tmpl.list_price or 0.0,
                "delay": si.delay or 0,
                "categ_id": tmpl.categ_id.id,
                "categ_name": tmpl.categ_id.display_name,
                "image_128": self._clinic_b64(tmpl.image_128),
                "qty_available": tmpl.qty_available,
            })
        rows.sort(key=lambda r: r["name"].lower())
        cats = self.env["product.category"].search_read([], ["id", "display_name"])
        return {
            "vendor": {"id": vendor.id, "name": vendor.display_name},
            "products": rows,
            "categories": cats,
        }

    @api.model
    def clinic_supplier_save_product(self, vals):
        """Create or update one of the supplier's own products.

        vals: {id?, name, price, delay, categ_id?, image (base64|false)}
        Returns the saved template id.
        """
        vendor = self._clinic_current_vendor()
        if not vendor:
            raise UserError(_("No supplier company is linked to your user."))
        name = (vals.get("name") or "").strip()
        if not name:
            raise UserError(_("Product name is required."))
        price = float(vals.get("price") or 0.0)
        delay = int(vals.get("delay") or 0)
        tmpl_vals = {
            "name": name,
            "list_price": price,
            "standard_price": price,
        }
        if vals.get("categ_id"):
            tmpl_vals["categ_id"] = int(vals["categ_id"])
        if "image" in vals:
            tmpl_vals["image_1920"] = vals["image"] or False

        tmpl_id = vals.get("id")
        if tmpl_id:
            tmpl = self.browse(int(tmpl_id))
            # a supplier may only edit a product they actually offer
            has = self.env["product.supplierinfo"].search_count([
                ("product_tmpl_id", "=", tmpl.id),
                ("partner_id", "=", vendor.id),
            ])
            if not has:
                raise UserError(_("You can only edit your own products."))
            tmpl.write(tmpl_vals)
        else:
            tmpl_vals.update({
                "type": "consu",
                "is_storable": True,
                "is_clinic_supply": True,
            })
            tmpl = self.create(tmpl_vals)

        # ensure a supplierinfo line (price / lead time) for this vendor
        si = self.env["product.supplierinfo"].search([
            ("product_tmpl_id", "=", tmpl.id),
            ("partner_id", "=", vendor.id),
        ], limit=1)
        si_vals = {"price": price, "delay": delay}
        if si:
            si.write(si_vals)
        else:
            si_vals.update({"partner_id": vendor.id, "product_tmpl_id": tmpl.id})
            self.env["product.supplierinfo"].create(si_vals)
        return tmpl.id

    @api.model
    def clinic_supplier_unpublish(self, tmpl_id):
        """Remove the supplier's offer for a product (unlist it from the shop).
        Only removes this vendor's supplierinfo line; the product itself stays."""
        vendor = self._clinic_current_vendor()
        if not vendor:
            return False
        sis = self.env["product.supplierinfo"].search([
            ("product_tmpl_id", "=", int(tmpl_id)),
            ("partner_id", "=", vendor.id),
        ])
        sis.unlink()
        return True

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
