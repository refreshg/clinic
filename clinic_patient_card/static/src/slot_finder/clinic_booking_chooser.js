/** @odoo-module **/
// D-43: before a new booking opens, ask "existing patient or new patient
// (first visit)?". Existing → the booking form as before (Repeat Visit).
// New → the quick registration form first; once saved, the booking form opens
// with that patient already set (First Visit). Cancelling = no booking.
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

export class ClinicBookingChooser extends Component {
    static template = "clinic_patient_card.BookingChooser";
    static components = { Dialog };
    static props = { close: Function, onPick: Function };

    pick(kind) {
        this.props.close();
        this.props.onPick(kind);
    }
}

/**
 * @param {Object} services {action, dialog}
 * @param {Object} opts {context, target, onClose}
 */
export function openBookingChooser({ action, dialog }, { context, target, onClose }) {
    const openBooking = (extra) => action.doAction({
        type: "ir.actions.act_window",
        res_model: "calendar.event",
        views: [[false, "form"]],
        target,
        context: { ...context, ...extra },
    }, onClose ? { onClose } : {});
    dialog.add(ClinicBookingChooser, {
        onPick: (kind) => {
            if (kind === "repeat") {
                openBooking({ default_clinic_visit_kind: "repeat" });
                return;
            }
            dialog.add(FormViewDialog, {
                resModel: "res.partner",
                title: _t("პაციენტის რეგისტრაციის ფორმა"),
                context: {
                    default_is_patient: true,
                    form_view_ref: "clinic_patient_card.view_clinic_patient_quick_form",
                },
                onRecordSaved: (rec) => openBooking({
                    default_clinic_visit_kind: "first",
                    default_patient_id: rec.resId,
                }),
            });
        },
    });
}
