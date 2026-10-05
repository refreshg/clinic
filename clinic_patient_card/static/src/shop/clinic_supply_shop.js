/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { ClinicLightbox } from "@clinic_patient_card/xray_upload/clinic_lightbox";

export class ClinicSupplyShop extends Component {
    static template = "clinic_patient_card.ClinicSupplyShop";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.state = useState({
            offers: [],
            categories: [],       // raw category rows
            banners: [],
            bestsellerIds: [],
            wishlist: [],         // product ids
            lastOrder: false,
            vendorOff: {},
            brandOff: {},
            home: true,           // the shop opens on the home page (banners + sponsored + new)
            catId: false,         // selected top category
            subcatId: false,
            wishlistOnly: false,
            search: "",
            sortBy: "name",
            cart: {},             // `${product_id}_${vendor_id}` -> line
            cartOpen: false,
            compareKeys: [],      // offer keys picked for comparison (max 4)
            compareOpen: false,
            detail: null,
            bannerIdx: 0,
        });
        onWillStart(() => this.load());
        // more than 2 banners → the pair rotates instead of stacking
        onMounted(() => {
            this._bannerTimer = setInterval(() => {
                if (this.state.banners.length > 2 && !this.state.detail) {
                    this.nextBanner(1);
                }
            }, 6000);
        });
        onWillUnmount(() => clearInterval(this._bannerTimer));
    }

    async load() {
        const data = await this.orm.call("product.template", "clinic_shop_data", []);
        this.state.offers = data.offers;
        this.state.categories = data.categories;
        this.state.banners = data.banners;
        this.state.bestsellerIds = data.bestseller_ids;
        this.state.wishlist = data.wishlist_ids;
        this.state.lastOrder = data.last_order;
        this._restore();
    }

    // ---- cart + compare survive a page refresh (per-user localStorage) ----
    get _storeKey() {
        return "clinic_shop_" + (user.userId || 0);
    }
    _persist() {
        try {
            localStorage.setItem(this._storeKey, JSON.stringify({
                cart: this.state.cart,
                compareKeys: this.state.compareKeys,
            }));
        } catch (e) { /* storage full/blocked — non-fatal */ }
    }
    _restore() {
        try {
            const raw = localStorage.getItem(this._storeKey);
            if (!raw) {
                return;
            }
            const d = JSON.parse(raw);
            this.state.cart = d.cart || {};
            // keep only compare picks whose offers still exist
            this.state.compareKeys = (d.compareKeys || []).filter(
                (k) => this.state.offers.some((o) => o.key === k));
            if (Object.keys(this.state.cart).length) {
                this.state.cartOpen = true;
            }
        } catch (e) { /* corrupt storage — start clean */ }
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
            (c) => !c.parent_id && (used.has(c.id) || c.pinned) && c.shop_visible !== false);
    }
    // ---- category tree (any depth) ----
    get _catById() {
        const m = new Map();
        for (const c of this.state.categories) {
            m.set(c.id, c);
        }
        return m;
    }
    // categories that hold offers anywhere in their subtree (incl. ancestors)
    get _catsWithOffers() {
        const byId = this._catById;
        const used = new Set();
        for (const o of this.state.offers) {
            let c = byId.get(o.categ_id);
            while (c && !used.has(c.id)) {
                used.add(c.id);
                c = byId.get(c.parent_id);
            }
        }
        return used;
    }
    _children(parentId) {
        const used = this._catsWithOffers;
        return this.state.categories.filter(
            (c) => c.parent_id === parentId && (used.has(c.id) || c.pinned)
                && c.shop_visible !== false);
    }
    _descendants(catId) {
        const out = new Set([catId]);
        let frontier = [catId];
        while (frontier.length) {
            const next = [];
            for (const c of this.state.categories) {
                if (frontier.includes(c.parent_id) && !out.has(c.id)) {
                    out.add(c.id);
                    next.push(c.id);
                }
            }
            frontier = next;
        }
        return out;
    }
    // one chips-row per level along the selected path — unlimited depth
    get chipRows() {
        if (!this.state.catId) {
            return [];
        }
        const byId = this._catById;
        // selected path: subcat and its ancestors up to (excluding) the top cat
        const path = new Set();
        let n = this.state.subcatId ? byId.get(this.state.subcatId) : null;
        while (n && n.id !== this.state.catId) {
            path.add(n.id);
            n = byId.get(n.parent_id);
        }
        const rows = [];
        let parent = this.state.catId;
        for (;;) {
            const kids = this._children(parent);
            if (!kids.length) {
                break;
            }
            const selected = kids.find((k) => path.has(k.id));
            rows.push({ parent, kids, selectedId: selected ? selected.id : false });
            if (!selected) {
                break;
            }
            parent = selected.id;
        }
        return rows;
    }
    /** left-column menu: every top category; the branch of the selection is opened
     * level by level (children shown even while empty, they are pinned) */
    get menuRows() {
        const byId = this._catById;
        const path = new Set();
        let c = this.state.subcatId ? byId.get(this.state.subcatId) : null;
        while (c) {
            path.add(c.id);
            c = byId.get(c.parent_id);
        }
        if (this.state.catId) {
            path.add(this.state.catId);
        }
        const rows = [];
        const walk = (cat, depth, parent) => {
            const on = depth === 0 ? this.state.catId === cat.id && !this.state.subcatId
                : this.state.subcatId === cat.id;
            rows.push({ id: cat.id, name: cat.name, depth, parent, on, count: this.catCount(cat.id) });
            if (path.has(cat.id)) {
                for (const k of this._children(cat.id)) {
                    walk(k, depth + 1, cat.id);
                }
            }
        };
        for (const t of this.topCategories) {
            walk(t, 0, false);
        }
        return rows;
    }
    pickMenu(row) {
        if (!row.depth) {
            this.pickCat(row.id);
        } else {
            this.pickSubcat(row.id, row.parent);
        }
    }
    /** number of offers inside a category (any depth) — shown on the card / in the menu */
    catCount(id) {
        const tree = this._descendants(id);
        return this.state.offers.filter((o) => tree.has(o.categ_id)).length;
    }
    pickCat(id) {
        this.state.home = false;
        this.state.catId = id && this.state.catId !== id ? id : false;
        this.state.subcatId = false;
    }
    pickSubcat(id, parent) {
        if (!id) {
            // "ყველა" on this row → selection climbs back to the row's parent
            this.state.subcatId = parent === this.state.catId ? false : parent;
        } else {
            this.state.subcatId = this.state.subcatId === id ? (parent === this.state.catId ? false : parent) : id;
        }
    }

    // ------------------------------------------------------------------
    // filtering / sorting
    // ------------------------------------------------------------------
    // vendor/brand toggles apply EVERYWHERE (grid + strips + similar)
    _passesFilters(o) {
        if (this.state.vendorOff[o.vendor_id]) {
            return false;
        }
        if (o.brand_id && this.state.brandOff[o.brand_id]) {
            return false;
        }
        return true;
    }
    _passes(o) {
        if (!this._passesFilters(o)) {
            return false;
        }
        if (this.state.subcatId
                && !this._descendants(this.state.subcatId).has(o.categ_id)) {
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
                    || seen.has(o.product_id) || !this._passesFilters(o)) {
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

    // front page: one titled section per category (marketplace style)
    get categorySections() {
        const out = [];
        for (const c of this.topCategories) {
            const inTree = this._descendants(c.id);
            const seen = new Set();
            const offers = [];
            for (const o of this.state.offers) {
                if (!inTree.has(o.categ_id) || !this._passesFilters(o)
                        || seen.has(o.product_id)) {
                    continue;
                }
                seen.add(o.product_id);
                offers.push(o);
            }
            if (offers.length) {
                out.push({ cat: c, offers: offers.slice(0, 8), total: offers.length });
            }
        }
        return out;
    }

    /** "all categories" page: the category cards */
    get isPlainView() {
        return !this.state.home && !this.state.search && !this.state.catId
            && !this.state.wishlistOnly;
    }
    /** home page: banners + sponsored + new + bestsellers */
    get isHomeView() {
        return this.state.home && !this.state.search && !this.state.catId
            && !this.state.wishlistOnly;
    }
    goHome() {
        this.state.home = true;
        this.state.catId = false;
        this.state.subcatId = false;
        this.state.wishlistOnly = false;
        this.state.search = "";
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
            this.state.offers.filter(
                (o) => o.sponsored && this._passesFilters(o)), 8);
    }
    get newOffers() {
        return this._uniqueByProduct(
            this.state.offers.filter(
                (o) => o.is_new && this._passesFilters(o)), 8);
    }
    get bestsellerOffers() {
        const out = [];
        for (const pid of this.state.bestsellerIds) {
            const o = this.state.offers.find(
                (x) => x.product_id === pid && this._passesFilters(x));
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
    // compare (reviewer: pick products like real shops → side-by-side table)
    // ------------------------------------------------------------------
    inCompare(o) {
        return this.state.compareKeys.includes(o.key);
    }
    toggleCompare(o) {
        const k = this.state.compareKeys;
        if (k.includes(o.key)) {
            this.state.compareKeys = k.filter((x) => x !== o.key);
        } else if (k.length >= 4) {
            this.notification.add(_t("შედარებაში მაქსიმუმ 4 პროდუქტი ეტევა"), { type: "warning" });
        } else {
            k.push(o.key);
        }
        this._persist();
    }
    get compareOffers() {
        return this.state.compareKeys
            .map((k) => this.state.offers.find((o) => o.key === k))
            .filter(Boolean);
    }
    openCompare() {
        if (this.compareOffers.length >= 2) {
            this.state.compareOpen = true;
        } else {
            this.notification.add(_t("აირჩიე მინიმუმ 2 პროდუქტი ⇄ ღილაკით"), { type: "info" });
        }
    }
    clearCompare() {
        this.state.compareKeys = [];
        this.state.compareOpen = false;
        this._persist();
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
    // the two banners currently occupying the two slots
    get visibleBanners() {
        const b = this.state.banners;
        if (b.length <= 2) {
            return b;
        }
        const i = this.state.bannerIdx % b.length;
        return [b[i], b[(i + 1) % b.length]];
    }
    openBanner(bn) {
        if (bn.link) {
            window.open(bn.link, "_blank");
        }
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
        this._persist();
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
        const d = await this.orm.call("product.template", "clinic_shop_detail",
            [offer.product_id, offer.vendor_id]);
        // similar products (same category), one offer per product
        const similar = this._uniqueByProduct(
            this.state.offers.filter(
                (o) => o.categ_id === offer.categ_id
                    && o.product_id !== offer.product_id), 6);
        // preselect the options of the variant the card showed
        const cur = d.variants.find((v) => v.id === d.current) || d.variants[0];
        const selected = {};
        for (const opt of d.options) {
            const hit = opt.values.find((x) => cur && cur.combo.includes(x.id));
            selected[opt.id] = hit ? hit.id : (opt.values[0] && opt.values[0].id);
        }
        const reviews = await this.orm.call("product.template", "clinic_shop_reviews", [d.tmpl_id]);
        this.state.detail = {
            ...offer,
            tmpl_id: d.tmpl_id,
            reviews,
            draft: this._newReviewDraft(reviews),
            media: d.media,
            mediaIdx: 0,
            options: d.options,
            variants: d.variants,
            selected,
            desc: d.desc,
            addQty: 1,
            similar,
        };
    }
    /** products with options (colour, size…) open the window first: the choice is made BEFORE ordering */
    addOrChoose(o) {
        if (o.multi) {
            this.openDetail(o);
        } else {
            this.addToCart(o);
        }
    }
    // ---- reviews inside the product window ----
    _newReviewDraft(r) {
        return {
            rating: r && r.mine ? r.mine.rating : 0,
            text: r && r.mine ? r.mine.text : "",
            images: [],
            open: false,
        };
    }
    setStars(n) {
        this.state.detail.draft.rating = n;
    }
    onReviewImages(ev) {
        for (const f of [...ev.target.files]) {
            const rd = new FileReader();
            rd.onload = () => {
                this.state.detail.draft.images.push({
                    preview: rd.result, b64: String(rd.result).split(",")[1] });
            };
            rd.readAsDataURL(f);
        }
        ev.target.value = "";
    }
    dropReviewImage(i) {
        this.state.detail.draft.images.splice(i, 1);
    }
    async saveReview() {
        const d = this.state.detail;
        if (!d.draft.rating) {
            this.notification.add(_t("აირჩიე ვარსკვლავები"), { type: "warning" });
            return;
        }
        await this.orm.call("product.template", "clinic_shop_review_save",
            [d.tmpl_id, d.draft.rating, d.draft.text, d.draft.images.map((x) => x.b64)]);
        d.reviews = await this.orm.call("product.template", "clinic_shop_reviews", [d.tmpl_id]);
        d.draft = this._newReviewDraft(d.reviews);
        this.notification.add(_t("შეფასება შენახულია"), { type: "success" });
    }
    async deleteReview(r) {
        const d = this.state.detail;
        await this.orm.call("product.template", "clinic_shop_review_delete", [r.id]);
        d.reviews = await this.orm.call("product.template", "clinic_shop_reviews", [d.tmpl_id]);
        d.draft = this._newReviewDraft(d.reviews);
    }
    openReviewPhoto(images, i) {
        this.dialog.add(ClinicLightbox, {
            index: i, items: images.map((x, k) => ({ id: k, name: "", url: x.url })),
        });
    }
    stars(n) {
        return "★".repeat(Math.round(n)) + "☆".repeat(5 - Math.round(n));
    }
    // ---- product window helpers ----
    get detailVariant() {
        const d = this.state.detail;
        if (!d) { return null; }
        const want = Object.values(d.selected).filter(Boolean);
        return d.variants.find((v) => want.every((id) => v.combo.includes(id))
            && v.combo.length === want.length) || d.variants[0] || null;
    }
    get detailPrice() {
        const v = this.detailVariant;
        return v ? v.price : this.state.detail.price;
    }
    get detailQty() {
        const v = this.detailVariant;
        return v ? v.qty : 0;
    }
    /** stock of the supplier's warehouse for one option value, combined with the OTHER
     * options already chosen (so "L" shows how many L of the chosen colour are left) */
    optionStock(optId, valueId) {
        const d = this.state.detail;
        const want = [];
        for (const o of d.options) {
            const id = o.id === optId ? valueId : d.selected[o.id];
            if (id) { want.push(id); }
        }
        return d.variants
            .filter((v) => want.every((id) => v.combo.includes(id)))
            .reduce((s, v) => s + (v.qty > 0 ? v.qty : 0), 0);
    }
    get detailOrderable() {
        const d = this.state.detail;
        return this.detailQty > 0 || d.preorder;
    }
    pickOption(optId, valueId) {
        this.state.detail.selected[optId] = valueId;
    }
    get detailMedia() {
        const d = this.state.detail;
        return d && d.media.length ? d.media[d.mediaIdx] : null;
    }
    mediaGo(step) {
        const d = this.state.detail;
        const n = d.media.length;
        if (n) { d.mediaIdx = (d.mediaIdx + step + n) % n; }
    }
    setMedia(i) {
        this.state.detail.mediaIdx = i;
    }
    /** YouTube / Vimeo link -> embeddable url; anything else is treated as a video file */
    videoEmbed(url) {
        let m = /(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{6,})/.exec(url || "");
        if (m) { return { iframe: "https://www.youtube.com/embed/" + m[1] }; }
        m = /vimeo\.com\/(?:video\/)?(\d+)/.exec(url || "");
        if (m) { return { iframe: "https://player.vimeo.com/video/" + m[1] }; }
        return { file: url };
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
        const v = this.detailVariant;
        if (!this.detailOrderable) {
            this.notification.add(_t("ეს ვარიანტი მომწოდებლის საწყობში ამოწურულია"), { type: "warning" });
            return;
        }
        if (!d.preorder && d.addQty > this.detailQty) {
            this.notification.add(
                _t("მომწოდებელს ამ ვარიანტზე მხოლოდ ") + this.detailQty + _t(" ერთეული აქვს"),
                { type: "warning" });
            return;
        }
        // the chosen variant is what goes into the cart (own key, name and price)
        const offer = v ? {
            ...d, key: `${v.id}_${d.vendor_id}`, product_id: v.id,
            name: v.name, price: v.price,
        } : d;
        this.addToCart(offer, d.addQty);
        this.closeDetail();
    }
    setQty(key, ev) {
        const v = parseFloat(ev.target.value);
        if (this.state.cart[key]) {
            this.state.cart[key].qty = isNaN(v) || v < 1 ? 1 : v;
        }
        this._persist();
    }
    removeLine(key) {
        delete this.state.cart[key];
        this._persist();
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
        this._persist();
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
