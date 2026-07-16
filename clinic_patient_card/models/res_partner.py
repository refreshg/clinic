# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


# Fields that, when changed, bump the "medical history last updated" stamp.
MEDICAL_TRACKED_FIELDS = {
    "allergy_ids",
    "chronic_diseases",
    "current_medications",
    "is_pregnant",
    "has_bleeding_disorder",
    "has_cardio_risk",
    "medical_risk_notes",
}


class ResPartner(models.Model):
    _inherit = "res.partner"

    # ------------------------------------------------------------------
    # Master flag
    # ------------------------------------------------------------------
    is_patient = fields.Boolean(string="Is a Patient", index=True)

    # ==================================================================
    # 1.1 Basic information
    # ==================================================================
    name_latin = fields.Char(
        string="Name (Latin)",
        help="Latinized full name, used for foreign patients.",
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
    patient_ref = fields.Char(
        string="Patient ID / History No.",
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: "New",
        help="Unique patient identifier, also used as the medical history number.",
    )
    registration_date = fields.Date(
        string="Registration Date", default=fields.Date.context_today,
    )
    referral_source = fields.Selection(
        [
            ("recommendation", "Recommendation"),
            ("social_google", "Social / Google"),
            ("insurance", "Insurance"),
            ("other", "Other"),
        ],
        string="Referral Source",
    )
    referral_source_other = fields.Char(string="Referral Source (Other)")
    is_foreign = fields.Boolean(string="Foreign Patient")
    nationality_country_id = fields.Many2one("res.country", string="Nationality")
    is_first_visit = fields.Boolean(string="First Visit", default=True)

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
    chronic_diseases = fields.Text(string="Chronic Diseases")
    current_medications = fields.Text(string="Current Medications")
    is_pregnant = fields.Boolean(string="Pregnant")
    has_bleeding_disorder = fields.Boolean(string="Bleeding / Coagulation Problems")
    has_cardio_risk = fields.Boolean(string="Cardiovascular Risk")
    medical_risk_notes = fields.Text(string="Risk Notes")
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
            ("active", "Active"),
            ("on_hold", "On Hold"),
            ("completed", "Completed"),
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
    insurance_provider = fields.Char(string="Insurance Provider")
    insurance_policy_no = fields.Char(string="Policy No.")
    insurance_valid_until = fields.Date(string="Insurance Valid Until")
    insurance_notes = fields.Text(string="Insurance Notes")

    # ==================================================================
    # 1.6 Documents
    # ==================================================================
    document_ids = fields.One2many(
        "clinic.patient.document", "partner_id", string="Documents",
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

        for partner in self:
            by_num = {
                (t.tooth_number or "").strip(): t.status
                for t in partner.tooth_ids if t.tooth_number
            }
            partner.odontogram_html = (
                '<div style="overflow-x:auto;">'
                '<table style="border-collapse:collapse;margin-bottom:8px;">'
                f'{row(self._ODONTO_UPPER, by_num)}{row(self._ODONTO_LOWER, by_num)}'
                '</table>'
                f'<div style="font-size:11px;line-height:1.8;">{legend}</div>'
                '</div>'
            )

    # ------------------------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("is_patient") and vals.get("patient_ref", "New") == "New":
                vals["patient_ref"] = self.env["ir.sequence"].next_by_code(
                    "clinic.patient.ref"
                ) or "New"
        return super().create(vals_list)

    def write(self, vals):
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
