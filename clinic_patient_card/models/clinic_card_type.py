# -*- coding: utf-8 -*-
from odoo import fields, models


class ClinicCardType(models.Model):
    """Card types offered when a visit is paid by card (Configuration → Card Types)."""
    _name = "clinic.card.type"
    _description = "Payment Card Type"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
