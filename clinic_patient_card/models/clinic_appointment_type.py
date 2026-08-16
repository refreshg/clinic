# -*- coding: utf-8 -*-
from odoo import fields, models


class ClinicAppointmentType(models.Model):
    _name = "clinic.appointment.type"
    _description = "Appointment Type"
    _order = "name"

    name = fields.Char(string="Appointment Type", required=True, translate=True)
    color = fields.Integer(string="Color")
    default_duration = fields.Float(
        string="Default Duration (hours)", default=0.5,
        help="Pre-fills the appointment duration.",
    )
    procedure_id = fields.Many2one(
        "clinic.procedure.catalog", string="Default Procedure",
    )
    active = fields.Boolean(default=True)
