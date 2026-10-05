# -*- coding: utf-8 -*-
"""Product reviews of the supply shop (D-38, stage B).

A review = stars + text + photos of the RECEIVED goods, written by the clinic
(administrator or doctor) for a product they actually received. It shows in the
product window next to the sales / rating / return numbers. A review is also
created from the order's own rating (the manager rates the received order and may
attach photos of what arrived).
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError

RATINGS = [("1", "★"), ("2", "★★"), ("3", "★★★"), ("4", "★★★★"), ("5", "★★★★★")]


class ClinicShopReviewImage(models.Model):
    _name = "clinic.shop.review.image"
    _description = "Photo of a received product (review / order rating)"
    _order = "id"

    review_id = fields.Many2one("clinic.shop.review", ondelete="cascade", index=True)
    purchase_id = fields.Many2one("purchase.order", ondelete="cascade", index=True)
    from_order = fields.Boolean(help="Copy of a photo attached to the order's rating.")
    image = fields.Image(required=True, max_width=1920, max_height=1920)
    image_1024 = fields.Image(related="image", max_width=1024, max_height=1024, store=True)
    image_128 = fields.Image(related="image", max_width=128, max_height=128, store=True)


class ClinicShopReview(models.Model):
    _name = "clinic.shop.review"
    _description = "Supply shop product review"
    _order = "id desc"

    tmpl_id = fields.Many2one("product.template", required=True, ondelete="cascade", index=True)
    user_id = fields.Many2one(
        "res.users", string="Author", required=True, default=lambda s: s.env.user, index=True)
    rating = fields.Selection(RATINGS, required=True)
    text = fields.Text(string="Comment")
    image_ids = fields.One2many("clinic.shop.review.image", "review_id", string="Photos")
    purchase_id = fields.Many2one(
        "purchase.order", string="Order", help="Set when the review came from an order rating.")

    _sql_constraints = [
        ("user_tmpl_uniq", "unique(user_id, tmpl_id)",
         "You have already reviewed this product — edit your review."),
    ]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # ----------------------------------------------------------- helpers
    def _clinic_received_lines(self):
        """Clinic purchase lines of this template that have been received."""
        self.ensure_one()
        return self.env["purchase.order.line"].sudo().search([
            ("product_id.product_tmpl_id", "=", self.id),
            ("qty_received", ">", 0),
            "|", ("order_id.is_clinic_order", "=", True),
            ("order_id.clinic_request_id", "!=", False)])

    def _clinic_can_review(self):
        self.ensure_one()
        user = self.env.user
        in_role = user.has_group("clinic_patient_card.group_clinic_admin") \
            or user.has_group("clinic_patient_card.group_clinic_doctor")
        return bool(in_role and self._clinic_received_lines())

    # ----------------------------------------------------------- RPCs
    @api.model
    def clinic_shop_reviews(self, tmpl_id):
        tmpl = self.sudo().browse(int(tmpl_id))
        if not tmpl.exists():
            return {}
        lines = tmpl._clinic_received_lines()
        sold = sum(lines.mapped("qty_received"))
        reviews = self.env["clinic.shop.review"].sudo().search([("tmpl_id", "=", tmpl.id)])
        avg = round(sum(int(r.rating) for r in reviews) / len(reviews), 1) if reviews else 0
        returns = self.env["clinic.purchase.return"].sudo().search(
            [("purchase_id", "in", lines.mapped("order_id").ids)])
        me = self.env.user
        mine = reviews.filtered(lambda r: r.user_id == me)[:1]
        tz_dt = lambda d: fields.Datetime.to_string(  # noqa: E731
            fields.Datetime.context_timestamp(self, d)) if d else ""
        return {
            "sold": sold,
            "avg": avg,
            "count": len(reviews),
            "breakdown": {s: len(reviews.filtered(lambda r, s=s: r.rating == s)) for s in "54321"},
            "orders": len(lines.mapped("order_id")),
            "can_review": tmpl._clinic_can_review(),
            "mine": {
                "id": mine.id, "rating": int(mine.rating), "text": mine.text or "",
            } if mine else False,
            "returns": [{
                "id": r.id, "order": r.purchase_id.name, "state": r.state,
                "state_label": dict(r._fields["state"].selection).get(r.state, r.state),
                "reason": r.reason or "", "note": r.decision_note or "",
                "date": tz_dt(r.create_date),
                "image": "/web/image/clinic.purchase.return/%d/image" % r.id if r.image else False,
            } for r in returns],
            "reviews": [{
                "id": r.id,
                "author": r.user_id.name,
                "rating": int(r.rating),
                "text": r.text or "",
                "date": tz_dt(r.create_date),
                "own": r.user_id == me,
                "order": r.purchase_id.name or "",
                "images": [{
                    "url": "/web/image/clinic.shop.review.image/%d/image_1024" % i.id,
                    "thumb": "/web/image/clinic.shop.review.image/%d/image_128" % i.id,
                } for i in r.image_ids],
            } for r in reviews],
        }

    @api.model
    def clinic_shop_review_save(self, tmpl_id, rating, text, images=None, remove_images=None):
        tmpl = self.sudo().browse(int(tmpl_id))
        if not tmpl.exists():
            raise UserError(_("Product not found."))
        if not self.browse(tmpl.id)._clinic_can_review():
            raise UserError(_("You can review a product only after the clinic has received it."))
        rating = str(int(rating))
        if rating not in dict(RATINGS):
            raise UserError(_("Choose 1 to 5 stars."))
        Review = self.env["clinic.shop.review"].sudo()
        rev = Review.search([("tmpl_id", "=", tmpl.id), ("user_id", "=", self.env.uid)], limit=1)
        vals = {"rating": rating, "text": (text or "").strip() or False}
        if rev:
            rev.write(vals)
        else:
            rev = Review.create(dict(vals, tmpl_id=tmpl.id, user_id=self.env.uid))
        if remove_images:
            rev.image_ids.filtered(lambda i: i.id in [int(x) for x in remove_images]).unlink()
        for b64 in images or []:
            if b64:
                self.env["clinic.shop.review.image"].sudo().create(
                    {"review_id": rev.id, "image": b64})
        return rev.id

    @api.model
    def clinic_shop_review_delete(self, review_id):
        rev = self.env["clinic.shop.review"].sudo().browse(int(review_id))
        if rev.exists() and (rev.user_id == self.env.user
                             or self.env.user.has_group("clinic_patient_card.group_clinic_admin")):
            rev.unlink()
        return True


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    clinic_rating_image_ids = fields.One2many(
        "clinic.shop.review.image", "purchase_id", string="Photos of the received goods")

    def write(self, vals):
        res = super().write(vals)
        if "clinic_rating_product" in vals and vals.get("clinic_rating_product"):
            for po in self:
                po._clinic_sync_reviews()
        return res

    def _clinic_sync_reviews(self):
        """The order's rating becomes a review on every product of the order (author =
        the user who rated), carrying the order's photos of the received goods."""
        self.ensure_one()
        Review = self.env["clinic.shop.review"].sudo()
        tmpls = self.order_line.mapped("product_id.product_tmpl_id").filtered("is_clinic_supply")
        for tmpl in tmpls:
            rev = Review.search([("tmpl_id", "=", tmpl.id), ("user_id", "=", self.env.uid)], limit=1)
            vals = {"rating": self.clinic_rating_product, "text": self.clinic_rating_note or False,
                    "purchase_id": self.id}
            if rev:
                rev.write(vals)
                rev.image_ids.filtered("from_order").unlink()
            else:
                rev = Review.create(dict(vals, tmpl_id=tmpl.id, user_id=self.env.uid))
            for img in self.clinic_rating_image_ids:
                self.env["clinic.shop.review.image"].sudo().create(
                    {"review_id": rev.id, "from_order": True, "image": img.image})
