/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { deserializeDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

/**
 * Patient Card page — Soft-UI design ported from
 * docs/design_handoff_patient_card/ into a native OWL client action.
 * Reads a real res.partner; visual + read (FDI painting is interactive on
 * screen, persisting to tooth_ids is a later step).
 */

// FDI tooth status catalogue (colors from tokens.css). `odoo` maps to the
// clinic.patient.tooth selection values (root_canal / to_extract differ).
const STATUSES = [
    { id: "healthy", odoo: "healthy", label: _t("ჯანმრთელი"), color: "#ffffff", ink: "#3a3654", border: "#e3e1f0" },
    { id: "caries", odoo: "caries", label: _t("კარიესი"), color: "#f76d9d", ink: "#fff" },
    { id: "filled", odoo: "filled", label: _t("დაბჟენილი"), color: "#7b6fd6", ink: "#fff" },
    { id: "crown", odoo: "crown", label: _t("გვირგვინი"), color: "#f5c351", ink: "#3a3654" },
    { id: "root", odoo: "root_canal", label: _t("არხის მკურნალობა"), color: "#9d8df1", ink: "#fff" },
    { id: "implant", odoo: "implant", label: _t("იმპლანტი"), color: "#b3b0c9", ink: "#fff" },
    { id: "missing", odoo: "missing", label: _t("არ არის"), color: "#3a3654", ink: "#fff" },
    { id: "extract", odoo: "to_extract", label: _t("ამოსაღები"), color: "#fb9d5b", ink: "#fff" },
    { id: "other", odoo: "other", label: _t("სხვა"), color: "#e3e1f0", ink: "#3a3654" },
];
const BY_ODOO = Object.fromEntries(STATUSES.map((s) => [s.odoo, s]));
const BY_ID = Object.fromEntries(STATUSES.map((s) => [s.id, s]));

const FDI = {
    q1: [18, 17, 16, 15, 14, 13, 12, 11],
    q2: [21, 22, 23, 24, 25, 26, 27, 28],
    q4: [48, 47, 46, 45, 44, 43, 42, 41],
    q3: [31, 32, 33, 34, 35, 36, 37, 38],
};

const MONTHS_KA = ["იან", "თებ", "მარ", "აპრ", "მაი", "ივნ", "ივლ", "აგვ", "სექ", "ოქტ", "ნოე", "დეკ"];

export class ClinicPatientCardPage extends Component {
    static template = "clinic_patient_card.ClinicPatientCardPage";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.STATUSES = STATUSES;
        this.FDI = FDI;
        this.nav = [
            { id: "bell", title: _t("შეტყობინებები"), icon: "bell" },
            { id: "patient", title: _t("პაციენტი"), icon: "user" },
            { id: "records", title: _t("ჩანაწერები"), icon: "file" },
            { id: "stats", title: _t("სტატისტიკა"), icon: "chart" },
            { id: "calendar", title: _t("კალენდარი"), icon: "calendar" },
        ];
        this.state = useState({
            loading: true,
            tab: "main",
            brush: "caries",
            navActive: "patient",
            teeth: {},        // {num: {status, note}}
            mainFlags: {},
            medFlags: {},
            note: "",
            search: "",
            data: null,       // view-model built from res.partner
        });
        const ctx = this.props.action && this.props.action.context;
        this.partnerId =
            (ctx && (ctx.active_id || ctx.default_partner_id)) ||
            (this.props.action && this.props.action.params && this.props.action.params.partner_id) ||
            false;
        onWillStart(() => this.load());
    }

    // ── data ────────────────────────────────────────────────────────
    async load() {
        if (!this.partnerId) {
            this.state.loading = false;
            return;
        }
        const fields = [
            "display_name", "name", "name_latin", "vat", "patient_ref",
            "birthdate", "age", "gender", "phone", "email",
            "street", "city", "zip", "referral_source", "registration_date",
            "nationality_country_id", "guardian_id",
            "is_foreign", "is_first_visit", "is_repeat", "is_regular", "is_minor",
            "smoker", "alcohol", "has_bleeding_disorder", "has_cardio_risk",
            "chronic_diseases", "current_medications", "family_history",
            "last_dental_visit_date", "has_bruxism", "periodontitis_risk",
            "medical_update_date", "has_xray", "has_ct",
            "preferred_payment_method", "discount_percent", "discount_fixed", "loyalty_status",
            "insurance_company_id", "insurance_policy_no", "insurance_valid_until", "insurance_notes",
            "no_show_rate", "ltv_forecast", "risk_level", "risk_notes",
            "patient_note", "patient_phone_ids", "allergy_ids", "procedure_history_ids",
            "tooth_ids", "document_ids",
        ];
        const [p] = await this.orm.read("res.partner", [this.partnerId], fields);
        // Money fields are gated by accounting groups — a doctor may not read
        // them; the page must still open (reviewer: "doesn't open from the
        // doctor account"). Fetch them separately and fall back to 0.
        Object.assign(p, { credit: 0, debit: 0, total_invoiced: 0 });
        try {
            const [money] = await this.orm.read("res.partner", [this.partnerId],
                ["credit", "debit", "total_invoiced"]);
            Object.assign(p, money);
        } catch {
            // no accounting access — keep zeros
        }

        const [phones, allergies, procs, teeth, docs] = await Promise.all([
            p.patient_phone_ids?.length
                ? this.orm.read("clinic.patient.phone", p.patient_phone_ids,
                    ["phone", "country_code", "phone_type", "channel", "is_primary", "is_emergency", "relation"])
                : [],
            p.allergy_ids?.length
                ? this.orm.read("clinic.patient.allergy", p.allergy_ids, ["allergy_type", "name", "reaction", "severity", "note"])
                : [],
            p.procedure_history_ids?.length
                ? this.orm.read("clinic.procedure.history", p.procedure_history_ids,
                    ["status", "procedure_id", "qty", "procedure_date", "planned_date", "doctor_id", "tooth"])
                : [],
            p.tooth_ids?.length
                ? this.orm.read("clinic.patient.tooth", p.tooth_ids, ["tooth_number", "status", "note"])
                : [],
            p.document_ids?.length
                ? this.orm.read("clinic.patient.document", p.document_ids, ["name", "date", "note"])
                : [],
        ]);

        // teeth -> {num: {status(id), note}}
        const teethState = {};
        for (const t of teeth) {
            const num = parseInt(t.tooth_number, 10);
            if (!num) continue;
            const st = BY_ODOO[t.status] || BY_ID.healthy;
            teethState[num] = { status: st.id, note: t.note || "" };
        }

        this.state.teeth = teethState;
        this.state.note = p.patient_note || "";
        this.state.mainFlags = {
            foreign: !!p.is_foreign, first: !!p.is_first_visit, repeat: !!p.is_repeat,
            permanent: !!p.is_regular, minor: !!p.is_minor,
        };
        this.state.medFlags = {
            smoker: !!p.smoker, alcohol: !!p.alcohol, blood: !!p.has_bleeding_disorder, cardio: !!p.has_cardio_risk,
        };
        this.state.data = this._buildVM(p, { phones, allergies, procs, docs });
        this.state.loading = false;
    }

    _buildVM(p, rel) {
        const money = (v) => "₾ " + (v || 0).toFixed(2);
        const gender = { male: _t("მამრობითი"), female: _t("მდედრობითი") }[p.gender] || "—";
        const referral = p.referral_source && p.referral_source !== "false" ? p.referral_source : "—";
        const a0 = rel.allergies[0];
        const allergyTitle = a0
            ? `${this._allergyType(a0.allergy_type)} — ${a0.name || ""}`.trim()
            : _t("ალერგია არ არის დაფიქსირებული");
        const riskMap = { low: _t("დაბალი"), medium: _t("საშუალო"), high: _t("მაღალი") };

        return {
            id: p.id,
            initials: this._initials(p.name),
            name: p.display_name || p.name,
            ref: p.patient_ref || "—",
            isRepeat: !!p.is_repeat,
            latinName: p.name_latin || "—",
            birthDate: this._fmtDate(p.birthdate),
            age: p.age || "—",
            personalNo: p.vat || "—",
            phone: p.phone || "—",
            email: p.email || "—",
            address: [p.street, p.city, p.zip].filter(Boolean).join(", ") || "—",
            citizenship: (p.nationality_country_id && p.nationality_country_id[1]) || "—",
            gender,
            referralSource: referral,
            guardian: (p.guardian_id && p.guardian_id[1]) || "—",
            registeredAt: this._fmtDate(p.registration_date),
            debt: money(p.credit),
            advance: money(p.debit),
            totalInvoiced: money(p.total_invoiced),
            lastVisitShort: this._fmtShort(p.last_dental_visit_date),
            lastVisit: this._fmtDate(p.last_dental_visit_date),
            // medical
            allergyTitle,
            allergyReaction: (a0 && a0.reaction) || "—",
            allergySeverity: this._severity(a0 && a0.severity),
            allergyNote: (a0 && a0.note) || "",
            hasAllergy: !!a0,
            chronicDiseases: p.chronic_diseases || "—",
            medications: p.current_medications || "—",
            familyHistory: p.family_history || "—",
            bruxism: p.has_bruxism ? _t("დიახ") : _t("არა"),
            periodontitisRisk: riskMap[p.periodontitis_risk] || "—",
            updatedAt: this._fmtDate(p.medical_update_date),
            hasXray: !!p.has_xray,
            hasCt: !!p.has_ct,
            // financial
            paymentTerms: "—",
            preferredMethod: this._paymentMethod(p.preferred_payment_method),
            discountPercent: (p.discount_percent || 0).toFixed(2),
            discountAmount: (p.discount_fixed || 0).toFixed(2),
            loyalty: p.loyalty_status && p.loyalty_status !== "false" ? p.loyalty_status : _t("არ არის"),
            insuranceCompany: (p.insurance_company_id && p.insurance_company_id[1]) || "—",
            policyNo: p.insurance_policy_no || "—",
            insuranceValidUntil: this._fmtDate(p.insurance_valid_until),
            insuranceNotes: p.insurance_notes || "—",
            // profile
            noShowRate: p.no_show_rate || 0,
            ltvForecast: p.ltv_forecast || 0,
            riskLevel: riskMap[p.risk_level] || "—",
            riskNotes: p.risk_notes || "—",
            // relations
            contacts: rel.phones.map((ph) => ({
                id: ph.id, isPrimary: !!ph.is_primary, phone: ph.phone || "—",
                countryCode: ph.country_code || "—",
                type: ph.phone_type || "—", channel: ph.channel || "—",
                isEmergency: !!ph.is_emergency, relation: ph.relation || "—",
            })),
            procedures: rel.procs.map((pr) => ({
                id: pr.id, status: this._procStatus(pr.status),
                name: (pr.procedure_id && pr.procedure_id[1]) || "—",
                qty: (pr.qty || 1).toFixed(2),
                date: this._fmtShort(pr.procedure_date || pr.planned_date),
                performer: (pr.doctor_id && pr.doctor_id[1]) || "clinic",
                tooth: pr.tooth || "—",
            })),
            documents: rel.docs.map((d) => ({
                id: d.id, title: d.name || _t("დოკუმენტი"),
                date: this._fmtShort(d.date), note: d.note || "",
            })),
        };
    }

    // ── formatting helpers ─────────────────────────────────────────
    _initials(name) {
        if (!name) return "?";
        return name.trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
    }
    _fmtDate(d) {
        if (!d) return "—";
        try { return deserializeDate(d).toFormat("dd.LL.yyyy"); } catch (e) { return d; }
    }
    _fmtShort(d) {
        if (!d) return "—";
        try { const dt = deserializeDate(d); return `${dt.day} ${MONTHS_KA[dt.month - 1]}`; } catch (e) { return d; }
    }
    _allergyType(t) {
        return { drug: _t("მედიკამენტი"), food: _t("საკვები"), material: _t("მასალა"), other: _t("სხვა") }[t] || _t("ალერგია");
    }
    _severity(s) {
        return { mild: _t("მსუბუქი"), moderate: _t("საშუალო"), severe: _t("მძიმე") }[s] || "—";
    }
    _paymentMethod(m) {
        if (!m || m === "false") return "—";
        return { cash: _t("ნაღდი"), card: _t("ბარათი"), transfer: _t("გადარიცხვა"), mixed: _t("შერეული") }[m] || m;
    }
    _procStatus(s) {
        return { planned: _t("დაგეგმილი"), in_progress: _t("მიმდინარე"), done: _t("დასრულებული"),
            postponed: _t("გადადებული"), cancelled: _t("გაუქმებული") }[s] || s;
    }

    // ── view accessors used by the template ────────────────────────
    st(id) { return BY_ID[id] || BY_ID.healthy; }
    toothStyle(num) {
        const rec = this.state.teeth[num];
        const st = rec ? this.st(rec.status) : this.st("healthy");
        const marked = rec && rec.status !== "healthy";
        if (marked) {
            return `background:${st.color};color:${st.ink};box-shadow:0 8px 16px ${st.color}55;`;
        }
        return "";
    }
    toothTitle(num) {
        const rec = this.state.teeth[num];
        return (rec ? this.st(rec.status) : this.st("healthy")).label;
    }
    get selectedTeeth() {
        return Object.keys(this.state.teeth).map(Number).sort((a, b) => a - b)
            .map((num) => ({ num, ...this.state.teeth[num], st: this.st(this.state.teeth[num].status) }));
    }
    swatchStyle(id) {
        const st = this.st(id);
        return `background:${st.color};${st.border ? `border:1px solid ${st.border};` : ""}`;
    }
    barStyle(percent, color) {
        const w = Math.max(0, Math.min(100, percent || 0));
        return `width:${w}%;background:${color};`;
    }

    // ── interactions ───────────────────────────────────────────────
    setTab(t) { this.state.tab = t; }
    setNav(id) { this.state.navActive = id; }
    setBrush(id) { this.state.brush = id; }
    paintTooth(num) {
        const cur = this.state.teeth[num];
        this.state.teeth[num] = { status: this.state.brush, note: (cur && cur.note) || "" };
    }
    removeTooth(num) { delete this.state.teeth[num]; }
    toggleMain(key) { this.state.mainFlags[key] = !this.state.mainFlags[key]; }
    toggleMed(key) { this.state.medFlags[key] = !this.state.medFlags[key]; }
    removeContact(id) {
        this.state.data.contacts = this.state.data.contacts.filter((c) => c.id !== id);
    }
    removeProcedure(id) {
        this.state.data.procedures = this.state.data.procedures.filter((p) => p.id !== id);
    }
    onNote(ev) { this.state.note = ev.target.value; }
    onSearch(ev) { this.state.search = ev.target.value; }
    newVisit() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "calendar.event",
            views: [[false, "form"]],
            target: "current",
            context: { default_is_clinic: true, default_patient_id: this.partnerId, default_partner_ids: [[4, this.partnerId]] },
        });
    }
}

registry.category("actions").add("clinic_patient_card_page", ClinicPatientCardPage);
