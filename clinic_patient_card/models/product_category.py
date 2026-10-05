# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models
from odoo.tools import file_open

from .clinic_shop_tree import TREE


class ProductCategory(models.Model):
    """Shop v2 (reviewer batch #2): categories carry a photo for the
    storefront tiles; subcategories come from the standard parent_id tree."""
    _inherit = "product.category"

    image_128 = fields.Image(max_width=256, max_height=256)
    # explicit storefront control: untick to keep the category (and its tile)
    # out of the shop menu even when it holds published products
    clinic_shop_visible = fields.Boolean(
        string="Show in Shop Menu", default=True)
    # keep the tile on the storefront even while no supplier offers a product in it
    clinic_shop_pinned = fields.Boolean(string="Always show tile", default=False)

    @api.model
    def _clinic_seed_shop_categories(self):
        """Seed the shop's category tree (models/clinic_shop_tree.py): the seven
        original categories keep their records, the rest is created when missing
        (matched by name + parent). Every node is pinned so the menu shows the
        whole structure; top categories get a starter picture when they have
        none (the clinic replaces it in Configuration -> Categories — an
        existing photo is never overwritten)."""
        def photo(fname):
            try:
                with file_open("clinic_patient_card/static/src/img/shop/%s.png" % fname, "rb") as fh:
                    return base64.b64encode(fh.read())
            except OSError:
                return False

        expected = set()

        def node(name, parent):
            cat = self.search([("name", "=", name), ("parent_id", "=", parent.id or False)], limit=1)
            if not cat:
                cat = self.create({"name": name, "parent_id": parent.id or False})
            if not cat.clinic_shop_pinned:
                cat.clinic_shop_pinned = True
            expected.add(cat.id)
            return cat

        def kids(parent, children):
            for ch in children:
                if isinstance(ch, str):
                    node(ch, parent)
                else:
                    sub = node(ch[0], parent)
                    kids(sub, ch[1])

        for name, xmlid, fname, children in TREE:
            top = self.env.ref("clinic_patient_card." + xmlid, raise_if_not_found=False) if xmlid else False
            top = top or node(name, self.browse())
            vals = {"clinic_shop_pinned": True}
            if not top.image_128 and fname:
                img = photo(fname)
                if img:
                    vals["image_128"] = img
            top.write(vals)
            expected.add(top.id)
            kids(top, children)
        # remove pinned nodes that left the tree (an older grouping); their products
        # move up to the parent first, deepest nodes first
        stale = self.search([("clinic_shop_pinned", "=", True), ("id", "not in", list(expected))])
        for cat in stale.sorted(lambda c: len(c.parent_path or ""), reverse=True):
            prods = self.env["product.template"].with_context(active_test=False).search(
                [("categ_id", "=", cat.id)])
            if prods and cat.parent_id:
                prods.write({"categ_id": cat.parent_id.id})
            if not prods or cat.parent_id:
                try:
                    with self.env.cr.savepoint():
                        cat.unlink()
                except Exception:
                    cat.clinic_shop_pinned = False
