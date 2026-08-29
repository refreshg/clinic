# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    # The room a dentist usually works in — auto-filled on new visits.
    default_room_id = fields.Many2one("clinic.room", string="Default Room")

    @api.model
    def clinic_dentists(self):
        """Dentist columns for the planning board.

        An Administrator sees every clinic dentist; a Clinic Doctor who is not
        an administrator sees only their own column (they may only view their
        own appointments — enforced by the calendar.event record rule too)."""
        doctor_group = self.env.ref(
            "clinic_patient_card.group_clinic_doctor", raise_if_not_found=False
        )
        admin_group = self.env.ref(
            "clinic_patient_card.group_clinic_admin", raise_if_not_found=False
        )
        if not doctor_group:
            return []
        is_admin = admin_group and admin_group in self.env.user.all_group_ids
        if not is_admin and doctor_group in self.env.user.all_group_ids:
            # a plain doctor: only their own column
            return [{"id": self.env.user.id, "name": self.env.user.name}]
        users = self.search([("all_group_ids", "in", doctor_group.id)])
        return [{"id": u.id, "name": u.name} for u in users]
