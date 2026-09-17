/** @odoo-module **/
// "➕ ახალი პაციენტი" on the booking form (Dentos's add-person icon).
//
// The Patient m2o keeps its normal internal link (full client card);
// this widget opens the QUICK registration form in a stacked dialog and,
// on save, drops the new patient straight into the open booking — so the
// registration popup never hijacks navigation to existing patients.
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

export class ClinicNewPatientBtn extends Component {
    static template = "clinic_patient_card.NewPatientBtn";
    static props = { ...standardWidgetProps };

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    }

    open() {
        const record = this.props.record;
        this.dialog.add(FormViewDialog, {
            resModel: "res.partner",
            title: _t("პაციენტის რეგისტრაციის ფორმა"),
            context: {
                default_is_patient: true,
                form_view_ref:
                    "clinic_patient_card.view_clinic_patient_quick_form",
            },
            onRecordSaved: async (rec) => {
                const [row] = await this.orm.read(
                    "res.partner", [rec.resId], ["display_name"]);
                // Odoo 19 relational model: m2o values are {id, display_name}
                // objects — a [id, name] tuple is silently dropped.
                await record.update({
                    patient_id: {
                        id: rec.resId,
                        display_name: row ? row.display_name : "",
                    },
                });
            },
        });
    }
}

registry.category("view_widgets").add("clinic_new_patient_btn", {
    component: ClinicNewPatientBtn,
});
