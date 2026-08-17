/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

// Short beep via the Web Audio API (no asset file needed).
function beep() {
    try {
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (!Ctx) {
            return;
        }
        const ctx = new Ctx();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.frequency.value = 880;
        gain.gain.value = 0.15;
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        setTimeout(() => {
            osc.stop();
            ctx.close();
        }, 250);
    } catch (e) {
        // audio not available — ignore
    }
}

// R10 — the dentist gets a live sound + toast when a patient checks in.
export const clinicArrivedService = {
    dependencies: ["bus_service", "notification"],
    start(env, { bus_service, notification }) {
        bus_service.subscribe("clinic_patient_arrived", (payload) => {
            const room = payload && payload.room ? ` (${payload.room})` : "";
            notification.add(`${(payload && payload.patient) || ""}${room}`, {
                title: _t("Patient arrived"),
                type: "info",
                sticky: false,
            });
            beep();
        });
        bus_service.start();
    },
};

registry.category("services").add("clinic_arrived_service", clinicArrivedService);
