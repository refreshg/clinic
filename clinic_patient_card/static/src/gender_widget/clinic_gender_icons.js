/** @odoo-module **/
// Gender card picker — avatar cards instead of radio buttons (design ref: docs/Design/).
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const IMG_BASE = "/clinic_patient_card/static/src/gender_widget/img/";

export class ClinicGenderIcons extends Component {
    static template = "clinic_patient_card.GenderIcons";
    static props = { ...standardFieldProps };
    static supportedTypes = ["selection"];

    get options() {
        return this.props.record.fields[this.props.name].selection || [];
    }

    // once a gender is picked only that card stays; clicking it again clears
    // the pick and brings the other cards back
    get visibleOptions() {
        const value = this.currentValue;
        return value ? this.options.filter((opt) => opt[0] === value) : this.options;
    }

    get currentValue() {
        return this.props.record.data[this.props.name];
    }

    pick(value) {
        if (this.props.readonly) return;
        const next = this.currentValue === value ? false : value;
        this.props.record.update({ [this.props.name]: next });
    }

    imgSrc(key) {
        if (key === "male") return IMG_BASE + "male.svg";
        if (key === "female") return IMG_BASE + "female.svg";
        return IMG_BASE + "other.svg";
    }
}

registry.category("fields").add("clinic_gender_icons", {
    component: ClinicGenderIcons,
    supportedTypes: ["selection"],
});
