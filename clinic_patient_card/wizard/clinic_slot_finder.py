# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ClinicSlotFinder(models.TransientModel):
    """Free-slot search per direction + duration (reviewer batch #2)."""
    _name = "clinic.slot.finder"
    _description = "Clinic Free Slot Finder"

    event_id = fields.Many2one("calendar.event")
    direction_id = fields.Many2one("clinic.direction", string="Direction")
    duration = fields.Float(string="Duration (hours)", default=0.5)
    date_from = fields.Date(string="From Date")
    line_ids = fields.One2many("clinic.slot.finder.line", "wizard_id")

    def action_search(self):
        self.ensure_one()
        self.line_ids.unlink()
        date_from = (fields.Datetime.to_datetime(self.date_from)
                     if self.date_from else None)
        slots = self.env["calendar.event"].clinic_free_slots(
            self.direction_id.id, self.duration, date_from)
        self.env["clinic.slot.finder.line"].create([{
            "wizard_id": self.id,
            "start": s["start"],
            "stop": s["stop"],
            "dentist_id": s["dentist_id"],
            "room": s["room"],
        } for s in slots])
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }


class ClinicSlotFinderLine(models.TransientModel):
    _name = "clinic.slot.finder.line"
    _description = "Clinic Free Slot"
    _order = "start, id"

    wizard_id = fields.Many2one("clinic.slot.finder", ondelete="cascade")
    start = fields.Datetime()
    stop = fields.Datetime()
    dentist_id = fields.Many2one("res.users", string="Doctor")
    room = fields.Char(string="Room")

    def action_pick(self):
        """Write the chosen slot back onto the visit being edited."""
        self.ensure_one()
        ev = self.wizard_id.event_id
        vals = {
            "start": self.start,
            "stop": self.stop,
            "dentist_id": self.dentist_id.id,
        }
        if self.wizard_id.direction_id:
            vals["direction_id"] = self.wizard_id.direction_id.id
        if ev:
            ev.write(vals)
            return {"type": "ir.actions.act_window_close"}
        # new, unsaved visit: open a prefilled form instead
        return {
            "type": "ir.actions.act_window",
            "res_model": "calendar.event",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_is_clinic": True,
                **{"default_" + k: v for k, v in vals.items()},
            },
        }
