# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    """Dental procedures are standard products (type=service), not a custom
    catalog — so they reuse pricing, taxes and invoicing out of the box.
    """
    _inherit = "product.template"

    is_clinic_procedure = fields.Boolean(string="Clinic Procedure")
    # Consumables / materials the clinic keeps in stock and reorders from vendors.
    is_clinic_supply = fields.Boolean(string="Clinic Supply")
