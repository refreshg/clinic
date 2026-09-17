/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * D3 — Dentos-style visit working page.
 *
 * Header: patient info cards. Left: medical sections (✓ when filled).
 * Center (Procedures tab): FDI odontogram to pick a tooth → ICD-10 →
 * procedure → add; the table below lists the visit's procedure rows.
 * Billing math itself lands in D4 — the tab shows the running totals.
 */

// FDI quadrant rows exactly as Dentos draws them (permanent + primary).
const FDI_ROWS = [
    { cls: "up", left: [18, 17, 16, 15, 14, 13, 12, 11], right: [21, 22, 23, 24, 25, 26, 27, 28] },
    { cls: "up small", left: [55, 54, 53, 52, 51], right: [61, 62, 63, 64, 65] },
    { cls: "down small", left: [85, 84, 83, 82, 81], right: [71, 72, 73, 74, 75] },
    { cls: "down", left: [48, 47, 46, 45, 44, 43, 42, 41], right: [31, 32, 33, 34, 35, 36, 37, 38] },
];

const SECTIONS = [
    { key: "clinic_complaints", label: _t("ჩივილები / ანამნეზი") },
    { key: "clinic_objective", label: _t("ობიექტური გამოკვლევები") },
    { key: "clinic_exam_results", label: _t("გამოკვლევის შედეგები") },
    { key: "clinic_prescription", label: _t("დანიშნულება / რეკომენდაციები") },
    { key: "clinic_epicrisis", label: _t("ვიზიტის ეპიკრიზი") },
];

const PROC_STATUSES = [
    ["planned", _t("დაგეგმილი")],
    ["in_progress", _t("მიმდინარე")],
    ["done", _t("დასრულებული")],
    ["postponed", _t("გადადებული")],
    ["cancelled", _t("გაუქმებული")],
];

export class ClinicVisitPage extends Component {
    static template = "clinic_patient_card.VisitPage";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.fdiRows = FDI_ROWS;
        this.sectionsMeta = SECTIONS;
        this.procStatuses = PROC_STATUSES;
        this.visitId =
            this.props.action?.params?.visit_id ||
            this.props.action?.context?.active_id;
        this.state = useState({
            data: null,
            tab: "procedures",
            section: null,          // opened section key (null = odontogram)
            sectionDraft: "",
            tooth: "",
            icd10Id: false,
            productId: false,
            saving: false,
            payCash: 0,
            payTerminal: 0,
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.data = await this.orm.call(
            "calendar.event", "clinic_visit_page_data", [this.visitId]);
    }

    // ---- header helpers -------------------------------------------------
    fmtDT(s) {
        if (!s) { return ""; }
        return s.slice(0, 16).replace("T", " ");
    }
    get visitRange() {
        const v = this.state.data.visit;
        return `${this.fmtDT(v.start)} — ${(v.stop || "").slice(11, 16)}`;
    }

    // ---- sections -------------------------------------------------------
    sectionFilled(key) {
        return !!(this.state.data.sections[key] || "").trim();
    }
    openSection(key) {
        this.state.section = key;
        this.state.sectionDraft = this.state.data.sections[key] || "";
    }
    async saveSection() {
        const key = this.state.section;
        await this.orm.write("calendar.event", [this.visitId],
            { [key]: this.state.sectionDraft });
        this.state.data.sections[key] = this.state.sectionDraft;
        this.notification.add(_t("შენახულია"), { type: "success" });
    }

    // ---- odontogram / add procedure ------------------------------------
    isSel(n) {
        return this.state.tooth === String(n);
    }
    pickTooth(n) {
        this.state.tooth = this.state.tooth === String(n) ? "" : String(n);
    }
    async addProcedure() {
        if (!this.state.productId) {
            this.notification.add(_t("აირჩიე პროცედურა"), { type: "warning" });
            return;
        }
        this.state.saving = true;
        try {
            const prod = this.state.data.products.find(
                (p) => p.id === this.state.productId);
            await this.orm.create("clinic.procedure.history", [{
                partner_id: this.state.data.patient.id,
                appointment_id: this.visitId,
                procedure_id: this.state.productId,
                icd10_id: this.state.icd10Id || false,
                tooth: this.state.tooth || false,
                status: "planned",
                qty: 1,
                price_unit: prod ? prod.lst_price : 0,
            }]);
            this.state.tooth = "";
            this.state.icd10Id = false;
            this.state.productId = false;
            await this.load();
        } finally {
            this.state.saving = false;
        }
    }
    async setProcStatus(proc, status) {
        await this.orm.write("clinic.procedure.history", [proc.id],
            { status });
        proc.status = status;
    }
    async setProcDiscount(proc, value) {
        const discount = Math.max(0, Math.min(100, parseFloat(value) || 0));
        await this.orm.write("clinic.procedure.history", [proc.id],
            { discount_percent: discount });
        await this.load();
    }
    async removeProc(proc) {
        await this.orm.unlink("clinic.procedure.history", [proc.id]);
        await this.load();
    }
    get totalAmount() {
        return this.state.data.procedures.reduce(
            (s, p) => s + (p.amount_total || 0), 0);
    }

    // ---- billing (D4) ---------------------------------------------------
    async registerPayment() {
        this.state.saving = true;
        try {
            await this.orm.call("calendar.event",
                "clinic_visit_register_payment", [this.visitId],
                { cash: parseFloat(this.state.payCash) || 0,
                  terminal: parseFloat(this.state.payTerminal) || 0 });
            this.notification.add(_t("გადახდა დაფიქსირდა"), { type: "success" });
            await this.load();
        } catch (e) {
            // the RPC layer already toasts the UserError
        } finally {
            this.state.saving = false;
        }
    }
    async finishVisit() {
        await this.orm.call("calendar.event", "action_done", [[this.visitId]]);
        this.notification.add(_t("ვიზიტი დასრულდა"), { type: "success" });
        await this.load();
    }

    // ---- navigation -----------------------------------------------------
    openPatient() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: this.state.data.patient.id,
            views: [[false, "form"]],
        });
    }
    openVisitForm() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "calendar.event",
            res_id: this.visitId,
            views: [[false, "form"]],
            target: "new",
        });
    }
}

registry.category("actions").add("clinic_visit_page", ClinicVisitPage);
