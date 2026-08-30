# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


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
    assistant_id = fields.Many2one(
        "res.users", string="Assistant / Resident",
        help="Assisting doctor or resident for this visit.",
    )
    room_id = fields.Many2one("clinic.room", string="Room")
    diagnosis = fields.Char(string="Diagnosis", copy=False)
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
    # Amounts registered by the payment wizard (mixed = cash + terminal split).
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id.id,
    )
    amount_paid = fields.Monetary(
        string="Paid Amount", currency_field="currency_id", readonly=True, copy=False,
    )
    amount_cash = fields.Monetary(
        string="Cash Part", currency_field="currency_id", readonly=True, copy=False,
    )
    amount_terminal = fields.Monetary(
        string="Terminal Part", currency_field="currency_id", readonly=True, copy=False,
    )
    # Dispensary programme: patients booked for a 6-month control visit.
    is_dispensary = fields.Boolean(string="Dispensary Control", copy=False)
    dispensary_notified = fields.Boolean(copy=False)  # 14-day reminder sent
    # Reviewer asks that reschedules / duration corrections stay visible.
    was_rescheduled = fields.Boolean(
        string="Rescheduled", copy=False,
        help="The start time was moved after the visit had been booked.",
    )
    duration_edited = fields.Boolean(
        string="Duration Corrected", copy=False,
        help="The duration was changed manually after the visit had been booked.",
    )
    # Read-only summary of the previous visit (date + procedures).
    parent_visit_info = fields.Char(
        string="Previous Visit Summary", compute="_compute_parent_visit_info",
    )
    # Teeth touched in this visit (from the procedure lines) — history list column.
    tooth_display = fields.Char(
        string="Teeth", compute="_compute_tooth_display",
    )

    @api.depends("procedure_line_ids.tooth")
    def _compute_tooth_display(self):
        for ev in self:
            teeth = [t for t in ev.procedure_line_ids.mapped("tooth") if t]
            # de-duplicate, keep order
            ev.tooth_display = ", ".join(dict.fromkeys(teeth)) or False

    @api.model
    def clinic_board_config(self):
        """Working schedule for the Planning board (grey out closed time)."""
        company = self.env.company
        return {
            "workdays": sorted(company._clinic_workdays()),  # 0=Mon .. 6=Sun
            "work_start": company.clinic_work_start or 0.0,
            "work_end": company.clinic_work_end or 24.0,
        }

    @api.depends("parent_appointment_id.start",
                 "parent_appointment_id.procedure_line_ids")
    def _compute_parent_visit_info(self):
        for ev in self:
            parent = ev.parent_appointment_id
            if not parent:
                ev.parent_visit_info = False
                continue
            date = ""
            if parent.start:
                local = fields.Datetime.context_timestamp(ev, parent.start)
                date = local.strftime("%d.%m.%Y %H:%M")
            procs = ", ".join(
                (line.procedure_id.name or line.name or "")
                for line in parent.procedure_line_ids
                if (line.procedure_id.name or line.name)
            )
            ev.parent_visit_info = " — ".join(part for part in (date, procs) if part) \
                or parent.display_name

    @api.constrains("is_clinic", "patient_id")
    def _check_clinic_patient(self):
        # Reviewer: a booking must never exist without a patient.
        for ev in self:
            if ev.is_clinic and not ev.patient_id:
                raise ValidationError(
                    _("A clinic visit cannot be saved without a patient.")
                )

    # ------------------------------------------------------------------
    # Scheduling rules (reviewer): working hours, no past bookings,
    # no double-booking of a dentist (or a room, company-configurable).
    # ------------------------------------------------------------------
    def _clinic_validate_schedule(self, start_dt, stop_dt=None):
        """Block bookings in the past (Clinic Administrators may override) and
        outside the clinic's working days/hours (context clinic_force=1 skips
        the schedule checks, e.g. for controlled data fixes)."""
        if self.env.context.get("clinic_force"):
            return
        # 1) not in the past (5-minute grace); ONLY the Administrator account
        # (base.user_admin) may back-date — user decision: everyone else,
        # including clinic-admin-role and Settings users, is blocked.
        admin_user = self.env.ref("base.user_admin", raise_if_not_found=False)
        if not admin_user or self.env.user.id != admin_user.id:
            if start_dt < fields.Datetime.now() - timedelta(minutes=5):
                raise UserError(_(
                    "Booking in the past is not allowed. "
                    "Ask the administrator if a back-dated visit is needed."
                ))
        # 2) inside working days/hours (local clinic time).
        company = self.env.company
        local_start = fields.Datetime.context_timestamp(self, start_dt)
        workdays = company._clinic_workdays()
        if workdays and local_start.weekday() not in workdays:
            raise UserError(_(
                "The clinic is closed on %s — booking is not possible."
            ) % local_start.strftime("%A"))
        start_h = local_start.hour + local_start.minute / 60.0
        if start_h < (company.clinic_work_start or 0.0) - 1e-6:
            raise UserError(_(
                "The visit starts before the clinic opens (%(open)02d:%(om)02d).",
                open=int(company.clinic_work_start),
                om=int(round((company.clinic_work_start % 1) * 60)),
            ))
        if stop_dt:
            local_stop = fields.Datetime.context_timestamp(self, stop_dt)
            stop_h = local_stop.hour + local_stop.minute / 60.0
            if local_stop.date() != local_start.date():
                stop_h += 24.0
            if stop_h > (company.clinic_work_end or 24.0) + 1e-6:
                raise UserError(_(
                    "The visit ends after the clinic closes (%(close)02d:%(cm)02d).",
                    close=int(company.clinic_work_end),
                    cm=int(round((company.clinic_work_end % 1) * 60)),
                ))

    @api.constrains("start", "stop", "dentist_id", "room_id", "clinic_state", "active")
    def _check_clinic_overlap(self):
        # Booked time is locked: the same dentist (and, if enabled, the same
        # room) cannot hold two overlapping live clinic visits. sudo() so the
        # per-doctor record rule can't hide a clashing visit.
        block_room = self.env.company.clinic_block_room_overlap
        for ev in self:
            if (
                not ev.is_clinic or not ev.start or not ev.stop
                or ev.clinic_state in ("cancelled", "no_show") or not ev.active
            ):
                continue
            if ev.clinic_state == "requested":
                # reserve/waitlist entries are placeholders — they neither
                # clash nor lock time until they are confirmed onto the grid
                continue
            base = [
                ("id", "!=", ev.id),
                ("is_clinic", "=", True),
                ("active", "=", True),
                ("clinic_state", "not in", ("cancelled", "no_show", "requested")),
                ("start", "<", ev.stop),
                ("stop", ">", ev.start),
            ]
            Event = self.sudo()
            if ev.dentist_id:
                clash = Event.search(base + [("dentist_id", "=", ev.dentist_id.id)], limit=1)
                if clash:
                    raise ValidationError(_(
                        "%(dentist)s is already booked at that time (%(visit)s). "
                        "Pick a free slot.",
                        dentist=ev.dentist_id.name, visit=clash.display_name,
                    ))
            if block_room and ev.room_id:
                clash = Event.search(base + [("room_id", "=", ev.room_id.id)], limit=1)
                if clash:
                    raise ValidationError(_(
                        "Room %(room)s is already occupied at that time (%(visit)s).",
                        room=ev.room_id.name, visit=clash.display_name,
                    ))

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
            # Don't stomp a slot picked on the planning board (it passes
            # default_stop): the type's default duration applies only when the
            # visit was started without an explicit time range.
            if atype.default_duration and not self.env.context.get("default_stop"):
                self.duration = atype.default_duration

    @api.onchange("dentist_id")
    def _onchange_dentist_id(self):
        # Reviewer: picking the dentist auto-fills their room (still editable).
        if self.dentist_id and self.dentist_id.default_room_id and not self.room_id:
            self.room_id = self.dentist_id.default_room_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("is_clinic"):
                continue
            # Onchange doesn't run on RPC creates (e.g. from the Planning
            # board): apply the dentist's default room here as well.
            if vals.get("dentist_id") and not vals.get("room_id"):
                dentist = self.env["res.users"].browse(vals["dentist_id"])
                if dentist.default_room_id:
                    vals["room_id"] = dentist.default_room_id.id
            # Scheduling rules: no past bookings, working hours only.
            if vals.get("start"):
                self._clinic_validate_schedule(
                    fields.Datetime.to_datetime(vals["start"]),
                    vals.get("stop") and fields.Datetime.to_datetime(vals["stop"]),
                )
        return super().create(vals_list)

    # States in which a start/duration change counts as a visible correction.
    _CLINIC_TRACK_STATES = ("booked", "confirmed", "arrived", "in_progress")

    def write(self, vals):
        # Flag reschedules / manual duration corrections on clinic visits so the
        # calendar can show them. No-op for non-clinic events (the recurrence
        # engine rewrites start/stop internally) and for our own flag writes.
        # Scheduling rules apply when a clinic visit's start is (re)set.
        if vals.get("start") and any(ev.is_clinic for ev in self):
            self._clinic_validate_schedule(
                fields.Datetime.to_datetime(vals["start"]),
                vals.get("stop") and fields.Datetime.to_datetime(vals["stop"]),
            )
        resched_ids, dured_ids = [], []
        if not self.env.context.get("clinic_flagging") and (
            "start" in vals or "stop" in vals or "duration" in vals
        ):
            for ev in self:
                if not ev.is_clinic or ev.clinic_state not in self._CLINIC_TRACK_STATES:
                    continue
                if vals.get("start"):
                    new_start = fields.Datetime.to_datetime(vals["start"])
                    if ev.start and new_start != ev.start:
                        resched_ids.append(ev.id)
                new_duration = None
                if "duration" in vals and vals["duration"]:
                    new_duration = vals["duration"]
                elif vals.get("stop") and not vals.get("start") and ev.start:
                    new_stop = fields.Datetime.to_datetime(vals["stop"])
                    new_duration = (new_stop - ev.start).total_seconds() / 3600.0
                if (
                    new_duration is not None
                    and ev.duration
                    and abs(new_duration - ev.duration) > 1 / 60.0
                ):
                    dured_ids.append(ev.id)
        res = super().write(vals)
        if resched_ids or dured_ids:
            flagger = self.with_context(clinic_flagging=True)
            if resched_ids:
                flagger.browse(resched_ids).write({"was_rescheduled": True})
            if dured_ids:
                flagger.browse(dured_ids).write({"duration_edited": True})
        return res

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
        # Reviewer: an arrived patient may not move to In Progress until their
        # personal data is complete (personal no., phone, birth date).
        for ev in self:
            if ev.is_clinic:
                ev._check_patient_data_complete()
        self.write({"clinic_state": "in_progress", "treat_start_time": fields.Datetime.now()})

    def _check_patient_data_complete(self):
        self.ensure_one()
        patient = self.patient_id
        missing = []
        if not patient or not (patient.vat or "").strip():
            missing.append(_("Personal No."))
        # NB: Odoo 19 res.partner has no `mobile` field any more.
        has_phone = patient and (
            (patient.phone or "").strip() or patient.patient_phone_ids
        )
        if not has_phone:
            missing.append(_("Phone"))
        if not patient or not patient.birthdate:
            missing.append(_("Birth Date"))
        if missing:
            raise UserError(
                _("Cannot start the visit — fill in the patient's data first: %s")
                % ", ".join(missing)
            )

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
                # Suggest the same time slot one week later (editable).
                "default_start": self.start and fields.Datetime.to_string(
                    self.start + timedelta(days=7)
                ),
                "default_stop": self.stop and fields.Datetime.to_string(
                    self.stop + timedelta(days=7)
                ),
            },
        }

    # ------------------------------------------------------------------
    # Waitlist / dispensary (reviewer): 6-month control visits wait in a
    # reserve list and reach the main calendar only after confirmation.
    # ------------------------------------------------------------------
    def action_book(self):
        """Confirm a reserve (requested) entry onto the main calendar."""
        for ev in self:
            if ev.is_clinic and ev.clinic_state == "requested":
                # run the overlap constraint against the grid by leaving
                # 'requested' — the constrains() fires on this write
                ev.write({"clinic_state": "booked"})

    def action_dispensary_next(self):
        """Book the patient for a 6-month dispensary control — lands in the
        reserve list (requested) until the administrator confirms it."""
        self.ensure_one()
        start = self.start and self.start + timedelta(days=182)
        stop = self.stop and self.stop + timedelta(days=182)
        new = self.with_context(clinic_force=1).create({
            "name": _("Dispensary control: %s") % (self.patient_id.name or ""),
            "is_clinic": True,
            "is_dispensary": True,
            "clinic_state": "requested",
            "patient_id": self.patient_id.id,
            "dentist_id": self.dentist_id.id,
            "room_id": self.room_id.id,
            "appointment_type_id": self.appointment_type_id.id,
            "parent_appointment_id": self.id,
            "start": start,
            "stop": stop,
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Dispensary control scheduled"),
                "message": _("%(patient)s added to the reserve list for %(date)s.",
                             patient=self.patient_id.name or "",
                             date=fields.Datetime.context_timestamp(
                                 self, new.start).strftime("%d.%m.%Y %H:%M") if new.start else ""),
                "type": "success",
                "sticky": False,
            },
        }

    def _clinic_admin_users(self):
        group = self.env.ref(
            "clinic_patient_card.group_clinic_admin", raise_if_not_found=False)
        if not group:
            return self.env["res.users"]
        return self.env["res.users"].search([("all_group_ids", "in", group.id)])

    @api.model
    def _cron_dispensary_reminders(self):
        """Daily: dispensary reserve visits starting within 14 days → to-do
        activity + live toast for the administrators ('time to call')."""
        due = self.search([
            ("is_clinic", "=", True),
            ("is_dispensary", "=", True),
            ("clinic_state", "=", "requested"),
            ("dispensary_notified", "=", False),
            ("start", "!=", False),
            ("start", "<=", fields.Datetime.now() + timedelta(days=14)),
        ])
        if not due:
            return
        admins = self._clinic_admin_users()
        todo = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        model_id = self.env["ir.model"]._get_id("calendar.event")
        for ev in due:
            when = fields.Datetime.context_timestamp(ev, ev.start).strftime("%d.%m.%Y %H:%M")
            for user in admins:
                if todo:
                    self.env["mail.activity"].create({
                        "res_model_id": model_id,
                        "res_id": ev.id,
                        "activity_type_id": todo.id,
                        "summary": _("Call to confirm dispensary control: %(patient)s (%(when)s)",
                                     patient=ev.patient_id.name or "", when=when),
                        "date_deadline": fields.Date.context_today(self),
                        "user_id": user.id,
                    })
                if user.partner_id:
                    self.env["bus.bus"]._sendone(user.partner_id, "clinic_dispensary_due", {
                        "patient": ev.patient_id.name or "",
                        "when": when,
                    })
        due.with_context(clinic_flagging=True).write({"dispensary_notified": True})

    @api.model
    def _cron_booking_report(self):
        """Weekly: booking summary (last 7 days) as a to-do for the admins."""
        since = fields.Datetime.now() - timedelta(days=7)
        bookings = self.search([
            ("is_clinic", "=", True),
            ("create_date", ">=", since),
            ("clinic_state", "not in", ("cancelled", "no_show")),
        ])
        per_dentist = {}
        for ev in bookings:
            key = ev.dentist_id.name or _("(no dentist)")
            per_dentist[key] = per_dentist.get(key, 0) + 1
        detail = ", ".join("%s: %s" % (k, v) for k, v in sorted(per_dentist.items()))
        summary = _("Weekly bookings: %(total)s new (%(detail)s)",
                    total=len(bookings), detail=detail or "-")
        todo = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not todo:
            return
        # res.users has no chatter — hang the to-do on the admin's partner.
        partner_model_id = self.env["ir.model"]._get_id("res.partner")
        for user in self._clinic_admin_users():
            if not user.partner_id:
                continue
            self.env["mail.activity"].create({
                "res_model_id": partner_model_id,
                "res_id": user.partner_id.id,
                "activity_type_id": todo.id,
                "summary": summary,
                "date_deadline": fields.Date.context_today(self),
                "user_id": user.id,
            })

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
