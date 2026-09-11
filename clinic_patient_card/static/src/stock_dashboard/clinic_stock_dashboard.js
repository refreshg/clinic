/** @odoo-module **/
// Manager dashboard (batch #2 B4, items 102-114): 12 blocks over one RPC.
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ClinicStockDashboard extends Component {
    static template = "clinic_patient_card.ClinicStockDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ d: null });
        onWillStart(async () => {
            this.state.d = await this.orm.call(
                "purchase.order", "clinic_dashboard_data", []);
        });
    }

    money(v) {
        return (v || 0).toFixed(2) + " " + (this.state.d.currency || "");
    }
    openRequests() {
        this.action.doAction("clinic_patient_card.action_clinic_purchase_request");
    }
    statusLabel(s) {
        const map = {
            availability: "ხელმისაწვდომობა ✓", preparing: "მზადდება",
            ready: "მზადაა", in_transit: "გზაშია", delivered: "მოტანილი",
            draft: "დრაფტი", sent: "გაგზავნილი", purchase: "დადასტურებული",
        };
        return map[s] || s || "";
    }
}

registry.category("actions").add("clinic_stock_dashboard", ClinicStockDashboard);
