# -*- coding: utf-8 -*-
import io

import xlsxwriter

from odoo import http
from odoo.http import content_disposition, request

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
KIND_FILE = {"doctor": "doctors", "assistant": "assistants", "admin": "administration"}
HEADER = [
    "თანამშრომელი", "გეგმა (სთ)", "გეგმა დღემდე (სთ)", "ნამუშევარი (სთ)", "სხვაობა (სთ)",
    "შეგანაკვეთური (სთ)", "დაგვიანება (წთ)", "დაგვიანების დღეები", "გაცდენა (დღე)",
    "შვებულება (დღე)", "ბიულეტენი (დღე)", "დასვენება (დღე)", "შესრულება %",
]


class ClinicHoursExport(http.Controller):
    """Worked hours of one staff group for a period as .xlsx (same numbers as
    the "ნამუშევარი საათები" screen)."""

    @http.route("/clinic/worked_hours/export", type="http", auth="user")
    def export(self, kind=None, date_from=None, date_to=None, mode="week", **kw):
        user = request.env.user
        if not (
            user.has_group("clinic_patient_card.group_clinic_admin")
            or user.has_group("clinic_patient_card.group_clinic_doctor")
        ) or kind not in KIND_FILE or not date_from or not date_to:
            return request.not_found()
        data = request.env["clinic.schedule.line"].clinic_hours_data(
            kind, date_from, date_to, mode)

        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {"in_memory": True})
        ws = wb.add_worksheet("Worked hours")
        bold = wb.add_format({"bold": True, "bg_color": "#E8EAF6", "border": 1})
        ws.write(0, 0, "პერიოდი: %s – %s" % (date_from, date_to))
        for col, title in enumerate(HEADER):
            ws.write(2, col, title, bold)
        for row, r in enumerate(data["rows"], start=3):
            values = [
                r["name"], r["planned"], r["planned_to_date"], r["worked"], r["diff"],
                r["overtime"], r["late_minutes"], r["late_days"], r["absent_days"],
                r["vacation"], r["sick"], r["off"],
                r["pct"] if r["pct"] is not None else "",
            ]
            for col, val in enumerate(values):
                ws.write(row, col, val)
        ws.set_column(0, 0, 26)
        ws.set_column(1, 12, 16)
        wb.close()
        filename = "worked_hours_%s_%s_%s.xlsx" % (KIND_FILE[kind], date_from, date_to)
        return request.make_response(buf.getvalue(), headers=[
            ("Content-Type", XLSX), ("Content-Disposition", content_disposition(filename))])
