/** @odoo-module **/
// "ნამუშევარი საათები" — plan (staff schedule) vs fact (hr_attendance) per
// employee for a day / week / month / year, with an Excel export.
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const WD_FULL = ["ორშაბათი", "სამშაბათი", "ოთხშაბათი", "ხუთშაბათი", "პარასკევი", "შაბათი", "კვირა"];
const MONTHS = ["იანვარი", "თებერვალი", "მარტი", "აპრილი", "მაისი", "ივნისი",
    "ივლისი", "აგვისტო", "სექტემბერი", "ოქტომბერი", "ნოემბერი", "დეკემბერი"];
const KINDS = [
    { key: "doctor", label: "ექიმები" },
    { key: "admin", label: "ადმინისტრაცია" },
    { key: "assistant", label: "ასისტენტები" },
];

function iso(d) {
    const off = d.getTimezoneOffset() * 60000;
    return new Date(d - off).toISOString().slice(0, 10);
}
function parse(s) {
    return new Date(s + "T00:00:00");
}
function addDays(s, n) {
    const d = parse(s);
    d.setDate(d.getDate() + n);
    return iso(d);
}

export class ClinicWorkedHours extends Component {
    static template = "clinic_patient_card.ClinicWorkedHours";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.KINDS = KINDS;
        this.state = useState({
            kind: false, // the server picks the user's own group on first load
            mode: "week",
            anchor: iso(new Date()),
            loading: true,
            data: { rows: [], totals: {}, buckets: [], counts: {}, is_admin: false,
                    visible_kinds: [] },
        });
        onWillStart(() => this.load());
    }

    get visibleKinds() {
        const ok = this.state.data.visible_kinds;
        return KINDS.filter((k) => ok.includes(k.key));
    }

    get range() {
        const { mode, anchor } = this.state;
        const d = parse(anchor);
        if (mode === "day") {
            return { from: anchor, to: anchor };
        }
        if (mode === "week") {
            const from = addDays(anchor, -((d.getDay() + 6) % 7));
            return { from, to: addDays(from, 6) };
        }
        if (mode === "month") {
            return {
                from: iso(new Date(d.getFullYear(), d.getMonth(), 1)),
                to: iso(new Date(d.getFullYear(), d.getMonth() + 1, 0)),
            };
        }
        return { from: d.getFullYear() + "-01-01", to: d.getFullYear() + "-12-31" };
    }
    get rangeLabel() {
        const { from, to } = this.range;
        const a = parse(from);
        const b = parse(to);
        const { mode } = this.state;
        if (mode === "year") {
            return a.getFullYear() + " წელი";
        }
        if (mode === "month") {
            return MONTHS[a.getMonth()] + " " + a.getFullYear();
        }
        if (mode === "day") {
            return a.getDate() + " " + MONTHS[a.getMonth()] + ", " + WD_FULL[(a.getDay() + 6) % 7];
        }
        return a.getDate() + " " + MONTHS[a.getMonth()] + " – " + b.getDate() + " " + MONTHS[b.getMonth()];
    }
    get exportUrl() {
        const { from, to } = this.range;
        return "/clinic/worked_hours/export?kind=" + this.state.kind + "&mode=" + this.state.mode
            + "&date_from=" + from + "&date_to=" + to;
    }

    async load() {
        this.state.loading = true;
        const { from, to } = this.range;
        this.state.data = await this.orm.call("clinic.schedule.line", "clinic_hours_data",
            [this.state.kind, from, to, this.state.mode]);
        this.state.kind = this.state.data.kind;
        this.state.loading = false;
    }
    setKind(k) {
        this.state.kind = k;
        this.load();
    }
    setMode(m) {
        this.state.mode = m;
        this.load();
    }
    today() {
        this.state.anchor = iso(new Date());
        this.load();
    }
    step(dir) {
        const { mode, anchor } = this.state;
        const d = parse(anchor);
        if (mode === "day") {
            this.state.anchor = addDays(anchor, dir);
        } else if (mode === "week") {
            this.state.anchor = addDays(anchor, 7 * dir);
        } else if (mode === "month") {
            this.state.anchor = iso(new Date(d.getFullYear(), d.getMonth() + dir, 1));
        } else {
            this.state.anchor = iso(new Date(d.getFullYear() + dir, 0, 1));
        }
        this.load();
    }

    // ---- formatting ----
    fmt(v) {
        return (Math.round((v || 0) * 10) / 10).toString();
    }
    signed(v) {
        const r = Math.round((v || 0) * 10) / 10;
        return (r > 0 ? "+" : "") + r;
    }
    diffClass(v) {
        return v > 0.05 ? "cw_pos" : v < -0.05 ? "cw_neg" : "cw_zero";
    }
    pctWidth(r) {
        return "width:" + Math.min(r.pct || 0, 100) + "%;";
    }
    get chartMax() {
        const all = this.state.data.buckets.flatMap((b) => [b.planned, b.worked]);
        return Math.max(...all, 1);
    }
    barStyle(v) {
        return "height:" + Math.round((v / this.chartMax) * 100) + "%;";
    }
    get showChart() {
        return this.state.mode !== "day" && this.state.data.buckets.length > 0;
    }
}

registry.category("actions").add("clinic_worked_hours", ClinicWorkedHours);
