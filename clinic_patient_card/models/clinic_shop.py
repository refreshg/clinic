# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ClinicShopBanner(models.Model):
    """Promo banners on the Supply Shop main page (reviewer batch #2)."""
    _name = "clinic.shop.banner"
    _description = "Clinic Shop Banner"
    _order = "sequence, id"

    name = fields.Char(required=True)
    image = fields.Image(required=True, max_width=1600, max_height=500)
    note = fields.Char(string="Subtitle")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)


class ClinicShopWishlist(models.Model):
    """Per-user wishlist of shop products (reviewer batch #2)."""
    _name = "clinic.shop.wishlist"
    _description = "Clinic Shop Wishlist"

    user_id = fields.Many2one(
        "res.users", required=True, default=lambda s: s.env.user,
        ondelete="cascade", index=True)
    product_id = fields.Many2one(
        "product.product", required=True, ondelete="cascade")

    _user_product_uniq = models.Constraint(
        "unique (user_id, product_id)",
        "This product is already in the wishlist.")
