/** @odoo-module **/
// Full-screen picture viewer: previous / next, X in the top-right corner, keyboard
// arrows + Esc. Opened from the gallery (and from the picture page) by a click.
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { imageUrl } from "@web/core/utils/urls";
import { ImageField, imageField } from "@web/views/fields/image/image_field";

export class ClinicLightbox extends Component {
    static template = "clinic_patient_card.Lightbox";
    static props = { items: Array, index: Number, close: Function };

    setup() {
        this.state = useState({ i: this.props.index });
        this.onKey = (ev) => {
            if (ev.key === "Escape") {
                this.props.close();
            } else if (ev.key === "ArrowRight") {
                this.next();
            } else if (ev.key === "ArrowLeft") {
                this.prev();
            }
        };
        onMounted(() => window.addEventListener("keydown", this.onKey, true));
        onWillUnmount(() => window.removeEventListener("keydown", this.onKey, true));
    }
    get cur() {
        return this.props.items[this.state.i];
    }
    get many() {
        return this.props.items.length > 1;
    }
    next() {
        this.state.i = (this.state.i + 1) % this.props.items.length;
    }
    prev() {
        this.state.i = (this.state.i - 1 + this.props.items.length) % this.props.items.length;
    }
}

/** read-only picture for the gallery cards: a click opens the viewer over ALL pictures */
export class ClinicZoomImage extends ImageField {
    static template = "clinic_patient_card.ZoomImage";

    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    itemOf(rec) {
        if (!rec.resId || !rec.data[this.props.name]) {
            return null;
        }
        return {
            id: rec.resId,
            name: rec.data.name || "",
            url: imageUrl(rec.resModel, rec.resId, this.props.name, { unique: rec.data.write_date }),
        };
    }

    onZoom() {
        const rec = this.props.record;
        let records = [rec];
        try {
            const list = rec.model.root.data.xray_ids;
            if (list && list.records) {
                records = list.records;
            }
        } catch (e) {
            /* single picture */
        }
        const items = records.map((r) => this.itemOf(r)).filter(Boolean);
        const index = Math.max(0, items.findIndex((it) => it.id === rec.resId));
        if (items.length) {
            this.dialog.add(ClinicLightbox, { items, index });
        }
    }
}

registry.category("fields").add("clinic_zoom_image", {
    ...imageField,
    component: ClinicZoomImage,
});
