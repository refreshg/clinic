# Clinic — project notes for Claude

## Platform
- Odoo custom-addons project: Odoo **Community** edition.
- Community only: do NOT depend on Enterprise modules (web_studio, account_accountant,
  documents, sign, appointment, planning, etc.). Check every `depends` against Community
  availability before using it.
- License for custom modules: LGPL-3 compatible.

## Odoo version
- **Target Odoo version: 19.0** (Community; server build `19.0-20260630`).
  Detected from `clinic_patient_card/__manifest__.py` → `version: 19.0.2.0.0`.
- Odoo 19 syntax rules to respect:
  - No `attrs`/`states` in views → direct expressions: `invisible="not is_patient"`.
  - Use `<list>` (not `<tree>`).
  - `name_get()` deprecated → `display_name` / `_compute_display_name`.
  - Deprecated `record._cr/_context/_uid` and `odoo.osv` → use `env.cr/env.context/env.uid`.
  - External API: JSON-2 (`POST /json/2/<model>/<method>`, bearer API key) available;
    XML-RPC/JSON-RPC still work.

## Product / plan
- **`docs/PRD.md` is the source of truth** for requirements, data model, phases and
  decisions (patient card 1.1–1.9). Keep it updated as scope changes.
- Status (as of v19.0.29.0.0): Phases 1–2, Rev-A, Phase 3 (A/B/C) and Phase 4 are DONE
  and live. Extras also live: OWL Planning board (Clinic>Planning; click empty grid slot
  to book, with a ripple/ghost cue), a visual patient Dashboard (Health-Care style OWL
  action, "Open Dashboard" on the Patient Card tab), a custom OWL Supply Shop, and a
  supplier portal (Clinic Supplier role: standard Inventory is the base, "My Shop" panel
  publishes products into the shop). Ordering models the correct chain: clinic checkout
  makes a purchase.order AND a mirror sale.order for the supplier — the supplier confirms
  the SO, which mirror-confirms the PO and notifies the clinic. Clinic visit forms hide
  meeting-only fields (Location/Video Link/attendees) and open the Clinic tab by default.
  A full Soft-UI patient-card page (OWL client action `clinic_patient_card_page`, ported
  from `docs/design_handoff_patient_card/`) opens via "🪪 პაციენტის ბარათი" on the Patient
  Card tab, reading a real res.partner (read-only for now). Each doctor sees only their own
  appointments on the calendar/board; the admin sees all.

## Next steps (pick up here)
- **Patient-card page write-back** — persist the interactions: tooth painting → `tooth_ids`,
  note → `patient_note`, status/med flags → the partner booleans, +add contact/procedure.
  Currently the page is read-only (painting is on-screen only).
- **Form-100** generation and **EHR sync**.
- **Clickable odontogram** on the res.partner form itself (status change on tooth click).
- **Real photos** for the demo supply products (user to drop files into scratchpad).

## Key architecture decisions (this build)
- **Shop = custom OWL, not `website_sale`** — website_sale sells (sale.order); the clinic
  BUYS. The storefront is a custom OWL client action over standard `purchase`.
- **PO↔SO chain** — one Odoo DB holds clinic + suppliers as users. Clinic checkout creates
  `purchase.order` (RFQ) per vendor AND a mirror `sale.order` (customer = clinic company,
  tagged `clinic_supplier_id`/`clinic_purchase_id`). Supplier confirms the SO →
  `_clinic_notify_clinic_confirmed` mirror-confirms the linked PO. Mirror SO lines skip
  delivery (`sale.order.line._action_launch_stock_rule` no-op for clinic orders) so confirm
  never depends on warehouse routes — goods reach the clinic via the PO receipt.
- **Supplier products = standard Inventory as the base** — the "My Shop" OWL panel is only a
  management UI; products/stock live in standard Inventory, scoped per supplier by ir.rule
  (`seller_ids.partner_id.commercial_partner_id == user's`). Panel writes use `.sudo()` with
  vendor scoping enforced in code (so creating a new product isn't blocked before its
  supplierinfo exists).
- **Roles gate menus** — Clinic Administrator / Doctor / Supplier. Suppliers see only
  My Shop / My Inventory / My Orders — no calendar/visits. Verify menu visibility with
  `ir.ui.menu.load_menus`, NOT a raw `search` (raw search ignores group gating).
- **Custom board is the calendar** — the standard Appointments/My Calendar list menus were
  removed; the OWL Planning board is the scheduling UI. The act_window actions stay defined
  for quick-action buttons. The board's hour window is dynamic (default 08–18, auto-fits the
  day's earliest/latest visit so late ones aren't clipped) and it owns its own vertical scroll
  (`height:100%` + `max-height:calc(100vh - 46px)` + `overflow-y:auto`) so short/laptop screens
  can always reach the bottom rows — don't rely on the surrounding Odoo container to scroll.
- **Design handoffs → native OWL, not React embed** — the Soft-UI card was delivered as a
  React/Vite reference (`patient-card-ui/`), then rebuilt as an OWL client action so it lives
  in our stack on real data. Design tokens are copied 1:1 into a scoped SCSS block; lucide
  icons become inline SVG. Never embed a foreign framework (React) into the Odoo backend.
- **Doctor appointment scoping = GLOBAL ir.rule** — restricting `calendar.event` per dentist
  must be a global rule (no `groups`, AND-combined). A group rule only OR-widens the base
  `calendar` rules and still leaks other dentists' visits. The rule: non-clinic OR own-dentist
  OR (admin ? all : none). **Odoo 19 gotcha:** the domain engine rejects the `(1,'=',0)`
  always-false trick — use `('id','!=',False)` / `('id','=',False)` for the admin branch.

## How to work here
- Use the **odoo-development** skill for all Odoo questions; read the relevant file in
  its `references/official/` before answering precise API questions.
- Never modify Odoo core; inherit models (`_inherit`) and views (`inherit_id` + xpath).
- Reuse standard Odoo fields/features FIRST; build custom only for what's missing.
- Every new model needs `security/ir.model.access.csv` entries. Two security layers:
  ACL (model CRUD) + record rules (`ir.rule`, row-level).
- Upgrade-safe: business logic in models, minimal xpath surface; ORM over SQL (raw SQL
  only via `odoo.tools.SQL`).
- UI source strings in English + Georgian `i18n/ka.po`. The `.po` is generated by
  exporting the module `.pot` (`base.language.export`, lang `__new__`) and filling
  msgstr; export after a server restart so the fresh registry includes new field labels.
- **Never commit secrets** (DB / SSH / admin passwords, API keys) to the repo. Instance
  and server credentials live only in local Claude memory.
