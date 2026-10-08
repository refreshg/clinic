/** @odoo-module **/
// D-49: "🩺 სამედიცინო ბარათი" tab — what the form still lacks (red), PDF / print
// buttons and the live card itself (the report's HTML render), rebuilt from the
// records every time the tab opens, so it is always current.
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

const REPORT = "clinic_patient_card.report_clinic_med_card";

export class ClinicMedCard extends Component {
    static template = "clinic_patient_card.MedCard";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ missing: [], stamp: Date.now() });
        onWillStart(() => this.load());
    }
    get partnerId() {
        return this.props.record.resId || false;
    }
    get previewUrl() {
        // the stamp defeats the browser cache: the card is rebuilt on every refresh
        return `/report/html/${REPORT}/${this.partnerId}?t=${this.state.stamp}`;
    }
    async load() {
        if (!this.partnerId) {
            return;
        }
        this.state.missing = await this.orm.call("res.partner", "clinic_med_card_missing", [[this.partnerId]]);
    }
    async refresh() {
        await this.load();
        this.state.stamp = Date.now();
    }
    async pdf() {
        const act = await this.orm.call("res.partner", "action_med_card_pdf", [[this.partnerId]]);
        await this.action.doAction(act);
    }
    print() {
        window.open(`/report/pdf/${REPORT}/${this.partnerId}`, "_blank");
    }
}

registry.category("view_widgets").add("clinic_med_card", {
    component: ClinicMedCard,
});
