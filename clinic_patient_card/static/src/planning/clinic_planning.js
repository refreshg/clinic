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
const START_HOUR = 8;
const END_HOUR = 18;
const HOUR_PX = 64;

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
        return (END_HOUR - START_HOUR) * HOUR_PX;
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
        for (let h = START_HOUR; h <= END_HOUR; h++) {
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

        const [events, types, rooms, fg] = await Promise.all([
            this.orm.searchRead("calendar.event",
                [["is_clinic", "=", true], ["start", ">=", from], ["start", "<=", to]],
                ["name", "start", "stop", "dentist_id", "room_id", "appointment_type_id", "patient_id", "clinic_state"]),
            this.orm.searchRead("clinic.appointment.type", [], ["name", "color"]),
            this.orm.searchRead("clinic.room", [], ["name"]),
            this.orm.call("calendar.event", "fields_get", [["clinic_state"], ["selection"]]),
        ]);
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
        // dentist columns (with the room they work in that day)
        const dmap = new Map();
        for (const e of dayEvents) {
            if (e.dentist_id && !dmap.has(e.dentist_id[0])) {
                dmap.set(e.dentist_id[0], {
                    id: e.dentist_id[0],
                    name: e.dentist_id[1],
                    room: e.room_id ? e.room_id[1] : "",
                });
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
        const top = Math.max(0, (s - START_HOUR) * HOUR_PX);
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
        if (s === "paid" || s === "done") return "cp_st_done";
        if (s === "in_progress") return "cp_st_prog";
        if (s === "arrived" || s === "confirmed") return "cp_st_arr";
        if (s === "cancelled" || s === "no_show") return "cp_st_cancel";
        return "cp_st_booked";
    }

    get nowTop() {
        if (this.state.date !== this._todayStr()) {
            return -1;
        }
        const now = new Date();
        const h = now.getHours() + now.getMinutes() / 60;
        if (h < START_HOUR || h > END_HOUR) {
            return -1;
        }
        return (h - START_HOUR) * HOUR_PX;
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
}

registry.category("actions").add("clinic_planning", ClinicPlanning);
