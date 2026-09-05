/** @odoo-module **/
// "🕐 თავისუფალი დროები" — a fully client-side dialog.
//
// History of this file (reviewer complaints, in order):
//  1. a form <button> auto-saved the half-filled visit → became a widget;
//  2. action.doAction(target="new") REPLACED the visit dialog underneath;
//  3. FormViewDialog stacked fine, but any server-returned window-close from
//     its buttons still landed on the ACTION dialog (the visit form) — Back
//     looked dead and X blew up on a destroyed component.
// So: no wizard records, no action stack. The dialog searches through one
// RPC (calendar.event.clinic_free_slots), the pick lands in the open form
// via record.update, and closing touches nothing but this dialog.
import { Component, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Dialog } from "@web/core/dialog/dialog";

// record.data many2one values differ across Odoo versions: [id, name] tuple
// or {id, display_name} object — read both shapes.
function m2oId(v) {
    if (!v) { return false; }
    if (Array.isArray(v)) { return v[0] || false; }
    return v.id || false;
}
function m2oName(v) {
    if (!v) { return ""; }
    if (Array.isArray(v)) { return v[1] || ""; }
    return v.display_name || "";
}

export class ClinicSlotFinderDialog extends Component {
    static template = "clinic_patient_card.SlotFinderDialog";
    static components = { Dialog };
    static props = {
        directionId: { type: [Number, Boolean], optional: true },
        durationMin: { type: Number, optional: true },
        dentistId: { type: [Number, Boolean], optional: true },
        dentistName: { type: String, optional: true },
        onPick: Function,
        close: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            directions: [],
            directionId: this.props.directionId || false,
            durationMin: this.props.durationMin || 30,
            dateFrom: "",
            dentistId: this.props.dentistId || false,
            slots: [],
            message: "",
            searched: false,
        });
        onWillStart(async () => {
            this.state.directions = await this.orm.searchRead(
                "clinic.direction", [], ["name"]);
            await this.search();
        });
    }

    get durationOptions() {
        const opts = [];
        for (let m = 10; m <= 180; m += 10) {
            const h = String(Math.floor(m / 60)).padStart(2, "0");
            const mm = String(m % 60).padStart(2, "0");
            opts.push({ value: m, label: `${h}:${mm}` });
        }
        return opts;
    }

    async search() {
        const dirId = this.state.directionId ? Number(this.state.directionId) : false;
        const slots = await this.orm.call(
            "calendar.event", "clinic_free_slots",
            [dirId, Number(this.state.durationMin) / 60,
             this.state.dateFrom || false, 5,
             this.state.dentistId || false]);
        this.state.slots = slots;
        this.state.searched = true;
        if (!slots.length) {
            if (this.state.dentistId) {
                this.state.message = _t("No free slots for this doctor in the coming days — try another date or clear the doctor filter.");
                return;
            }
            const dir = this.state.directions.find((d) => d.id === dirId);
            this.state.message = dir
                ? _t('No free slots for "%s" — check that a doctor carries this direction (user\'s Clinic tab) or try another date/duration.', dir.name)
                : _t("No free slots in the coming days — try another date or duration.");
        } else {
            this.state.message = "";
        }
    }

    clearDentist() {
        this.state.dentistId = false;
        this.search();
    }

    pick(slot) {
        const dirId = this.state.directionId ? Number(this.state.directionId) : false;
        const dir = this.state.directions.find((d) => d.id === dirId);
        this.props.onPick({
            start: slot.start,
            stop: slot.stop,
            dentist_id: slot.dentist_id,
            dentist: slot.dentist,
            direction: dir ? [dir.id, dir.name] : false,
        });
        this.props.close();
    }
}

export class ClinicSlotFinderBtn extends Component {
    static template = "clinic_patient_card.SlotFinderBtn";
    static props = { ...standardWidgetProps };

    setup() {
        this.dialog = useService("dialog");
    }

    get visible() {
        const d = this.props.record.data;
        if (!d.is_clinic) {
            return false;
        }
        return !d.clinic_state || ["requested", "booked"].includes(d.clinic_state);
    }

    onClick() {
        const d = this.props.record.data;
        const record = this.props.record;
        this.dialog.add(ClinicSlotFinderDialog, {
            directionId: m2oId(d.direction_id),
            durationMin: d.duration ? Math.round(d.duration * 60) : 30,
            dentistId: m2oId(d.dentist_id),
            dentistName: m2oName(d.dentist_id),
            onPick: (slot) => {
                const vals = {
                    start: deserializeDateTime(slot.start),
                    stop: deserializeDateTime(slot.stop),
                };
                if (slot.dentist_id) {
                    vals.dentist_id = [slot.dentist_id, slot.dentist];
                }
                if (slot.direction) {
                    vals.direction_id = slot.direction;
                }
                record.update(vals);
            },
        });
    }
}

registry.category("view_widgets").add("clinic_slot_finder_btn", {
    component: ClinicSlotFinderBtn,
});
