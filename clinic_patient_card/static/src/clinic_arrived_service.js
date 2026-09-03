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
// Pleasant notification chime — a short melody of sine notes with sustain.
function playMelody(notes) {
    const ctx = ensureAudio();
    if (!ctx) {
        return;
    }
    const now = ctx.currentTime;
    notes.forEach((n, i) => {
        const t = now + (n.at !== undefined ? n.at : i * 0.16);
        const dur = n.dur || 0.5;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.value = n.f;
        gain.gain.setValueAtTime(0.0001, t);
        gain.gain.exponentialRampToValueAtTime(0.32, t + 0.03);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + dur);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + dur + 0.05);
    });
}
// Friendly ascending arpeggio (C5-E5-G5-C6), then repeat softer.
function chimeArrived() {
    playMelody([
        { f: 523.25 }, { f: 659.25 }, { f: 783.99 }, { f: 1046.5, dur: 0.7 },
    ]);
}
// Two-tone alert for low stock.
function chimeAlert() {
    playMelody([
        { f: 880, at: 0, dur: 0.35 }, { f: 587.33, at: 0.3, dur: 0.5 },
        { f: 880, at: 0.7, dur: 0.35 }, { f: 587.33, at: 1.0, dur: 0.5 },
    ]);
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
            chimeArrived();
        });
        bus_service.subscribe("clinic_low_stock", (payload) => {
            const items = (payload && payload.items) || [];
            notification.add(items.join(", "), {
                title: _t("Low stock (%s)", (payload && payload.count) || 0),
                type: "warning",
                sticky: true,
            });
            chimeAlert();
        });
        // Supplier side: a new order arrived from the clinic.
        bus_service.subscribe("clinic_new_order", (payload) => {
            notification.add(
                _t("New order %s — please confirm", (payload && payload.name) || ""),
                { title: _t("New clinic order"), type: "info", sticky: true }
            );
            chimeArrived();
        });
        // Clinic side: the supplier confirmed the order.
        bus_service.subscribe("clinic_order_confirmed", (payload) => {
            const arr = payload && payload.arrival ? ` — ${payload.arrival}` : "";
            notification.add(
                `${(payload && payload.vendor) || ""}: ${(payload && payload.name) || ""}${arr}`,
                { title: _t("Order confirmed by supplier"), type: "success", sticky: true }
            );
            chimeArrived();
        });
        // A doctor drafted a retail sale — the admin must approve it.
        bus_service.subscribe("clinic_sale_request", (payload) => {
            notification.add(
                `${(payload && payload.doctor) || ""} → ${(payload && payload.patient) || ""} (${(payload && payload.order) || ""})`,
                { title: _t("Doctor sale request"), type: "warning", sticky: true }
            );
            chimeAlert();
        });
        // Dispensary control due in 2 weeks — time to call the patient.
        bus_service.subscribe("clinic_dispensary_due", (payload) => {
            notification.add(
                `${(payload && payload.patient) || ""} — ${(payload && payload.when) || ""}`,
                { title: _t("Dispensary control: call the patient"), type: "warning", sticky: true }
            );
            chimeAlert();
        });
        bus_service.start();
    },
};

registry.category("services").add("clinic_arrived_service", clinicArrivedService);
