# -*- coding: utf-8 -*-
from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def clinic_dentists(self):
        """Clinic dentists for the planning board — every user in the Clinic
        Doctor group, so their columns show even on a day with no bookings."""
        group = self.env.ref(
            "clinic_patient_card.group_clinic_doctor", raise_if_not_found=False
        )
        if not group:
            return []
        users = self.search([("all_group_ids", "in", group.id)])
        return [{"id": u.id, "name": u.name} for u in users]
