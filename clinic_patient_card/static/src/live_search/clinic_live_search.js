/** @odoo-module **/
// Patients list: matching patients appear right in the search dropdown while
// typing (name / surname, phone, e-mail, personal no.) — click one to open
// the card. With no match the standard "Search … for:" entries remain.
//
// Opt-in per action via context `clinic_live_search`.
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { SearchBar } from "@web/search/search_bar/search_bar";

const DEBOUNCE_MS = 200;
const MAX_PATIENTS = 8;

patch(SearchBar.prototype, {
    setup() {
        super.setup(...arguments);
        this.clinicAction = useService("action");
    },

    async computeState() {
        await super.computeState(...arguments);
        if (!this.env.searchModel.globalContext?.clinic_live_search) {
            return;
        }
        const query = this.state.query.trim();
        if (!query) {
            return;
        }
        // debounce: only the last keystroke of a burst hits the server
        await new Promise((resolve) => setTimeout(resolve, DEBOUNCE_MS));
        if (this.state.query.trim() !== query) {
            return;
        }
        const rows = await this.orm.searchRead(
            "res.partner",
            [
                ["is_patient", "=", true],
                "|", "|", "|",
                ["name", "ilike", query],
                ["phone", "ilike", query],
                ["email", "ilike", query],
                ["vat", "ilike", query],
            ],
            ["display_name", "phone", "email", "vat"],
            { limit: MAX_PATIENTS, order: "name" }
        );
        // stale answer (query changed while waiting) or nothing found
        if (this.state.query.trim() !== query || !rows.length) {
            return;
        }
        const items = rows.map((p) => ({
            id: `clinic_patient_${p.id}`,
            isChild: true,
            clinicPatientId: p.id,
            label: [p.display_name, p.vat, p.phone, p.email]
                .filter(Boolean)
                .join(" · "),
        }));
        // patients replace the generic "Search <field> for:" entries; when
        // nobody matches, those stay as the fallback
        this.items.length = 0;
        this.items.push(...items);
    },

    selectItem(item) {
        if (item.clinicPatientId) {
            this.resetState();
            return this.clinicAction.doAction({
                type: "ir.actions.act_window",
                res_model: "res.partner",
                res_id: item.clinicPatientId,
                views: [[false, "form"]],
                target: "current",
            });
        }
        return super.selectItem(...arguments);
    },
});
