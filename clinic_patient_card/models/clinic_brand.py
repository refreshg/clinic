# -*- coding: utf-8 -*-
from odoo import fields, models


class ClinicBrand(models.Model):
    """Manufacturer brand of a clinic supply (reviewer batch #2: brand shown
    on the product and used as a shop filter)."""
    _name = "clinic.brand"
    _description = "Clinic Supply Brand"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    logo = fields.Image(max_width=256, max_height=256)
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint(
        "unique (name)", "This brand already exists.")
