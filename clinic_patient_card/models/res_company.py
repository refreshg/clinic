# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    """One clinic-wide working schedule (user decision — no per-dentist
    calendars). Booking outside these days/hours is blocked and the Planning
    board greys the closed time out."""
    _inherit = "res.company"

    clinic_workday_mon = fields.Boolean(string="Monday", default=True)
    clinic_workday_tue = fields.Boolean(string="Tuesday", default=True)
    clinic_workday_wed = fields.Boolean(string="Wednesday", default=True)
    clinic_workday_thu = fields.Boolean(string="Thursday", default=True)
    clinic_workday_fri = fields.Boolean(string="Friday", default=True)
    clinic_workday_sat = fields.Boolean(string="Saturday", default=True)
    clinic_workday_sun = fields.Boolean(string="Sunday", default=False)
    clinic_work_start = fields.Float(
        string="Opens At", default=9.0, help="Clinic opening hour (local time)."
    )
    clinic_work_end = fields.Float(
        string="Closes At", default=18.0, help="Clinic closing hour (local time)."
    )
    # If one room hosts two chairs, turn this off on the company form.
    clinic_block_room_overlap = fields.Boolean(
        string="Block Room Double-Booking", default=True,
    )

    def _clinic_workdays(self):
        """Return the set of working weekday numbers (0=Monday .. 6=Sunday)."""
        self.ensure_one()
        flags = [
            self.clinic_workday_mon, self.clinic_workday_tue,
            self.clinic_workday_wed, self.clinic_workday_thu,
            self.clinic_workday_fri, self.clinic_workday_sat,
            self.clinic_workday_sun,
        ]
        return {i for i, on in enumerate(flags) if on}
