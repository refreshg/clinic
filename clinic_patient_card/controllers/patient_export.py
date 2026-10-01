# -*- coding: utf-8 -*-
import io
from datetime import date

import xlsxwriter

from odoo import http
from odoo.http import content_disposition, request

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
STATUS_FILE = {"primary": "primary", "unique": "unique", "all": "all"}
HEADER = [
    "პაციენტის ID", "სახელი", "გვარი", "პირადი №", "დაბადების თარიღი",
    "ტელეფონი", "ელ. ფოსტა", "დაზღვევა", "მომართვის წყარო",
    "ჩატარებული ვიზიტები", "ბოლო ვიზიტი",
]


class ClinicPatientExport(http.Controller):
    """One click on a Clinic menu item downloads the patients of a ready-made
    status (primary = came once, unique = came several times) as .xlsx."""

    @http.route("/clinic/patients/export", type="http", auth="user")
    def export(self, status=None, **kw):
        user = request.env.user
        if not (
            user.has_group("clinic_patient_card.group_clinic_admin")
            or user.has_group("clinic_patient_card.group_clinic_doctor")
        ):
            return request.not_found()
        if status not in STATUS_FILE:
            return request.not_found()

        domain = [("is_patient", "=", True)]
        if status != "all":
            domain.append(("clinic_patient_status", "=", status))
        patients = request.env["res.partner"].search(domain, order="name")
        referral = dict(
            request.env["res.partner"]._fields["referral_source"]
            ._description_selection(request.env)
        )

        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {"in_memory": True})
        ws = wb.add_worksheet("Patients")
        bold = wb.add_format({"bold": True, "bg_color": "#E8EAF6", "border": 1})
        for col, title in enumerate(HEADER):
            ws.write(0, col, title, bold)
        for row, p in enumerate(patients, start=1):
            done = p.clinic_visit_ids.filtered(
                lambda v: v.clinic_state in ("done", "paid"))
            last = max(done.mapped("start")) if done else False
            values = [
                p.patient_ref or "",
                p.first_name or "",
                p.last_name or "",
                p.vat or "",
                p.birthdate.strftime("%d.%m.%Y") if p.birthdate else "",
                p.phone or "",
                p.email or "",
                p.insurance_company_id.name or "",
                referral.get(p.referral_source, "") if p.referral_source else "",
                p.clinic_done_visits,
                last.strftime("%d.%m.%Y") if last else "",
            ]
            for col, val in enumerate(values):
                ws.write(row, col, val)
        ws.set_column(0, 0, 14)
        ws.set_column(1, 2, 18)
        ws.set_column(3, 8, 20)
        ws.set_column(9, 10, 18)
        wb.close()

        filename = "patients_%s_%s.xlsx" % (STATUS_FILE[status], date.today().isoformat())
        return request.make_response(
            buf.getvalue(),
            headers=[
                ("Content-Type", XLSX),
                ("Content-Disposition", content_disposition(filename)),
            ],
        )
