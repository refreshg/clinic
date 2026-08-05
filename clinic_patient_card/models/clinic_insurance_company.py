# -*- coding: utf-8 -*-
from odoo import fields, models


class ClinicInsuranceCompany(models.Model):
    _name = "clinic.insurance.company"
    _description = "Insurance Company"
    _order = "name"

    name = fields.Char(string="Insurance Company", required=True)
    note = fields.Char(string="Note")
    active = fields.Boolean(string="Active", default=True)
