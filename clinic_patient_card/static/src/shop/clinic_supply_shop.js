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
            categories: [],       // raw category rows
            banners: [],
            bestsellerIds: [],
            wishlist: [],         // product ids
            lastOrder: false,
            vendorOff: {},
            brandOff: {},
            catId: false,         // selected top category
            subcatId: false,
            wishlistOnly: false,
            search: "",
            sortBy: "name",
            cart: {},             // `${product_id}_${vendor_id}` -> line
            cartOpen: false,
            detail: null,
            bannerIdx: 0,
        });
        onWillStart(() => this.load());
    }

    async load() {
        const data = await this.orm.call("product.template", "clinic_shop_data", []);
        this.state.offers = data.offers;
        this.state.categories = data.categories;
        this.state.banners = data.banners;
        this.state.bestsellerIds = data.bestseller_ids;
        this.state.wishlist = data.wishlist_ids;
        this.state.lastOrder = data.last_order;
    }

    // ------------------------------------------------------------------
    // catalogue structure
    // ------------------------------------------------------------------
    get vendors() {
        const m = new Map();
        for (const o of this.state.offers) {
            m.set(o.vendor_id, o.vendor_name);
        }
        return [...m.entries()].map(([id, name]) => ({ id, name }));
    }
    get brands() {
        const m = new Map();
        for (const o of this.state.offers) {
            if (o.brand_id) {
                m.set(o.brand_id, o.brand);
            }
        }
        return [...m.entries()].map(([id, name]) => ({ id, name }));
    }
    get topCategories() {
        // top-level categories that actually hold shop offers, keeping photos
        const used = new Set(this.state.offers.map((o) => o.top_categ_id));
        return this.state.categories.filter(
            (c) => !c.parent_id && used.has(c.id) && c.shop_visible !== false);
    }
    get subCategories() {
        if (!this.state.catId) {
            return [];
        }
        const used = new Set(this.state.offers.map((o) => o.categ_id));
        return this.state.categories.filter(
            (c) => c.parent_id === this.state.catId && used.has(c.id)
                && c.shop_visible !== false);
    }
    pickCat(id) {
        this.state.catId = this.state.catId === id ? false : id;
        this.state.subcatId = false;
    }
    pickSubcat(id) {
        this.state.subcatId = this.state.subcatId === id ? false : id;
    }

    // ------------------------------------------------------------------
    // filtering / sorting
    // ------------------------------------------------------------------
    _passes(o) {
        if (this.state.vendorOff[o.vendor_id]) {
            return false;
        }
        if (o.brand_id && this.state.brandOff[o.brand_id]) {
            return false;
        }
        if (this.state.subcatId && o.categ_id !== this.state.subcatId) {
            return false;
        }
        if (this.state.catId && !this.state.subcatId
                && o.top_categ_id !== this.state.catId) {
            return false;
        }
        if (this.state.wishlistOnly
                && !this.state.wishlist.includes(o.product_id)) {
            return false;
        }
        const q = (this.state.search || "").toLowerCase();
        if (q && !(`${o.name} ${o.vendor_name} ${o.brand}`.toLowerCase().includes(q))) {
            return false;
        }
        return true;
    }
    get shownOffers() {
        const list = this.state.offers.filter((o) => this._passes(o));
        const s = this.state.sortBy;
        if (s === "price_asc") {
            list.sort((a, b) => a.price - b.price);
        } else if (s === "price_desc") {
            list.sort((a, b) => b.price - a.price);
        } else {
            list.sort((a, b) => a.name.localeCompare(b.name));
        }
        return list;
    }
    // reviewer item 14: similar products appear automatically while searching —
    // same category as the found ones, not matching the text themselves
    get similarOffers() {
        const q = (this.state.search || "").toLowerCase();
        if (!q || !this.shownOffers.length) {
            return [];
        }
        const cats = new Set(this.shownOffers.map((o) => o.categ_id));
        const shownKeys = new Set(this.shownOffers.map((o) => o.key));
        const seen = new Set();
        const out = [];
        for (const o of this.state.offers) {
            if (shownKeys.has(o.key) || !cats.has(o.categ_id)
                    || seen.has(o.product_id)) {
                continue;
            }
            seen.add(o.product_id);
            out.push(o);
            if (out.length >= 6) {
                break;
            }
        }
        return out;
    }

    get isPlainView() {
        return !this.state.search && !this.state.catId
            && !this.state.wishlistOnly;
    }
    _uniqueByProduct(list, limit) {
        const seen = new Set();
        const out = [];
        for (const o of list) {
            if (seen.has(o.product_id)) {
                continue;
            }
            seen.add(o.product_id);
            out.push(o);
            if (out.length >= limit) {
                break;
            }
        }
        return out;
    }
    get sponsoredOffers() {
        return this._uniqueByProduct(
            this.state.offers.filter((o) => o.sponsored), 8);
    }
    get newOffers() {
        return this._uniqueByProduct(
            this.state.offers.filter((o) => o.is_new), 8);
    }
    get bestsellerOffers() {
        const out = [];
        for (const pid of this.state.bestsellerIds) {
            const o = this.state.offers.find((x) => x.product_id === pid);
            if (o) {
                out.push(o);
            }
        }
        return out;
    }

    onSort(ev) {
        this.state.sortBy = ev.target.value;
    }
    toggleVendor(id) {
        this.state.vendorOff[id] = !this.state.vendorOff[id];
    }
    toggleBrand(id) {
        this.state.brandOff[id] = !this.state.brandOff[id];
    }
    onSearch(ev) {
        this.state.search = ev.target.value;
    }
    toggleWishlistOnly() {
        this.state.wishlistOnly = !this.state.wishlistOnly;
    }

    // ------------------------------------------------------------------
    // wishlist
    // ------------------------------------------------------------------
    inWishlist(o) {
        return this.state.wishlist.includes(o.product_id);
    }
    async toggleWish(o) {
        const on = await this.orm.call(
            "product.template", "clinic_wishlist_toggle", [o.product_id]);
        if (on && !this.state.wishlist.includes(o.product_id)) {
            this.state.wishlist.push(o.product_id);
        } else if (!on) {
            this.state.wishlist = this.state.wishlist.filter(
                (id) => id !== o.product_id);
        }
    }

    // ------------------------------------------------------------------
    // banners
    // ------------------------------------------------------------------
    get banner() {
        const b = this.state.banners;
        return b.length ? b[this.state.bannerIdx % b.length] : false;
    }
    nextBanner(step) {
        const n = this.state.banners.length || 1;
        this.state.bannerIdx = (this.state.bannerIdx + step + n) % n;
    }

    // ------------------------------------------------------------------
    // cart
    // ------------------------------------------------------------------
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
    // reviewer item 13: repeat the last order, still editable in the cart
    repeatLastOrder() {
        const lo = this.state.lastOrder;
        if (!lo) {
            return;
        }
        for (const l of lo.lines) {
            let offer = this.state.offers.find(
                (o) => o.product_id === l.product_id
                    && o.vendor_id === l.vendor_id);
            if (!offer) {
                offer = this.state.offers.find(
                    (o) => o.product_id === l.product_id);
            }
            if (offer) {
                this.addToCart(offer, l.qty);
            }
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
        // reviewer item 15: price/vendor comparison — every vendor's offer
        // for this product, cheapest first
        const others = this.state.offers
            .filter((o) => o.product_id === offer.product_id)
            .sort((a, b) => a.price - b.price);
        // similar products (same category), one offer per product
        const similar = this._uniqueByProduct(
            this.state.offers.filter(
                (o) => o.categ_id === offer.categ_id
                    && o.product_id !== offer.product_id), 6);
        this.state.detail = {
            ...offer,
            qty_available: p.length ? p[0].qty_available : 0,
            image_big: (p.length && p[0].image_1920) || offer.image,
            desc,
            addQty: 1,
            vendorOffers: others,
            similar,
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
