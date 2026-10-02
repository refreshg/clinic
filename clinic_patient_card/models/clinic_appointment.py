# -*- coding: utf-8 -*-
from datetime import timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


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
    # Reviewer batch #2: "Diagnosis" reads as the visit comment (shown on the
    # board card too); same column, no data lost.
    diagnosis = fields.Char(string="Comment", copy=False)
    direction_id = fields.Many2one(
        "clinic.direction", string="Direction", index=True,
    )
    # Link to the family member the visit relates to (e.g. parent booking for
    # a child). Any existing clinic patient can be picked (their record is
    # the data); the pick is remembered on the patient's family list, and
    # "Create" makes a new patient.
    family_link_id = fields.Many2one(
        "res.partner", string="Family Member Link",
        domain="[('is_patient', '=', True), ('id', '!=', patient_id)]",
    )
    family_member_domain_ids = fields.Many2many(
        "res.partner", compute="_compute_family_member_domain",
    )
    # Pregnancy is asked afresh for EVERY visit: booking a new visit clears the
    # patient's answer (see _clinic_reset_pregnancy), the administrator fills it on
    # the card before arrival, and it is frozen on the visit at arrival.
    visit_pregnancy = fields.Selection(
        [("yes", "კი"), ("no", "არა")], string="Pregnancy (this visit)", copy=False)
    # Warning for the doctor on the visit form: only a POSITIVE answer shows
    # (pregnant / allergic), with the clinic's sign icons.
    health_pregnancy_alert = fields.Boolean(compute="_compute_health_info")
    health_allergy_alert = fields.Boolean(compute="_compute_health_info")
    health_allergy_info = fields.Char(compute="_compute_health_info")

    @api.depends("patient_id", "patient_id.gender", "patient_id.pregnancy_answer",
                 "visit_pregnancy", "patient_id.allergy_answer",
                 "patient_id.allergy_ids.name", "patient_id.allergy_ids.reaction")
    def _compute_health_info(self):
        for ev in self:
            p = ev.patient_id
            preg = bool(p and p.gender == "female"
                        and (ev.visit_pregnancy or p.pregnancy_answer) == "yes")
            allergic = bool(p and p.allergy_answer == "yes")
            info = False
            if allergic:
                info = ", ".join(
                    a.name + (" — " + a.reaction if a.reaction else "")
                    for a in p.allergy_ids) or "რაზე — არ არის მითითებული"
            ev.health_pregnancy_alert = preg
            ev.health_allergy_alert = allergic
            ev.health_allergy_info = info
    # Referral source right on the booking (writes through to the patient).
    referral_source = fields.Selection(
        related="patient_id.referral_source", readonly=False,
    )
    # Dentos-style booking extras: staff observers sitting in on the visit,
    # and — when the referral came from a colleague — the referring employee.
    observer_ids = fields.Many2many(
        "res.users", "clinic_visit_observer_rel", "event_id", "user_id",
        string="Observers",
        help="Staff members observing this visit (Dentos: დამკვირვებელი).",
    )
    referral_user_id = fields.Many2one(
        "res.users", string="Referred by (employee)",
        help="Set when a staff member referred the patient.",
    )
    # D2 — consent sheets (personal data + informed medical, signed on screen)
    consent_ids = fields.One2many(
        "clinic.consent", "visit_id", string="Consents",
    )
    consent_signed = fields.Boolean(
        string="Consents Signed", compute="_compute_consent_signed",
    )
    # D3 — medical sections of the visit page (Dentos left-hand menu).
    clinic_case_type = fields.Selection(
        [("planned", "Planned"), ("urgent", "Urgent")],
        string="Case Type", default="planned",
    )
    clinic_complaints = fields.Text(string="Complaints / Anamnesis")
    # Dentos parity: complaints picked from a catalog + free "other";
    # the objective exam is a structured set of fields.
    clinic_complaint_ids = fields.Many2many(
        "clinic.complaint", string="Complaints (catalog)",
    )
    clinic_complaints_other = fields.Char(string="Complaints (other)")
    clinic_obj_bite = fields.Char(string="Bite (თანკბილვა)")
    clinic_obj_mucosa = fields.Char(string="Oral Mucosa Condition")
    clinic_obj_periodontium = fields.Char(string="Periodontium Condition")
    clinic_obj_pocket_depth = fields.Char(string="Periodontal Pocket Depth")
    clinic_obj_plaque = fields.Char(string="Plaque (ნადები)")
    clinic_obj_exam_plan = fields.Char(string="Examination Plan")
    clinic_obj_other = fields.Char(string="Objective (other)")
    prescription_ids = fields.One2many(
        "clinic.prescription", "visit_id", string="Prescriptions",
    )
    clinic_objective = fields.Text(string="Objective Examination")
    clinic_exam_results = fields.Text(string="Examination Results")
    clinic_prescription = fields.Text(string="Prescription / Recommendations")
    clinic_epicrisis = fields.Text(string="Visit Epicrisis")

    @api.depends("consent_ids.state")
    def _compute_consent_signed(self):
        for ev in self:
            signed = ev.consent_ids.filtered(lambda c: c.state == "signed")
            ev.consent_signed = bool(signed) and len(signed) == len(
                ev.consent_ids) and len(ev.consent_ids) >= 2

    def _clinic_pending_retail(self):
        """Retail sales (რეალიზაცია) made for the patient ON THE VISIT'S DAY (the
        administration sells e.g. a toothbrush while the patient settles up)
        that are not paid yet: they are added to the amount due on the billing
        tab. Older unpaid sales are not pulled into a later visit."""
        self.ensure_one()
        if not (self.patient_id and self.start):
            return self.env["sale.order"]
        local = fields.Datetime.context_timestamp(self, self.start)
        day0 = local.replace(hour=0, minute=0, second=0, microsecond=0)
        utc = lambda d: d.astimezone(pytz.UTC).replace(tzinfo=None)
        return self.env["sale.order"].sudo().search([
            ("partner_id", "=", self.patient_id.id), ("is_clinic_retail", "=", True),
            ("state", "in", ("draft", "sent", "sale")),
            ("clinic_visit_id", "=", False),
            ("date_order", ">=", utc(day0)),
            ("date_order", "<", utc(day0 + timedelta(days=1)))], order="date_order, id")

    def clinic_visit_register_payment(self, cash=0.0, terminal=0.0, method=None,
                                      card_type_id=None):
        """D4 — payment straight from the visit page's billing tab.

        `method` is the chosen payment method (cash / card / transfer /
        insurance / mixed). cash / card / mixed: cash + terminal must cover the
        discounted procedures total; transfer / insurance pay the whole total
        outside the till. Without `method` the old rule applies (derived from
        the amounts). The invoice is created like in
        clinic.payment.wizard.action_confirm and the visit lands in `paid`."""
        self.ensure_one()
        cash = cash or 0.0
        terminal = terminal or 0.0
        retail = self._clinic_pending_retail()
        total = (sum(self.procedure_line_ids.mapped("amount_total"))
                 + sum(retail.mapped("amount_total")))
        rounding = self.currency_id.rounding or 0.01
        if method not in (None, False, "cash", "card", "transfer", "insurance", "mixed"):
            raise UserError(_("Unknown payment method."))
        if method in ("transfer", "insurance"):
            cash = terminal = 0.0
        else:
            if cash < 0 or terminal < 0:
                raise UserError(_("Cash and terminal amounts cannot be negative."))
            if float_compare(cash + terminal, total,
                             precision_rounding=rounding) != 0:
                raise UserError(_(
                    "Cash (%(cash).2f) + terminal (%(term).2f) must equal the "
                    "total (%(total).2f).", cash=cash, term=terminal, total=total,
                ))
        if not method:
            method = ("mixed" if cash and terminal
                      else "card" if terminal else "cash")
        self.payment_method = method
        if self.procedure_line_ids:
            self._create_invoice_from_procedures()
        # the retail sales are settled with this payment: approve the draft ones
        # (the standard approval raises their invoice) and tie them to the visit
        for order in retail:
            if order.state in ("draft", "sent"):
                order.action_confirm()
            order.clinic_visit_id = self.id
        vals = {
            "clinic_state": "paid",
            "amount_paid": total,
            "amount_cash": cash if method == "mixed" else 0.0,
            "amount_terminal": terminal if method == "mixed" else 0.0,
        }
        if method in ("card", "mixed") and card_type_id:
            vals["card_type_id"] = self.env["clinic.card.type"].browse(card_type_id).exists().id
        self.write(vals)
        return True

    def action_open_visit_page(self):
        """Open the Dentos-style visit working page (OWL, D3)."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "clinic_visit_page",
            "name": self.patient_id.name or self.name,
            "params": {"visit_id": self.id},
        }

    @api.model
    def clinic_visit_page_data(self, visit_id):
        """One-round-trip payload for the visit page."""
        ev = self.browse(visit_id)
        ev.ensure_one()
        p = ev.patient_id
        procs = ev.env["clinic.procedure.history"].search_read(
            [("appointment_id", "=", ev.id)],
            ["tooth", "icd10_id", "procedure_id", "name", "qty", "status",
             "price_unit", "discount_percent", "amount_total"],
            order="id",
        )
        icd = ev.env["clinic.icd10"].search_read([], ["code", "name"])
        products = ev.env["product.product"].search_read(
            [("is_clinic_procedure", "=", True)],
            ["name", "lst_price"], order="name",
        )
        sections = {
            f: ev[f] or ""
            for f in ("clinic_complaints", "clinic_objective",
                      "clinic_exam_results", "clinic_prescription",
                      "clinic_epicrisis")
        }
        prescriptions = ev.env["clinic.prescription"].search_read(
            [("visit_id", "=", ev.id)],
            ["rec_type", "medicament", "period", "qty", "directions"],
            order="id",
        )
        allergies = p.allergy_ids.read(["name", "reaction", "note"]) if p else []
        complaint_catalog = ev.env["clinic.complaint"].search_read(
            [], ["name"], order="name")
        objective = {
            f: ev[f] or ""
            for f in ("clinic_obj_bite", "clinic_obj_mucosa",
                      "clinic_obj_periodontium", "clinic_obj_pocket_depth",
                      "clinic_obj_plaque", "clinic_obj_exam_plan",
                      "clinic_obj_other")
        }
        is_admin = ev.env.user.has_group(
            "clinic_patient_card.group_clinic_admin")
        return {
            "is_admin": is_admin,
            "card_types": self.env["clinic.card.type"].sudo().search_read([], ["name"]),
            "complaints": {
                "case_type": ev.clinic_case_type,
                "ids": ev.clinic_complaint_ids.ids,
                "other": ev.clinic_complaints_other or "",
                "anamnesis": ev.clinic_complaints or "",
            },
            "complaint_catalog": complaint_catalog,
            "objective": objective,
            "prescriptions": prescriptions,
            "allergies": allergies,
            "visit": {
                "id": ev.id,
                "start": ev.start and fields.Datetime.to_string(ev.start),
                "stop": ev.stop and fields.Datetime.to_string(ev.stop),
                "state": ev.clinic_state,
                "case_type": ev.clinic_case_type,
                "dentist": ev.dentist_id.name or "",
                "assistant": ev.assistant_id.name or "",
                "observers": ev.observer_ids.mapped("name"),
                "consent_signed": ev.consent_signed,
                "amount_paid": ev.amount_paid,
                "comment": ev.diagnosis or "",
            },
            "patient": {
                "id": p.id,
                "name": p.name or "",
                "vat": p.vat or "",
                "phone": p.phone or "",
                "birthdate": p.birthdate and fields.Date.to_string(p.birthdate) or "",
                "insurance": p.insurance_company_id.name or "",
                "allergies": p.allergy_ids.mapped("display_name"),
                "balance": 0.0,
                "health": dict(p._clinic_health_warning(),
                               pregnancy=ev.visit_pregnancy or p.pregnancy_answer or False),
            },
            "sections": sections,
            "procedures": procs,
            "retail": [
                {"id": o.id, "name": o.name, "amount": o.amount_total,
                 "lines": ", ".join(
                     "%s × %g" % (l.product_id.display_name or l.name, l.product_uom_qty)
                     for l in o.order_line if not l.display_type)}
                for o in ev._clinic_pending_retail()],
            "icd10": icd,
            "products": products,
        }

    def action_open_consents(self):
        """თანხმობის ფურცელი — make sure both sheets exist, then walk
        through them starting with the personal-data one (Dentos order);
        already-signed sheets open read-only for review."""
        self.ensure_one()
        Consent = self.env["clinic.consent"]
        for ctype in ("personal_data", "medical"):
            if not self.consent_ids.filtered(
                    lambda c, t=ctype: c.consent_type == t):
                Consent.create({
                    "visit_id": self.id,
                    "consent_type": ctype,
                    "body": Consent._default_body(ctype),
                })
        first = self.consent_ids.sorted(
            key=lambda c: (c.state == "signed", c.consent_type != "personal_data")
        )[:1]
        return {
            "type": "ir.actions.act_window",
            "name": _("თანხმობის ფურცელი"),
            "res_model": "clinic.consent",
            "res_id": first.id,
            "view_mode": "form",
            "target": "new",
        }

    @api.depends("patient_id")
    def _compute_family_member_domain(self):
        for ev in self:
            ev.family_member_domain_ids = ev.patient_id.family_member_ids
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
    card_type_id = fields.Many2one(
        "clinic.card.type", string="Card Type", copy=False,
        help="Type of the card used for a card / mixed payment.",
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

    @api.model
    def clinic_board_staff(self, date):
        """The doctors' schedule of one day for the Planning board:
        {user_id: {type: shift|off|vacation|sick, start, end, name, bg, border,
        text, label}}. Doctors without an entry that day are simply absent."""
        from .clinic_schedule import DAY_TYPES, SHIFT_PALETTE
        labels = dict(DAY_TYPES)
        lines = self.env["clinic.schedule.line"].sudo().search([
            ("date", "=", date), ("employee_id.clinic_staff_kind", "=", "doctor")])
        out = {}
        for ln in lines:
            user = ln.employee_id.user_id
            if not user:
                continue
            if ln.day_type == "shift" and ln.shift_id:
                bg, border, text = SHIFT_PALETTE[ln.shift_id.color % len(SHIFT_PALETTE)]
                out[user.id] = {
                    "type": "shift", "start": ln.shift_id.start_hour, "end": ln.shift_id.end_hour,
                    "name": ln.shift_id.name, "bg": bg, "border": border, "text": text,
                }
            else:
                out[user.id] = {"type": ln.day_type, "label": labels.get(ln.day_type, "")}
        return out

    @api.model
    def _clinic_staff_window(self, dentist, local_date):
        """The doctor's scheduled working window on a local date (staff
        schedule, milestone S): None = no entry (fall back to the clinic
        hours), False = not working (day off / vacation / sick), or
        (start_hour, end_hour) of the assigned shift."""
        if not dentist:
            return None
        emp = self.env["hr.employee"].sudo().search([
            ("user_id", "=", dentist.id), ("clinic_staff_kind", "=", "doctor")], limit=1)
        if not emp:
            return None
        line = self.env["clinic.schedule.line"].sudo().search([
            ("employee_id", "=", emp.id), ("date", "=", local_date)], limit=1)
        if not line:
            return None
        if line.day_type != "shift" or not line.shift_id:
            return False
        return (line.shift_id.start_hour, line.shift_id.end_hour)

    def _clinic_validate_staff_schedule(self, dentist, start_dt, stop_dt=None):
        """No booking on a doctor's day off / vacation / sick day or outside
        their scheduled shift (only when their schedule is filled in for that
        day). clinic_force=1 skips it, like the other schedule guards."""
        if self.env.context.get("clinic_force") or not dentist or not start_dt:
            return
        local_start = fields.Datetime.context_timestamp(self, start_dt)
        win = self._clinic_staff_window(dentist, local_start.date())
        if win is None:
            return
        day = local_start.strftime("%d.%m.%Y")
        if win is False:
            raise UserError(_(
                "%(doc)s does not work on %(day)s (day off / vacation / sick leave "
                "in the staff schedule) — booking is not possible.",
                doc=dentist.name, day=day))
        start_h = local_start.hour + local_start.minute / 60.0
        stop_h = None
        if stop_dt:
            local_stop = fields.Datetime.context_timestamp(self, stop_dt)
            stop_h = local_stop.hour + local_stop.minute / 60.0
            if local_stop.date() != local_start.date():
                stop_h += 24.0
        if start_h < win[0] - 1e-6 or (stop_h is not None and stop_h > win[1] + 1e-6):
            def hm(v):
                return "%02d:%02d" % (int(v), int(round((v % 1) * 60)))
            raise UserError(_(
                "%(doc)s works %(a)s–%(b)s on %(day)s — booking outside this time is not possible.",
                doc=dentist.name, a=hm(win[0]), b=hm(win[1]), day=day))

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
            # onchange fires only on a USER change of the type, so applying the
            # type's duration is always what they asked for — the earlier
            # default_stop guard also blocked it on board-opened forms
            # (reviewer: "ტიპს ვირჩევ და ხანგრძლივობას არ წერს").
            if atype.default_duration:
                self.duration = atype.default_duration

    @api.onchange("dentist_id")
    def _onchange_dentist_id(self):
        # Reviewer: picking the dentist auto-fills their room and direction
        # (both still editable) — scenario 2: booking from the doctor's column.
        if self.dentist_id and self.dentist_id.default_room_id and not self.room_id:
            self.room_id = self.dentist_id.default_room_id
        if self.dentist_id and self.dentist_id.direction_id and not self.direction_id:
            self.direction_id = self.dentist_id.direction_id

    @api.onchange("patient_id", "appointment_type_id")
    def _onchange_clinic_name(self):
        # The subject is hidden on clinic visits — keep it meaningful anyway.
        if self.is_clinic and self.patient_id:
            parts = [self.patient_id.name]
            if self.appointment_type_id:
                parts.append(self.appointment_type_id.name)
            self.name = " — ".join(parts)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("is_clinic"):
                continue
            # Onchange doesn't run on RPC creates (e.g. from the Planning
            # board): apply the dentist's default room + direction here too.
            if vals.get("dentist_id"):
                dentist = self.env["res.users"].browse(vals["dentist_id"])
                if dentist.default_room_id and not vals.get("room_id"):
                    vals["room_id"] = dentist.default_room_id.id
                if dentist.direction_id and not vals.get("direction_id"):
                    vals["direction_id"] = dentist.direction_id.id
            # Subject fallback: patient — type (the field is hidden on the form).
            if not vals.get("name") and vals.get("patient_id"):
                patient = self.env["res.partner"].browse(vals["patient_id"])
                atype = vals.get("appointment_type_id") and self.env[
                    "clinic.appointment.type"].browse(vals["appointment_type_id"])
                vals["name"] = patient.name + (
                    " — " + atype.name if atype else "")
            # Scheduling rules: no past bookings, working hours only.
            if vals.get("start"):
                start_dt = fields.Datetime.to_datetime(vals["start"])
                stop_dt = vals.get("stop") and fields.Datetime.to_datetime(vals["stop"])
                self._clinic_validate_schedule(start_dt, stop_dt)
                # the doctor's own schedule (reserve entries have no real slot)
                if vals.get("clinic_state") != "requested" and vals.get("dentist_id"):
                    self._clinic_validate_staff_schedule(
                        self.env["res.users"].browse(vals["dentist_id"]), start_dt, stop_dt)
        events = super().create(vals_list)
        events._clinic_remember_family_link()
        events.filtered(lambda e: e.clinic_state != "requested")._clinic_reset_pregnancy()
        return events

    def _clinic_remember_family_link(self):
        """Keep the chosen family member on BOTH patients' family lists."""
        for ev in self:
            link, patient = ev.family_link_id, ev.patient_id
            if not (link and patient) or link == patient:
                continue
            # a family member picked on a visit is a clinic client too
            if not link.is_patient:
                link.sudo().is_patient = True
            if link not in patient.family_member_ids:
                patient.sudo().family_member_ids = [(4, link.id)]
            if patient not in link.family_member_ids:
                link.sudo().family_member_ids = [(4, patient.id)]

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
        # the doctor's own schedule — when the time or the doctor changes
        if any(k in vals for k in ("start", "stop", "duration", "dentist_id")):
            for ev in self:
                if not ev.is_clinic or ev.clinic_state in ("requested", "cancelled", "no_show"):
                    continue
                new_start = (fields.Datetime.to_datetime(vals["start"])
                             if vals.get("start") else ev.start)
                if not new_start:
                    continue
                if vals.get("stop"):
                    new_stop = fields.Datetime.to_datetime(vals["stop"])
                elif vals.get("duration"):
                    new_stop = new_start + timedelta(hours=vals["duration"])
                elif ev.start and ev.stop:
                    new_stop = new_start + (ev.stop - ev.start)
                else:
                    new_stop = None
                dentist = (self.env["res.users"].browse(vals["dentist_id"])
                           if vals.get("dentist_id") else ev.dentist_id)
                ev._clinic_validate_staff_schedule(dentist, new_start, new_stop)
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
        if "family_link_id" in vals:
            self._clinic_remember_family_link()
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
        # Guard: birth date + personal no. must be filled before marking arrived.
        for ev in self:
            if ev.is_clinic:
                ev._check_patient_data_complete()
        self.write({"clinic_state": "arrived", "checkin_time": fields.Datetime.now()})
        for ev in self:
            if ev.is_clinic and ev.patient_id.gender == "female":
                ev.visit_pregnancy = ev.patient_id.pregnancy_answer or False
        for ev in self:
            ev._notify_dentist_arrived()

    def action_start(self):
        # Reviewer: an arrived patient may not move to In Progress until their
        # personal data is complete (personal no., phone, birth date).
        for ev in self:
            if ev.is_clinic:
                ev._check_patient_data_complete()
                ev._check_patient_health_answers()
        self.write({"clinic_state": "in_progress", "treat_start_time": fields.Datetime.now()})

    def _check_patient_health_answers(self):
        """No procedure can be added to a visit while the patient card lacks the
        allergy answer (or, for a woman, the pregnancy answer)."""
        self.ensure_one()
        if self.env.context.get("clinic_force") or not self.patient_id:
            return
        missing = self.patient_id._clinic_missing_health_answers()
        if missing:
            raise UserError(_(
                "Cannot start the procedure — fill in on the patient card first: %s.",
                ", ".join(missing)))

    def _clinic_clear_card_pregnancy(self):
        """Clear the patient's card pregnancy answer once their visit is over
        (unless another visit of theirs is being treated right now)."""
        self.ensure_one()
        p = self.patient_id
        if not (self.is_clinic and p and p.pregnancy_answer):
            return
        busy = self.sudo().search_count([
            ("is_clinic", "=", True), ("patient_id", "=", p.id), ("id", "!=", self.id),
            ("clinic_state", "in", ("arrived", "in_progress"))])
        if not busy:
            p.sudo().write({"pregnancy_answer": False, "is_pregnant": False})

    def _clinic_reset_pregnancy(self):
        """A new booking asks pregnancy afresh: clear the card's answer for the
        patients of the new visits (unless that patient is being treated right
        now — their current visit keeps its answer)."""
        Event = self.sudo()
        for ev in self:
            p = ev.patient_id
            if not (ev.is_clinic and p and p.gender == "female" and p.pregnancy_answer):
                continue
            busy = Event.search_count([
                ("is_clinic", "=", True), ("patient_id", "=", p.id), ("id", "!=", ev.id),
                ("clinic_state", "in", ("arrived", "in_progress"))])
            if not busy:
                p.sudo().write({"pregnancy_answer": False, "is_pregnant": False})

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
        # allergy + (female) pregnancy answers — pregnancy is re-asked for every visit
        if patient and not self.env.context.get("clinic_force"):
            missing += patient._clinic_missing_health_answers()
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
            # the pregnancy answer belongs to THIS visit only: clear the card's
            # copy so the next visit asks again (the visit keeps its own value)
            if ev.is_clinic and ev.patient_id and not ev.visit_pregnancy:
                ev.visit_pregnancy = ev.patient_id.pregnancy_answer or False
            ev._clinic_clear_card_pregnancy()
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
        # Payment now happens on the visit page's billing tab (method, card
        # type, amounts) — the button only takes the administrator there.
        # The old wizard stays below as a fallback for the missing-page case.
        self.ensure_one()
        if self.env.user.has_group("clinic_patient_card.group_clinic_admin"):
            return self.action_open_visit_page()
        return {
            "type": "ir.actions.act_window",
            "name": _("Register Payment"),
            "res_model": "clinic.payment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_appointment_id": self.id},
        }

    def action_cancel(self):
        """Reviewer batch #2: the reason is typed right on the Cancel button —
        a small popup, no extra page."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Cancel Visit"),
            "res_model": "clinic.cancel.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_event_id": self.id},
        }

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

    def action_open_patient(self):
        """Jump from the visit straight to the patient's form (reviewer:
        convenient buttons instead of the tiny m2o arrow)."""
        self.ensure_one()
        if not self.patient_id:
            raise UserError(_("Set the patient first."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": self.patient_id.id,
            "views": [[False, "form"]],
            "target": "current",
            # lets the patient form offer "← back to the booking"
            "context": {"clinic_return_visit_id": self.id},
        }

    def action_open_patient_card(self):
        """Jump from the visit to the Soft-UI patient card page."""
        self.ensure_one()
        if not self.patient_id:
            raise UserError(_("Set the patient first."))
        return {
            "type": "ir.actions.client",
            "tag": "clinic_patient_card_page",
            "name": self.patient_id.display_name,
            "target": "current",
            "context": {"active_id": self.patient_id.id},
            "params": {"partner_id": self.patient_id.id},
        }

    def action_to_reserve(self):
        """Move a not-yet-started visit to the waitlist (reserve)."""
        for ev in self:
            if ev.is_clinic and ev.clinic_state in ("booked", "confirmed"):
                ev.write({"clinic_state": "requested"})

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

    def action_find_slots(self):
        """Open the free-slot finder prefilled from this visit."""
        self.ensure_one()
        wiz = self.env["clinic.slot.finder"].create({
            "event_id": self.id,
            "direction_id": self.direction_id.id,
            "duration": self.duration or 0.5,
        })
        wiz.action_search()
        return {
            "type": "ir.actions.act_window",
            "name": _("Free Slots"),
            "res_model": "clinic.slot.finder",
            "res_id": wiz.id,
            "view_mode": "form",
            "target": "new",
        }

    @api.model
    def clinic_free_slots(self, direction_id, duration, date_from=None, days=5,
                          dentist_id=None):
        """Free slots per direction+duration (reviewer batch #2, scenario 1).

        Returns [{start, stop, dentist_id, dentist, room}] within working
        hours, skipping busy intervals of each doctor of the direction.
        `duration` in hours; slots stepped on the 10-minute grid.
        """
        duration = duration or 0.5
        company = self.env.company
        workdays = company._clinic_workdays()
        w_start = company.clinic_work_start or 9.0
        w_end = company.clinic_work_end or 18.0
        doctor_group = self.env.ref("clinic_patient_card.group_clinic_doctor")
        # the Administrator account carries the doctor role only technically
        # (post_init grant) — it is reception, not a treating doctor
        admin_user = self.env.ref("base.user_admin", raise_if_not_found=False)
        dom = [("all_group_ids", "in", doctor_group.id)]
        if admin_user:
            dom.append(("id", "!=", admin_user.id))
        if dentist_id:
            # the visit is being booked with a specific doctor — only their
            # free time matters (reviewer)
            dom.append(("id", "=", dentist_id))
        elif direction_id:
            dom.append(("direction_id", "=", direction_id))
        doctors = self.env["res.users"].search(dom)
        if not doctors:
            return []
        tz = pytz.timezone(self.env.user.tz or "UTC")
        now_local = pytz.UTC.localize(fields.Datetime.now()).astimezone(tz)
        day0 = (tz.localize(fields.Datetime.to_datetime(date_from))
                if date_from else now_local)
        # busy intervals per doctor over the horizon (sudo: doctors' rule
        # must not hide other doctors' load from reception)
        horizon_start = day0.replace(hour=0, minute=0, second=0, microsecond=0)
        horizon_end = horizon_start + timedelta(days=days + 1)
        busy = self.sudo().search_read([
            ("is_clinic", "=", True),
            ("dentist_id", "in", doctors.ids),
            ("clinic_state", "not in", ("cancelled", "no_show", "requested")),
            ("start", "<", fields.Datetime.to_string(horizon_end.astimezone(pytz.UTC).replace(tzinfo=None))),
            ("stop", ">", fields.Datetime.to_string(horizon_start.astimezone(pytz.UTC).replace(tzinfo=None))),
        ], ["dentist_id", "start", "stop"])
        by_doc = {}
        for b in busy:
            s = pytz.UTC.localize(b["start"]).astimezone(tz)
            e = pytz.UTC.localize(b["stop"]).astimezone(tz)
            by_doc.setdefault(b["dentist_id"][0], []).append((s, e))
        slots = []
        step = timedelta(minutes=10)
        dur = timedelta(hours=duration)
        for d in range(days):
            day = horizon_start + timedelta(days=d)
            if workdays and ((day.weekday()) not in workdays):
                continue
            open_dt = day + timedelta(hours=w_start)
            close_dt = day + timedelta(hours=w_end)
            for doc in doctors:
                win = self._clinic_staff_window(doc, day.date())
                if win is False:
                    continue  # day off / vacation / sick leave
                doc_open, doc_close = open_dt, close_dt
                if win:
                    doc_open = max(open_dt, day + timedelta(hours=win[0]))
                    doc_close = min(close_dt, day + timedelta(hours=win[1]))
                cur = doc_open
                intervals = sorted(by_doc.get(doc.id, []))
                while cur + dur <= doc_close:
                    if cur < now_local:  # never offer the past
                        cur += step
                        continue
                    end = cur + dur
                    clash = next((iv for iv in intervals
                                  if iv[0] < end and iv[1] > cur), None)
                    if clash:
                        # jump to the end of the clash, snapped up to 10 min
                        cur = clash[1]
                        extra = (10 - cur.minute % 10) % 10
                        cur += timedelta(minutes=extra,
                                         seconds=-cur.second,
                                         microseconds=-cur.microsecond)
                        continue
                    slots.append({
                        "start": fields.Datetime.to_string(
                            cur.astimezone(pytz.UTC).replace(tzinfo=None)),
                        "stop": fields.Datetime.to_string(
                            end.astimezone(pytz.UTC).replace(tzinfo=None)),
                        "label": cur.strftime("%d.%m %H:%M"),
                        "dentist_id": doc.id,
                        "dentist": doc.name,
                        "room": doc.default_room_id.name or "",
                    })
                    cur += step
                    if len(slots) >= 400:
                        break
        slots.sort(key=lambda s: (s["start"], s["dentist"]))
        return slots[:120]

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
