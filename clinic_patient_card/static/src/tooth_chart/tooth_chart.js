/** @odoo-module **/
// Tooth chart (D-33): the clinic's healthy-teeth drawing; each tooth changes to
// the disease (planned diagnosis) or the treatment (done procedure). Same
// component on the visit page and on the patient card (Medical tab).
import { Component, markup, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { CHART_VIEWBOX, TEETH } from "./tooth_chart_data";
import { ARCH_VIEWBOX, archChart } from "./arch_layout";

const VIEW_KEY = "clinic_tooth_chart_view";
import {
    CONDITION_LABELS, CONDITION_OCC, CONDITION_SIDE,
    TREATMENT_LABELS, TREATMENT_OCC, TREATMENT_SIDE,
} from "./tooth_chart_overlays";

export class ClinicToothChart extends Component {
    static template = "clinic_patient_card.ToothChart";
    static props = {
        partnerId: { type: [Number, Boolean], optional: true },
        selected: { type: String, optional: true },
        version: { type: Number, optional: true },
        onSelect: { type: Function, optional: true },
        "*": true,
    };

    setup() {
        this.orm = useService("orm");
        this.viewBox = CHART_VIEWBOX;
        let view = "rows";
        try { view = localStorage.getItem(VIEW_KEY) || "rows"; } catch (e) { /* ignore */ }
        this.state = useState({ states: {}, hover: null, view });
        this.legend = [
            ...Object.entries(CONDITION_LABELS).map(([k, v]) => ({ k, v, kind: "cond" })),
            ...Object.entries(TREATMENT_LABELS).filter(([k]) => k !== "missing")
                .map(([k, v]) => ({ k, v, kind: "treat" })),
        ];
        onWillStart(() => this.load(this.props.partnerId));
        onWillUpdateProps((np) => {
            if (np.partnerId !== this.props.partnerId || np.version !== this.props.version) {
                return this.load(np.partnerId);
            }
        });
    }

    async load(partnerId) {
        this.state.states = partnerId
            ? await this.orm.call("res.partner", "clinic_tooth_states", [[partnerId]])
            : {};
    }

    setView(v) {
        this.state.view = v;
        try { localStorage.setItem(VIEW_KEY, v); } catch (e) { /* private mode */ }
    }

    /** the whole chart as ONE svg string — OWL would put separately injected
     * markup in the HTML namespace and the shapes would not draw */
    get svg() {
        const sel = this.props.selected;
        const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");
        const parts = {};
        for (const t of TEETH) {
            const s = this.state.states[String(t.f)] || {};
            const missing = s.treat === "missing" || s.treat === "extracted";
            let side = t.si;
            let occ = t.oi;
            if (s.cond) {
                side += (CONDITION_SIDE[s.cond] || (() => ""))(t.g);
                occ += (CONDITION_OCC[s.cond] || (() => ""))(t.g);
            }
            if (s.treat) {
                side += (TREATMENT_SIDE[s.treat] || (() => ""))(t.g);
                occ += (TREATMENT_OCC[s.treat] || (() => ""))(t.g);
            }
            parts[t.f] = {
                side, occ, tip: esc(this.tip(t.f, s)),
                cls: "tc_tooth" + (missing ? " tc_missing" : "")
                    + (sel && String(t.f) === sel ? " tc_sel" : "")
                    + (s.cond || s.treat ? " tc_has" : ""),
            };
        }
        if (this.state.view === "arch") {
            return markup(`<svg class="tc_svg" viewBox="${ARCH_VIEWBOX}" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">`
                + archChart(parts, TEETH) + "</svg>");
        }
        let out = `<svg class="tc_svg" viewBox="${this.viewBox}" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">`;
        for (const t of TEETH) {
            const p = parts[t.f];
            out += `<g class="${p.cls}" data-f="${t.f}"><title>${p.tip}</title>`
                + `<rect x="${t.lx - 16}" y="${t.ly - 150}" width="32" height="170" fill="transparent"/>`
                + `<g transform="${t.st}">${p.side}</g><g transform="${t.ot}">${p.occ}</g>`
                + `<text x="${t.lx}" y="${t.ly}" class="tc_lbl" text-anchor="middle">${t.f}</text></g>`;
        }
        return markup(out + "</svg>");
    }

    tip(fdi, s) {
        const parts = [String(fdi)];
        if (s.cond_label) { parts.push(s.cond_label); }
        if (s.diagnosis) { parts.push(s.diagnosis); }
        if (s.treat_label) { parts.push(s.treat_label); }
        if (s.procedure) { parts.push(s.procedure); }
        return parts.join(" · ");
    }

    onClick(ev) {
        const g = ev.target.closest("[data-f]");
        if (g && this.props.onSelect) {
            this.props.onSelect(Number(g.dataset.f));
        }
    }
}

// Patient card: click a tooth -> same "diagnosis + procedure" add as the visit page.
export class ClinicToothAddDialog extends Component {
    static template = "clinic_patient_card.ToothAddDialog";
    static components = { Dialog };
    static props = { partnerId: Number, tooth: Number, close: Function, onDone: Function };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ icd: [], products: [], icd10Id: 0, productId: 0, saving: false });
        onWillStart(async () => {
            this.state.icd = await this.orm.searchRead("clinic.icd10", [], ["code", "name"], { order: "code" });
            this.state.products = await this.orm.searchRead(
                "product.product", [["is_clinic_procedure", "=", true]],
                ["name", "lst_price"], { order: "name" });
        });
    }

    async add() {
        const prod = this.state.products.find((p) => p.id === Number(this.state.productId));
        if (!prod) {
            this.notification.add(_t("აირჩიე პროცედურა"), { type: "warning" });
            return;
        }
        this.state.saving = true;
        try {
            await this.orm.create("clinic.procedure.history", [{
                partner_id: this.props.partnerId,
                procedure_id: prod.id,
                icd10_id: Number(this.state.icd10Id) || false,
                tooth: String(this.props.tooth),
                status: "planned",
                qty: 1,
                price_unit: prod.lst_price,
            }]);
            this.props.onDone();
            this.props.close();
        } finally {
            this.state.saving = false;
        }
    }
}

// Patient-card widget: <widget name="clinic_tooth_chart"/> on the partner form.
export class ClinicToothChartWidget extends Component {
    static template = "clinic_patient_card.ToothChartWidget";
    static components = { ClinicToothChart };
    static props = { ...standardWidgetProps };
    setup() {
        this.dialog = useService("dialog");
        this.state = useState({ ver: 0 });
    }
    get partnerId() {
        return this.props.record.resId || false;
    }
    pick(fdi) {
        if (!this.partnerId) { return; }
        this.dialog.add(ClinicToothAddDialog, {
            partnerId: this.partnerId, tooth: fdi,
            onDone: () => { this.state.ver++; },
        });
    }
}
registry.category("view_widgets").add("clinic_tooth_chart", {
    component: ClinicToothChartWidget,
});
