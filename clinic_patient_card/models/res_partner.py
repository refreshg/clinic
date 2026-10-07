# -*- coding: utf-8 -*-
import re

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Latin-only e-mail (reviewer: no Georgian letters in e-mails).
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
# Phone: digits with the usual separators only.
PHONE_RE = re.compile(r"^[0-9+\-\s()]+$")


# Fields that, when changed, bump the "medical history last updated" stamp.
MEDICAL_TRACKED_FIELDS = {
    "allergy_ids",
    "chronic_diseases",
    "current_medications",
    "is_pregnant",
    "allergy_answer",
    "pregnancy_answer",
    "has_bleeding_disorder",
    "has_cardio_risk",
    "medical_risk_notes",
    "anamnesis_general",
    "smoker",
    "alcohol",
    "family_history",
    "has_xray",
    "has_ct",
    "imaging_source",
}


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Patients are searchable by personal no. / phone / patient ref too.
    _rec_names_search = [
        "complete_name", "email", "ref", "vat", "company_registry",
        "phone", "patient_ref",
    ]

    # ------------------------------------------------------------------
    # Master flag
    # ------------------------------------------------------------------
    is_patient = fields.Boolean(string="Is a Patient", index=True)

    # ------------------------------------------------------------------
    # Reviewer validations (patients only)
    # ------------------------------------------------------------------
    @api.constrains("is_patient", "email")
    def _check_patient_email(self):
        for p in self:
            if p.is_patient and p.email and not EMAIL_RE.match(p.email.strip()):
                raise ValidationError(_(
                    "E-mail must use Latin letters only (e.g. name@mail.com): %s"
                ) % p.email)

    @api.constrains("is_patient", "phone")
    def _check_patient_phone(self):
        for p in self:
            if p.is_patient and p.phone and not PHONE_RE.match(p.phone.strip()):
                raise ValidationError(_(
                    "Phone number may contain digits only: %s"
                ) % p.phone)

    @api.constrains("is_patient", "vat")
    def _check_patient_vat(self):
        for p in self:
            if not p.is_patient or not p.vat:
                continue
            vat = p.vat.strip()
            # A foreign citizen's document is a passport number — letters
            # allowed; a Georgian personal number stays digits-only.
            if p.is_foreign:
                if not vat.isalnum():
                    raise ValidationError(_(
                        "Passport number may contain letters and digits only: %s"
                    ) % p.vat)
            elif not vat.isdigit():
                raise ValidationError(_(
                    "Personal No. may contain digits only: %s"
                ) % p.vat)
            # Reviewer: re-registering an already registered personal no. is
            # forbidden. (Python check, not SQL — empty vats and companies
            # must stay unconstrained.)
            dup = self.sudo().search_count([
                ("id", "!=", p.id),
                ("is_patient", "=", True),
                ("vat", "=", vat),
            ])
            if dup:
                raise ValidationError(_(
                    "A patient with personal no. %s is already registered."
                ) % vat)

    def _compute_display_name(self):
        # In clinic pickers (context clinic_show_ids) a patient shows their
        # personal no. and phone next to the name, so reception can tell
        # namesakes apart while searching.
        super()._compute_display_name()
        for p in self:
            # base prefixes the workplace ("Company, Person" — from parent_id
            # OR the free-text company_name); a patient is found by their own
            # name, the workplace stays a field on the card
            if p.is_patient:
                p.display_name = p.name or ""
        if self.env.context.get("clinic_show_ids"):
            for p in self:
                if p.is_patient:
                    extra = " · ".join(x for x in (p.vat, p.phone) if x)
                    if extra:
                        p.display_name = f"{p.display_name} · {extra}"

    # ==================================================================
    # 1.1 Basic information
    # ==================================================================
    # Dentos-style registration keeps first/last name apart; `name` is
    # rebuilt from them in create/write so the rest of Odoo keeps working
    # on the single field. Existing patients (name only) stay untouched.
    first_name = fields.Char(string="First Name")
    last_name = fields.Char(string="Last Name")
    name_latin = fields.Char(
        string="Name (Latin)",
        help="Latinized full name, used for foreign patients.",
    )
    address_latin = fields.Char(
        string="Address (Latin)",
        help="Latinized home address, used for foreign patients.",
    )
    clinic_visit_ids = fields.One2many(
        "calendar.event", "patient_id", string="Visits",
        domain=[("is_clinic", "=", True)],
    )
    # Patient status for the Patients list side panel / filters (2026-10-01):
    # by COMPLETED (done/paid) clinic visits — 1 = primary, 2+ = unique
    # (user's naming); a patient with no completed visit has no status.
    clinic_done_visits = fields.Integer(
        string="Completed Visits", compute="_compute_clinic_patient_status",
        store=True,
    )
    clinic_patient_status = fields.Selection(
        [("primary", "პირველადი"), ("unique", "უნიკალური")],
        string="Patient Status", compute="_compute_clinic_patient_status",
        store=True,
    )

    @api.depends("is_patient", "clinic_visit_ids.clinic_state")
    def _compute_clinic_patient_status(self):
        for p in self:
            done = len(p.clinic_visit_ids.filtered(
                lambda v: v.clinic_state in ("done", "paid")))
            p.clinic_done_visits = done
            if not p.is_patient:
                p.clinic_patient_status = False
            elif done == 1:
                p.clinic_patient_status = "primary"
            elif done >= 2:
                p.clinic_patient_status = "unique"
            else:
                p.clinic_patient_status = False

    clinic_signature_sample = fields.Binary(
        string="Signature Sample", attachment=True,
        help="Kept from the first signed consent sheet (D2).",
    )
    # Personal number reuses the standard `vat` (Tax ID) field — no custom field.
    birthdate = fields.Date(string="Date of Birth")
    age = fields.Integer(string="Age", compute="_compute_age", store=False)
    gender = fields.Selection(
        [
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
        ],
        string="Gender",
    )
    # History number: auto-assigned by default, but can be set/overridden manually.
    patient_ref = fields.Char(
        string="Patient ID / History No.",
        copy=False,
        index=True,
        default=lambda self: "New",
        help="Patient / medical history number. Auto-assigned, editable manually.",
    )
    registration_date = fields.Date(
        string="Registration Date", default=fields.Date.context_today,
    )
    referral_source = fields.Selection(
        [
            ("recommendation", "Recommendation"),
            ("doctor_referral", "Doctor Referral"),
            ("facebook", "Facebook"),
            ("instagram", "Instagram"),
            ("google", "Google / Search"),
            ("insurance", "Insurance"),
            ("returning", "Returning Patient"),
            ("walk_in", "Walk-in"),
            ("other", "Other"),
        ],
        string="Referral Source",
    )
    referral_source_other = fields.Char(string="Referral Source (Other)")
    is_foreign = fields.Boolean(string="Foreign Patient")
    nationality_country_id = fields.Many2one("res.country", string="Nationality")
    # Patient differentiation flags (D-45): counted from the COMPLETED visits,
    # never ticked by hand — 0 = first visit, 1+ = repeat, N+ = regular
    # (N = system parameter clinic.regular_patient_visits; clinic still to decide).
    is_first_visit = fields.Boolean(
        string="First Visit", compute="_compute_visit_flags", store=True)
    is_repeat = fields.Boolean(
        string="Repeat Patient", compute="_compute_visit_flags", store=True)
    is_regular = fields.Boolean(
        string="Regular Patient", compute="_compute_visit_flags", store=True)

    @api.depends("is_patient", "clinic_done_visits")
    def _compute_visit_flags(self):
        threshold = int(self.env["ir.config_parameter"].sudo().get_param(
            "clinic.regular_patient_visits", "5") or 5)
        for p in self:
            done = p.clinic_done_visits if p.is_patient else -1
            p.is_first_visit = done == 0
            p.is_repeat = done >= 1
            p.is_regular = done >= threshold

    @api.model
    def _clinic_recompute_visit_flags(self):
        """D-45 (upgrade / threshold change): recount every patient's flags."""
        patients = self.sudo().with_context(active_test=False).search([("is_patient", "=", True)])
        for name in ("is_first_visit", "is_repeat", "is_regular"):
            self.env.add_to_compute(self._fields[name], patients)
        patients._recompute_recordset()
    # Guardian for minors.
    is_minor = fields.Boolean(string="Minor", compute="_compute_is_minor", store=True)
    guardian_id = fields.Many2one("res.partner", string="Guardian / Parent")
    # Family members are linked patient profiles (reviewer batch #2).
    family_member_ids = fields.Many2many(
        "res.partner", "clinic_family_member_rel", "partner_id", "member_id",
        string="Family Members",
        domain="[('is_patient', '=', True), ('id', '!=', id)]",
    )
    # Free note about the patient, visible up front.
    patient_note = fields.Text(string="Patient Note")

    # ==================================================================
    # 1.2 Contact information
    # ==================================================================
    # Phones carry per-row channel, emergency flag and relationship (see model).
    patient_phone_ids = fields.One2many(
        "clinic.patient.phone", "partner_id", string="Phone Numbers",
    )

    # ==================================================================
    # 1.3 Medical history
    # ==================================================================
    allergy_ids = fields.One2many(
        "clinic.patient.allergy", "partner_id", string="Allergies",
    )
    anamnesis_general = fields.Text(string="General Anamnesis")
    chronic_diseases = fields.Text(string="Chronic Diseases")
    current_medications = fields.Text(string="Current Medications")
    is_pregnant = fields.Boolean(string="Pregnant")
    # Explicit yes/no answers: an empty allergy list / unticked box cannot be
    # told apart from "never asked", so the card REQUIRES an answer (2026-09-30).
    allergy_answer = fields.Selection(
        [("yes", "კი"), ("no", "არა")], string="Allergies",
    )
    pregnancy_answer = fields.Selection(
        [("yes", "კი"), ("no", "არა")], string="Pregnancy",
    )
    # the day the pregnancy answer was given: an answer is valid for THAT day's
    # visit only, so every new visit day asks again (even if nothing cleared it)
    pregnancy_answered_on = fields.Date(string="Pregnancy answered on", copy=False)
    # D-44: an allergy answer is valid for 6 months, then the patient is asked again
    allergy_answered_on = fields.Date(string="Allergies answered on", copy=False)
    # red warning on the patient form (same as on the booking popup)
    health_pregnancy_alert = fields.Boolean(compute="_compute_health_alerts")
    health_allergy_alert = fields.Boolean(compute="_compute_health_alerts")
    health_allergy_info = fields.Char(compute="_compute_health_alerts")

    @api.depends("gender", "pregnancy_answer", "allergy_answer",
                 "allergy_ids.name", "allergy_ids.reaction")
    def _compute_health_alerts(self):
        for p in self:
            p.health_pregnancy_alert = p.gender == "female" and p.pregnancy_answer == "yes"
            # an expired answer (D-44) keeps the warning while allergies are on file
            allergic = p.allergy_answer == "yes" or (not p.allergy_answer and bool(p.allergy_ids))
            p.health_allergy_alert = allergic
            p.health_allergy_info = allergic and (", ".join(
                a.name + (" — " + a.reaction if a.reaction else "")
                for a in p.allergy_ids) or "რაზე — არ არის მითითებული")
    smoker = fields.Boolean(string="Smoker")
    alcohol = fields.Boolean(string="Alcohol")
    family_history = fields.Text(string="Family History")
    has_bleeding_disorder = fields.Boolean(string="Bleeding / Coagulation Problems")
    has_cardio_risk = fields.Boolean(string="Cardiovascular Risk")
    medical_risk_notes = fields.Text(string="Risk Notes")
    # Imaging (X-ray / CT): whether present and taken here or brought in.
    has_xray = fields.Boolean(string="Has X-ray")
    has_ct = fields.Boolean(string="Has CT")
    imaging_source = fields.Selection(
        [
            ("here", "Taken here"),
            ("brought", "Brought"),
        ],
        string="Imaging Source",
    )
    medical_update_date = fields.Datetime(string="Medical History Updated On", readonly=True)
    medical_update_uid = fields.Many2one(
        "res.users", string="Medical History Updated By", readonly=True,
    )

    # ==================================================================
    # 1.4 Dental history
    # ==================================================================
    last_dental_visit_date = fields.Date(string="Last Dental Visit")
    treatment_plan_status = fields.Selection(
        [
            ("none", "None"),
            ("planned", "Planned"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("postponed", "Postponed"),
            ("cancelled", "Cancelled"),
        ],
        string="Treatment Plan Status",
        default="none",
    )
    procedure_history_ids = fields.One2many(
        "clinic.procedure.history", "partner_id", string="Procedure History",
    )
    # 1.4 Dental chart (FDI tooth numbering).
    tooth_ids = fields.One2many(
        "clinic.patient.tooth", "partner_id", string="Dental Chart",
    )
    # Visual odontogram rendered from tooth_ids (server-side, read-only).
    odontogram_html = fields.Html(
        string="Odontogram", compute="_compute_odontogram_html", sanitize=False,
    )
    has_bruxism = fields.Boolean(string="Bruxism")
    periodontitis_risk = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ],
        string="Periodontitis Risk",
    )
    dental_other_notes = fields.Text(string="Other Predispositions")

    # ==================================================================
    # 1.5 Financial status
    #   Balance / invoices / payments reuse the standard `account` module
    #   (credit, debit, total_invoiced, invoice_ids, property_payment_term_id).
    # ==================================================================
    preferred_payment_method = fields.Selection(
        [
            ("cash", "Cash"),
            ("card", "Card"),
            ("transfer", "Bank Transfer"),
            ("insurance", "Insurance"),
            ("mixed", "Mixed"),
        ],
        string="Preferred Payment Method",
    )
    discount_percent = fields.Float(string="Discount (%)")
    discount_fixed = fields.Float(string="Discount (amount)")
    loyalty_status = fields.Selection(
        [
            ("none", "None"),
            ("silver", "Silver"),
            ("gold", "Gold"),
            ("platinum", "Platinum"),
        ],
        string="Loyalty Status",
        default="none",
    )
    # Insurance company = a standard contact (organization), not a custom model.
    is_insurance_company = fields.Boolean(string="Is an Insurance Company")
    insurance_company_id = fields.Many2one(
        "res.partner", string="Insurance Company",
        domain="[('is_insurance_company', '=', True)]",
    )
    insurance_policy_no = fields.Char(string="Policy No.")
    insurance_valid_until = fields.Date(string="Insurance Valid Until")
    insurance_notes = fields.Text(string="Insurance Notes")

    # ==================================================================
    # 1.6 Documents
    # ==================================================================
    document_ids = fields.One2many(
        "clinic.patient.document", "partner_id", string="Documents",
    )
    # Medical tab: allergy documents (also uploaded from the visit page)
    allergy_doc_ids = fields.One2many(
        "clinic.patient.document", "partner_id", string="Allergy documents",
        domain=[("doc_type", "=", "allergy_doc")],
    )
    # the SAME documents under the allergy answer on the main card tab (admin +
    # doctor) — a second field because one form cannot hold one x2many twice
    allergy_doc_card_ids = fields.One2many(
        "clinic.patient.document", "partner_id", string="Allergy test documents",
        domain=[("doc_type", "=", "allergy_doc")],
    )
    allergy_doc_count = fields.Integer(compute="_compute_allergy_doc_count")

    @api.depends("allergy_doc_ids")
    def _compute_allergy_doc_count(self):
        for p in self:
            p.allergy_doc_count = len(p.allergy_doc_ids)
    # Medical tab: examination results (a file and/or typed text), doctor side
    exam_result_ids = fields.One2many(
        "clinic.patient.document", "partner_id", string="Examination results",
        domain=[("doc_type", "=", "exam_result")],
    )
    # Medical tab gallery: the pictures (X-ray / photos) among the documents
    xray_ids = fields.One2many(
        "clinic.patient.document", "partner_id", string="X-ray / Photos",
        domain=[("doc_type", "=", "xray")],
    )

    # ==================================================================
    # 1.7 Patient profile / analytics
    #   Auto-computation lands with the appointment module (Phase 3);
    #   for now these are entered manually.
    # ==================================================================
    no_show_rate = fields.Float(string="No-show Rate (%)")
    ltv_forecast = fields.Float(string="LTV Forecast")
    risk_level = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ],
        string="Risk Level",
    )
    risk_notes = fields.Char(string="Risk Details")

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends("birthdate")
    def _compute_age(self):
        today = fields.Date.context_today(self)
        for partner in self:
            bd = partner.birthdate
            if bd:
                partner.age = today.year - bd.year - (
                    (today.month, today.day) < (bd.month, bd.day)
                )
            else:
                partner.age = 0

    # Role helpers for view-level access (see security/clinic_groups.xml).
    can_edit_medical = fields.Boolean(compute="_compute_clinic_access")

    @api.depends_context("uid")
    def _compute_clinic_access(self):
        is_doctor = self.env.user.has_group("clinic_patient_card.group_clinic_doctor")
        for partner in self:
            partner.can_edit_medical = is_doctor

    @api.depends("birthdate")
    def _compute_is_minor(self):
        today = fields.Date.context_today(self)
        for partner in self:
            bd = partner.birthdate
            if bd:
                age = today.year - bd.year - (
                    (today.month, today.day) < (bd.month, bd.day)
                )
                partner.is_minor = age < 18
            else:
                partner.is_minor = False

    # FDI permanent-teeth layout (two quadrants per jaw).
    _ODONTO_UPPER = ["18", "17", "16", "15", "14", "13", "12", "11",
                     "21", "22", "23", "24", "25", "26", "27", "28"]
    _ODONTO_LOWER = ["48", "47", "46", "45", "44", "43", "42", "41",
                     "31", "32", "33", "34", "35", "36", "37", "38"]
    _ODONTO_COLORS = {
        "healthy": "#ffffff", "caries": "#e74c3c", "filled": "#3498db",
        "crown": "#f1c40f", "root_canal": "#9b59b6", "implant": "#95a5a6",
        "missing": "#2c3e50", "to_extract": "#e67e22", "other": "#bdc3c7",
    }

    @api.depends("tooth_ids.tooth_number", "tooth_ids.status")
    def _compute_odontogram_html(self):
        colors = self._ODONTO_COLORS
        labels = dict(
            self.env["clinic.patient.tooth"].fields_get(["status"])["status"]["selection"]
        )
        dark = {"missing", "root_canal", "crown"}

        def cell(num, status):
            bg = colors.get(status, "#ffffff")
            fg = "#ffffff" if status in dark else "#333333"
            title = labels.get(status, "")
            return (
                '<td style="border:1px solid #bbb;width:32px;height:38px;'
                'text-align:center;vertical-align:middle;font-size:11px;'
                f'background:{bg};color:{fg};" title="{title}">{num}</td>'
            )

        def row(nums, by_num):
            left = "".join(cell(n, by_num.get(n, "healthy")) for n in nums[:8])
            right = "".join(cell(n, by_num.get(n, "healthy")) for n in nums[8:])
            return f'<tr>{left}<td style="width:12px;border:0;"></td>{right}</tr>'

        legend = "".join(
            '<span style="display:inline-block;margin:0 10px 4px 0;white-space:nowrap;">'
            f'<span style="display:inline-block;width:12px;height:12px;background:{colors[k]};'
            'border:1px solid #bbb;vertical-align:middle;"></span> '
            f'{labels.get(k, k)}</span>'
            for k in colors
        )

        caption = _(
            "FDI numbering: the 1st digit is the quadrant (1-4), the 2nd is the "
            "tooth position (1-8). 32 teeth in total."
        )
        for partner in self:
            by_num = {
                (t.tooth_number or "").strip(): t.status
                for t in partner.tooth_ids if t.tooth_number
            }
            partner.odontogram_html = (
                '<div style="overflow-x:auto;">'
                f'<div style="font-size:11px;color:#666;margin-bottom:6px;">{caption}</div>'
                '<table style="border-collapse:collapse;margin-bottom:8px;">'
                f'{row(self._ODONTO_UPPER, by_num)}{row(self._ODONTO_LOWER, by_num)}'
                '</table>'
                f'<div style="font-size:11px;line-height:1.8;">{legend}</div>'
                '</div>'
            )

    # ------------------------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------------------------
    @staticmethod
    def _clinic_join_name(vals, current=None):
        # first/last name → single `name`; a value typed straight into
        # `name` (no first/last in the payload) always wins.
        if "first_name" in vals or "last_name" in vals:
            first = vals.get(
                "first_name", current.first_name if current else None) or ""
            last = vals.get(
                "last_name", current.last_name if current else None) or ""
            full = f"{first} {last}".strip()
            if full and "name" not in vals:
                vals["name"] = full

    def _clinic_missing_health_answers(self):
        """Labels of the mandatory health answers still empty on this patient:
        allergy (yes/no) always, pregnancy (yes/no) only for female patients.
        The doctor may not start a procedure while any is missing."""
        self.ensure_one()
        missing = []
        if not self.allergy_answer or (
                self.allergy_answered_on
                and self.allergy_answered_on < self._clinic_allergy_cutoff()):
            missing.append(_("Allergies (yes/no)"))
        if self.gender == "female" and (
                not self.pregnancy_answer
                or self.pregnancy_answered_on != fields.Date.context_today(self)):
            missing.append(_("Pregnancy (yes/no)"))
        return missing

    def _clinic_health_warning(self):
        """Data for the red warning on the visit page."""
        self.ensure_one()
        allergies = [
            (a.name + (" — " + a.reaction if a.reaction else ""))
            for a in self.allergy_ids
        ]
        return {
            "allergy": self.allergy_answer or False,
            "allergies": allergies,
            "pregnancy": self.pregnancy_answer or False,
            "pregnancy_applies": self.gender == "female",
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._clinic_join_name(vals)
            self._clinic_sync_pregnancy(vals)
            if vals.get("is_patient") and vals.get("patient_ref", "New") == "New":
                vals["patient_ref"] = self.env["ir.sequence"].next_by_code(
                    "clinic.patient.ref"
                ) or "New"
        return super().create(vals_list)

    @api.model
    def _clinic_sync_pregnancy(self, vals):
        """Stamp the day of the health answers (pregnancy: 1 day, allergy: 6 months)."""
        today = fields.Date.context_today(self)
        if "pregnancy_answer" in vals:
            vals["is_pregnant"] = vals["pregnancy_answer"] == "yes"
            vals["pregnancy_answered_on"] = today if vals["pregnancy_answer"] else False
        if "allergy_answer" in vals:
            vals["allergy_answered_on"] = today if vals["allergy_answer"] else False

    @api.model
    def _clinic_allergy_cutoff(self):
        """Allergy answers given before this day are stale (D-44: 6 months)."""
        return fields.Date.context_today(self) - relativedelta(months=6)

    @api.model
    def _cron_reset_stale_pregnancy(self):
        """Forget yesterday's pregnancy answers: the next visit asks afresh.
        Skipped for a patient who is being treated right now."""
        today = fields.Date.context_today(self)
        stale = self.sudo().search([
            ("pregnancy_answer", "!=", False),
            "|", ("pregnancy_answered_on", "=", False),
            ("pregnancy_answered_on", "<", today)])
        Event = self.env["calendar.event"].sudo()
        busy = set(Event.search(Event._clinic_treated_now_domain()).mapped("patient_id").ids)
        stale.filtered(lambda p: p.id not in busy).write({"pregnancy_answer": False})
        # D-44: allergy answers older than 6 months are asked again (same daily cron;
        # the allergy list itself is kept)
        old_allergy = self.sudo().search([
            ("allergy_answer", "!=", False),
            ("allergy_answered_on", "!=", False),
            ("allergy_answered_on", "<", self._clinic_allergy_cutoff())])
        old_allergy.filtered(lambda p: p.id not in busy).write({"allergy_answer": False})
        return len(stale) + len(old_allergy)

    @api.model
    def _clinic_stamp_allergy_answers(self):
        """D-44 (upgrade): answers given before the stamp existed count from today."""
        self.sudo().search([
            ("allergy_answer", "!=", False), ("allergy_answered_on", "=", False),
        ]).write({"allergy_answered_on": fields.Date.context_today(self)})

    def write(self, vals):
        self._clinic_sync_pregnancy(vals)
        if ("first_name" in vals or "last_name" in vals) and len(self) == 1:
            self._clinic_join_name(vals, current=self)
        # Assign a patient reference the first time a partner is flagged as patient.
        if vals.get("is_patient"):
            for partner in self:
                if not partner.patient_ref or partner.patient_ref == "New":
                    seq = self.env["ir.sequence"].next_by_code("clinic.patient.ref")
                    if seq:
                        partner.patient_ref = seq
        # Stamp the medical-history update metadata.
        if MEDICAL_TRACKED_FIELDS.intersection(vals):
            vals["medical_update_date"] = fields.Datetime.now()
            vals["medical_update_uid"] = self.env.uid
        return super().write(vals)

    # ------------------------------------------------------------------
    # 1.9 Quick actions
    #   Placeholder buttons — they intentionally do nothing yet, for the
    #   features whose functionality is not built (booking, Form-100, EHR…).
    # ------------------------------------------------------------------
    def action_back_to_visit(self):
        """Return from the patient form (opened off a booking) to that
        booking: the planning board re-opens the visit dialog. The button
        saves the form first, so nothing typed is lost."""
        visit_id = self.env.context.get("clinic_return_visit_id")
        if not visit_id:
            return {"type": "ir.actions.act_window_close"}
        if self.env.context.get("clinic_return_page"):
            # opened from the visit working page -> back to that page
            return {
                "type": "ir.actions.client",
                "tag": "clinic_visit_page",
                "name": self.env["calendar.event"].browse(visit_id).patient_id.name
                or _("Visit"),
                "params": {"visit_id": visit_id},
            }
        return {
            "type": "ir.actions.client",
            "tag": "clinic_planning",
            "name": _("Planning"),
            "context": {"open_visit_id": visit_id},
        }

    def action_clinic_todo(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Coming soon"),
                "message": _("This quick action is not available yet."),
                "type": "info",
                "sticky": False,
            },
        }

    def action_create_booking(self):
        """Quick action: open a new clinic appointment for this patient."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("New Appointment"),
            "res_model": "calendar.event",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_is_clinic": True,
                "default_patient_id": self.id,
                "default_partner_ids": [(4, self.id)],
                "default_name": self.name,
            },
        }

    def action_open_dashboard(self):
        """Open the visual patient dashboard (OWL client action) for this patient."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "clinic_patient_dashboard",
            "name": self.display_name,
            "target": "current",
            "context": {"active_id": self.id, "default_partner_id": self.id},
            "params": {"partner_id": self.id},
        }

    def action_new_sale_order(self):
        """რეალიზაცია — start a retail sale (toothbrushes etc.) for this patient."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("New Sale"),
            "res_model": "sale.order",
            "view_mode": "form",
            "target": "current",
            "context": {"default_partner_id": self.id, "default_is_clinic_retail": True},
        }

    def action_open_card_page(self):
        """Open the full Soft-UI patient card page (OWL client action)."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "clinic_patient_card_page",
            "name": self.display_name,
            "target": "current",
            "context": {"active_id": self.id, "default_partner_id": self.id},
            "params": {"partner_id": self.id},
        }
