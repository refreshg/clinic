# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ClinicShopBanner(models.Model):
    """Promo banners on the Supply Shop main page (reviewer batch #2)."""
    _name = "clinic.shop.banner"
    _description = "Clinic Shop Banner"
    _order = "sequence, id"

    name = fields.Char(required=True)
    image = fields.Image(max_width=1600, max_height=500,
                         help="Required unless a video link is given.")
    video_url = fields.Char(
        string="Video link (YouTube / Vimeo / file URL)",
        help="When set, the banner slot plays this video (muted, looping) instead of a picture.")
    note = fields.Char(string="Subtitle")
    link_url = fields.Char(
        string="Link (URL)",
        help="Opens in a new tab when the banner is clicked.")
    show_text = fields.Boolean(
        string="Show Texts on Banner", default=True,
        help="Untick when the image already carries its own text.")
    size = fields.Selection(
        [("auto", "Automatic (by position)"),
         ("third", "Small — 1/3 of the row"),
         ("half", "Medium — 1/2 of the row"),
         ("two_thirds", "Wide — 2/3 of the row"),
         ("full", "Full row")],
        string="Width", default="auto", required=True,
        help="Banners flow left to right; a new row starts when the row is full.")
    height = fields.Integer(
        string="Height (px)", help="Empty / 0 = the default height of the chosen width.")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    @api.model
    def _clinic_split_video(self, vals):
        """A YouTube / Vimeo link typed into "Link (URL)" is a video, not a page to open."""
        link = (vals.get("link_url") or "").lower()
        if link and not vals.get("video_url") and any(
                h in link for h in ("youtube.com", "youtu.be", "vimeo.com")):
            vals["video_url"] = vals["link_url"]
            vals["link_url"] = False
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        return super().create([self._clinic_split_video(dict(v)) for v in vals_list])

    def write(self, vals):
        return super().write(self._clinic_split_video(dict(vals)))

    @api.constrains("name", "image", "video_url")
    def _check_banner_content(self):
        for rec in self:
            if not rec.image and not (rec.video_url or "").strip():
                raise UserError(_("A banner needs a picture or a video link."))


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
