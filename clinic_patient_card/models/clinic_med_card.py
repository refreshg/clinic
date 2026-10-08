# -*- coding: utf-8 -*-
"""Medical card (D-49): the Ministry form №IV-220/ა + examination sheet №IV-220-1/ა.

Step 1 (this file so far): the vocabularies of the official form and where the
visit page records them —
  * complaints: the clinic's own catalog (clinic.complaint) where every item may
    point to ONE of the 18 checkboxes of the form (`form_item`); items without a
    checkbox print under "სხვა";
  * objective exam: three checkbox groups of the form (periodontium, plaque,
    examination plan) stored as one json on the visit (`clinic_obj_checks`);
    the older free-text fields stay as the "სხვა" of each group;
  * "დაავადებული კბილ(ებ)ი" (`clinic_complaint_teeth`).
"""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError

# the 18 complaint checkboxes of form IV-220-1/ა, in the form's order (left, right)
FORM_COMPLAINTS = [
    ("irritant", "გამღიზიანებლით გამოწვეული მიზეზობრივი ხასიათის ტკივილი"),
    ("bite_pain", "ტკივილი კბილის კბილზე დაჭერისას"),
    ("dull", "ყრუ ხასიათის ტკივილი"),
    ("spontaneous", "თვითნებითი ხასიათის ტკივილი"),
    ("night", "ღამის ტკივილი"),
    ("aesthetic", "ესთეტიკური დისკომფორტი"),
    ("filling", "ბჟენის დეფექტი"),
    ("crown", "გვირგვინის დეფექტი"),
    ("root", "ფესვი"),
    ("asymmetry", "სახის ასიმეტრია"),
    ("calculus", "ქვისა და რბილი ნადების არსებობა"),
    ("gum_bleeding", "სისხლდენა ღრძილებიდან"),
    ("adentia", "ადენტია"),
    ("halitosis", "ჰალიტოზი"),
    ("tmj", "საფეთქელ-ქვედა ყბის სახსრის პათოლოგია"),
    ("mobility", "კბილის მორყევა"),
    ("acute", "მწვავე შეტევითი ხასიათის ტკივილი"),
    ("chewing", "ღეჭვით ფუნქციის დარღვევა"),
]
FORM_PERIODONTIUM = [
    ("edema", "შეშუპება"), ("hyperemia", "ჰიპერემია"), ("cyanosis", "ციანოზი"),
    ("retraction", "რეტრაქცია"), ("hypertrophy", "ჰიპერტროფია"), ("bleeding", "სისხლდენა"),
    ("bone_pocket", "ძვლოვანი ჯიბე"), ("atrophy", "ალვეოლური მორჩის ატროფია"),
    ("perio_pocket", "პაროდონტული ჯიბე"),
]
FORM_PLAQUE = [
    ("none", "არ აღინიშნება"), ("soft", "რბილი"), ("pigmented", "პიგმენტური"),
    ("hard", "მაგარი"), ("supra", "ღრძილზედა"), ("sub", "ღრძილქვეშა"),
]
FORM_EXAM_PLAN = [
    ("anamnesis", "ანამნეზის შეკრება"), ("face_exam", "სახისა და პირის ღრუს დათვალიერება"),
    ("thermo", "თერმოდიაგნოსტიკა"), ("visio", "ვიზიორენტგენოგრაფიული გამოკვლევა"),
    ("xray", "რენტგენოლოგიური გამოკვლევა"), ("allergo", "სპეციფიური ალერგოდიაგნოსტიკა"),
    ("opg", "ორთოპანტომოგრაფია"), ("eod", "ელექტროოდონტომეტრია"),
    ("apex", "აპექს-ლოკაცია"), ("ct", "კომპიუტერული ტომოგრაფია"),
]
OBJ_GROUPS = {"perio": FORM_PERIODONTIUM, "plaque": FORM_PLAQUE, "plan": FORM_EXAM_PLAN}


class ClinicComplaint(models.Model):
    _inherit = "clinic.complaint"
    _order = "sequence, name"

    sequence = fields.Integer(default=100)
    form_item = fields.Selection(
        FORM_COMPLAINTS, string="Form IV-220-1/ა checkbox",
        help="Which checkbox of the official examination sheet this complaint ticks; "
             "empty = printed under \"სხვა\".")


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    clinic_complaint_teeth = fields.Char(string="Affected teeth")
    # {"perio": [keys], "plaque": [keys], "plan": [keys]} — the form's checkboxes
    clinic_obj_checks = fields.Json(string="Objective exam checkboxes", default=dict)

    @api.model
    def clinic_form_vocab(self):
        """The checkbox lists of the official form for the visit page."""
        return {k: [list(x) for x in v] for k, v in OBJ_GROUPS.items()}


# --- step 2: the card itself (built live on every open / print) ------------------
GE_MONTHS = ["იანვარი", "თებერვალი", "მარტი", "აპრილი", "მაისი", "ივნისი", "ივლისი",
             "აგვისტო", "სექტემბერი", "ოქტომბერი", "ნოემბერი", "დეკემბერი"]
# tooth chart picture -> the letter code of the form's legend
FORM_TOOTH_CODES = {
    "caries": "კ", "deep_caries": "კ", "defect": "აკ", "attrition": "აკ", "fracture": "აკ",
    "pulpitis": "პ", "periapical": "პტ", "cyst": "პტ", "filling": "ბ", "canal_filled": "ბ",
    "crown": "ხგ", "veneer": "ხგ", "bridge": "ხკ", "implant": "ი", "extracted": "0",
    "missing": "ა", "retained": "რკ", "root_remnant": "ფ",
}
MOBILITY_CODES = {1: "I", 2: "II", 3: "III"}
CARD_VISIT_STATES = ("arrived", "in_progress", "done", "paid")
FORM_ADVICE = "პაციენტს მიეცა რჩევა-დარიგება პირის ღრუს სანაციის შესახებ."


def _ge_date(d):
    return "%02d %s, %d" % (d.day, GE_MONTHS[d.month - 1], d.year) if d else ""


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _clinic_check_med_card_access(self):
        user = self.env.user
        if not (user.has_group("clinic_patient_card.group_clinic_admin")
                or user.has_group("clinic_patient_card.group_clinic_doctor")):
            raise AccessError(_("Only clinic doctors and administrators can open the medical card."))

    def _clinic_card_visits(self):
        """All clinic visits that took place (sudo: a doctor sees only own visits,
        the card must hold every visit of the patient)."""
        self.ensure_one()
        return self.env["calendar.event"].sudo().search([
            ("is_clinic", "=", True), ("patient_id", "=", self.id),
            ("clinic_state", "in", CARD_VISIT_STATES)], order="start, id")

    def _clinic_card_teeth(self):
        """{fdi: code} for the form's tooth scheme (current state of the chart +
        mobility degree of the latest periodontal chart)."""
        self.ensure_one()
        codes = {}
        for fdi, s in self.sudo().clinic_tooth_states().items():
            codes[int(fdi)] = (FORM_TOOTH_CODES.get(s.get("treat"))
                               or FORM_TOOTH_CODES.get(s.get("cond")) or "")
        perio = self.env["clinic.perio.chart"].sudo().search(
            [("partner_id", "=", self.id)], order="date desc, id desc", limit=1)
        for fdi, t in (perio.data or {}).items():
            mob = MOBILITY_CODES.get(t.get("mob") or 0) if isinstance(t, dict) else None
            if mob and str(fdi).isdigit():
                codes[int(fdi)] = (codes.get(int(fdi), "") + " " + mob).strip()
        return codes

    @staticmethod
    def _clinic_visit_lines(ev):
        lines = ev.procedure_line_ids.filtered(lambda l: l.status != "cancelled")
        diag = []
        for line in lines.filtered("icd10_id"):
            label = line.icd10_id.display_name + (" (%s)" % line.tooth if line.tooth else "")
            if label not in diag:
                diag.append(label)
        treat = ["%s%s" % (line.procedure_id.name or line.name or "",
                           " (%s)" % line.tooth if line.tooth else "") for line in lines]
        return diag, treat

    @staticmethod
    def _clinic_local_date(ev):
        return fields.Datetime.context_timestamp(ev, ev.start).strftime("%d.%m.%Y") if ev.start else ""

    def _clinic_med_card_data(self):
        """Everything form IV-220/ა + IV-220-1/ა print, from the live records."""
        self.ensure_one()
        self._clinic_check_med_card_access()
        p = self.sudo()
        visits = self._clinic_card_visits()
        first, rest, last = visits[:1], visits[1:], visits[-1:]
        phone = p.phone or (p.patient_phone_ids[:1].display_name or "")
        address = ", ".join(x for x in (p.street, p.city_id.name if p.city_id else p.city) if x)
        if p.allergy_answer == "no":
            allergy = "არ აღნიშნა"
        elif p.allergy_answer == "yes" or p.allergy_ids:
            allergy = "; ".join(a.name + (" — " + a.reaction if a.reaction else "")
                                for a in p.allergy_ids) or "აღნიშნა (რაზე — არ არის მითითებული)"
        else:
            allergy = ""
        teeth = self._clinic_card_teeth()
        n2 = {}
        if first:
            ev = first
            items = set(ev.clinic_complaint_ids.mapped("form_item")) - {False}
            other = [c.name for c in ev.clinic_complaint_ids if not c.form_item]
            if ev.clinic_complaints_other:
                other.append(ev.clinic_complaints_other)
            checks = ev.clinic_obj_checks or {}
            diag, treat = self._clinic_visit_lines(ev)
            n2 = {
                "date": self._clinic_local_date(ev),
                "complaints": [(label, k in items) for k, label in FORM_COMPLAINTS],
                "teeth_text": ev.clinic_complaint_teeth or "",
                "complaint_other": "; ".join(other),
                "anamnesis": ev.clinic_complaints or "",
                "defects": ", ".join(str(f) for f in sorted(teeth) if teeth[f]),
                "bite": ev.clinic_obj_bite or "",
                "mucosa": ev.clinic_obj_mucosa or "",
                "perio": [(label, k in (checks.get("perio") or [])) for k, label in FORM_PERIODONTIUM],
                "plaque": [(label, k in (checks.get("plaque") or [])) for k, label in FORM_PLAQUE],
                "plan": [(label, k in (checks.get("plan") or [])) for k, label in FORM_EXAM_PLAN],
                "pocket": ev.clinic_obj_pocket_depth or "",
                "obj_other": "; ".join(x for x in (ev.clinic_obj_periodontium, ev.clinic_obj_plaque,
                                                   ev.clinic_obj_other) if x),
                "plan_other": ev.clinic_obj_exam_plan or "",
                "result": ev.clinic_exam_results or "",
                "diagnosis": "; ".join(diag),
                "treatment": "; ".join(treat),
            }
        rows = []
        for ev in rest:
            diag, treat = self._clinic_visit_lines(ev)
            parts = []
            if ev.clinic_complaints:
                parts.append("ანამნეზი: " + ev.clinic_complaints)
            if ev.clinic_exam_results:
                parts.append("სტატუსი: " + ev.clinic_exam_results)
            if diag:
                parts.append("დიაგნოზი: " + "; ".join(diag))
            if treat:
                parts.append("მკურნალობა: " + "; ".join(treat))
            rx = ev.prescription_ids.mapped("medicament")
            if rx:
                parts.append("დანიშნულება: " + "; ".join(rx))
            rows.append({"date": self._clinic_local_date(ev), "text": "\n".join(parts),
                         "doctor": ev.dentist_id.name or ""})
        advice = [FORM_ADVICE] + ["%s%s" % (r.medicament, " — " + r.directions if r.directions else "")
                                  for r in last.prescription_ids]
        return {
            "company": self.env.company.name or "",
            "card_no": p.vat or p.patient_ref or "",
            "name": " ".join(x for x in (p.last_name, p.first_name) if x) or p.name or "",
            "gender": {"male": "მამრობითი", "female": "მდედრობითი"}.get(p.gender, ""),
            "birthdate": _ge_date(p.birthdate),
            "phone": phone,
            "vat": p.vat or "",
            "address": address,
            "work": ", ".join(x for x in (p.parent_id.name if p.parent_id else "", p.function) if x),
            "allergy": allergy,
            "diseases": "\n".join(x for x in (p.chronic_diseases, p.medical_risk_notes) if x),
            "policy": p.insurance_policy_no or "",
            "insurer": p.insurance_company_id.name or "",
            "n2": n2,
            "teeth": teeth,
            "rows": rows,
            "epicrisis": last.clinic_epicrisis or "",
            "advice": advice,
            "printed": fields.Datetime.context_timestamp(self, fields.Datetime.now()).strftime("%d.%m.%Y %H:%M"),
            "printed_by": self.env.user.name,
        }

    def clinic_med_card_missing(self):
        """What the form still lacks — shown in red on the card tab (live)."""
        self.ensure_one()
        self._clinic_check_med_card_access()
        p = self.sudo()
        miss = []
        if not p.vat:
            miss.append(_("Personal No."))
        if not p.birthdate:
            miss.append(_("Birth Date"))
        if not p.gender:
            miss.append(_("Gender"))
        if not p.street:
            miss.append(_("Address"))
        if not (p.phone or p.patient_phone_ids):
            miss.append(_("Phone"))
        if not p.allergy_answer:
            miss.append(_("Allergy answer (expired or not given)"))
        visits = self._clinic_card_visits()
        if not visits:
            miss.append(_("No visit yet — the examination sheet is empty"))
        else:
            first = visits[:1]
            if not first.clinic_complaint_ids and not first.clinic_complaints_other:
                miss.append(_("First visit: complaints"))
            if not any((first.clinic_obj_checks or {}).values()):
                miss.append(_("First visit: objective exam checkboxes"))
            if not first.procedure_line_ids.filtered("icd10_id"):
                miss.append(_("First visit: ICD-10 diagnosis"))
        return miss

    def action_med_card_pdf(self):
        self.ensure_one()
        self._clinic_check_med_card_access()
        return self.env.ref("clinic_patient_card.action_report_clinic_med_card").report_action(self)
