/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

// One shared AudioContext, unlocked on the first user gesture (browsers block
// audio until the user interacts with the page).
let audioCtx = null;
function ensureAudio() {
    try {
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (!Ctx) {
            return null;
        }
        if (!audioCtx) {
            audioCtx = new Ctx();
        }
        if (audioCtx.state === "suspended") {
            audioCtx.resume();
        }
        return audioCtx;
    } catch (e) {
        return null;
    }
}
function beep(times = 2) {
    const ctx = ensureAudio();
    if (!ctx) {
        return;
    }
    for (let i = 0; i < times; i++) {
        const t = ctx.currentTime + i * 0.28;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.frequency.value = 900;
        gain.gain.setValueAtTime(0.0001, t);
        gain.gain.exponentialRampToValueAtTime(0.25, t + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.22);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.24);
    }
}

export const clinicArrivedService = {
    dependencies: ["bus_service", "notification"],
    start(env, { bus_service, notification }) {
        // Unlock audio on any user interaction (autoplay policy).
        const unlock = () => ensureAudio();
        window.addEventListener("click", unlock);
        window.addEventListener("keydown", unlock);

        bus_service.subscribe("clinic_patient_arrived", (payload) => {
            const room = payload && payload.room ? ` (${payload.room})` : "";
            notification.add(`${(payload && payload.patient) || ""}${room}`, {
                title: _t("Patient arrived"),
                type: "info",
                sticky: false,
            });
            beep(2);
        });
        bus_service.subscribe("clinic_low_stock", (payload) => {
            const items = (payload && payload.items) || [];
            notification.add(items.join(", "), {
                title: _t("Low stock (%s)", (payload && payload.count) || 0),
                type: "warning",
                sticky: true,
            });
            beep(3);
        });
        bus_service.start();
    },
};

registry.category("services").add("clinic_arrived_service", clinicArrivedService);
