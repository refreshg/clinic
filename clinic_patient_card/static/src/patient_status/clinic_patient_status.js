/** @odoo-module **/
// Patients screen: two icon buttons next to "New" (primary = came once,
// unique = came several times) that filter the list, plus an Export button
// downloading the matching patients as .xlsx. Wired through js_class on the
// Patients kanban/list (primary views bound to action_clinic_patients).
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

const STATUSES = ["primary", "unique"];

export class ClinicPatientButtons extends Component {
    static template = "clinic_patient_card.PatientButtons";
    static props = {};

    setup() {
        this.state = useState({ tick: 0 });
        // re-render whenever the search model changes (filter toggled…)
        useBus(this.env.searchModel, "update", () => this.state.tick++);
    }

    _item(status) {
        return Object.values(this.env.searchModel.searchItems).find(
            (i) => i.name === "status_" + status
        );
    }
    isActive(status) {
        const item = this._item(status);
        return !!item && this.env.searchModel.query.some(
            (q) => q.searchItemId === item.id);
    }
    get activeStatus() {
        return STATUSES.find((s) => this.isActive(s)) || false;
    }
    toggle(status) {
        const model = this.env.searchModel;
        const item = this._item(status);
        if (!item) {
            return;
        }
        // exclusive: switch the other status off first
        for (const other of STATUSES) {
            if (other !== status && this.isActive(other)) {
                model.toggleSearchItem(this._item(other).id);
            }
        }
        model.toggleSearchItem(item.id);
    }
    get exportUrl() {
        return "/clinic/patients/export?status=" + (this.activeStatus || "all");
    }
}

class ClinicPatientsKanbanController extends KanbanController {
    static template = "clinic_patient_card.PatientsKanbanView";
    static components = { ...KanbanController.components, ClinicPatientButtons };
}
class ClinicPatientsListController extends ListController {
    static template = "clinic_patient_card.PatientsListView";
    static components = { ...ListController.components, ClinicPatientButtons };
}

registry.category("views").add("clinic_patients_kanban", {
    ...kanbanView,
    Controller: ClinicPatientsKanbanController,
});
registry.category("views").add("clinic_patients_list", {
    ...listView,
    Controller: ClinicPatientsListController,
});
