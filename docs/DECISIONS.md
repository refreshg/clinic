<!-- last-synced: 2026-09-13, commit: 91e1c22 -->
# Decisions (ADR) — clinic_patient_card

Format: Context → Decision → Rejected → Consequences. New custom code requires a D-entry
(standard-first rule, see CLAUDE.md §Workflow).

### D-1: Custom OWL Supply Shop instead of website_sale
Date 2026-08-18 (b138010) · Context: clinic staff need a storefront to BUY from suppliers;
user: "მაღაზიის იერი პრინციპულია". · Decision: OWL client action over standard `purchase`
(checkout → `clinic_create_rfqs`). · Rejected: `website_sale` (sells via sale.order — wrong
direction), bare Purchase app (no shop UX). · Consequences: custom JS to maintain; standard
RFQ/receipt flow untouched.

### D-2: PO↔SO mirror chain for supplier confirmation
Date 2026-08-18 (e4ac23b) · Context: one DB holds clinic + suppliers; supplier must see a
SALES document ("correct chain" — user). · Decision: checkout creates purchase.order AND a
mirror sale.order (`clinic_supplier_id`/`clinic_purchase_id`); supplier confirms SO →
auto-confirms PO. Mirror SO lines skip `_action_launch_stock_rule` (goods arrive via PO
receipt). · Rejected: supplier acting on the clinic's PO directly. · Consequences: two linked
docs per order; SO confirm independent of warehouse routes.

### D-3: Supplier products = standard Inventory base + sudo panel
Date 2026-08-18 (12bab3b) · Context: user: "ფუძე იქნება ინვენთორი, პანელი დატოვე". ·
Decision: products/stock live in std Inventory, scoped per supplier by ir.rule on
`seller_ids.partner_id.commercial_partner_id`; "My Shop" panel writes via `.sudo()` with
vendor scoping in code (new product has no supplierinfo yet). · Rejected: parallel custom
catalog. · Consequences: supplier menu = My Shop / My Inventory / My Orders only.

### D-4: Clinic schedule = simple fields on res.company (not resource.calendar)
Date 2026-08-29 (7f5a218) · Context: reviewer demands working-hours lock + no double-booking;
user chose ONE clinic-wide schedule. · Decision: 9 fields on res.company; guards in
create/write keyed on `'start' in vals` (state-only writes pass); `clinic_force=1` ctx escape;
overlap via python constrains with sudo() search. · Rejected: `resource.calendar` (per-resource
weight, no overlap guard anyway). · Consequences: per-dentist schedules would need a redesign.

### D-5: Past-booking bypass = the Administrator ACCOUNT only
Date 2026-08-30 (a12e834) · Context: group-based gate leaked — the `clinic` reception user
carries Settings rights. · Decision: only `base.user_admin` (uid 2) may back-date; everyone
else blocked (5-min grace). · Rejected: `group_clinic_admin` / `base.group_system` gates. ·
Consequences: back-dated corrections go through the owner's account.

### D-6: `requested` state = reserve/waitlist semantics
Date 2026-08-30 (d874382) · Context: reviewer's "სარეზერვო ველი" + dispensary flow. ·
Decision: `requested` entries are placeholders — excluded from the board grid AND from the
overlap constraint both directions; `action_book` → booked re-runs overlap; dispensary
entries created with `clinic_force` (+182d may hit closed days). · Rejected: separate
waitlist model. · Consequences: reserve never blocks a slot until confirmed.

### D-7: Doctor visit scoping = GLOBAL ir.rule
Date 2026-08-18 (df815fd) · Context: group rules only OR-widen base calendar rules → leak. ·
Decision: global rule `['|','|',('is_clinic','=',False), admin?all:none, ('dentist_id','=',user.id)]`;
Odoo 19 rejects `(1,'=',0)` → use `('id','!=',False)/('id','=',False)`. · Consequences: menu
visibility must be verified via `ir.ui.menu.load_menus`, not raw search.

### D-8: Appointments on calendar.event (Community)
Date 2026-08 (Phase 3A) · Context: Enterprise `appointment`/gantt unavailable. · Decision:
`_inherit calendar.event` + `clinic_state` machine + custom OWL board as the calendar UI
(standard Appointments/My Calendar menus removed). · Rejected: new `clinic.appointment`
model (would lose reminders/recurrence/attendee infra).

### D-9: Procedures = service products; insurance = partners
Date 2026-08 (standard-reuse refactor) · Decision: `product.product` + `is_clinic_procedure`
(pricing/invoicing free); `res.partner` + `is_insurance_company`. · Rejected: custom catalog
models (existed briefly, dropped). · Consequences: procedure price lives on the product.

### D-10: Design handoffs → native OWL, never React embed
Date 2026-08-18 (6b88385) · Context: Soft-UI card delivered as React/Vite reference. ·
Decision: rebuild in OWL on real res.partner data; tokens copied 1:1 to scoped SCSS; lucide
→ inline SVG. `patient-card-ui/` stays as reference only. · Rejected: iframe/asset React
embed (two frameworks, data bridge, upgrade pain).

### D-11: No automated test suite — live verification
Date 2026-09-03 (user answer) · Decision: verification = JSON-RPC scenarios + browser checks
against the live instance after each deploy; no `--test-enable` suite. · Consequences:
regressions caught manually; each commit documents what was verified.

### D-12: Personal number = standard `vat` field
Date 2026-07 (Rev-A) · Decision: reuse `vat` relabelled "პირადი ნომერი"; digits-only +
unique-among-patients python constrain (base_vat rejected — EU-format oriented). ·
Consequences: no duplicate field; validations are clinic-specific.

### D-13: Doctor retail requests = draft sale.order (no custom request model)
Date 2026-09-03 (b6e1446) · Context: batch #2 — a doctor picks products for a patient, the
admin approves into billing or rejects with a visible comment. · Decision: reuse sale.order
(`is_clinic_retail`): doctor drafts (own-drafts record rules, self-confirm impossible),
admins get activity + `clinic_sale_request` toast, admin confirm auto-creates the draft
invoice, rejection = cancel + chatter comment (doctor auto-follows). `user_id` pinned to
the creating doctor. · Rejected: a parallel clinic.sale.request model. · Consequences: full
standard sale/invoice chain reused; doctors carry narrow sale ACLs.

### D-15: Purchase requests = new clinic.purchase.request model
Date 2026-09-05 (3cfc026) · Context: batch #2 demands a pipeline in FRONT of the purchase:
4 intake sources, manager review with stock recommendations, mandatory reject comment,
redistribute-instead-of-buy, and a 10-state lifecycle where stock moves only on receipt.
· Decision: a dedicated model (+lines) that ENDS in standard purchase.orders (RFQ per
vendor via clinic_request_id); receipt validation drives the received state. · Rejected:
bare purchase.order states (no review/recommendation/reject-comment semantics),
purchase_requisition (tenders/blanket agreements — different purpose). · Consequences: one
extra model to maintain; the stock/purchase chain itself stays 100% standard.

### D-16: Free-slot finder = pure client-side dialog
Date 2026-09-05 (f3d42af) · Context: three form-integrated attempts failed in sequence —
an object button auto-saves the half-filled visit; action.doAction(target=new) REPLACES the
visit dialog; FormViewDialog stacks, but its buttons' window-close actions still land on
the action-stack dialog (the visit form). · Decision: a view widget opens an OWL Dialog
that calls clinic_free_slots directly and hands the pick to the open form via
record.update — no wizard records in the UI path, no action stack, nothing saved until the
user presses Save. · Consequences: clinic.slot.finder wizard stays as RPC fallback only.

### D-17: Global Save/Discard = FormStatusIndicator template extension
Date 2026-09-05 (aa5646a) · Context: reviewer wants obvious Save/Back on every form, but
only when there is something to save; the standard breadcrumb cloud/✕ went unnoticed, and
per-view special buttons cannot know the dirty state. · Decision: t-inherit extension of
web.FormStatusIndicator relabels its buttons ("შენახვა"/"გაუქმება", btn-primary/secondary) —
the indicator's own dirty/new gating provides exactly the wanted visibility. · Rejected:
always-visible special="save" bars per view (shown even with nothing to save — reverted).

### D-19: Supplier-owned warehouses on standard locations, deduction at shipping
Date 2026-09-12 (232d1bb, 3430f77) · Context: suppliers must manage their own stock and
shelves; the user ruled the stock must drop when the supplier SHIPS, not when the clinic
receives. · Decision: per-supplier location pair Suppliers/<name> (internal) + In Transit
(transit), auto-created each upgrade; partner.property_stock_supplier = the transit shelf
so standard receipts drain it; the mirror-SO "In Transit" button validates an internal
picking warehouse→transit (reserving from shelves first); returns land back in their
warehouse; shop availability/pre-order reads THEIR stock. Shelves = child locations
(owner tag inherited); moves via a small ownership-guarded wizard. Suppliers get scoped
read-only history (My Transfers) instead of the Inventory app. · Rejected: full Inventory
app with per-supplier rules (huge leak surface), deduction on clinic receipt. ·
Consequences: engine is 100% standard stock; unshipped-but-received goods show as negative
transit — a correct signal.

### D-20: Supplier product access — read open, write scoped
Date 2026-09-12 (5996a69) · Context: the per-supplier READ rule on products crashed any
supplier page that merely referenced a foreign product (prefetch/chatter) — the "My Orders
redirect" hunt. · Decision: product template/variant rules keep write/create/unlink scoped
to own catalogue but no longer restrict read; My Inventory got its own scoped action; a
request-PO auto-creates the vendor's supplierinfo line on Place Order (B32) so own-order
references always resolve. · Rejected: enumerating every read path with extra rules. ·
Consequences: suppliers can see other catalogues' names/stock figures — accepted for this
single-DB trusted marketplace.

### D-18: Returns = dedicated model over a hand-built reverse picking
Date 2026-09-11 (52877b4) · Context: reviewer items 34-40 want a 48h return window with a
mandatory reason + photo, supplier review/approve/reject-with-comment and status tracking;
none of that exists on a bare reverse transfer, and stock.return.picking's internal API
shifts between versions. · Decision: clinic.purchase.return (mail.thread) drives the
pipeline; approval creates a plain outgoing picking stock→vendor built directly from the
receipt's done moves. · Rejected: chatter-only returns; calling the return wizard's
internals. · Consequences: the physical flow stays a standard stock.move trail; one small
model to maintain.

### D-14: Depend on sale_pdf_quote_builder + sudo its salesman-gated hooks
Date 2026-09-03 (b6e1446) · Context: doctor's SO create crashed — sale_pdf_quote_builder's
field DEFAULT is wired straight to its function (bypasses MRO) and searches on a field
group-gated to salesmen; worse, without a dependency our module loads FIRST, so our method
overrides sat EARLIER in the MRO and never won. · Decision: add `sale_pdf_quote_builder`
to depends (auto-installed with sale anyway) so our class loads later; skip its default in
`default_get` for non-salesmen; run its availability compute as sudo. · Lesson: to override
another module's behaviour you MUST depend on it — same-model classes compose in module
load order.

### D-21: CSS-only Soft-UI restyles hooked by a marker div + :has()
Date 2026-09-13 (78ff323..91e1c22) · Context: reviewer wanted the patient form and the
planning board redesigned "visually only — touch no functionality". A class set on
<sheet> in the arch never renders (the Odoo 19 form compiler drops sheet attributes), so
there was nothing to scope the SCSS to. · Decision: inject an invisible
<div class="o_clinic_soft"/> into the sheet via xpath and scope every rule with
:has(> .o_clinic_soft) (asset bundles compile :has() fine). The board restyle only appends
selectors onto existing cp_* classes; cards size to their duration (cp_small ≤15min /
cp_mid ≤35min) via one pure JS helper, geometry (HOUR_PX=96) untouched. Groups whose every
field is invisible are hidden with :not(:has(...)) so they don't render as empty cards.
· Rejected: rebuilding the form as an OWL page (functionality risk); adding classes from
JS (runtime cost for a static hook). · Consequences: the restyles are drop-out safe
(deleting the SCSS restores the stock look); marker-div is THE pattern for targeting one
specific form's sheet.
