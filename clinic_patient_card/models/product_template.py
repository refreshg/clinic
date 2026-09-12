# -*- coding: utf-8 -*-
from datetime import timedelta

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

    # Reviewer batch #2 — extra info every warehouse product must show.
    # Name/photo/category/code/UoM/qty/vendor/expiry are standard fields;
    # only these three are missing from stock Odoo:
    clinic_brand_id = fields.Many2one("clinic.brand", string="Brand")
    clinic_avg_consumption = fields.Float(
        string="Avg. Monthly Consumption", compute="_compute_clinic_stock_info",
        digits="Product Unit of Measure",
        help="Average quantity consumed per month over the last 90 days "
             "(stock moves leaving internal locations: usage, scrap, delivery).")
    clinic_last_purchase_price = fields.Float(
        string="Last Purchase Price", compute="_compute_clinic_stock_info",
        digits="Product Price",
        help="Unit price of the most recent confirmed purchase order; falls "
             "back to the first vendor pricelist line.")

    # Shop v2 storefront flags (reviewer batch #2)
    clinic_sponsored = fields.Boolean(
        string="Sponsored (Shop)",
        help="Shown in the sponsored strip on the Supply Shop main page.")
    clinic_preorder = fields.Boolean(
        string="Pre-order Allowed",
        help="Shop shows a pre-order badge when the vendor is out of stock.")

    def _compute_clinic_stock_info(self):
        # sudo: doctors/staff without purchase or full stock rights must still
        # be able to open the product form
        Move = self.env["stock.move"].sudo()
        Pol = self.env["purchase.order.line"].sudo()
        since = fields.Datetime.now() - timedelta(days=90)
        for tmpl in self:
            variants = tmpl.product_variant_ids
            consumed = Move._read_group(
                [("product_id", "in", variants.ids),
                 ("state", "=", "done"),
                 ("date", ">=", since),
                 ("location_id.usage", "=", "internal"),
                 ("location_dest_id.usage", "in",
                  ("customer", "production", "inventory"))],
                [], ["product_uom_qty:sum"])
            qty = consumed[0][0] if consumed else 0.0
            tmpl.clinic_avg_consumption = (qty or 0.0) / 3.0
            pol = Pol.search(
                [("product_id", "in", variants.ids),
                 ("state", "in", ("purchase", "done"))],
                order="date_approve desc, id desc", limit=1)
            tmpl.clinic_last_purchase_price = (
                pol.price_unit if pol else (tmpl.seller_ids[:1].price or 0.0))

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
        sis = self.env["product.supplierinfo"].sudo().search(
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
                "brand_id": tmpl.clinic_brand_id.id or False,
                "brand_name": tmpl.clinic_brand_id.name or "",
            })
        rows.sort(key=lambda r: r["name"].lower())
        cats = self.env["product.category"].search_read([], ["id", "display_name"])
        brands = self.env["clinic.brand"].sudo().search_read([], ["id", "name"])
        return {
            "vendor": {"id": vendor.id, "name": vendor.display_name},
            "products": rows,
            "categories": cats,
            "brands": brands,
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
        # the supplier owns the brand of THEIR product (reviewer): pick an
        # existing one or type a new name — created via sudo, deduplicated
        if "brand_id" in vals or vals.get("brand_new"):
            Brand = self.env["clinic.brand"].sudo()
            new_name = (vals.get("brand_new") or "").strip()
            if new_name:
                brand = Brand.search([("name", "=ilike", new_name)], limit=1)
                if not brand:
                    brand = Brand.create({"name": new_name})
                tmpl_vals["clinic_brand_id"] = brand.id
            else:
                tmpl_vals["clinic_brand_id"] = int(vals["brand_id"]) if vals.get("brand_id") else False
        if "image" in vals:
            tmpl_vals["image_1920"] = vals["image"] or False

        # The ORM writes run as sudo so the "own products only" record rule
        # never blocks a supplier from creating a brand-new product (which has
        # no supplierinfo line yet); vendor scoping is still enforced here.
        sudo = self.sudo()
        tmpl_id = vals.get("id")
        if tmpl_id:
            tmpl = sudo.browse(int(tmpl_id))
            # a supplier may only edit a product they actually offer
            has = self.env["product.supplierinfo"].sudo().search_count([
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
            tmpl = sudo.create(tmpl_vals)

        # ensure a supplierinfo line (price / lead time) for this vendor
        si = self.env["product.supplierinfo"].sudo().search([
            ("product_tmpl_id", "=", tmpl.id),
            ("partner_id", "=", vendor.id),
        ], limit=1)
        si_vals = {"price": price, "delay": delay}
        if si:
            si.write(si_vals)
        else:
            si_vals.update({"partner_id": vendor.id, "product_tmpl_id": tmpl.id})
            self.env["product.supplierinfo"].sudo().create(si_vals)
        return tmpl.id

    @api.model
    def clinic_supplier_unpublish(self, tmpl_id):
        """Remove the supplier's offer for a product (unlist it from the shop).
        Only removes this vendor's supplierinfo line; the product itself stays."""
        vendor = self._clinic_current_vendor()
        if not vendor:
            return False
        sis = self.env["product.supplierinfo"].sudo().search([
            ("product_tmpl_id", "=", int(tmpl_id)),
            ("partner_id", "=", vendor.id),
        ])
        sis.unlink()
        return True

    # ------------------------------------------------------------------
    # Supply Shop v2 — one RPC feeds the whole storefront (reviewer batch #2:
    # category tiles+photos, brands, banners, sponsored/new strips,
    # bestsellers, wishlist, repeat-last-order, vendor price comparison).
    # ------------------------------------------------------------------
    @api.model
    def clinic_shop_data(self):
        env = self.env
        b64 = self._clinic_b64
        now = fields.Datetime.now()
        new_after = now - timedelta(days=30)
        sis = env["product.supplierinfo"].sudo().search(
            [("product_tmpl_id.is_clinic_supply", "=", True)])
        # B4 item 12: average vendor rating from the orders' star ratings
        rating_map = {}
        for po in env["purchase.order"].sudo().search(
                [("is_clinic_order", "=", True),
                 ("clinic_rating_vendor", "!=", False)]):
            r = rating_map.setdefault(po.partner_id.id, [0, 0])
            r[0] += int(po.clinic_rating_vendor)
            r[1] += 1
        vendor_ratings = {vid: round(s / n, 1) for vid, (s, n) in rating_map.items()}
        offers = []
        for si in sis:
            if not si.partner_id:
                continue
            tmpl = si.product_tmpl_id
            prod = si.product_id or tmpl.product_variant_ids[:1]
            if not prod:
                continue
            categ = tmpl.categ_id
            top = categ
            while top.parent_id:
                top = top.parent_id
            offers.append({
                "key": "%s_%s" % (prod.id, si.partner_id.id),
                "product_id": prod.id,
                "name": prod.display_name,
                "vendor_id": si.partner_id.id,
                "vendor_name": si.partner_id.display_name,
                "price": si.price or 0.0,
                "delay": si.delay or 0,
                "image": b64(prod.image_128),
                "categ_id": categ.id or False,
                "categ_name": categ.display_name or "",
                "top_categ_id": top.id or False,
                "brand_id": tmpl.clinic_brand_id.id or False,
                "brand": tmpl.clinic_brand_id.name or "",
                "sponsored": tmpl.clinic_sponsored,
                "preorder": tmpl.clinic_preorder,
                "is_new": bool(tmpl.create_date and tmpl.create_date >= new_after),
                "qty": prod.qty_available,
                "vendor_rating": vendor_ratings.get(si.partner_id.id, 0),
            })
        categories = [{
            "id": c.id, "name": c.name,
            "parent_id": c.parent_id.id or False,
            "image": b64(c.image_128),
            "shop_visible": c.clinic_shop_visible,
        } for c in env["product.category"].sudo().search([])]
        banners = [{
            "id": bn.id, "name": bn.name, "note": bn.note or "",
            "image": b64(bn.image),
            "link": bn.link_url or "",
            "show_text": bn.show_text,
        } for bn in env["clinic.shop.banner"].sudo().search([])]
        # bestsellers: most purchased over the last 90 days (confirmed POs)
        best = env["purchase.order.line"].sudo()._read_group(
            [("order_id.state", "in", ("purchase", "done")),
             ("order_id.date_approve", ">=", now - timedelta(days=90)),
             ("product_id.is_clinic_supply", "=", True)],
            ["product_id"], ["product_qty:sum"])
        best.sort(key=lambda r: r[1], reverse=True)
        bestseller_ids = [p.id for p, _q in best[:8]]
        wishlist_ids = env["clinic.shop.wishlist"].search(
            [("user_id", "=", env.uid)]).mapped("product_id").ids
        # the current user's last shop order → "repeat last order"
        last_po = env["purchase.order"].sudo().search(
            [("is_clinic_order", "=", True), ("create_uid", "=", env.uid)],
            order="id desc", limit=1)
        last_order = False
        if last_po:
            last_order = {
                "name": last_po.name,
                "lines": [{
                    "product_id": l.product_id.id,
                    "vendor_id": last_po.partner_id.id,
                    "qty": l.product_qty,
                    "price": l.price_unit,
                } for l in last_po.order_line if l.product_id],
            }
        return {
            "offers": offers,
            "categories": categories,
            "banners": banners,
            "bestseller_ids": bestseller_ids,
            "wishlist_ids": wishlist_ids,
            "last_order": last_order,
        }

    @api.model
    def clinic_wishlist_toggle(self, product_id):
        """Add/remove one product from the current user's wishlist."""
        Wish = self.env["clinic.shop.wishlist"]
        rec = Wish.search([
            ("user_id", "=", self.env.uid),
            ("product_id", "=", int(product_id)),
        ], limit=1)
        if rec:
            rec.unlink()
            return False
        Wish.create({"product_id": int(product_id)})
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
        # batch #2: the alert also drafts a purchase request (source=low_stock)
        # unless an open request already covers the product
        self.env["clinic.purchase.request"]._clinic_auto_request_low_stock(low)
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
