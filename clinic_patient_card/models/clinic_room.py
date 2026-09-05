# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ClinicRoom(models.Model):
    _name = "clinic.room"
    _description = "Clinic Room / Chair"
    _order = "sequence, name"

    name = fields.Char(string="Room", required=True)
    sequence = fields.Integer(default=10)
    note = fields.Char(string="Note")
    active = fields.Boolean(default=True)
    # Every room owns a stock location under WH/Stock/Cabinets, so cabinet
    # stock, transfers Room→Room and per-location min/max rules all run on
    # standard Inventory (reviewer batch #2: warehouse structure).
    location_id = fields.Many2one(
        "stock.location", string="Stock Location", copy=False, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        rooms = super().create(vals_list)
        rooms._clinic_ensure_location()
        return rooms

    def write(self, vals):
        res = super().write(vals)
        if "name" in vals:
            # keep the location named after the room
            for room in self.filtered("location_id"):
                room.location_id.sudo().name = room.name
        return res

    def _clinic_ensure_location(self):
        parent = self.env.ref(
            "clinic_patient_card.stock_location_clinic_cabinets",
            raise_if_not_found=False)
        if not parent:
            return
        Location = self.env["stock.location"].sudo()
        for room in self.filtered(lambda r: not r.location_id):
            room.location_id = Location.create({
                "name": room.name,
                "usage": "internal",
                "location_id": parent.id,
            }).id

    @api.model
    def _clinic_sync_locations(self):
        """Idempotent — called from data on every module upgrade so rooms that
        existed before batch #2 (or were imported) get their location too."""
        self.with_context(active_test=False).search(
            [("location_id", "=", False)])._clinic_ensure_location()
        return True
