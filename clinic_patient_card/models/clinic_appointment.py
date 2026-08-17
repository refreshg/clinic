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
    # Procedures performed/planned in THIS visit (auto-pushed to patient history).
    procedure_line_ids = fields.One2many(
        "clinic.procedure.history", "appointment_id", string="Procedures",
    )
    payment_method = fields.Selection(
        [
            ("cash", "Cash"),
            ("card", "Card"),
            ("transfer", "Bank Transfer"),
            ("insurance", "Insurance"),
            ("mixed", "Mixed"),
        ],
        string="Payment Method",
    )

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
        # R2/R9 (admin marks arrival) + R10 (notify the dentist).
        self.write({"clinic_state": "arrived", "checkin_time": fields.Datetime.now()})
        for ev in self:
            ev._notify_dentist_arrived()

    def action_start(self):
        self.write({"clinic_state": "in_progress", "treat_start_time": fields.Datetime.now()})

    def action_done(self):
        # R12 — the doctor closes: push the visit's procedures to patient history.
        now = fields.Datetime.now()
        today = fields.Date.context_today(self)
        for ev in self:
            ev.write({"clinic_state": "done", "treat_end_time": now})
            for line in ev.procedure_line_ids:
                vals = {}
                if line.status != "done":
                    vals["status"] = "done"
                if not line.procedure_date:
                    vals["procedure_date"] = today
                if not line.doctor_id:
                    vals["doctor_id"] = (ev.dentist_id or self.env.user).id
                if not line.partner_id and ev.patient_id:
                    vals["partner_id"] = ev.patient_id.id
                if vals:
                    line.write(vals)
            if ev.patient_id:
                ev.patient_id.last_dental_visit_date = today

    def action_pay(self):
        # R14 — open the payment wizard (shows amount + payment method).
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Register Payment"),
            "res_model": "clinic.payment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_appointment_id": self.id},
        }

    def action_cancel(self):
        for ev in self:
            if not ev.cancel_reason:
                raise UserError(_("Please set a cancellation reason before cancelling."))
        self.write({"clinic_state": "cancelled"})

    def action_no_show(self):
        self.write({"clinic_state": "no_show"})

    # ------------------------------------------------------------------
    # 3C helpers — notification, follow-up, invoicing
    # ------------------------------------------------------------------
    def _notify_dentist_arrived(self):
        """R10 — to-do activity + live bus push (sound/toast) for the dentist."""
        self.ensure_one()
        dentist = self.dentist_id
        if not dentist:
            return
        todo = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if todo:
            self.env["mail.activity"].create({
                "res_model_id": self.env["ir.model"]._get_id("calendar.event"),
                "res_id": self.id,
                "activity_type_id": todo.id,
                "summary": _("Patient arrived: %s") % (self.patient_id.name or ""),
                "date_deadline": fields.Date.context_today(self),
                "user_id": dentist.id,
            })
        # Notify the dentist AND the acting user (so a single-session admin also
        # hears/sees it, and it works even if the dentist isn't logged in).
        payload = {
            "appointment_id": self.id,
            "patient": self.patient_id.name or "",
            "room": self.room_id.name or "",
        }
        partners = dentist.partner_id
        if self.env.user.partner_id:
            partners |= self.env.user.partner_id
        for partner in partners:
            self.env["bus.bus"]._sendone(partner, "clinic_patient_arrived", payload)

    def action_next_visit(self):
        """R13 — create a linked follow-up appointment (long-term plans)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Next Visit"),
            "res_model": "calendar.event",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_is_clinic": True,
                "default_patient_id": self.patient_id.id,
                "default_dentist_id": self.dentist_id.id,
                "default_room_id": self.room_id.id,
                "default_appointment_type_id": self.appointment_type_id.id,
                "default_parent_appointment_id": self.id,
                "default_name": self.name,
            },
        }

    def _create_invoice_from_procedures(self):
        """R14/pattern-5 — draft an invoice from the visit's procedure products.
        Defensive: skips silently if accounting has no sales journal configured.
        """
        self.ensure_one()
        if not self.patient_id:
            return
        lines = self.procedure_line_ids.filtered(lambda l: l.procedure_id)
        if not lines:
            return
        journal = self.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", self.env.company.id)], limit=1
        )
        if not journal:
            return
        invoice_lines = [
            (0, 0, {
                "product_id": line.procedure_id.id,
                "name": line.name or line.procedure_id.name,
                "quantity": line.qty or 1.0,
                "price_unit": line.procedure_id.list_price,
            })
            for line in lines
        ]
        self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.patient_id.id,
            "invoice_origin": self.name or "",
            "invoice_line_ids": invoice_lines,
        })
