# -*- coding: utf-8 -*-
"""Periodontal chart (D-48): one examination of a patient's gums, modelled on
the Bern chart (periodontalchart-online.com) — per tooth (FDI 11–48): missing,
implant, mobility, furcation (molars) and, on the buccal and the oral side at 3
sites each, bleeding on probing, plaque, gingival margin and probing depth.

All measurements live in ONE json field (32 teeth x ~30 values would otherwise
be ~1000 columns or rows per exam); the summary is computed and stored.

  data = {"16": {"m": false, "i": false, "mob": 0,
                 "b": {"f": 0, "gm": [0, 0, 0], "pd": [3, "", 4],
                       "bop": [0, 1, 0], "pl": [0, 0, 1]},
                 "o": {...same, the palatal / lingual side...}}, ...}

Gingival margin (GM): distance CEJ -> gingival margin in mm, POSITIVE = recession
(margin apical to the CEJ), negative = margin coronal (swelling / overgrowth).
Clinical attachment level: CAL = PD + GM.
"""
from odoo import api, fields, models

SIDES = ("b", "o")


def _num(v):
    """'' / None -> None (not measured); anything else -> float."""
    if v in ("", None, False):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def perio_summary(data):
    """Means and percentages over the measured sites of the present teeth."""
    pds, cals = [], []
    bop = plaque = sites = 0
    teeth = 0
    for tooth in (data or {}).values():
        if not isinstance(tooth, dict) or tooth.get("m"):
            continue
        teeth += 1
        for side in SIDES:
            s = tooth.get(side) or {}
            pd_l, gm_l = s.get("pd") or [], s.get("gm") or []
            bop_l, pl_l = s.get("bop") or [], s.get("pl") or []
            for i in range(3):
                pd = _num(pd_l[i] if i < len(pd_l) else None)
                gm = _num(gm_l[i] if i < len(gm_l) else None) or 0.0
                sites += 1
                if pd is not None:
                    pds.append(pd)
                    cals.append(pd + gm)
                if i < len(bop_l) and bop_l[i]:
                    bop += 1
                if i < len(pl_l) and pl_l[i]:
                    plaque += 1
    return {
        "teeth_present": teeth,
        "mean_pd": round(sum(pds) / len(pds), 1) if pds else 0.0,
        "mean_cal": round(sum(cals) / len(cals), 1) if cals else 0.0,
        "bop_pct": round(100.0 * bop / sites) if sites else 0.0,
        "plaque_pct": round(100.0 * plaque / sites) if sites else 0.0,
        "deep_sites": len([p for p in pds if p >= 4]),
    }


class ClinicPerioChart(models.Model):
    _name = "clinic.perio.chart"
    _description = "Periodontal Chart"
    _order = "date desc, id desc"

    partner_id = fields.Many2one(
        "res.partner", string="Patient", required=True, ondelete="cascade", index=True)
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    doctor_id = fields.Many2one(
        "res.users", string="Doctor", default=lambda self: self.env.user)
    appointment_id = fields.Many2one(
        "calendar.event", string="Visit", ondelete="set null", index=True)
    data = fields.Json(string="Measurements", default=dict)
    note = fields.Text(string="Note")

    teeth_present = fields.Integer(string="Teeth", compute="_compute_summary", store=True)
    mean_pd = fields.Float(string="Mean probing depth (mm)", digits=(4, 1),
                           compute="_compute_summary", store=True)
    mean_cal = fields.Float(string="Mean attachment level (mm)", digits=(4, 1),
                            compute="_compute_summary", store=True)
    bop_pct = fields.Float(string="Bleeding on probing (%)", digits=(5, 0),
                           compute="_compute_summary", store=True)
    plaque_pct = fields.Float(string="Plaque (%)", digits=(5, 0),
                              compute="_compute_summary", store=True)
    deep_sites = fields.Integer(string="Sites ≥ 4 mm", compute="_compute_summary", store=True)

    @api.depends("data")
    def _compute_summary(self):
        for chart in self:
            s = perio_summary(chart.data)
            chart.teeth_present = s["teeth_present"]
            chart.mean_pd = s["mean_pd"]
            chart.mean_cal = s["mean_cal"]
            chart.bop_pct = s["bop_pct"]
            chart.plaque_pct = s["plaque_pct"]
            chart.deep_sites = s["deep_sites"]

    @api.depends("date", "partner_id")
    def _compute_display_name(self):
        for chart in self:
            chart.display_name = "%s — %s" % (
                chart.partner_id.name or "", fields.Date.to_string(chart.date) or "")


class ResPartner(models.Model):
    _inherit = "res.partner"

    perio_chart_ids = fields.One2many(
        "clinic.perio.chart", "partner_id", string="Periodontal charts")
