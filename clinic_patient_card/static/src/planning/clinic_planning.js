/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { deserializeDateTime } from "@web/core/l10n/dates";

// Odoo-ish calendar palette (index = appointment_type.color 0..11).
const COLORS = [
    "#6c8ebf", "#43a047", "#f4a63b", "#8e44ad", "#e74c3c", "#00acc1",
    "#ec407a", "#c0a000", "#7e57c2", "#26a69a", "#78909c", "#5c6bc0",
];
const START_HOUR = 8;
const END_HOUR = 19;
const HOUR_PX = 56;

export class ClinicPlanning extends Component {
    static template = "clinic_patient_card.ClinicPlanning";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            date: this._todayStr(),
            dentists: [],
            events: [],
            types: {},
        });
        onWillStart(() => this.load());
    }

    _todayStr() {
        const d = new Date();
        const off = d.getTimezoneOffset() * 60000;
        return new Date(d - off).toISOString().slice(0, 10);
    }

    get totalHeight() {
        return (END_HOUR - START_HOUR) * HOUR_PX;
    }

    hours() {
        const out = [];
        for (let h = START_HOUR; h < END_HOUR; h++) {
            out.push(h);
        }
        return out;
    }

    async load() {
        const d = new Date(this.state.date + "T00:00:00");
        const prev = new Date(d); prev.setDate(prev.getDate() - 1);
        const next = new Date(d); next.setDate(next.getDate() + 1);
        const dayStr = (x) => {
            const off = x.getTimezoneOffset() * 60000;
            return new Date(x - off).toISOString().slice(0, 10);
        };
        const from = dayStr(prev) + " 00:00:00";
        const to = dayStr(next) + " 23:59:59";

        const events = await this.orm.searchRead(
            "calendar.event",
            [["is_clinic", "=", true], ["start", ">=", from], ["start", "<=", to]],
            ["name", "start", "stop", "dentist_id", "appointment_type_id", "patient_id", "clinic_state"]
        );
        const types = await this.orm.searchRead(
            "clinic.appointment.type", [], ["name", "color"]
        );
        const typeMap = {};
        for (const t of types) {
            typeMap[t.id] = t;
        }
        const dayEvents = events.filter(
            (e) => deserializeDateTime(e.start).toFormat("yyyy-LL-dd") === this.state.date
        );
        const dmap = new Map();
        for (const e of dayEvents) {
            if (e.dentist_id) {
                dmap.set(e.dentist_id[0], e.dentist_id[1]);
            }
        }
        this.state.types = typeMap;
        this.state.events = dayEvents;
        this.state.dentists = [...dmap.entries()].map(([id, name]) => ({ id, name }));
    }

    eventsFor(dentistId) {
        return this.state.events.filter(
            (e) => e.dentist_id && e.dentist_id[0] === dentistId
        );
    }

    _hourOf(dtStr) {
        const dt = deserializeDateTime(dtStr);
        return dt.hour + dt.minute / 60;
    }

    eventStyle(ev) {
        const s = this._hourOf(ev.start);
        const e = this._hourOf(ev.stop);
        const top = Math.max(0, (s - START_HOUR) * HOUR_PX);
        const height = Math.max(22, (e - s) * HOUR_PX - 2);
        let idx = 0;
        const t = ev.appointment_type_id && this.state.types[ev.appointment_type_id[0]];
        if (t) {
            idx = ((t.color || 0) % COLORS.length + COLORS.length) % COLORS.length;
        }
        return `top:${top}px;height:${height}px;background:${COLORS[idx]};`;
    }

    evTime(ev) {
        const s = deserializeDateTime(ev.start).toFormat("HH:mm");
        const e = deserializeDateTime(ev.stop).toFormat("HH:mm");
        return `${s} – ${e}`;
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

    changeDay(delta) {
        const d = new Date(this.state.date + "T00:00:00");
        d.setDate(d.getDate() + delta);
        const off = d.getTimezoneOffset() * 60000;
        this.state.date = new Date(d - off).toISOString().slice(0, 10);
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
}

registry.category("actions").add("clinic_planning", ClinicPlanning);
