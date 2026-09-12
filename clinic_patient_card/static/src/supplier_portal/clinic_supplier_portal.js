/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Supplier Portal — "My Products".
 *
 * A supplier user manages the products they publish. Everything saved here
 * becomes a clinic supply with a product.supplierinfo line for this vendor,
 * so it appears immediately in the clinic Supply Shop. Backend methods on
 * product.template enforce that a supplier only touches their own products.
 */
export class ClinicSupplierPortal extends Component {
    static template = "clinic_patient_card.ClinicSupplierPortal";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            vendor: null,
            products: [],
            categories: [],
            brands: [],
            editing: null, // {id?, name, price, delay, categ_id, image}
        });
        onWillStart(() => this.load());
    }

    async load() {
        const res = await this.orm.call("product.template", "clinic_supplier_products", []);
        this.state.vendor = res.vendor || null;
        this.state.products = res.products || [];
        this.state.categories = res.categories || [];
        this.state.brands = res.brands || [];
        this.state.loading = false;
    }

    // ---- editor ----
    newProduct() {
        this.state.editing = {
            id: false,
            name: "",
            price: 0,
            delay: 3,
            categ_id: this.state.categories.length ? this.state.categories[0].id : false,
            brand_id: false,
            brand_is_new: false,
            brand_new: "",
            preorder: false,
            image: false,
            image_preview: false,
        };
    }
    editProduct(p) {
        this.state.editing = {
            id: p.id,
            name: p.name,
            price: p.price,
            delay: p.delay,
            categ_id: p.categ_id || false,
            brand_id: p.brand_id || false,
            brand_is_new: false,
            brand_new: "",
            preorder: !!p.preorder,
            image: undefined, // undefined => keep existing image on save
            image_preview: p.image_128 ? "data:image/png;base64," + p.image_128 : false,
        };
    }
    cancelEdit() {
        this.state.editing = null;
    }
    onField(field, ev) {
        let v = ev.target.value;
        if (field === "price") {
            v = parseFloat(v) || 0;
        } else if (field === "delay") {
            v = parseInt(v, 10) || 0;
        } else if (field === "categ_id") {
            v = parseInt(v, 10) || false;
        } else if (field === "brand_id") {
            if (v === "__new") {
                this.state.editing.brand_is_new = true;
                this.state.editing.brand_id = false;
                return;
            }
            this.state.editing.brand_is_new = false;
            v = parseInt(v, 10) || false;
        }
        this.state.editing[field] = v;
    }
    onImage(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) {
            return;
        }
        const reader = new FileReader();
        reader.onload = () => {
            const b64 = String(reader.result).split(",")[1] || false;
            this.state.editing.image = b64;
            this.state.editing.image_preview = reader.result;
        };
        reader.readAsDataURL(file);
    }

    async save() {
        const e = this.state.editing;
        if (!e.name || !e.name.trim()) {
            this.notification.add(_t("Product name is required."), { type: "warning" });
            return;
        }
        const vals = {
            name: e.name,
            price: e.price,
            delay: e.delay,
            categ_id: e.categ_id,
            brand_id: e.brand_id,
            preorder: e.preorder,
        };
        if (e.brand_is_new && e.brand_new.trim()) {
            vals.brand_new = e.brand_new.trim();
        }
        if (e.id) {
            vals.id = e.id;
        }
        if (e.image !== undefined) {
            vals.image = e.image; // new/base64 or false to clear
        }
        await this.orm.call("product.template", "clinic_supplier_save_product", [vals]);
        this.state.editing = null;
        await this.load();
        this.notification.add(_t("Product saved — it is now live in the clinic shop."), {
            type: "success",
        });
    }

    async toggleShop(p) {
        const on = await this.orm.call(
            "product.template", "clinic_supplier_toggle_shop", [p.id]);
        p.shop_published = on;
        this.notification.add(
            on ? _t("Product is visible in the shop again.")
               : _t("Product hidden from the shop (price kept)."),
            { type: "info" });
    }

    async unpublish(p) {
        await this.orm.call("product.template", "clinic_supplier_unpublish", [p.id]);
        await this.load();
        this.notification.add(_t("Product removed from the shop."), { type: "info" });
    }

    openOrders() {
        // The supplier fulfils clinic orders as their own sales orders.
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("My Orders"),
            res_model: "sale.order",
            domain: [["is_clinic_order", "=", true]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("clinic_supplier_portal", ClinicSupplierPortal);
