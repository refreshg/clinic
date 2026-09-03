# -*- coding: utf-8 -*-
from odoo import fields, models


class ClinicDirection(models.Model):
    """Clinical direction / specialty (therapy, surgery, orthodontics, ...).

    Reviewer batch #2: a booking carries a direction; each doctor has one, and
    the free-slot search runs per direction.
    """
    _name = "clinic.direction"
    _description = "Clinic Direction (Specialty)"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
