/** @odoo-module **/
// Staff schedule screen (client action `clinic_schedule`).
// Two interchangeable looks over the same data:
//   "grid"   — hour grid, days as columns, shifts as coloured blocks
//   "matrix" — one row per employee, one coloured cell per day
// Modes: day / week / month (month is always the matrix). Administrators click a
// cell / block to assign a shift, a day off, vacation or sick leave.
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const WD = ["ორშ", "სამ", "ოთხ", "ხუთ", "პარ", "შაბ", "კვი"];
const WD_FULL = ["ორშაბათი", "სამშაბათი", "ოთხშაბათი", "ხუთშაბათი", "პარასკევი", "შაბათი", "კვირა"];
const MONTHS = ["იანვარი", "თებერვალი", "მარტი", "აპრილი", "მაისი", "ივნისი",
    "ივლისი", "აგვისტო", "სექტემბერი", "ოქტომბერი", "ნოემბერი", "დეკემბერი"];
const KINDS = [
    { key: "doctor", label: "ექიმები" },
    { key: "assistant", label: "ასისტენტები" },
    { key: "admin", label: "ადმინისტრაცია" },
];
const DAY_TYPES = [
    { key: "off", label: "დასვენება", icon: "🌙" },
    { key: "vacation", label: "შვებულება", icon: "☀" },
    { key: "sick", label: "ბიულეტენი", icon: "✚" },
];
const HOUR_PX = 36;
const PALETTE = Array.from({ length: 12 }, (_v, i) => i); // classes cs_c0 .. cs_c11

function iso(d) {
    const off = d.getTimezoneOffset() * 60000;
    return new Date(d - off).toISOString().slice(0, 10);
}
function parse(s) {
    return new Date(s + "T00:00:00");
}
function addDays(s, n) {
    const d = parse(s);
    d.setDate(d.getDate() + n);
    return iso(d);
}
function fmtHour(v) {
    const h = Math.floor(v);
    const m = Math.round((v - h) * 60);
    return String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0");
}

export class ClinicSchedule extends Component {
    static template = "clinic_patient_card.ClinicSchedule";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.KINDS = KINDS;
        this.DAY_TYPES = DAY_TYPES;
        this.PALETTE = PALETTE;
        this.state = useState({
            kind: false, // the server picks the user's own group on first load
            mode: "week",
            view: "matrix",
            anchor: iso(new Date()),
            loading: true,
            data: { employees: [], shifts: [], lines: [], counts: {}, is_admin: false,
                    closed_weekdays: [], visible_kinds: [] },
            pop: null, // {empId, date, x, y}
            custom: { start: "09:00", end: "18:00" },
            editShift: null, // {id (0 = new), start, end} — the sidebar "სამუშაო დრო" editor
        });
        this.lineMap = {};
        this.shiftMap = {};
        onWillStart(() => this.load());
    }

    get activeShifts() {
        return this.state.data.shifts.filter((s) => !s.archived);
    }

    // ---- shift templates (sidebar editor, administrators) ----
    _toHHMM(v) {
        return fmtHour(v);
    }
    startEditShift(s) {
        this.state.editShift = {
            id: s.id, start: this._toHHMM(s.start), end: this._toHHMM(s.end), color: s.color,
        };
    }
    startNewShift() {
        // pre-select the first colour no shift of this group uses yet
        const used = this.activeShifts.map((s) => s.color);
        const free = PALETTE.find((c) => !used.includes(c));
        this.state.editShift = { id: 0, start: "09:00", end: "18:00", color: free === undefined ? 0 : free };
    }
    pickShiftColor(c) {
        this.state.editShift.color = c;
    }
    cancelEditShift() {
        this.state.editShift = null;
    }
    get editShiftInvalid() {
        const e = this.state.editShift;
        if (!e) {
            return true;
        }
        const s = this._hhmm(e.start);
        const t = this._hhmm(e.end);
        return s === false || t === false || t <= s;
    }
    async saveShift() {
        const e = this.state.editShift;
        if (this.editShiftInvalid) {
            return;
        }
        await this.orm.call("clinic.schedule.line", "clinic_shift_save",
            [this.state.kind, e.id, this._hhmm(e.start), this._hhmm(e.end), e.color]);
        this.state.editShift = null;
        await this.load();
        this.notification.add(
            e.id ? "ცვლის საათები შეიცვალა — ცვლილება ვრცელდება დღევანდლიდან, წარსული დღეები უცვლელია."
                 : "ახალი დრო დაემატა.",
            { type: "success" });
    }
    async deleteShift(s) {
        if (!window.confirm("წაიშალოს ცვლა " + s.name + "?")) {
            return;
        }
        await this.orm.call("clinic.schedule.line", "clinic_shift_delete", [s.id]);
        this.state.editShift = null;
        await this.load();
    }

    get visibleKinds() {
        const ok = this.state.data.visible_kinds;
        return KINDS.filter((k) => ok.includes(k.key));
    }

    // ---- range ----
    get range() {
        const { mode, anchor } = this.state;
        let from, to;
        if (mode === "day") {
            from = to = anchor;
        } else if (mode === "week") {
            const wd = (parse(anchor).getDay() + 6) % 7;
            from = addDays(anchor, -wd);
            to = addDays(from, 6);
        } else {
            const d = parse(anchor);
            from = iso(new Date(d.getFullYear(), d.getMonth(), 1));
            to = iso(new Date(d.getFullYear(), d.getMonth() + 1, 0));
        }
        const dates = [];
        for (let s = from; s <= to; s = addDays(s, 1)) {
            dates.push(s);
        }
        return { from, to, dates };
    }
    get effView() {
        return this.state.mode === "month" ? "matrix" : this.state.view;
    }
    get rangeLabel() {
        const { from, to } = this.range;
        const a = parse(from);
        const b = parse(to);
        if (this.state.mode === "month") {
            return MONTHS[a.getMonth()] + " " + a.getFullYear();
        }
        if (this.state.mode === "day") {
            return a.getDate() + " " + MONTHS[a.getMonth()] + ", " + WD_FULL[(a.getDay() + 6) % 7];
        }
        return a.getDate() + " " + MONTHS[a.getMonth()] + " – " + b.getDate() + " "
            + MONTHS[b.getMonth()] + " " + b.getFullYear();
    }

    // ---- data ----
    async load() {
        this.state.loading = true;
        const { from, to } = this.range;
        const data = await this.orm.call("clinic.schedule.line", "clinic_schedule_data",
            [this.state.kind, from, to]);
        this.state.data = data;
        this.state.kind = data.kind;
        this.lineMap = {};
        for (const ln of data.lines) {
            this.lineMap[ln.employee_id + "|" + ln.date] = ln;
        }
        this.shiftMap = {};
        for (const s of data.shifts) {
            this.shiftMap[s.id] = s;
        }
        this.state.loading = false;
    }
    setKind(k) {
        this.state.kind = k;
        this.state.pop = null;
        this.load();
    }
    setMode(m) {
        this.state.mode = m;
        this.state.pop = null;
        this.load();
    }
    setView(v) {
        this.state.view = v;
        this.state.pop = null;
    }
    today() {
        this.state.anchor = iso(new Date());
        this.load();
    }
    step(dir) {
        const { mode, anchor } = this.state;
        if (mode === "day") {
            this.state.anchor = addDays(anchor, dir);
        } else if (mode === "week") {
            this.state.anchor = addDays(anchor, 7 * dir);
        } else {
            const d = parse(anchor);
            this.state.anchor = iso(new Date(d.getFullYear(), d.getMonth() + dir, 1));
        }
        this.state.pop = null;
        this.load();
    }

    // ---- cell helpers ----
    lineOf(empId, date) {
        return this.lineMap[empId + "|" + date];
    }
    shiftOf(line) {
        return line && line.shift_id ? this.shiftMap[line.shift_id] : null;
    }
    cellClass(empId, date) {
        const ln = this.lineOf(empId, date);
        if (!ln) {
            return "cs_empty";
        }
        if (ln.day_type === "shift") {
            const s = this.shiftOf(ln);
            return "cs_shift cs_c" + (s ? s.color : 0);
        }
        return "cs_type cs_" + ln.day_type;
    }
    cellText(empId, date) {
        const ln = this.lineOf(empId, date);
        if (!ln) {
            return "";
        }
        if (ln.day_type === "shift") {
            const s = this.shiftOf(ln);
            return s ? s.name : "";
        }
        const t = DAY_TYPES.find((x) => x.key === ln.day_type);
        return t ? t.icon + " " + t.label : "";
    }
    hoursOf(empId) {
        let total = 0;
        for (const date of this.range.dates) {
            const ln = this.lineOf(empId, date);
            const s = this.shiftOf(ln);
            if (s) {
                total += s.hours;
            }
        }
        return Math.round(total * 10) / 10;
    }
    dayCaption(date) {
        const d = parse(date);
        return WD[(d.getDay() + 6) % 7] + " " + d.getDate();
    }
    dayCaptionFull(date) {
        const d = parse(date);
        return WD_FULL[(d.getDay() + 6) % 7] + ", " + d.getDate();
    }
    isClosed(date) {
        return this.state.data.closed_weekdays.includes((parse(date).getDay() + 6) % 7);
    }
    isToday(date) {
        return date === iso(new Date());
    }
    staffOnDay(date) {
        return this.state.data.lines.filter(
            (l) => l.date === date && l.day_type === "shift").length;
    }

    // ---- hour grid ----
    get gridStart() {
        const sh = this.state.data.shifts;
        return sh.length ? Math.floor(Math.min(...sh.map((s) => s.start))) : 9;
    }
    get gridEnd() {
        const sh = this.state.data.shifts;
        return sh.length ? Math.ceil(Math.max(...sh.map((s) => s.end))) : 20;
    }
    get gridHours() {
        const out = [];
        for (let h = this.gridStart; h <= this.gridEnd; h++) {
            out.push(h);
        }
        return out;
    }
    get gridHeight() {
        return (this.gridEnd - this.gridStart) * HOUR_PX;
    }
    hourLabel(h) {
        return fmtHour(h);
    }
    blocksOf(date) {
        const lines = this.state.data.lines.filter(
            (l) => l.date === date && l.day_type === "shift" && this.shiftMap[l.shift_id]);
        const n = lines.length || 1;
        const emp = {};
        for (const e of this.state.data.employees) {
            emp[e.id] = e;
        }
        return lines.map((l, i) => {
            const s = this.shiftMap[l.shift_id];
            const e = emp[l.employee_id];
            return {
                key: l.employee_id + "|" + date,
                empId: l.employee_id,
                name: e ? e.name : "",
                time: s.name,
                color: s.color,
                style: "top:" + ((s.start - this.gridStart) * HOUR_PX) + "px;height:"
                    + ((s.end - s.start) * HOUR_PX - 3) + "px;left:" + (i * 100 / n)
                    + "%;width:calc(" + (100 / n) + "% - 4px);",
            };
        });
    }
    chipsOf(date) {
        const emp = {};
        for (const e of this.state.data.employees) {
            emp[e.id] = e;
        }
        return this.state.data.lines
            .filter((l) => l.date === date && l.day_type !== "shift")
            .map((l) => {
                const t = DAY_TYPES.find((x) => x.key === l.day_type);
                return {
                    key: l.employee_id + "|" + date,
                    empId: l.employee_id,
                    cls: "cs_type cs_" + l.day_type,
                    text: (t ? t.icon + " " + t.label : "") + " · " + (emp[l.employee_id] ? emp[l.employee_id].name : ""),
                };
            });
    }

    // ---- editing (administrators) ----
    openPop(ev, empId, date) {
        if (!this.state.data.is_admin || this.isClosed(date)) {
            return;
        }
        ev.stopPropagation();
        const r = ev.currentTarget.getBoundingClientRect();
        this.state.pop = {
            empId, date,
            x: Math.min(r.left, window.innerWidth - 270),
            y: Math.min(r.bottom + 4, window.innerHeight - 330),
        };
    }
    openAdd(ev, date) {
        this.openPop(ev, 0, date);
    }
    // toolbar "＋ დამატება": pick the employee and the date inside the popover
    openToolbarAdd(ev) {
        ev.stopPropagation();
        const r = ev.currentTarget.getBoundingClientRect();
        this.state.pop = {
            empId: 0,
            date: this.state.anchor,
            x: Math.max(Math.min(r.left, window.innerWidth - 270), 8),
            y: Math.min(r.bottom + 4, window.innerHeight - 380),
        };
    }
    closePop() {
        this.state.pop = null;
    }
    get popEmployeeName() {
        const p = this.state.pop;
        const e = p && this.state.data.employees.find((x) => x.id === p.empId);
        return e ? e.name : "";
    }
    get popDateLabel() {
        return this.state.pop ? this.dayCaptionFull(this.state.pop.date) : "";
    }
    pickEmployee(empId) {
        this.state.pop.empId = empId;
    }
    async choose(dayType, shiftId, start, end) {
        const p = this.state.pop;
        const res = await this.orm.call("clinic.schedule.line", "clinic_schedule_set",
            [p.empId, p.date, dayType || false, shiftId || false, start || false, end || false]);
        this.state.pop = null;
        await this.load();
        if (res && res.conflicts) {
            this.notification.add(
                res.conflicts + " უკვე დაჯავშნილი ვიზიტი ექცევა ახალი გრაფიკის გარეთ — "
                + "გადაამოწმეთ და საჭიროების შემთხვევაში გადაიტანეთ.",
                { type: "warning", sticky: true });
        }
    }
    _hhmm(value) {
        const [h, m] = (value || "").split(":").map(Number);
        return Number.isNaN(h) || Number.isNaN(m) ? false : Math.round((h + m / 60) * 100) / 100;
    }
    async chooseCustom() {
        const start = this._hhmm(this.state.custom.start);
        const end = this._hhmm(this.state.custom.end);
        if (start === false || end === false || end <= start) {
            return; // the inputs show the problem; nothing sent
        }
        await this.choose("shift", false, start, end);
    }
    get customInvalid() {
        const s = this._hhmm(this.state.custom.start);
        const e = this._hhmm(this.state.custom.end);
        return s === false || e === false || e <= s;
    }
}

registry.category("actions").add("clinic_schedule", ClinicSchedule);
