# -*- coding: utf-8 -*-
"""Tooth chart states (D-33): what the clinic's tooth chart draws per tooth.

One source of truth for the chart on the visit page AND the patient card:
the patient's procedure lines (tooth + ICD-10 diagnosis + status).
  * a PLANNED procedure with a diagnosis  -> the tooth shows that DISEASE
  * a DONE procedure                      -> the tooth shows the TREATMENT done
The manual per-tooth statuses (clinic.patient.tooth) stay as a fallback.
The 14 diseases / 8 treatments are the clinic's design sheet.
"""
import re

from odoo import _, api, fields, models

CONDITIONS = [
    ("caries", "კარიესი"),
    ("deep_caries", "ღრმა კარიესი"),
    ("pulpitis", "პულპიტი"),
    ("periapical", "პერიოდონტიტი"),
    ("cyst", "კისტა / გრანულომა"),
    ("parodontitis", "პაროდონტიტი"),
    ("gingivitis", "გინგივიტი"),
    ("fracture", "მოტეხილობა / ბზარი"),
    ("defect", "სოლისებრი დეფექტი"),
    ("attrition", "ცვეთა"),
    ("calculus", "კბილის ქვა"),
    ("mobility", "მოძრაობა"),
    ("retained", "რეტინირებული"),
    ("root_remnant", "ფესვის ნარჩენი"),
]
TREATMENTS = [
    ("filling", "ბეჭედი (პლომბა)"),
    ("canal_filled", "არხი დაბჟენილია"),
    ("crown", "გვირგვინი"),
    ("bridge", "ხიდი"),
    ("implant", "იმპლანტი"),
    ("veneer", "ვინირი"),
    ("missing", "აკლია"),
    ("extracted", "ამოღებული"),
]

# diagnosis (ICD-10 prefix) -> disease; used while an ICD-10 row has no explicit
# `tooth_condition`. Longest prefix wins. Editable per diagnosis in
# Configuration -> ICD-10.
ICD_PREFIX = [
    ("K00.3", "defect"), ("K00.4", "defect"), ("K00.8", "defect"), ("K00.9", "defect"),
    ("K01.0", "retained"), ("K01.1", "retained"),
    ("K02.0", "caries"), ("K02.1", "deep_caries"), ("K02.2", "deep_caries"),
    ("K02.9", "caries"), ("K02", "caries"),
    ("K03.0", "attrition"), ("K03.1", "attrition"), ("K03.6", "calculus"),
    ("K03.8", "defect"),
    ("K04.0", "pulpitis"), ("K04.1", "pulpitis"), ("K04.2", "pulpitis"),
    ("K04.4", "pulpitis"), ("K04.5", "periapical"), ("K04.6", "periapical"),
    ("K04.7", "periapical"), ("K04.8", "cyst"),
    ("K05.0", "gingivitis"), ("K05.1", "gingivitis"),
    ("K05.2", "parodontitis"), ("K05.3", "parodontitis"), ("K05.4", "parodontitis"),
    ("K05", "parodontitis"),
    ("K08.1", "missing"), ("K08.3", "root_remnant"),
    ("S02.5", "fracture"),
]

# done-procedure name keywords -> treatment. Rules run in order; the first rule whose
# words match (and whose `not` words do not) wins. Used only while the procedure
# product has no explicit "Tooth chart picture". Georgian / Russian / English.
TREATMENT_RULES = [
    ("extracted", ["ექსტრაქც", "extraction", "удален"], []),
    ("bridge", ["ხიდ", "bridge", "мост"], []),
    ("crown", ["გვირგვინ", "crown", "коронк"], []),
    ("veneer", ["ვინირ", "veneer", "винир"], []),
    ("implant", ["იმპლანტ", "implant", "имплант"], []),
    ("canal_filled", ["არხიან", "root canal", "эндо"], ["გარეშე", "without"]),
    ("filling", ["ბჟენ", "პლომბ", "filling", "пломб"], ["გარეშე", "არხიან", "without"]),
]
# words that cancel any match: removal / fixing / retrieving is not a new treatment
TREATMENT_VETO = ["მოხსნ", "მოხსან", "ამოღება", "ფიქსაცი", "removal", "корректир"]

MANUAL_STATUS = {
    "caries": ("cond", "caries"), "filled": ("treat", "filling"),
    "crown": ("treat", "crown"), "root_canal": ("treat", "canal_filled"),
    "implant": ("treat", "implant"), "missing": ("treat", "missing"),
    "to_extract": ("treat", "extracted"),
}

TOOTH_RE = re.compile(r"(?<!\d)([1-4][1-8])(?!\d)")


def _treatment_key(text):
    low = (text or "").lower()
    if any(w in low for w in TREATMENT_VETO):
        return False
    for key, words, nots in TREATMENT_RULES:
        if any(w in low for w in words) and not any(n in low for n in nots):
            return key
    return False


class ClinicIcd10(models.Model):
    _inherit = "clinic.icd10"

    tooth_condition = fields.Selection(
        CONDITIONS + [("missing", "აკლია")], string="Tooth chart picture",
        help="What the tooth looks like on the chart while this diagnosis is planned. "
             "Empty = by the code (K02.1 deep caries, K04.0 pulpitis, …).")

    def _tooth_condition_key(self):
        self.ensure_one()
        if self.tooth_condition:
            return self.tooth_condition
        code = (self.code or "").upper()
        best = ""
        key = False
        for prefix, cond in ICD_PREFIX:
            if code.startswith(prefix) and len(prefix) > len(best):
                best, key = prefix, cond
        return key


class ProductTemplate(models.Model):
    _inherit = "product.template"

    clinic_tooth_treatment = fields.Selection(
        TREATMENTS, string="Tooth chart picture",
        help="What the tooth looks like once this procedure is DONE. "
             "Empty = guessed from the procedure name (filling, crown, implant, …).")


class ResPartner(models.Model):
    _inherit = "res.partner"

    def clinic_tooth_states(self):
        """{fdi: {cond, treat, cond_label, treat_label, diagnosis, procedure}} for
        the chart. Only teeth that are not simply healthy are returned."""
        self.ensure_one()
        cond_label = dict(CONDITIONS + [("missing", "აკლია")])
        treat_label = dict(TREATMENTS)
        out = {}

        def slot(fdi):
            return out.setdefault(fdi, {"cond": False, "treat": False,
                                        "diagnosis": "", "procedure": ""})

        # manual statuses first (lowest priority)
        for row in self.env["clinic.patient.tooth"].sudo().search([("partner_id", "=", self.id)]):
            kind, key = MANUAL_STATUS.get(row.status, (False, False))
            m = TOOTH_RE.search(str(row.tooth_number or "")) if hasattr(row, "tooth_number") else None
            fdi = int(m.group(1)) if m else False
            if fdi and kind:
                slot(fdi)["cond" if kind == "cond" else "treat"] = key
        lines = self.env["clinic.procedure.history"].sudo().search([
            ("partner_id", "=", self.id), ("tooth", "!=", False),
            ("status", "!=", "cancelled")], order="id")
        for ln in lines:
            for token in set(TOOTH_RE.findall(ln.tooth or "")):
                fdi = int(token)
                s = slot(fdi)
                name = ln.procedure_id.name or ln.name or ""
                if ln.status in ("planned", "in_progress", "postponed"):
                    cond = ln.icd10_id._tooth_condition_key() if ln.icd10_id else False
                    if cond:
                        s["cond"] = cond
                        s["diagnosis"] = ln.icd10_id.display_name
                        s["procedure"] = name
                elif ln.status == "done":
                    treat = (ln.procedure_id.product_tmpl_id.clinic_tooth_treatment
                             or _treatment_key(name))
                    if treat:
                        s["treat"] = treat
                        s["procedure"] = name
                        if treat in ("filling", "canal_filled", "crown", "bridge",
                                     "implant", "veneer", "extracted"):
                            s["cond"] = False  # the disease is treated now
        res = {}
        for fdi, s in out.items():
            cond, treat = s["cond"], s["treat"]
            if cond == "missing":
                cond, treat = False, "missing"
            if treat in ("missing", "extracted"):
                cond = False
            if not cond and not treat:
                continue
            res[str(fdi)] = {
                "cond": cond, "treat": treat,
                "cond_label": cond_label.get(cond, ""),
                "treat_label": treat_label.get(treat, ""),
                "diagnosis": s["diagnosis"], "procedure": s["procedure"],
            }
        return res
