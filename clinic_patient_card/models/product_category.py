# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductCategory(models.Model):
    """Shop v2 (reviewer batch #2): categories carry a photo for the
    storefront tiles; subcategories come from the standard parent_id tree."""
    _inherit = "product.category"

    image_128 = fields.Image(max_width=256, max_height=256)
