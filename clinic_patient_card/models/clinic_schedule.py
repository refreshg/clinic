# -*- coding: utf-8 -*-
"""Staff schedules (doctors / assistants / administration).

Standard-first: employees are the standard `hr.employee` (attendance later via
`hr_attendance`); only the shift templates and the per-day schedule lines are
custom (Community has no planning app). See docs/DECISIONS.md D-29.
"""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

STAFF_KINDS = [
    ("doctor", "ექიმი"),
    ("assistant", "ასისტენტი"),
    ("admin", "ადმინისტრატორი"),
]
DAY_TYPES = [
    ("shift", "ცვლა"),
    ("off", "დასვენება"),
    ("vacation", "შვებულება"),
    ("sick", "ბიულეტენი"),
]


def _fmt_hour(value):
    h = int(value)
    m = int(round((value - h) * 60))
    if m == 60:
        h, m = h + 1, 0
    return "%02d:%02d" % (h, m)


class ClinicShift(models.Model):
    _name = "clinic.shift"
    _description = "Staff Shift Template"
    _order = "staff_kind, sequence, start_hour"

    name = fields.Char(compute="_compute_name", store=True)
    staff_kind = fields.Selection(STAFF_KINDS, string="Staff", required=True)
    start_hour = fields.Float(string="From", required=True)
    end_hour = fields.Float(string="To", required=True)
    hours = fields.Float(compute="_compute_name", store=True)
    color = fields.Integer(
        string="Colour", default=0,
        help="0 pink · 1 green · 2 yellow · 3 blue (the palette of the schedule screen)",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    @api.depends("start_hour", "end_hour")
    def _compute_name(self):
        for s in self:
            s.name = "%s–%s" % (_fmt_hour(s.start_hour), _fmt_hour(s.end_hour))
            s.hours = max(s.end_hour - s.start_hour, 0.0)

    @api.constrains("start_hour", "end_hour", "color")
    def _check_shift(self):
        for s in self:
            if not (0.0 <= s.start_hour < s.end_hour <= 24.0):
                raise ValidationError(_("A shift must start before it ends (0–24 h)."))
            if not 0 <= s.color <= 3:
                raise ValidationError(_("Colour must be 0–3."))


class ClinicScheduleLine(models.Model):
    _name = "clinic.schedule.line"
    _description = "Staff Schedule Day"
    _order = "date, employee_id"

    employee_id = fields.Many2one(
        "hr.employee", required=True, ondelete="cascade", index=True,
    )
    date = fields.Date(required=True, index=True)
    day_type = fields.Selection(DAY_TYPES, default="shift", required=True)
    shift_id = fields.Many2one("clinic.shift")

    @api.constrains("employee_id", "date", "day_type", "shift_id")
    def _check_line(self):
        for line in self:
            if line.day_type == "shift" and not line.shift_id:
                raise ValidationError(_("Pick a shift for a working day."))
            if self.search_count([
                ("employee_id", "=", line.employee_id.id),
                ("date", "=", line.date),
                ("id", "!=", line.id),
            ]):
                raise ValidationError(_("This employee already has an entry on %s.") % line.date)

    # ------------------------------------------------------------------
    # Schedule screen API (client action `clinic_schedule`)
    # ------------------------------------------------------------------
    @api.model
    def _clinic_is_admin(self):
        return self.env.user.has_group("clinic_patient_card.group_clinic_admin")

    @api.model
    def clinic_schedule_data(self, kind, date_from, date_to):
        is_admin = self._clinic_is_admin()
        Employee = self.env["hr.employee"].sudo()
        if is_admin:
            Employee.clinic_sync_staff()
        domain = [("clinic_staff_kind", "!=", False)]
        all_staff = Employee.search(domain)
        counts = {k: 0 for k, _l in STAFF_KINDS}
        for e in all_staff:
            counts[e.clinic_staff_kind] += 1
        emps = all_staff.filtered(lambda e: e.clinic_staff_kind == kind)
        if not is_admin:  # doctors see only themselves
            emps = emps.filtered(lambda e: e.user_id == self.env.user)
        emps = emps.sorted("name")
        shifts = self.env["clinic.shift"].sudo().search([("staff_kind", "=", kind)])
        lines = self.sudo().search([
            ("employee_id", "in", emps.ids),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ])
        return {
            "is_admin": is_admin,
            "counts": counts,
            "employees": [
                {"id": e.id, "name": e.name, "job": e.job_title or ""} for e in emps
            ],
            "shifts": [
                {"id": s.id, "name": s.name, "start": s.start_hour, "end": s.end_hour,
                 "hours": s.hours, "color": s.color}
                for s in shifts
            ],
            "lines": [
                {"employee_id": ln.employee_id.id, "date": fields.Date.to_string(ln.date),
                 "day_type": ln.day_type, "shift_id": ln.shift_id.id or False}
                for ln in lines
            ],
        }

    @api.model
    def clinic_schedule_set(self, employee_id, date, day_type=False, shift_id=False):
        """Create / change / clear one employee-day. day_type falsy = clear."""
        if not self._clinic_is_admin():
            raise AccessError(_("Only a Clinic Administrator can edit schedules."))
        line = self.sudo().search([
            ("employee_id", "=", employee_id), ("date", "=", date)], limit=1)
        if not day_type:
            line.unlink()
            return True
        if day_type == "shift" and not shift_id:
            raise UserError(_("Pick a shift."))
        vals = {
            "day_type": day_type,
            "shift_id": shift_id if day_type == "shift" else False,
        }
        if line:
            line.write(vals)
        else:
            self.sudo().create(dict(vals, employee_id=employee_id, date=date))
        return True


# NB: _inherit classes of OTHER models live at the END of the file (a mid-file
# class would re-parent every def below it — see CLAUDE.md).
class HrEmployee(models.Model):
    _inherit = "hr.employee"

    clinic_staff_kind = fields.Selection(
        STAFF_KINDS, string="Clinic Role", copy=False,
        help="Puts the employee on the clinic staff schedule.",
    )

    @api.model
    def clinic_sync_staff(self):
        """Idempotent: every active clinic doctor / administrator user gets an
        employee record (the generic 'clinic' and the Administrator account
        are not staff). Assistants are added by hand with Clinic Role set."""
        doctor_grp = self.env.ref("clinic_patient_card.group_clinic_doctor")
        admin_grp = self.env.ref("clinic_patient_card.group_clinic_admin")
        skip = self.env.ref("base.user_admin", raise_if_not_found=False)
        users = self.env["res.users"].sudo().search([
            ("share", "=", False), ("active", "=", True),
            ("group_ids", "in", [doctor_grp.id, admin_grp.id]),
        ])
        for user in users:
            if (skip and user == skip) or user.login == "clinic":
                continue
            emp = self.sudo().with_context(active_test=False).search(
                [("user_id", "=", user.id)], limit=1)
            kind = "doctor" if doctor_grp in user.group_ids else "admin"
            if not emp:
                self.sudo().create({
                    "name": user.name, "user_id": user.id,
                    "clinic_staff_kind": kind,
                })
            elif not emp.clinic_staff_kind:
                emp.sudo().clinic_staff_kind = kind
        return True
