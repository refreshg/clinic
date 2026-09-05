# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ClinicSlotFinder(models.TransientModel):
    """Free-slot search per direction + duration (reviewer batch #2)."""
    _name = "clinic.slot.finder"
    _description = "Clinic Free Slot Finder"

    event_id = fields.Many2one("calendar.event")
    direction_id = fields.Many2one("clinic.direction", string="Direction")
    duration = fields.Float(string="Duration (hours)", default=0.5)
    date_from = fields.Date(string="From Date")
    line_ids = fields.One2many("clinic.slot.finder.line", "wizard_id")
    message = fields.Char(readonly=True)
    # The picked slot is stored HERE and applied to the open visit form by the
    # slot-finder widget WITHOUT saving the visit (reviewer: nothing may be
    # saved until the user presses Save).
    picked = fields.Boolean(readonly=True)
    picked_start = fields.Datetime(readonly=True)
    picked_stop = fields.Datetime(readonly=True)
    picked_dentist_id = fields.Many2one("res.users", readonly=True)

    def action_search(self):
        self.ensure_one()
        self.line_ids.unlink()
        date_from = (fields.Datetime.to_datetime(self.date_from)
                     if self.date_from else None)
        # an empty result must SAY why, not show a silent empty list
        if self.direction_id and not self.env["res.users"].search_count([
                ("all_group_ids", "in", self.env.ref(
                    "clinic_patient_card.group_clinic_doctor").id),
                ("direction_id", "=", self.direction_id.id)]):
            self.message = _(
                'No doctor is assigned to the "%s" direction — set it on the '
                "user's Clinic tab (Settings → Users).") % self.direction_id.name
            slots = []
        else:
            slots = self.env["calendar.event"].clinic_free_slots(
                self.direction_id.id, self.duration, date_from)
            self.message = (
                _("No free slots in the coming days — try another date or "
                  "duration.") if not slots else False)
        self.env["clinic.slot.finder.line"].create([{
            "wizard_id": self.id,
            "start": s["start"],
            "stop": s["stop"],
            "dentist_id": s["dentist_id"],
            "room": s["room"],
        } for s in slots])
        return {
            "type": "ir.actions.act_window",
            "name": _("Free Slots"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_close(self):
        # a footer special="cancel" tears down the WHOLE dialog stack (the
        # visit form behind the finder closed too) — a plain window-close
        # action closes only this dialog
        return {"type": "ir.actions.act_window_close"}


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
        """Remember the chosen slot on the wizard and close; the widget on the
        visit form copies it into the form's fields client-side, so the visit
        itself is NOT saved until the user presses Save."""
        self.ensure_one()
        self.wizard_id.write({
            "picked": True,
            "picked_start": self.start,
            "picked_stop": self.stop,
            "picked_dentist_id": self.dentist_id.id,
        })
        return {"type": "ir.actions.act_window_close"}
