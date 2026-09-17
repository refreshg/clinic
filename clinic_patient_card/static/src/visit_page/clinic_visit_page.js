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

// kind: text → plain textarea; the rest render their own Dentos form
const SECTIONS = [
    { key: "complaints", label: _t("ჩივილები"), kind: "complaints" },
    { key: "objective", label: _t("ობიექტური გამოკვლევები"), kind: "objective" },
    { key: "clinic_exam_results", label: _t("გამოკვლევის შედეგები"), kind: "text" },
    { key: "prescription", label: _t("დანიშნულება / რეკომ."), kind: "prescription" },
    { key: "allergy", label: _t("ალერგიულობა"), kind: "allergy" },
    { key: "clinic_epicrisis", label: _t("ვიზიტის ეპიკრიზი"), kind: "text" },
];

const OBJ_FIELDS = [
    ["clinic_obj_bite", _t("თანკბილვა")],
    ["clinic_obj_mucosa", _t("პირის ღრუს ლორწოვანი გარსის მდგომარეობა")],
    ["clinic_obj_periodontium", _t("პაროდონტის მდგომარეობა")],
    ["clinic_obj_pocket_depth", _t("პაროდონტული ჯიბის სიღრმე")],
    ["clinic_obj_plaque", _t("ნადები")],
    ["clinic_obj_exam_plan", _t("გამოკვლევის გეგმა")],
    ["clinic_obj_other", _t("სხვა")],
];

const REC_TYPES = [
    ["e_recipe", _t("ელ.რეცეპტი")],
    ["prescription", _t("დანიშნულება")],
    ["recommendation", _t("რეკომენდაცია")],
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
        this.objFields = OBJ_FIELDS;
        this.recTypes = REC_TYPES;
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
            compDraft: {},
            objDraft: {},
            rxDraft: {},
            algDraft: {},
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
    sectionMeta(key) {
        return SECTIONS.find((s) => s.key === key);
    }
    sectionFilled(key) {
        const d = this.state.data;
        switch (key) {
            case "complaints":
                return !!(d.complaints.ids.length || d.complaints.other
                    || (d.complaints.anamnesis || "").trim());
            case "objective":
                return Object.values(d.objective).some((v) => (v || "").trim());
            case "prescription":
                return !!d.prescriptions.length;
            case "allergy":
                return !!d.allergies.length;
            default:
                return !!(d.sections[key] || "").trim();
        }
    }
    openSection(key) {
        this.state.section = key;
        const d = this.state.data;
        const meta = this.sectionMeta(key);
        if (meta.kind === "text") {
            this.state.sectionDraft = d.sections[key] || "";
        } else if (meta.kind === "complaints") {
            this.state.compDraft = {
                case_type: d.complaints.case_type || "planned",
                other: d.complaints.other,
                anamnesis: d.complaints.anamnesis,
                pick: false,
            };
        } else if (meta.kind === "objective") {
            this.state.objDraft = { ...d.objective };
        } else if (meta.kind === "prescription") {
            this.state.rxDraft = { rec_type: "prescription", medicament: "",
                period: "", qty: 1, directions: "" };
        } else if (meta.kind === "allergy") {
            this.state.algDraft = { name: "", reaction: "", note: "" };
        }
    }
    async saveSection() {
        const key = this.state.section;
        await this.orm.write("calendar.event", [this.visitId],
            { [key]: this.state.sectionDraft });
        this.state.data.sections[key] = this.state.sectionDraft;
        this.notification.add(_t("შენახულია"), { type: "success" });
    }

    // ---- complaints (catalog tags + other + anamnesis) ------------------
    complaintName(id) {
        const c = this.state.data.complaint_catalog.find((x) => x.id === id);
        return c ? c.name : id;
    }
    async addComplaint() {
        const id = this.state.compDraft.pick;
        if (!id || this.state.data.complaints.ids.includes(id)) { return; }
        const ids = [...this.state.data.complaints.ids, id];
        await this.orm.write("calendar.event", [this.visitId],
            { clinic_complaint_ids: [[6, 0, ids]] });
        this.state.data.complaints.ids = ids;
        this.state.compDraft.pick = false;
    }
    async removeComplaint(id) {
        const ids = this.state.data.complaints.ids.filter((x) => x !== id);
        await this.orm.write("calendar.event", [this.visitId],
            { clinic_complaint_ids: [[6, 0, ids]] });
        this.state.data.complaints.ids = ids;
    }
    async saveComplaints() {
        const d = this.state.compDraft;
        await this.orm.write("calendar.event", [this.visitId], {
            clinic_case_type: d.case_type,
            clinic_complaints_other: d.other,
            clinic_complaints: d.anamnesis,
        });
        Object.assign(this.state.data.complaints, {
            case_type: d.case_type, other: d.other, anamnesis: d.anamnesis });
        this.notification.add(_t("შენახულია"), { type: "success" });
    }

    // ---- objective exam --------------------------------------------------
    async saveObjective() {
        await this.orm.write("calendar.event", [this.visitId],
            { ...this.state.objDraft });
        Object.assign(this.state.data.objective, this.state.objDraft);
        this.notification.add(_t("შენახულია"), { type: "success" });
    }

    // ---- prescriptions table --------------------------------------------
    recTypeLabel(t) {
        const r = REC_TYPES.find((x) => x[0] === t);
        return r ? r[1] : t;
    }
    async addPrescription() {
        const d = this.state.rxDraft;
        if (!d.medicament.trim()) {
            this.notification.add(_t("ჩაწერე მედიკამენტი"), { type: "warning" });
            return;
        }
        await this.orm.create("clinic.prescription", [{
            visit_id: this.visitId, rec_type: d.rec_type,
            medicament: d.medicament, period: d.period,
            qty: parseFloat(d.qty) || 1, directions: d.directions,
        }]);
        await this.load();
        this.openSection("prescription");
    }
    async removePrescription(row) {
        await this.orm.unlink("clinic.prescription", [row.id]);
        await this.load();
        this.openSection("prescription");
    }

    // ---- allergies table (lives on the PATIENT) --------------------------
    async addAllergy() {
        const d = this.state.algDraft;
        if (!d.name.trim()) {
            this.notification.add(_t("ჩაწერე მედიკამენტი/ნივთიერება"),
                { type: "warning" });
            return;
        }
        await this.orm.create("clinic.patient.allergy", [{
            partner_id: this.state.data.patient.id,
            name: d.name, reaction: d.reaction, note: d.note,
        }]);
        await this.load();
        this.openSection("allergy");
    }
    async removeAllergy(row) {
        await this.orm.unlink("clinic.patient.allergy", [row.id]);
        await this.load();
        this.openSection("allergy");
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
    get debtPreview() {
        // live "remaining" while typing the amounts
        const paid = (parseFloat(this.state.payCash) || 0)
            + (parseFloat(this.state.payTerminal) || 0);
        return Math.round((this.totalAmount - paid) * 100) / 100;
    }
    async registerPayment() {
        if (this.debtPreview !== 0) {
            this.notification.add(
                this.debtPreview > 0
                    ? _t("თანხა არასრულია — დავალიანება ") + this.debtPreview + " ₾"
                    : _t("შეყვანილი თანხა ჯამს აღემატება ") + (-this.debtPreview) + " ₾-ით",
                { type: "danger" });
            return;
        }
        this.state.saving = true;
        try {
            await this.orm.call("calendar.event",
                "clinic_visit_register_payment", [this.visitId],
                { cash: parseFloat(this.state.payCash) || 0,
                  terminal: parseFloat(this.state.payTerminal) || 0 });
            this.notification.add(_t("გადახდა დაფიქსირდა"), { type: "success" });
            await this.load();
        } catch (e) {
            this.notification.add(
                (e.data && e.data.message) || e.message || _t("გადახდა ვერ შესრულდა"),
                { type: "danger" });
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
