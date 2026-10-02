# -*- coding: utf-8 -*-
"""Treatment plan — the printable "TREATMENT PLAN" document of a patient.

The fixed parts (clinic header, "Approved by" block) live in the QWeb report;
everything else is filled per patient — and the table is pulled automatically
from the procedures the doctor planned (status `planned`) on the visit page.
See docs/DECISIONS.md D-30.
"""
from odoo import _, api, fields, models


class ClinicTreatmentPlan(models.Model):
    _name = "clinic.treatment.plan"
    _description = "Treatment Plan"
    _order = "date desc, id desc"

    # optional: the plan is also written for people who are not clients yet; with a
    # patient chosen, the doctor's planned procedures are pulled in automatically
    patient_id = fields.Many2one(
        "res.partner", string="Patient (client card)", index=True,
        domain="[('is_patient', '=', True)]", ondelete="set null",
        default=lambda self: self.env.context.get("default_patient_id"),
    )
    name = fields.Char(compute="_compute_name", store=True)
    # typed by hand for every plan (user): the name printed on the document
    patient_name = fields.Char(string="Patient Name")
    date = fields.Date(default=fields.Date.context_today)
    implantologist = fields.Char(string="Implantologist")
    prosthodontist = fields.Char(string="Prosthodontist")
    chief_doctor = fields.Char(string="Chief Medical Officer")
    line_ids = fields.One2many(
        "clinic.treatment.plan.line", "plan_id", string="Recommended Treatment", copy=True,
    )
    note = fields.Text(string="Note")
    schedule = fields.Text(string="Scheduled appointments")
    total_implantology = fields.Char(string="Total Treatment Cost (Implantology)")
    total_prosthodontics = fields.Char(string="Total Treatment Cost (Prosthodontics)")
    payment_note = fields.Text(string="Payment note")

    @api.model
    def _report_assets(self):
        """Logo + contact icons as data URIs (wkhtmltopdf cannot always reach the
        server's own static URLs from inside the container)."""
        import base64
        from odoo.tools import file_open
        base = "clinic_patient_card/static/src/img/plan/"
        out = {}
        for key in ("logo", "icon_location", "icon_phone", "icon_mail", "icon_web"):
            with file_open(base + key + ".png", "rb") as f:
                out[key] = "data:image/png;base64," + base64.b64encode(f.read()).decode()
        return out

    @api.model
    def _ent(self, text):
        """HTML-escape and turn every non-ASCII character into a numeric entity:
        the PDF engine of this server decodes the report body as Latin-1, which
        garbled Georgian and the euro sign — entities render correctly anyway."""
        from markupsafe import Markup, escape
        s = str(escape(text or ""))
        return Markup("".join(c if ord(c) < 128 else "&#%d;" % ord(c) for c in s))

    @api.model
    def _lines_of(self, text):
        return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]

    @api.depends("patient_id", "patient_name", "date")
    def _compute_name(self):
        for plan in self:
            plan.name = _("Treatment plan — %s") % (
                plan.patient_name or plan.patient_id.name or "")

    @api.model_create_multi
    def create(self, vals_list):
        plans = super().create(vals_list)
        for plan in plans:
            if not plan.line_ids:
                plan._pull_planned_procedures()
        return plans

    # ------------------------------------------------------------------
    def _money(self, amount, currency):
        txt = ("%.2f" % amount).rstrip("0").rstrip(".")
        return "%s %s" % (txt, currency.name or "")

    def action_pull_planned(self):
        """Add the patient's planned procedures that are not on the plan yet."""
        for plan in self:
            plan._pull_planned_procedures()
        return True

    def _pull_planned_procedures(self):
        self.ensure_one()
        if not self.patient_id:
            return
        History = self.env["clinic.procedure.history"].sudo()
        taken = self.line_ids.mapped("procedure_history_id").ids
        planned = History.search([
            ("partner_id", "=", self.patient_id.id), ("status", "=", "planned"),
            ("id", "not in", taken)])
        if not planned:
            return
        # visit label by the order of the visits (appointments) they belong to
        visits = planned.mapped("appointment_id").sorted(lambda a: (a.start or fields.Datetime.now(), a.id))
        visit_no = {a.id: i for i, a in enumerate(visits, start=1)}
        base = max(self.line_ids.mapped("sequence") or [0])
        seq = base
        for h in planned.sorted(lambda r: (visit_no.get(r.appointment_id.id, 99), r.id)):
            seq += 10
            n = visit_no.get(h.appointment_id.id)
            qty = h.qty or 1.0
            cur = h.currency_id or self.env.company.currency_id
            unit = self._money(h.price_unit, cur)
            if qty != 1:
                unit += " X %g" % qty
            self.env["clinic.treatment.plan.line"].create({
                "plan_id": self.id, "sequence": seq,
                "visit": ("VISIT %d" % n) if n else "",
                "department": h.appointment_id.direction_id.name or "",
                "tooth": h.tooth or "",
                "procedure": h.procedure_id.name or h.name or "",
                "unit_price": unit,
                "price": self._money(h.amount_total, cur),
                "procedure_history_id": h.id,
            })


class ClinicTreatmentPlanLine(models.Model):
    _name = "clinic.treatment.plan.line"
    _description = "Treatment Plan Line"
    _order = "sequence, id"

    plan_id = fields.Many2one("clinic.treatment.plan", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    visit = fields.Char(string="Visit")
    department = fields.Char(string="Department")
    tooth = fields.Char(string="Tooth #")
    procedure = fields.Text(string="Procedure")
    # prices are free text on purpose: "100 GEL X 5", "500 GEL // 250 GEL", "+ 196 EURO"
    unit_price = fields.Char(string="Unit price")
    price = fields.Char(string="Price")
    procedure_history_id = fields.Many2one(
        "clinic.procedure.history", string="Pulled from", ondelete="set null", copy=False)
