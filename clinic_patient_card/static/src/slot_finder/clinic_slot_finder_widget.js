/** @odoo-module **/
// "🕐 თავისუფალი დროები" as a view WIDGET, not a form button: object buttons
// force a save of the record first (the reviewer's complaint — a half-filled
// visit got auto-created). A widget click saves nothing; the picked slot is
// copied into the open form's fields and the user decides when to Save.
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class ClinicSlotFinderBtn extends Component {
    static template = "clinic_patient_card.SlotFinderBtn";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    get visible() {
        const d = this.props.record.data;
        if (!d.is_clinic) {
            return false;
        }
        return !d.clinic_state || ["requested", "booked"].includes(d.clinic_state);
    }

    async onClick() {
        const d = this.props.record.data;
        const [wizId] = await this.orm.create("clinic.slot.finder", [{
            direction_id: d.direction_id ? d.direction_id[0] : false,
            duration: d.duration || 0.5,
        }]);
        const act = await this.orm.call("clinic.slot.finder", "action_search", [[wizId]]);
        this.action.doAction(act, {
            onClose: async () => {
                const [w] = await this.orm.read(
                    "clinic.slot.finder", [wizId],
                    ["picked", "picked_start", "picked_stop",
                     "picked_dentist_id", "direction_id"]);
                if (!w || !w.picked) {
                    return;
                }
                const vals = {
                    start: deserializeDateTime(w.picked_start),
                    stop: deserializeDateTime(w.picked_stop),
                };
                if (w.picked_dentist_id) {
                    vals.dentist_id = w.picked_dentist_id;
                }
                if (w.direction_id) {
                    vals.direction_id = w.direction_id;
                }
                await this.props.record.update(vals);
            },
        });
    }
}

registry.category("view_widgets").add("clinic_slot_finder_btn", {
    component: ClinicSlotFinderBtn,
});
