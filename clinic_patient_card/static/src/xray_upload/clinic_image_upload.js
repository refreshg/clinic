/** @odoo-module **/
// Image field where a click on the EMPTY picture (the grey camera "+") opens the
// file chooser straight away, and the chooser accepts SEVERAL files: the first
// fills this record, every further one becomes its own picture record for the
// same patient. (The standard widget only uploads one file through the small
// hover pencil.)
import { registry } from "@web/core/registry";
import { useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { imageUrl } from "@web/core/utils/urls";
import { ImageField, imageField } from "@web/views/fields/image/image_field";
import { ClinicLightbox } from "./clinic_lightbox";

function readB64(file) {
    return new Promise((resolve, reject) => {
        const r = new FileReader();
        r.onload = () => resolve(String(r.result).split(",")[1]);
        r.onerror = reject;
        r.readAsDataURL(file);
    });
}

export class ClinicImageUpload extends ImageField {
    static template = "clinic_patient_card.ImageUpload";

    setup() {
        super.setup();
        this.fileInput = useRef("fileInput");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
    }

    get partnerId() {
        const p = this.props.record.data.partner_id;
        if (!p) { return false; }
        return Array.isArray(p) ? p[0] : p.id;
    }

    onImgClick() {
        const rec = this.props.record;
        if (rec.data[this.props.name]) {
            // a picture is there: click = full-screen view
            if (rec.resId) {
                this.dialog.add(ClinicLightbox, {
                    index: 0,
                    items: [{
                        id: rec.resId,
                        name: rec.data.name || "",
                        url: imageUrl(rec.resModel, rec.resId, this.props.name, { unique: rec.data.write_date }),
                    }],
                });
            }
            return;
        }
        if (this.props.readonly) {
            return;
        }
        this.fileInput.el.click();
    }

    async onFilesChosen(ev) {
        const files = [...ev.target.files];
        ev.target.value = "";
        if (!files.length) { return; }
        const extra = files.slice(1);
        if (extra.length && !this.partnerId) {
            this.notification.add(
                _t("რამდენიმე სურათისთვის ჯერ აირჩიე პაციენტი"), { type: "warning" });
            return;
        }
        const [first, ...rest] = files;
        const rec = this.props.record;
        const update = { [this.props.name]: await readB64(first) };
        if ("filename" in rec.data) { update.filename = first.name; }
        if ("name" in rec.data && !rec.data.name) { update.name = first.name.replace(/\.[^.]+$/, ""); }
        await rec.update(update);
        if (rest.length) {
            for (const f of rest) {
                await this.orm.create("clinic.patient.document", [{
                    partner_id: this.partnerId,
                    doc_type: "xray",
                    name: f.name.replace(/\.[^.]+$/, ""),
                    filename: f.name,
                    attachment: await readB64(f),
                }]);
            }
            this.notification.add(
                _t("დამატებით აიტვირთა სურათები: ") + rest.length, { type: "success" });
        }
    }
}

registry.category("fields").add("clinic_image_upload", {
    ...imageField,
    component: ClinicImageUpload,
});
