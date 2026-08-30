/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { deserializeDateTime } from "@web/core/l10n/dates";

// Palette indexed by clinic.appointment.type.color (0..11).
const COLORS = [
    "#6c8ebf", "#43a047", "#f4a63b", "#8e6fb0", "#e05a5a", "#00acc1",
    "#ec6f9e", "#c0a000", "#7e57c2", "#26a69a", "#78909c", "#5c6bc0",
];
const MONTHS = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];
const DOW = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
// Default working window; the board auto-expands it to fit early/late visits.
const DEFAULT_START_HOUR = 8;
const DEFAULT_END_HOUR = 18;
const MIN_HOUR = 0;
const MAX_HOUR = 24;
// 96px/hour so a 10-minute slot (the booking grain) is a workable 16px.
const HOUR_PX = 96;

export class ClinicPlanning extends Component {
    static template = "clinic_patient_card.ClinicPlanning";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.COLORS = COLORS;
        this.DOW = DOW;
        this.state = useState({
            date: this._todayStr(),
            dentists: [],
            events: [],
            types: [],
            typeMap: {},
            rooms: [],
            roomOff: {},          // {roomId: true} when unchecked
            dentistFilter: false, // false = all
            stateLabels: {},      // clinic_state value -> translated label
            startHour: DEFAULT_START_HOUR, // dynamic window, fitted to the day's visits
            endHour: DEFAULT_END_HOUR,
            config: null,         // clinic working schedule (grey out closed time)
            waitlist: [],         // reserve entries (clinic_state=requested)
            waitlistOpen: false,
        });
        onWillStart(() => this.load());
    }

    // ---- date helpers (local, no UTC drift) ----
    _iso(d) {
        const off = d.getTimezoneOffset() * 60000;
        return new Date(d - off).toISOString().slice(0, 10);
    }
    _todayStr() {
        return this._iso(new Date());
    }
    get totalHeight() {
        return (this.state.endHour - this.state.startHour) * HOUR_PX;
    }
    get monthLabel() {
        const d = new Date(this.state.date + "T00:00:00");
        return `${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
    }
    get dateLabel() {
        const d = new Date(this.state.date + "T00:00:00");
        return `${MONTHS[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
    }

    hours() {
        const out = [];
        for (let h = this.state.startHour; h <= this.state.endHour; h++) {
            out.push(h);
        }
        return out;
    }

    calendarWeeks() {
        const sel = new Date(this.state.date + "T00:00:00");
        const y = sel.getFullYear(), m = sel.getMonth();
        const start = new Date(y, m, 1);
        start.setDate(1 - start.getDay());
        const today = this._todayStr();
        const weeks = [];
        for (let w = 0; w < 6; w++) {
            const week = [];
            for (let i = 0; i < 7; i++) {
                const cur = new Date(start);
                cur.setDate(start.getDate() + w * 7 + i);
                const iso = this._iso(cur);
                week.push({
                    day: cur.getDate(),
                    iso,
                    inMonth: cur.getMonth() === m,
                    isToday: iso === today,
                    isSelected: iso === this.state.date,
                });
            }
            weeks.push(week);
        }
        return weeks;
    }

    async load() {
        const d = new Date(this.state.date + "T00:00:00");
        const prev = new Date(d); prev.setDate(prev.getDate() - 1);
        const next = new Date(d); next.setDate(next.getDate() + 1);
        const from = this._iso(prev) + " 00:00:00";
        const to = this._iso(next) + " 23:59:59";

        const [events, types, rooms, fg, dentists, config, waitlist] = await Promise.all([
            this.orm.searchRead("calendar.event",
                [["is_clinic", "=", true], ["clinic_state", "!=", "requested"],
                 ["start", ">=", from], ["start", "<=", to]],
                ["name", "start", "stop", "dentist_id", "room_id", "appointment_type_id",
                 "patient_id", "clinic_state", "was_rescheduled", "duration_edited",
                 "is_dispensary"]),
            this.orm.searchRead("clinic.appointment.type", [], ["name", "color"]),
            this.orm.searchRead("clinic.room", [], ["name"]),
            this.orm.call("calendar.event", "fields_get", [["clinic_state"], ["selection"]]),
            this.orm.call("res.users", "clinic_dentists", []),
            this.orm.call("calendar.event", "clinic_board_config", []),
            // reserve list: upcoming requested visits waiting for confirmation
            this.orm.searchRead("calendar.event",
                [["is_clinic", "=", true], ["clinic_state", "=", "requested"],
                 ["start", ">=", this._todayStr() + " 00:00:00"]],
                ["name", "start", "patient_id", "dentist_id", "is_dispensary"],
                { order: "start asc", limit: 80 }),
        ]);
        this.state.config = config;
        this.state.waitlist = waitlist;
        this.state.stateLabels = Object.fromEntries(
            (fg.clinic_state && fg.clinic_state.selection) || []
        );

        const typeMap = {};
        for (const t of types) {
            typeMap[t.id] = t;
        }
        const dayEvents = events.filter(
            (e) => deserializeDateTime(e.start).toFormat("yyyy-LL-dd") === this.state.date
        );
        // Fit the time window to the day's visits so early/late appointments
        // are never clipped: expand the default 08–18 window down/up to cover
        // the earliest start and latest stop, clamped to [0, 24].
        let startH = DEFAULT_START_HOUR;
        let endH = DEFAULT_END_HOUR;
        for (const e of dayEvents) {
            const s = Math.floor(this._hourOf(e.start));
            const en = Math.ceil(this._hourOf(e.stop));
            if (s < startH) startH = s;
            if (en > endH) endH = en;
        }
        this.state.startHour = Math.max(MIN_HOUR, startH);
        this.state.endHour = Math.min(MAX_HOUR, Math.max(endH, this.state.startHour + 1));
        // dentist columns: always show every clinic dentist (so an empty day
        // still has clickable columns), keeping the room seen in that day's
        // events when there is one.
        const dmap = new Map();
        for (const u of dentists || []) {
            dmap.set(u.id, { id: u.id, name: u.name, room: "" });
        }
        for (const e of dayEvents) {
            if (e.dentist_id) {
                const existing = dmap.get(e.dentist_id[0]) || {
                    id: e.dentist_id[0], name: e.dentist_id[1], room: "",
                };
                if (!existing.room && e.room_id) {
                    existing.room = e.room_id[1];
                }
                dmap.set(e.dentist_id[0], existing);
            }
        }
        this.state.events = dayEvents;
        this.state.types = types;
        this.state.typeMap = typeMap;
        this.state.rooms = rooms;
        this.state.dentists = [...dmap.values()];
    }

    get shownDentists() {
        if (this.state.dentistFilter) {
            return this.state.dentists.filter((d) => d.id === this.state.dentistFilter);
        }
        return this.state.dentists;
    }

    eventsFor(dentistId) {
        return this.state.events.filter((e) => {
            if (!e.dentist_id || e.dentist_id[0] !== dentistId) {
                return false;
            }
            if (e.room_id && this.state.roomOff[e.room_id[0]]) {
                return false;
            }
            return true;
        });
    }

    _colorHex(ev) {
        const t = ev.appointment_type_id && this.state.typeMap[ev.appointment_type_id[0]];
        const idx = t ? ((t.color || 0) % COLORS.length + COLORS.length) % COLORS.length : 10;
        return COLORS[idx];
    }
    _hourOf(dtStr) {
        const dt = deserializeDateTime(dtStr);
        return dt.hour + dt.minute / 60;
    }
    eventStyle(ev) {
        const s = this._hourOf(ev.start);
        const e = this._hourOf(ev.stop);
        const top = Math.max(0, (s - this.state.startHour) * HOUR_PX);
        const height = Math.max(30, (e - s) * HOUR_PX - 3);
        const hex = this._colorHex(ev);
        return `top:${top}px;height:${height}px;background:${hex}1f;border-left:3px solid ${hex};`;
    }
    evTime(ev) {
        return `${deserializeDateTime(ev.start).toFormat("HH:mm")} – ${deserializeDateTime(ev.stop).toFormat("HH:mm")}`;
    }
    patientName(ev) {
        return ev.patient_id ? ev.patient_id[1] : "";
    }
    stateLabel(ev) {
        return this.state.stateLabels[ev.clinic_state] || ev.clinic_state || "";
    }
    stateClass(ev) {
        const s = ev.clinic_state;
        // Reviewer: "Paid" and "Done" must be distinguishable at a glance.
        if (s === "paid") return "cp_st_paid";
        if (s === "done") return "cp_st_done";
        if (s === "in_progress") return "cp_st_prog";
        if (s === "arrived" || s === "confirmed") return "cp_st_arr";
        if (s === "cancelled" || s === "no_show") return "cp_st_cancel";
        return "cp_st_booked";
    }
    edited(ev) {
        // Reviewer: a corrected time/duration must stay visible on the calendar.
        return ev.was_rescheduled || ev.duration_edited;
    }
    typeName(ev) {
        return ev.appointment_type_id ? ev.appointment_type_id[1] : "";
    }

    // ---- working-schedule shading (reviewer: lock non-working time) ----
    _dateWeekday() {
        // 0=Mon .. 6=Sun, matching the backend convention.
        return (new Date(this.state.date + "T00:00:00").getDay() + 6) % 7;
    }
    get closedDay() {
        const c = this.state.config;
        return !!(c && c.workdays.length && !c.workdays.includes(this._dateWeekday()));
    }
    get offZones() {
        // Grey blocks (px) inside the rendered window for closed time.
        const c = this.state.config;
        if (!c) {
            return [];
        }
        if (this.closedDay) {
            return [{ top: 0, height: this.totalHeight }];
        }
        const zones = [];
        if (c.work_start > this.state.startHour) {
            zones.push({
                top: 0,
                height: (Math.min(c.work_start, this.state.endHour) - this.state.startHour) * HOUR_PX,
            });
        }
        if (c.work_end < this.state.endHour) {
            const top = (Math.max(c.work_end, this.state.startHour) - this.state.startHour) * HOUR_PX;
            zones.push({ top, height: this.totalHeight - top });
        }
        return zones;
    }
    _isWorkTime(hour) {
        const c = this.state.config;
        if (!c) {
            return true;
        }
        return !this.closedDay && hour >= c.work_start - 1e-6 && hour < c.work_end - 1e-6;
    }

    openHistory() {
        this.action.doAction("clinic_patient_card.action_clinic_visit_history");
    }
    openCancelled() {
        this.action.doAction("clinic_patient_card.action_clinic_visit_cancelled");
    }

    // ---- waitlist / reserve panel (dispensary + pending requests) ----
    get shownWaitlist() {
        let list = this.state.waitlist;
        if (this.state.dentistFilter) {
            list = list.filter((w) => w.dentist_id && w.dentist_id[0] === this.state.dentistFilter);
        }
        return list;
    }
    toggleWaitlist() {
        this.state.waitlistOpen = !this.state.waitlistOpen;
    }
    wlWhen(w) {
        return w.start ? deserializeDateTime(w.start).toFormat("dd.LL HH:mm") : "";
    }
    async confirmWait(w) {
        await this.orm.call("calendar.event", "action_book", [[w.id]]);
        await this.load();
    }

    get nowTop() {
        if (this.state.date !== this._todayStr()) {
            return -1;
        }
        const now = new Date();
        const h = now.getHours() + now.getMinutes() / 60;
        if (h < this.state.startHour || h > this.state.endHour) {
            return -1;
        }
        return (h - this.state.startHour) * HOUR_PX;
    }

    // ---- interactions ----
    selectDay(iso) {
        this.state.date = iso;
        this.load();
    }
    changeDay(delta) {
        const d = new Date(this.state.date + "T00:00:00");
        d.setDate(d.getDate() + delta);
        this.state.date = this._iso(d);
        this.load();
    }
    changeMonth(delta) {
        const d = new Date(this.state.date + "T00:00:00");
        d.setMonth(d.getMonth() + delta);
        this.state.date = this._iso(d);
        this.load();
    }
    setToday() {
        this.state.date = this._todayStr();
        this.load();
    }
    onDateInput(ev) {
        this.state.date = ev.target.value;
        this.load();
    }
    onDentistFilter(ev) {
        const v = ev.target.value;
        this.state.dentistFilter = v === "all" ? false : parseInt(v, 10);
    }
    toggleRoom(roomId) {
        this.state.roomOff[roomId] = !this.state.roomOff[roomId];
    }
    openEvent(ev) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "calendar.event",
            res_id: ev.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
    newAppointment() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "calendar.event",
            views: [[false, "form"]],
            target: "current",
            context: { default_is_clinic: true },
        });
    }

    // Click an empty area of a dentist's column -> new visit at that time.
    onSlotClick(dentist, ev) {
        // ignore clicks that landed on an existing event card
        if (ev.target.closest(".cp_event")) {
            return;
        }
        const rect = ev.currentTarget.getBoundingClientRect();
        const y = ev.clientY - rect.top;
        let hour = this.state.startHour + y / HOUR_PX;
        // snap to the nearest 10 minutes (reviewer: 10-minute grid)
        hour = Math.round(hour * 6) / 6;
        hour = Math.min(this.state.endHour - 0.5, Math.max(this.state.startHour, hour));
        // closed time is not clickable
        if (!this._isWorkTime(hour)) {
            return;
        }
        // quick visual feedback: a ripple + a ghost slot where we clicked
        this._flashSlot(ev.currentTarget, ev.clientX - rect.left, y);
        const h = Math.floor(hour);
        const m = Math.round((hour - h) * 60);
        const pad = (n) => (n < 10 ? "0" + n : "" + n);
        // naive local datetime string; the form widget interprets it in tz
        const start = `${this.state.date} ${pad(h)}:${pad(m)}:00`;
        const endHour = Math.min(this.state.endHour, hour + 0.5);
        const eh = Math.floor(endHour);
        const em = Math.round((endHour - eh) * 60);
        const stop = `${this.state.date} ${pad(eh)}:${pad(em)}:00`;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "calendar.event",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_is_clinic: true,
                default_dentist_id: dentist.id,
                default_user_id: dentist.id,
                default_start: start,
                default_stop: stop,
            },
        });
    }

    // Transient click feedback inside a column: a ripple at the pointer plus a
    // half-hour "ghost" block snapped to the slot, both auto-removed.
    _flashSlot(col, x, y) {
        // ghost snapped to the same 10-minute grid as the click
        const snappedTop = Math.round((y / HOUR_PX) * 6) / 6 * HOUR_PX;

        const ghost = document.createElement("div");
        ghost.className = "cp_ghost";
        ghost.style.top = `${Math.max(0, snappedTop)}px`;
        ghost.style.height = `${HOUR_PX / 2 - 2}px`;
        col.appendChild(ghost);

        const ripple = document.createElement("span");
        ripple.className = "cp_ripple";
        ripple.style.left = `${x}px`;
        ripple.style.top = `${y}px`;
        col.appendChild(ripple);

        setTimeout(() => {
            ghost.remove();
            ripple.remove();
        }, 450);
    }
}

registry.category("actions").add("clinic_planning", ClinicPlanning);
