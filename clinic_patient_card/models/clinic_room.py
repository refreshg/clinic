# -*- coding: utf-8 -*-
from odoo import fields, models


class ClinicRoom(models.Model):
    _name = "clinic.room"
    _description = "Clinic Room / Chair"
    _order = "sequence, name"

    name = fields.Char(string="Room", required=True)
    sequence = fields.Integer(default=10)
    note = fields.Char(string="Note")
    active = fields.Boolean(default=True)
