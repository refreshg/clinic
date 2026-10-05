/** @odoo-module **/
// Single image field where a click on the EMPTY picture (the grey camera "+")
// opens the file chooser straight away — the standard widget only uploads
// through the small hover pencil. Used on the product form (supplier products).
import { registry } from "@web/core/registry";
import { useRef } from "@odoo/owl";
import { ImageField, imageField } from "@web/views/fields/image/image_field";

export class ClinicImageClick extends ImageField {
    static template = "clinic_patient_card.ImageClick";

    setup() {
        super.setup();
        this.rootRef = useRef("root");
    }

    onRootClick(ev) {
        if (this.props.readonly || this.props.record.data[this.props.name]
                || ev.target.closest("button, input")) {
            return;
        }
        this.rootRef.el.querySelector(".o_select_file_button")?.click();
    }
}

registry.category("fields").add("clinic_image_click", {
    ...imageField,
    component: ClinicImageClick,
});
