/** @odoo-module **/
// Periodontal chart (D-48) on the patient card's Medical tab (doctor only):
// the list of the patient's examinations + an editor grid for both jaws —
// per tooth missing / implant / mobility / furcation (molars) and, per side at
// 3 sites, bleeding, plaque, gingival margin and probing depth; the attachment
// level (CAL = PD + GM) and the summary are computed live. One exam = one
// clinic.perio.chart record whose measurements are a json dict (see the model).
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { _t } from "@web/core/l10n/translation";

const UPPER = [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28];
const LOWER = [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38];
const MOLARS = new Set([16, 17, 18, 26, 27, 28, 36, 37, 38, 46, 47, 48]);
const LIST_FIELDS = ["date", "doctor_id", "teeth_present", "mean_pd", "mean_cal",
    "bop_pct", "plaque_pct", "deep_sites", "note"];
// the two jaws; the oral sides face each other in the middle (as in the mouth)
const JAWS = [
    { key: "upper", label: "ზედა ყბა", teeth: UPPER, sides: [
        { k: "b", label: "ვესტიბულური (ლოყის / ტუჩის მხარე)" },
        { k: "o", label: "პალატინური (სასის მხარე)" }] },
    { key: "lower", label: "ქვედა ყბა", teeth: LOWER, sides: [
        { k: "o", label: "ლინგვური (ენის მხარე)" },
        { k: "b", label: "ვესტიბულური (ლოყის / ტუჩის მხარე)" }] },
];

function emptySide() {
    return { f: 0, gm: [0, 0, 0], pd: ["", "", ""], bop: [0, 0, 0], pl: [0, 0, 0] };
}
function emptyTooth() {
    return { m: false, i: false, mob: 0, b: emptySide(), o: emptySide() };
}
function num(v) {
    if (v === "" || v === null || v === undefined || v === false) {
        return null;
    }
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
}
/** a saved tooth merged over the empty template (older / partial data stays valid) */
function normTooth(t) {
    const e = emptyTooth();
    if (!t || typeof t !== "object") {
        return e;
    }
    const side = (s, d) => ({
        f: (s && s.f) || 0,
        gm: [0, 1, 2].map((i) => (s && s.gm && s.gm[i] !== undefined ? s.gm[i] : d.gm[i])),
        pd: [0, 1, 2].map((i) => (s && s.pd && s.pd[i] !== undefined ? s.pd[i] : d.pd[i])),
        bop: [0, 1, 2].map((i) => (s && s.bop && s.bop[i] ? 1 : 0)),
        pl: [0, 1, 2].map((i) => (s && s.pl && s.pl[i] ? 1 : 0)),
    });
    return { m: !!t.m, i: !!t.i, mob: t.mob || 0, b: side(t.b, e.b), o: side(t.o, e.o) };
}

export class ClinicPerioChart extends Component {
    static template = "clinic_patient_card.PerioChart";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.jaws = JAWS;
        this.sites = [0, 1, 2];
        this.state = useState({ charts: [], edit: null, saving: false });
        onWillStart(() => this.loadList());
    }

    get partnerId() {
        return this.props.record.resId || false;
    }

    async loadList() {
        if (!this.partnerId) {
            return;
        }
        this.state.charts = await this.orm.searchRead(
            "clinic.perio.chart", [["partner_id", "=", this.partnerId]],
            LIST_FIELDS, { order: "date desc, id desc" });
    }

    // ---- open / new / close ---------------------------------------------
    newChart() {
        const data = {};
        for (const f of [...UPPER, ...LOWER]) {
            data[f] = emptyTooth();
        }
        this.state.edit = { id: false, date: luxon.DateTime.local().toISODate(), note: "", data };
    }
    async openChart(c) {
        const [r] = await this.orm.read("clinic.perio.chart", [c.id], ["date", "note", "data"]);
        const data = {};
        for (const f of [...UPPER, ...LOWER]) {
            data[f] = normTooth((r.data || {})[f]);
        }
        this.state.edit = { id: r.id, date: r.date, note: r.note || "", data };
    }
    close() {
        this.state.edit = null;
    }
    async remove(c) {
        if (!window.confirm(_t("წავშალო ეს გაზომვა?"))) {
            return;
        }
        await this.orm.unlink("clinic.perio.chart", [c.id]);
        if (this.state.edit && this.state.edit.id === c.id) {
            this.close();
        }
        await this.loadList();
    }
    async save() {
        const e = this.state.edit;
        const vals = { date: e.date, note: e.note, data: e.data };
        this.state.saving = true;
        try {
            if (e.id) {
                await this.orm.write("clinic.perio.chart", [e.id], vals);
            } else {
                [e.id] = await this.orm.create("clinic.perio.chart",
                    [{ ...vals, partner_id: this.partnerId }]);
            }
            this.notification.add(_t("პაროდონტოლოგიური სქემა შენახულია"), { type: "success" });
            await this.loadList();
        } finally {
            this.state.saving = false;
        }
    }

    // ---- cells ----------------------------------------------------------
    tooth(f) {
        return this.state.edit.data[f];
    }
    isMolar(f) {
        return MOLARS.has(f);
    }
    toggleMissing(f) {
        this.tooth(f).m = !this.tooth(f).m;
    }
    toggleImplant(f) {
        this.tooth(f).i = !this.tooth(f).i;
    }
    setMob(f, ev) {
        this.tooth(f).mob = Number(ev.target.value) || 0;
    }
    setFurc(f, side, ev) {
        this.tooth(f)[side].f = Number(ev.target.value) || 0;
    }
    setNum(f, side, key, i, ev) {
        const v = ev.target.value.trim();
        this.tooth(f)[side][key][i] = v === "" ? (key === "gm" ? 0 : "") : Number(v);
    }
    toggleFlag(f, side, key, i) {
        const arr = this.tooth(f)[side][key];
        arr[i] = arr[i] ? 0 : 1;
    }
    cal(f, side, i) {
        const s = this.tooth(f)[side];
        const pd = num(s.pd[i]);
        return pd === null ? "" : pd + (num(s.gm[i]) || 0);
    }
    pdClass(f, side, i) {
        const pd = num(this.tooth(f)[side].pd[i]);
        return pd === null ? "" : pd >= 6 ? "pc_bad" : pd >= 4 ? "pc_warn" : "";
    }
    val(v) {
        return v === null || v === undefined ? "" : v;
    }

    /** the same numbers the server stores (models/clinic_perio_chart.py) */
    get summary() {
        const pds = [];
        const cals = [];
        let bop = 0;
        let plaque = 0;
        let sites = 0;
        let teeth = 0;
        for (const t of Object.values(this.state.edit.data)) {
            if (t.m) {
                continue;
            }
            teeth++;
            for (const k of ["b", "o"]) {
                const s = t[k];
                for (const i of [0, 1, 2]) {
                    sites++;
                    const pd = num(s.pd[i]);
                    if (pd !== null) {
                        pds.push(pd);
                        cals.push(pd + (num(s.gm[i]) || 0));
                    }
                    bop += s.bop[i] ? 1 : 0;
                    plaque += s.pl[i] ? 1 : 0;
                }
            }
        }
        const mean = (a) => (a.length ? (a.reduce((x, y) => x + y, 0) / a.length).toFixed(1) : "—");
        return {
            teeth,
            pd: mean(pds),
            cal: mean(cals),
            bop: sites ? Math.round((100 * bop) / sites) : 0,
            plaque: sites ? Math.round((100 * plaque) / sites) : 0,
            deep: pds.filter((p) => p >= 4).length,
        };
    }
}

registry.category("view_widgets").add("clinic_perio_chart", {
    component: ClinicPerioChart,
});
