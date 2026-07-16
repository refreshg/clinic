# -*- coding: utf-8 -*-
from odoo import api, fields, models


# Fields that, when changed, bump the "medical history last updated" stamp.
MEDICAL_TRACKED_FIELDS = {
    "allergy_ids",
    "chronic_diseases",
    "current_medications",
    "pregnancy_status",
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
    personal_id = fields.Char(string="Personal ID No.", index=True)
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
    nationality_country_id = fields.Many2one("res.country", string="Country")
    is_first_visit = fields.Boolean(string="First Visit", default=True)

    # ==================================================================
    # 1.2 Contact information
    # ==================================================================
    patient_phone_ids = fields.One2many(
        "clinic.patient.phone", "partner_id", string="Phone Numbers",
    )
    preferred_comm_channel = fields.Selection(
        [
            ("sms", "SMS"),
            ("call", "Call"),
            ("whatsapp", "WhatsApp"),
            ("email", "Email"),
        ],
        string="Preferred Channel",
    )
    emergency_contact_name = fields.Char(string="Emergency Contact")
    emergency_contact_relation = fields.Char(string="Relationship")
    emergency_contact_phone = fields.Char(string="Emergency Phone")

    # ==================================================================
    # 1.3 Medical history
    # ==================================================================
    allergy_ids = fields.One2many(
        "clinic.patient.allergy", "partner_id", string="Allergies",
    )
    chronic_diseases = fields.Text(string="Chronic Diseases")
    current_medications = fields.Text(string="Current Medications")
    pregnancy_status = fields.Selection(
        [
            ("na", "N/A"),
            ("pregnant", "Pregnant"),
            ("not_pregnant", "Not Pregnant"),
            ("breastfeeding", "Breastfeeding"),
        ],
        string="Pregnancy Status",
        default="na",
    )
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
