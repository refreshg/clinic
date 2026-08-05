# -*- coding: utf-8 -*-
from odoo import fields, models


class ClinicProcedureCatalog(models.Model):
    _name = "clinic.procedure.catalog"
    _description = "Dental Procedure (catalog)"
    _order = "name"

    name = fields.Char(string="Procedure", required=True, translate=True)
    code = fields.Char(string="Code")
    default_price = fields.Float(string="Default Price")
    active = fields.Boolean(string="Active", default=True)
