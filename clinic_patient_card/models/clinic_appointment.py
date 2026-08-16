# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CalendarEvent(models.Model):
    """Extend the standard calendar.event with the dental-visit lifecycle.

    Clinic appointments ARE calendar events (is_clinic=True), so they reuse the
    standard Calendar engine, reminders and recurrence. The clinical workflow
    (state machine, time tracking) lives here; notifications / auto-invoice /
    procedure auto-fill land in Phase 3C.
    """
    _inherit = "calendar.event"

    is_clinic = fields.Boolean(string="Clinic Appointment", index=True)
    patient_id = fields.Many2one("res.partner", string="Patient", index=True)
    dentist_id = fields.Many2one("res.users", string="Dentist", index=True)
    room_id = fields.Many2one("clinic.room", string="Room")
    appointment_type_id = fields.Many2one(
        "clinic.appointment.type", string="Appointment Type",
    )
    # Pattern 1 — governed status lifecycle (see docs/booking-visit-patterns.md).
    clinic_state = fields.Selection(
        [
            ("requested", "Requested"),
            ("booked", "Booked"),
            ("confirmed", "Confirmed"),
            ("arrived", "Arrived"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("paid", "Paid"),
            ("cancelled", "Cancelled"),
            ("no_show", "No-Show"),
        ],
        string="Visit Status",
        default="booked",
        tracking=True,
        copy=False,
        index=True,
    )
    cancel_reason = fields.Char(string="Cancellation Reason", copy=False)
    # Pattern 3 — stage time tracking.
    checkin_time = fields.Datetime(string="Check-in Time", readonly=True, copy=False)
    treat_start_time = fields.Datetime(string="Treatment Start", readonly=True, copy=False)
    treat_end_time = fields.Datetime(string="Treatment End", readonly=True, copy=False)
    waiting_minutes = fields.Integer(
        string="Waiting (min)", compute="_compute_durations", store=True,
    )
    chair_minutes = fields.Integer(
        string="Chair Time (min)", compute="_compute_durations", store=True,
    )
    # Follow-up chaining (long-term treatment plans).
    parent_appointment_id = fields.Many2one("calendar.event", string="Previous Visit")

    @api.depends("checkin_time", "treat_start_time", "treat_end_time")
    def _compute_durations(self):
        for ev in self:
            if ev.checkin_time and ev.treat_start_time:
                ev.waiting_minutes = int(
                    (ev.treat_start_time - ev.checkin_time).total_seconds() // 60
                )
            else:
                ev.waiting_minutes = 0
            if ev.treat_start_time and ev.treat_end_time:
                ev.chair_minutes = int(
                    (ev.treat_end_time - ev.treat_start_time).total_seconds() // 60
                )
            else:
                ev.chair_minutes = 0

    @api.onchange("appointment_type_id")
    def _onchange_appointment_type_id(self):
        atype = self.appointment_type_id
        if atype:
            if not self.name:
                self.name = atype.name
            if atype.default_duration:
                self.duration = atype.default_duration

    # ------------------------------------------------------------------
    # Workflow transitions (Phase 3A — basic; guards/notifs in 3B/3C)
    # ------------------------------------------------------------------
    def action_confirm(self):
        self.write({"clinic_state": "confirmed"})

    def action_arrive(self):
        self.write({"clinic_state": "arrived", "checkin_time": fields.Datetime.now()})

    def action_start(self):
        self.write({"clinic_state": "in_progress", "treat_start_time": fields.Datetime.now()})

    def action_done(self):
        self.write({"clinic_state": "done", "treat_end_time": fields.Datetime.now()})

    def action_pay(self):
        self.write({"clinic_state": "paid"})

    def action_cancel(self):
        for ev in self:
            if not ev.cancel_reason:
                raise UserError(_("Please set a cancellation reason before cancelling."))
        self.write({"clinic_state": "cancelled"})

    def action_no_show(self):
        self.write({"clinic_state": "no_show"})
