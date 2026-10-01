# -*- coding: utf-8 -*-
"""Staff schedules (doctors / assistants / administration).

Standard-first: employees are the standard `hr.employee` (attendance later via
`hr_attendance`); only the shift templates and the per-day schedule lines are
custom (Community has no planning app). See docs/DECISIONS.md D-29.
"""
from datetime import datetime, timedelta

import pytz

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


SHIFT_COLORS = 12  # palette size of the schedule screen (classes cs_c0 .. cs_c11)
# (background, border, text) per colour index — mirrors $cs_palette in clinic_schedule.scss;
# the Planning board gets these as inline colours (it has no schedule stylesheet)
SHIFT_PALETTE = [
    ("#fbd5e3", "#f3a9c6", "#8a2a52"), ("#d6f0e3", "#98d5b5", "#1f6b46"),
    ("#fdeec2", "#f0cd72", "#7d5a05"), ("#d9e8fb", "#9cc2f1", "#214f8b"),
    ("#e6dcf7", "#bda6ea", "#4b2f8a"), ("#fde0cc", "#f3ab7c", "#8a4310"),
    ("#cdeeee", "#7fcfcf", "#14605f"), ("#fbd3d0", "#ef9a94", "#8e2019"),
    ("#e6f2c4", "#bcd96f", "#4c6212"), ("#d3d8f8", "#99a4ec", "#26319a"),
    ("#efe3d1", "#d4bc98", "#6b4f26"), ("#dde1e8", "#b0b8c6", "#3a4456"),
]
LATE_GRACE_H = 5 / 60.0  # a check-in up to 5 minutes after the shift start is not "late"
MONTHS_KA = ["იანვარი", "თებერვალი", "მარტი", "აპრილი", "მაისი", "ივნისი",
             "ივლისი", "აგვისტო", "სექტემბერი", "ოქტომბერი", "ნოემბერი", "დეკემბერი"]
WD_KA = ["ორშ", "სამ", "ოთხ", "ხუთ", "პარ", "შაბ", "კვი"]


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
        help="0-11: index in the schedule screen palette (pink, green, yellow, blue, purple, "
             "orange, teal, red, lime, indigo, sand, slate)",
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
            if not 0 <= s.color < SHIFT_COLORS:
                raise ValidationError(_("Colour must be 0–%s.") % (SHIFT_COLORS - 1))


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
    def _clinic_own_kind(self):
        emp = self.env["hr.employee"].sudo().search([
            ("user_id", "=", self.env.user.id), ("clinic_staff_kind", "!=", False)], limit=1)
        return emp.clinic_staff_kind or False

    @api.model
    def _clinic_resolve_kind(self, kind, is_admin):
        """The group a screen opens on: a non-admin always sees their own
        group; an admin gets the requested one, else their own, else doctors."""
        own = self._clinic_own_kind()
        if not is_admin:
            return own or "doctor"
        return kind or own or "doctor"

    @api.model
    def _clinic_closed_weekdays(self):
        """Weekdays (0=Mon..6=Sun) on which the clinic is closed — from the
        company's Clinic Schedule; no working days configured = nothing closed."""
        workdays = self.env.company._clinic_workdays()
        return sorted(set(range(7)) - workdays) if workdays else []

    @api.model
    def clinic_schedule_data(self, kind, date_from, date_to):
        is_admin = self._clinic_is_admin()
        kind = self._clinic_resolve_kind(kind, is_admin)
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
        lines = self.sudo().search([
            ("employee_id", "in", emps.ids),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ])
        # active templates + archived ones still referenced by the shown days
        shifts = self.env["clinic.shift"].sudo().with_context(active_test=False).search(
            [("staff_kind", "=", kind)]).filtered(
            lambda s: s.active or s in lines.shift_id)
        return {
            "kind": kind,
            "visible_kinds": [k for k, _l in STAFF_KINDS] if is_admin else [kind],
            "is_admin": is_admin,
            "closed_weekdays": self._clinic_closed_weekdays(),
            "counts": counts,
            "employees": [
                {"id": e.id, "name": e.name, "job": e.job_title or ""} for e in emps
            ],
            "shifts": [
                {"id": s.id, "name": s.name, "start": s.start_hour, "end": s.end_hour,
                 "hours": s.hours, "color": s.color, "archived": not s.active}
                for s in shifts
            ],
            "lines": [
                {"employee_id": ln.employee_id.id, "date": fields.Date.to_string(ln.date),
                 "day_type": ln.day_type, "shift_id": ln.shift_id.id or False}
                for ln in lines
            ],
        }

    @api.model
    def clinic_schedule_set(self, employee_id, date, day_type=False, shift_id=False,
                            start=False, end=False):
        """Create / change / clear one employee-day. day_type falsy = clear.
        A shift can also be given as custom hours (start/end as floats): the
        matching template is reused or created on the fly."""
        if not self._clinic_is_admin():
            raise AccessError(_("Only a Clinic Administrator can edit schedules."))
        line = self.sudo().search([
            ("employee_id", "=", employee_id), ("date", "=", date)], limit=1)
        if not day_type:
            line.unlink()
            return True
        if fields.Date.to_date(date).weekday() in self._clinic_closed_weekdays():
            raise UserError(_("The clinic is closed on this day — nothing to schedule."))
        if day_type == "shift" and not shift_id:
            shift_id = self._clinic_custom_shift(employee_id, start, end).id
        vals = {
            "day_type": day_type,
            "shift_id": shift_id if day_type == "shift" else False,
        }
        if line:
            line.write(vals)
        else:
            self.sudo().create(dict(vals, employee_id=employee_id, date=date))
        return {"conflicts": self._clinic_visit_conflicts(employee_id, date)}

    @api.model
    def _clinic_visit_conflicts(self, employee_id, date):
        """Live visits of the doctor on that day that fall outside the (new)
        schedule — existing bookings are NOT moved, the admin is warned."""
        emp = self.env["hr.employee"].sudo().browse(employee_id)
        if emp.clinic_staff_kind != "doctor" or not emp.user_id:
            return 0
        Event = self.env["calendar.event"].sudo()
        local_date = fields.Date.to_date(date)
        win = Event._clinic_staff_window(emp.user_id, local_date)
        if win is None:
            return 0
        tz = pytz.timezone(self.env.user.tz or "Asia/Tbilisi")
        start_utc = tz.localize(datetime.combine(local_date, datetime.min.time())).astimezone(
            pytz.utc).replace(tzinfo=None)
        visits = Event.search([
            ("is_clinic", "=", True), ("dentist_id", "=", emp.user_id.id),
            ("clinic_state", "not in", ("cancelled", "no_show", "requested")),
            ("start", ">=", start_utc), ("start", "<", start_utc + timedelta(days=1)),
        ])
        count = 0
        for v in visits:
            if win is False:
                count += 1
                continue
            ls = pytz.utc.localize(v.start).astimezone(tz)
            le = pytz.utc.localize(v.stop).astimezone(tz)
            sh, eh = ls.hour + ls.minute / 60.0, le.hour + le.minute / 60.0
            if sh < win[0] - 1e-6 or eh > win[1] + 1e-6:
                count += 1
        return count

    # ---- shift templates, editable from the schedule screen (admin) ----
    @api.model
    def _clinic_next_color(self, kind):
        """First palette colour not used by an active shift of that group
        (all used -> the least used one), so every new time looks different."""
        used = self.env["clinic.shift"].sudo().search(
            [("staff_kind", "=", kind)]).mapped("color")
        for c in range(SHIFT_COLORS):
            if c not in used:
                return c
        return min(range(SHIFT_COLORS), key=used.count)

    @api.model
    def clinic_shift_save(self, kind, shift_id, start, end, color=None):
        """Add a new shift time (shift_id falsy) or change an existing one.
        A change of the HOURS applies from TODAY on: if the old shift was used
        on past days they keep it (history of worked hours stays true) and
        today/future days move to a fresh template. The colour is cosmetic and
        changes in place."""
        if not self._clinic_is_admin():
            raise AccessError(_("Only a Clinic Administrator can edit shifts."))
        if kind not in dict(STAFF_KINDS):
            raise UserError(_("Unknown staff group."))
        if start is False or end is False or not (0.0 <= start < end <= 24.0):
            raise UserError(_("Enter a start and an end time (start before end)."))
        Shift = self.env["clinic.shift"].sudo()
        same = Shift.search([
            ("staff_kind", "=", kind),
            ("start_hour", ">=", start - 0.005), ("start_hour", "<=", start + 0.005),
            ("end_hour", ">=", end - 0.005), ("end_hour", "<=", end + 0.005),
        ], limit=1)
        if color is not None and not (isinstance(color, int) and 0 <= color < SHIFT_COLORS):
            raise UserError(_("Unknown colour."))
        if not shift_id:
            if same:
                if color is not None:
                    same.color = color
                return same.id
            return Shift.create({
                "staff_kind": kind, "start_hour": start, "end_hour": end,
                "color": self._clinic_next_color(kind) if color is None else color,
                "sequence": 100,
            }).id
        shift = Shift.browse(shift_id).exists()
        if not shift or shift.staff_kind != kind:
            raise UserError(_("Shift not found."))
        if same and same != shift:
            raise UserError(_("A shift with exactly these hours already exists."))
        new_color = shift.color if color is None else color
        if abs(shift.start_hour - start) < 0.005 and abs(shift.end_hour - end) < 0.005:
            shift.color = new_color  # only the colour changed
            return shift.id
        today = fields.Date.context_today(self)
        used_in_past = self.sudo().search_count([
            ("shift_id", "=", shift.id), ("date", "<", today)])
        if not used_in_past:
            shift.write({"start_hour": start, "end_hour": end, "color": new_color})
            return shift.id
        new = Shift.create({
            "staff_kind": kind, "start_hour": start, "end_hour": end,
            "color": new_color, "sequence": shift.sequence,
        })
        self.sudo().search([("shift_id", "=", shift.id), ("date", ">=", today)]).write(
            {"shift_id": new.id})
        shift.active = False
        return new.id

    @api.model
    def clinic_shift_delete(self, shift_id):
        if not self._clinic_is_admin():
            raise AccessError(_("Only a Clinic Administrator can edit shifts."))
        shift = self.env["clinic.shift"].sudo().browse(shift_id).exists()
        if not shift:
            return True
        today = fields.Date.context_today(self)
        if self.sudo().search_count([("shift_id", "=", shift.id), ("date", ">=", today)]):
            raise UserError(_(
                "This shift is used from today on — clear those days first."))
        if self.sudo().search_count([("shift_id", "=", shift.id)]):
            shift.active = False  # past days keep their hours
        else:
            shift.unlink()
        return True

    @api.model
    def _clinic_custom_shift(self, employee_id, start, end):
        if start is False or end is False or not (0.0 <= start < end <= 24.0):
            raise UserError(_("Enter a start and an end time (start before end)."))
        kind = self.env["hr.employee"].sudo().browse(employee_id).clinic_staff_kind
        Shift = self.env["clinic.shift"].sudo()
        shift = Shift.search([
            ("staff_kind", "=", kind),
            ("start_hour", ">=", start - 0.005), ("start_hour", "<=", start + 0.005),
            ("end_hour", ">=", end - 0.005), ("end_hour", "<=", end + 0.005),
        ], limit=1)
        if not shift:
            shift = Shift.create({
                "staff_kind": kind, "start_hour": start, "end_hour": end,
                "color": self._clinic_next_color(kind),
                "sequence": 100,
            })
        return shift

    # ------------------------------------------------------------------
    # "ნამუშევარი საათები": plan (schedule) vs fact (hr_attendance)
    # ------------------------------------------------------------------
    @api.model
    def clinic_hours_data(self, kind, date_from, date_to, mode="week"):
        is_admin = self._clinic_is_admin()
        kind = self._clinic_resolve_kind(kind, is_admin)
        Employee = self.env["hr.employee"].sudo()
        all_staff = Employee.search([("clinic_staff_kind", "!=", False)])
        counts = {k: 0 for k, _l in STAFF_KINDS}
        for e in all_staff:
            counts[e.clinic_staff_kind] += 1
        emps = all_staff.filtered(lambda e: e.clinic_staff_kind == kind)
        if not is_admin:
            emps = emps.filtered(lambda e: e.user_id == self.env.user)
        emps = emps.sorted("name")

        tz = pytz.timezone(self.env.user.tz or "Asia/Tbilisi")
        d_from = fields.Date.to_date(date_from)
        d_to = fields.Date.to_date(date_to)

        def to_utc(d):
            local = tz.localize(datetime.combine(d, datetime.min.time()))
            return local.astimezone(pytz.utc).replace(tzinfo=None)

        utc_from, utc_to = to_utc(d_from), to_utc(d_to + timedelta(days=1))
        now_utc = fields.Datetime.now()
        today = fields.Date.context_today(self)

        lines = self.sudo().search([
            ("employee_id", "in", emps.ids), ("date", ">=", d_from), ("date", "<=", d_to)])
        atts = self.env["hr.attendance"].sudo().search([
            ("employee_id", "in", emps.ids),
            ("check_in", ">=", utc_from), ("check_in", "<", utc_to)])

        plan, day_types = {}, {}
        for ln in lines:
            key = (ln.employee_id.id, ln.date)
            if ln.day_type == "shift" and ln.shift_id:
                plan[key] = (ln.shift_id.hours, ln.shift_id.start_hour)
            day_types.setdefault(ln.employee_id.id, {}).setdefault(ln.day_type, 0)
            day_types[ln.employee_id.id][ln.day_type] += 1

        worked, first_in, last_out = {}, {}, {}
        for a in atts:
            local_in = pytz.utc.localize(a.check_in).astimezone(tz)
            key = (a.employee_id.id, local_in.date())
            end = a.check_out or min(now_utc, a.check_in + timedelta(hours=16))
            worked[key] = worked.get(key, 0.0) + max((end - a.check_in).total_seconds() / 3600.0, 0.0)
            first_in[key] = min(first_in.get(key, 99.0), local_in.hour + local_in.minute / 60.0)
            if a.check_out:
                lo = pytz.utc.localize(a.check_out).astimezone(tz)
                last_out[key] = max(last_out.get(key, 0.0), lo.hour + lo.minute / 60.0)

        dates, d = [], d_from
        while d <= d_to:
            dates.append(d)
            d += timedelta(days=1)

        rows = []
        for e in emps:
            planned = planned_td = wk = overtime = 0.0
            late_min = late_days = absent = 0
            for d in dates:
                key = (e.id, d)
                p_h, p_start = plan.get(key, (0.0, 0.0))
                w_h = worked.get(key, 0.0)
                planned += p_h
                wk += w_h
                if d <= today:
                    planned_td += p_h
                    overtime += max(w_h - p_h, 0.0)
                    if p_h and key in first_in:
                        late = first_in[key] - p_start
                        if late > LATE_GRACE_H:
                            late_min += int(round(late * 60))
                            late_days += 1
                    if p_h and d < today and w_h == 0.0:
                        absent += 1
            dt = day_types.get(e.id, {})
            day_key = (e.id, d_from)
            rows.append({
                "id": e.id, "name": e.name, "job": e.job_title or "",
                "planned": round(planned, 2), "planned_to_date": round(planned_td, 2),
                "worked": round(wk, 2), "diff": round(wk - planned_td, 2),
                "overtime": round(overtime, 2),
                "late_minutes": late_min, "late_days": late_days, "absent_days": absent,
                "vacation": dt.get("vacation", 0), "sick": dt.get("sick", 0), "off": dt.get("off", 0),
                "pct": round(wk / planned_td * 100) if planned_td else None,
                "first_in": _fmt_hour(first_in[day_key]) if mode == "day" and day_key in first_in else "",
                "last_out": _fmt_hour(last_out[day_key]) if mode == "day" and day_key in last_out else "",
            })

        # chart buckets (aggregated over the listed employees)
        chunks = []
        if mode in ("day", "week"):
            chunks = [(d, d, WD_KA[d.weekday()] + " " + str(d.day)) for d in dates]
        elif mode == "month":
            start = d_from
            while start <= d_to:
                end = min(start + timedelta(days=6 - start.weekday()), d_to)
                chunks.append((start, end, "%d–%d" % (start.day, end.day)))
                start = end + timedelta(days=1)
        else:  # year
            for m in range(1, 13):
                first = d_from.replace(month=m, day=1)
                last = (first.replace(year=first.year + 1, month=1, day=1) if m == 12
                        else first.replace(month=m + 1, day=1)) - timedelta(days=1)
                chunks.append((first, min(last, d_to), MONTHS_KA[m - 1][:3]))
        buckets = []
        for c_from, c_to, label in chunks:
            b_plan = b_work = 0.0
            for e in emps:
                d = c_from
                while d <= c_to:
                    b_plan += plan.get((e.id, d), (0.0, 0.0))[0]
                    b_work += worked.get((e.id, d), 0.0)
                    d += timedelta(days=1)
            buckets.append({"label": label, "from": fields.Date.to_string(c_from),
                            "planned": round(b_plan, 2), "worked": round(b_work, 2)})

        totals = {k: round(sum(r[k] for r in rows), 2) for k in (
            "planned", "planned_to_date", "worked", "diff", "overtime")}
        totals.update({k: sum(r[k] for r in rows) for k in (
            "late_minutes", "late_days", "absent_days", "vacation", "sick", "off")})
        return {
            "kind": kind,
            "visible_kinds": [k for k, _l in STAFF_KINDS] if is_admin else [kind],
            "is_admin": is_admin, "counts": counts, "rows": rows,
            "totals": totals, "buckets": buckets,
            "closed_weekdays": self._clinic_closed_weekdays(),
        }


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
