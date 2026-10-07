/** @odoo-module **/
// "📎 სინჯის ატვირთვა" next to the allergy answer on the patient card: one click
// opens the file chooser (several files allowed); each file becomes an allergy
// document of the patient (the same list as the doctor's Medical tab and the
// visit page), and the card reloads to show it.
import { Component, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

function readB64(file) {
    return new Promise((resolve, reject) => {
        const r = new FileReader();
        r.onload = () => resolve(String(r.result).split(",")[1]);
        r.onerror = reject;
        r.readAsDataURL(file);
    });
}

export class ClinicAllergyUpload extends Component {
    static template = "clinic_patient_card.AllergyUpload";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.fileInput = useRef("fileInput");
    }

    get count() {
        return this.props.record.data.allergy_doc_count || 0;
    }

    async choose() {
        const rec = this.props.record;
        // the documents hang on the patient: a new card must be saved first
        if (!rec.resId || rec.isDirty) {
            if (!(await rec.save())) { return; }
        }
        this.fileInput.el.click();
    }

    async onFiles(ev) {
        const files = [...ev.target.files];
        ev.target.value = "";
        if (!files.length) { return; }
        const rec = this.props.record;
        const vals = [];
        for (const f of files) {
            vals.push({
                partner_id: rec.resId,
                doc_type: "allergy_doc",
                name: f.name.replace(/\.[^.]+$/, ""),
                filename: f.name,
                attachment: await readB64(f),
            });
        }
        await this.orm.create("clinic.patient.document", vals);
        await rec.load();
        this.notification.add(_t("ატვირთულია: ") + files.length, { type: "success" });
    }
}

registry.category("view_widgets").add("clinic_allergy_upload", {
    component: ClinicAllergyUpload,
});
