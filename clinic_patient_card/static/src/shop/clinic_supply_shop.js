/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class ClinicSupplyShop extends Component {
    static template = "clinic_patient_card.ClinicSupplyShop";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            offers: [],
            vendors: [],
            vendorOff: {},
            categories: [],
            catOff: {},
            search: "",
            sortBy: "name",
            cart: {},        // key `${product_id}_${vendor_id}` -> line
            cartOpen: false,
            detail: null,    // open product detail
        });
        onWillStart(() => this.load());
    }

    async load() {
        const sis = await this.orm.searchRead(
            "product.supplierinfo", [],
            ["partner_id", "product_tmpl_id", "product_id", "price", "delay"]
        );
        // resolve a product.product id + name for each template
        const tmplIds = [...new Set(sis.map((s) => s.product_tmpl_id && s.product_tmpl_id[0]).filter(Boolean))];
        const prods = tmplIds.length
            ? await this.orm.searchRead("product.product",
                [["product_tmpl_id", "in", tmplIds]],
                ["product_tmpl_id", "display_name"])
            : [];
        const byTmpl = {};
        for (const p of prods) {
            if (p.product_tmpl_id && !byTmpl[p.product_tmpl_id[0]]) {
                byTmpl[p.product_tmpl_id[0]] = p;
            }
        }
        const offers = [];
        const vmap = new Map();
        for (const s of sis) {
            if (!s.partner_id) {
                continue;
            }
            let pid, pname;
            if (s.product_id) {
                pid = s.product_id[0];
                pname = s.product_id[1];
            } else if (s.product_tmpl_id && byTmpl[s.product_tmpl_id[0]]) {
                const pp = byTmpl[s.product_tmpl_id[0]];
                pid = pp.id;
                pname = pp.display_name;
            } else {
                continue;
            }
            offers.push({
                key: `${pid}_${s.partner_id[0]}`,
                product_id: pid,
                name: pname,
                vendor_id: s.partner_id[0],
                vendor_name: s.partner_id[1],
                price: s.price || 0,
                delay: s.delay || 0,
            });
            vmap.set(s.partner_id[0], s.partner_id[1]);
        }
        // fetch image + category for every offered product
        const pids = [...new Set(offers.map((o) => o.product_id))];
        const details = pids.length
            ? await this.orm.searchRead("product.product", [["id", "in", pids]],
                ["image_128", "categ_id"])
            : [];
        const dmap = {};
        for (const d of details) {
            dmap[d.id] = d;
        }
        const cmap = new Map();
        for (const o of offers) {
            const d = dmap[o.product_id];
            o.image = (d && d.image_128) || false;
            o.hot = o.product_id % 3 === 0;
            o.categ_id = d && d.categ_id ? d.categ_id[0] : false;
            o.categ_name = d && d.categ_id ? d.categ_id[1] : "";
            if (o.categ_id) {
                cmap.set(o.categ_id, o.categ_name);
            }
        }
        this.state.offers = offers;
        this.state.vendors = [...vmap.entries()].map(([id, name]) => ({ id, name }));
        this.state.categories = [...cmap.entries()].map(([id, name]) => ({ id, name }));
    }

    get shownOffers() {
        const q = (this.state.search || "").toLowerCase();
        const list = this.state.offers.filter((o) => {
            if (this.state.vendorOff[o.vendor_id]) {
                return false;
            }
            if (o.categ_id && this.state.catOff[o.categ_id]) {
                return false;
            }
            if (q && !(`${o.name} ${o.vendor_name}`.toLowerCase().includes(q))) {
                return false;
            }
            return true;
        });
        const s = this.state.sortBy;
        const sorted = [...list];
        if (s === "price_asc") {
            sorted.sort((a, b) => a.price - b.price);
        } else if (s === "price_desc") {
            sorted.sort((a, b) => b.price - a.price);
        } else {
            sorted.sort((a, b) => a.name.localeCompare(b.name));
        }
        return sorted;
    }
    onSort(ev) {
        this.state.sortBy = ev.target.value;
    }

    toggleVendor(id) {
        this.state.vendorOff[id] = !this.state.vendorOff[id];
    }
    toggleCat(id) {
        this.state.catOff[id] = !this.state.catOff[id];
    }
    onSearch(ev) {
        this.state.search = ev.target.value;
    }

    addToCart(offer, qty = 1) {
        const key = offer.key || `${offer.product_id}_${offer.vendor_id}`;
        const c = this.state.cart[key];
        if (c) {
            c.qty += qty;
        } else {
            this.state.cart[key] = {
                product_id: offer.product_id,
                name: offer.name,
                vendor_id: offer.vendor_id,
                vendor_name: offer.vendor_name,
                price: offer.price,
                qty: qty,
            };
        }
        this.state.cartOpen = true;
    }

    async openDetail(offer) {
        const p = await this.orm.read("product.product", [offer.product_id],
            ["qty_available", "product_tmpl_id", "image_1920"]);
        let desc = "";
        if (p.length && p[0].product_tmpl_id) {
            const t = await this.orm.read("product.template", [p[0].product_tmpl_id[0]],
                ["description_sale", "description"]);
            desc = (t.length && (t[0].description_sale || t[0].description)) || "";
        }
        this.state.detail = {
            ...offer,
            qty_available: p.length ? p[0].qty_available : 0,
            image_big: (p.length && p[0].image_1920) || offer.image,
            desc,
            addQty: 1,
        };
    }
    closeDetail() {
        this.state.detail = null;
    }
    setDetailQty(ev) {
        const v = parseFloat(ev.target.value);
        this.state.detail.addQty = isNaN(v) || v < 1 ? 1 : v;
    }
    addDetailToCart() {
        const d = this.state.detail;
        this.addToCart(d, d.addQty);
        this.closeDetail();
    }
    setQty(key, ev) {
        const v = parseFloat(ev.target.value);
        if (this.state.cart[key]) {
            this.state.cart[key].qty = isNaN(v) || v < 1 ? 1 : v;
        }
    }
    removeLine(key) {
        delete this.state.cart[key];
    }
    get cartLines() {
        return Object.entries(this.state.cart).map(([key, l]) => ({ key, ...l }));
    }
    get cartCount() {
        return this.cartLines.length;
    }
    get cartTotal() {
        return this.cartLines.reduce((s, l) => s + l.price * l.qty, 0);
    }
    toggleCart() {
        this.state.cartOpen = !this.state.cartOpen;
    }

    async checkout() {
        const cart = this.cartLines.map((l) => ({
            product_id: l.product_id,
            vendor_id: l.vendor_id,
            qty: l.qty,
            price: l.price,
        }));
        if (!cart.length) {
            return;
        }
        const poIds = await this.orm.call("purchase.order", "clinic_create_rfqs", [cart]);
        this.state.cart = {};
        this.state.cartOpen = false;
        this.notification.add(
            _t("Sent to suppliers — %s RFQ(s) created", (poIds || []).length),
            { type: "success" }
        );
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Requests for Quotation"),
            res_model: "purchase.order",
            domain: [["id", "in", poIds || []]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("clinic_supply_shop", ClinicSupplyShop);
