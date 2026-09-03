<!-- last-synced: 2026-09-03, commit: 43e00a7 -->
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

### D-14: Depend on sale_pdf_quote_builder + sudo its salesman-gated hooks
Date 2026-09-03 (b6e1446) · Context: doctor's SO create crashed — sale_pdf_quote_builder's
field DEFAULT is wired straight to its function (bypasses MRO) and searches on a field
group-gated to salesmen; worse, without a dependency our module loads FIRST, so our method
overrides sat EARLIER in the MRO and never won. · Decision: add `sale_pdf_quote_builder`
to depends (auto-installed with sale anyway) so our class loads later; skip its default in
`default_get` for non-salesmen; run its availability compute as sudo. · Lesson: to override
another module's behaviour you MUST depend on it — same-model classes compose in module
load order.
