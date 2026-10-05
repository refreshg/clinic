# -*- coding: utf-8 -*-
"""Product gallery (several pictures + video links) and options (colour, size…)
for the supply shop's product window (D-38).

Standard-first: options = the standard product attributes / variants
(`product.attribute`, `product.template.attribute.line`); the gallery is a tiny
custom model because Community has no `product.image` without website_sale.
Suppliers maintain both from their panel (the panel writes through sudo with
vendor scoping — see `clinic_supplier_save_product`).
"""
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ClinicProductMedia(models.Model):
    _name = "clinic.product.media"
    _description = "Product gallery item (picture or video link)"
    _order = "sequence, id"

    tmpl_id = fields.Many2one(
        "product.template", string="Product", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    image = fields.Image(max_width=1920, max_height=1920)
    image_1024 = fields.Image(related="image", max_width=1024, max_height=1024, store=True)
    image_128 = fields.Image(related="image", max_width=128, max_height=128, store=True)
    video_url = fields.Char(string="Video link (YouTube / Vimeo / file URL)")

    @api.constrains("image", "video_url")
    def _check_content(self):
        for rec in self:
            if not rec.image and not (rec.video_url or "").strip():
                raise UserError(_("A gallery item needs a picture or a video link."))


class ProductTemplate(models.Model):
    _inherit = "product.template"

    clinic_media_ids = fields.One2many(
        "clinic.product.media", "tmpl_id", string="Gallery (pictures / videos)")

    # ---------------- supplier panel: gallery + options ----------------
    @api.model
    def clinic_supplier_products(self):
        res = super().clinic_supplier_products()
        for row in res.get("products", []):
            tmpl = self.sudo().browse(row["id"])
            row["media"] = [{
                "id": m.id,
                "preview": ("data:image/png;base64,%s" % m.image_128.decode())
                if m.image_128 else False,
                "video_url": m.video_url or "",
            } for m in tmpl.clinic_media_ids]
            row["options"] = [{
                "name": line.attribute_id.name,
                "values": ", ".join(line.value_ids.mapped("name")),
            } for line in tmpl.attribute_line_ids]
        return res

    @api.model
    def clinic_supplier_save_product(self, vals):
        tmpl_id = super().clinic_supplier_save_product(vals)
        tmpl = self.sudo().browse(tmpl_id)
        media = vals.get("media")
        if media:
            Media = self.env["clinic.product.media"].sudo()
            for mid in media.get("remove", []):
                Media.search([("id", "=", int(mid)), ("tmpl_id", "=", tmpl.id)]).unlink()
            for item in media.get("add", []):
                if item.get("image") or (item.get("video_url") or "").strip():
                    Media.create({
                        "tmpl_id": tmpl.id,
                        "image": item.get("image") or False,
                        "video_url": (item.get("video_url") or "").strip() or False,
                    })
        if vals.get("options") is not None:
            tmpl._clinic_apply_options(vals["options"])
        return tmpl_id

    def _clinic_apply_options(self, options):
        """options: [{name, values: "red, blue"}]; the template's attribute lines
        become exactly this list (variants follow the standard attribute logic)."""
        self.ensure_one()
        Attr = self.env["product.attribute"].sudo()
        Val = self.env["product.attribute.value"].sudo()
        keep = self.env["product.template.attribute.line"]
        for opt in options:
            name = (opt.get("name") or "").strip()
            raw = opt.get("values") or ""
            values = raw if isinstance(raw, list) else re.split(r"[,\n;]", raw)
            values = [v.strip() for v in values if v and v.strip()]
            values = list(dict.fromkeys(values))
            if not name or not values:
                continue
            attr = Attr.search([("name", "=ilike", name)], limit=1) or Attr.create({
                "name": name, "display_type": "radio", "create_variant": "always"})
            value_ids = []
            for v in values:
                val = Val.search([("attribute_id", "=", attr.id), ("name", "=ilike", v)], limit=1) \
                    or Val.create({"attribute_id": attr.id, "name": v})
                value_ids.append(val.id)
            line = self.attribute_line_ids.filtered(lambda l: l.attribute_id == attr)
            if line:
                line[0].write({"value_ids": [(6, 0, value_ids)]})
                line = line[0]
            else:
                line = self.env["product.template.attribute.line"].sudo().create({
                    "product_tmpl_id": self.id, "attribute_id": attr.id,
                    "value_ids": [(6, 0, value_ids)]})
            keep |= line
        (self.attribute_line_ids - keep).unlink()

    # ---------------- shop: the product window ----------------
    @api.model
    def clinic_shop_detail(self, product_id, vendor_id):
        """Everything the product window needs: gallery, options, variants with the
        vendor's price and own stock, description."""
        prod = self.env["product.product"].sudo().browse(int(product_id))
        tmpl = prod.product_tmpl_id
        if not tmpl.exists() or not tmpl.is_clinic_supply or not tmpl.clinic_shop_published:
            raise UserError(_("This product is not available in the shop."))
        sis = self.env["product.supplierinfo"].sudo().search([
            ("product_tmpl_id", "=", tmpl.id), ("partner_id", "=", int(vendor_id))])
        variants = tmpl.product_variant_ids

        def price_for(v):
            si = sis.filtered(lambda s: s.product_id == v) or sis.filtered(lambda s: not s.product_id)
            return ((si or sis)[:1].price) or 0.0

        qty = {}
        for q in self.env["stock.quant"].sudo().search([
                ("product_id", "in", variants.ids),
                ("location_id.clinic_supplier_id", "=", int(vendor_id)),
                ("location_id.usage", "=", "internal")]):
            qty[q.product_id.id] = qty.get(q.product_id.id, 0.0) + q.quantity

        media = []
        if tmpl.image_1920:
            media.append({"type": "image",
                          "url": "/web/image/product.template/%d/image_1024" % tmpl.id,
                          "thumb": "/web/image/product.template/%d/image_128" % tmpl.id})
        for m in tmpl.clinic_media_ids:
            if m.image:
                media.append({"type": "image",
                              "url": "/web/image/clinic.product.media/%d/image_1024" % m.id,
                              "thumb": "/web/image/clinic.product.media/%d/image_128" % m.id})
            if m.video_url:
                media.append({"type": "video", "url": m.video_url, "thumb": False})
        options = [{
            "id": line.attribute_id.id,
            "name": line.attribute_id.name,
            "values": [{"id": ptav.id, "name": ptav.name}
                       for ptav in line.product_template_value_ids if ptav.ptav_active],
        } for line in tmpl.attribute_line_ids]
        return {
            "tmpl_id": tmpl.id,
            "name": tmpl.name,
            "desc": tmpl.description_sale or tmpl.description or "",
            "media": media,
            "options": options,
            "variants": [{
                "id": v.id, "name": v.display_name,
                "combo": v.product_template_attribute_value_ids.ids,
                "price": price_for(v), "qty": qty.get(v.id, 0.0),
            } for v in variants],
            "current": prod.id,
        }
