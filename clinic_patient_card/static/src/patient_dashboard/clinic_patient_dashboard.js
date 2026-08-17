/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { deserializeDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

/**
 * Patient Dashboard — a visual, read-mostly overview of one patient
 * (res.partner) styled after the "Health Care" reference design:
 * profile card, vitals row, and a visit-history table.
 *
 * Only fields that really exist on the patient are bound. The vitals row
 * is a visual placeholder (the clinic does not store vitals yet), clearly
 * marked as "no data" rather than showing invented readings.
 */
export class ClinicPatientDashboard extends Component {
    static template = "clinic_patient_card.ClinicPatientDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            patient: null,
            history: [],
        });
        // partner id: from the action context (active_id) or the client action params
        const ctx = this.props.action && this.props.action.context;
        this.partnerId =
            (ctx && (ctx.active_id || ctx.default_partner_id)) ||
            (this.props.action &&
                this.props.action.params &&
                this.props.action.params.partner_id) ||
            false;
        onWillStart(() => this.load());
    }

    async load() {
        if (!this.partnerId) {
            this.state.loading = false;
            return;
        }
        const fields = [
            "display_name", "name", "email", "phone", "image_1024",
            "gender", "age", "is_patient", "patient_ref",
            "registration_date", "last_dental_visit_date",
            "treatment_plan_status", "risk_level",
            "credit", "total_invoiced",
            "procedure_history_ids",
        ];
        const [p] = await this.orm.read("res.partner", [this.partnerId], fields);
        // visit history — reuse the procedure history lines as "visits"
        let history = [];
        if (p && p.procedure_history_ids && p.procedure_history_ids.length) {
            const lines = await this.orm.read(
                "clinic.procedure.history",
                p.procedure_history_ids,
                ["procedure_id", "procedure_date", "planned_date", "status", "doctor_id", "appointment_id"]
            );
            history = lines
                .map((l) => ({
                    id: l.id,
                    date: l.procedure_date || l.planned_date || false,
                    diagnosis: l.procedure_id ? l.procedure_id[1] : "—",
                    status: l.status || "planned",
                    doctor: l.doctor_id ? l.doctor_id[1] : "",
                    visit: l.appointment_id ? l.appointment_id[1] : "",
                }))
                .sort((a, b) => (b.date || "").localeCompare(a.date || ""));
        }
        this.state.patient = p || null;
        this.state.history = history;
        this.state.loading = false;
    }

    // ---- display helpers ----
    get sexLabel() {
        const g = this.state.patient && this.state.patient.gender;
        return g === "male" ? _t("Male") : g === "female" ? _t("Female") : "—";
    }
    get statusLabel() {
        return this.state.patient && this.state.patient.is_patient
            ? _t("Active")
            : _t("Inactive");
    }
    get planLabel() {
        const map = {
            planned: _t("Planned"),
            in_progress: _t("In progress"),
            done: _t("Done"),
            postponed: _t("Postponed"),
            cancelled: _t("Cancelled"),
        };
        const v = this.state.patient && this.state.patient.treatment_plan_status;
        return (v && map[v]) || "—";
    }
    get riskLabel() {
        const map = { low: _t("Low"), medium: _t("Medium"), high: _t("High") };
        const v = this.state.patient && this.state.patient.risk_level;
        return (v && map[v]) || "—";
    }
    fmtDate(d) {
        if (!d) {
            return "—";
        }
        try {
            const dt = deserializeDate(d);
            return dt.toFormat("dd LLL, yyyy");
        } catch (e) {
            return d;
        }
    }
    fmtMoney(v) {
        return (v || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }
    statusClass(s) {
        return (
            {
                done: "cpd_pill cpd_pill_ok",
                in_progress: "cpd_pill cpd_pill_info",
                planned: "cpd_pill cpd_pill_warn",
                postponed: "cpd_pill cpd_pill_muted",
                cancelled: "cpd_pill cpd_pill_danger",
            }[s] || "cpd_pill cpd_pill_muted"
        );
    }
    statusText(s) {
        return (
            {
                done: _t("Done"),
                in_progress: _t("In progress"),
                planned: _t("Planned"),
                postponed: _t("Postponed"),
                cancelled: _t("Cancelled"),
            }[s] || s
        );
    }

    // ---- actions ----
    editProfile() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: this.partnerId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("clinic_patient_dashboard", ClinicPatientDashboard);
