<!-- last-synced: 2026-09-03, commit: f7f4be0 -->
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
- **Reviewer batch 28.08.26 — DONE (v19.0.30–46):** `docs/28.08.26.docx` (~30 items) fully
  implemented and user-tested: visit fields (assistant, diagnosis, paid amounts, reschedule
  flags), one clinic-wide schedule on res.company + booking guards (working hours; past =
  Administrator uid 2 only; dentist/room double-booking blocked), 10-minute board grid with
  hover + drag-to-size booking and popup visit form (UTC-serialized defaults!), visit
  history / cancelled+rescheduled lists, patient-form validations (latin email, digit
  phone/vat, unique vat) + "რეალიზაცია" tab (direct sale.order), patient search by vat/phone,
  waitlist/Reserve panel per dentist + dispensary 6-month flow with 14-day-before admin
  reminders and weekly booking reports. Meeting UI (Send email, RSVP "Going?", Busy row,
  attendees) hidden on clinic visits. Emails deferred (undecided what/when to send).
- **Reviewer batch #2 Track A (ჯავშნები) — DONE (v19.0.47-49):** doctor-access bug fixed, patient toggle back, family links, referrals analysis, visit form rebuilt in the main body (directions, cancel popup, 9 status colours, card shows pn/procedure/comment), free-slot finder wizard, doctor retail sale-requests with admin approval. Track B (მაღაზია/მარაგები) pending user green-light; SMS deferred.
- Status (as of v19.0.46.0.0): Phases 1–2, Rev-A, Phase 3 (A/B/C) and Phase 4 are DONE
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
- **Emails** (deferred from the reviewer batch) — clinic must first decide WHAT is sent WHEN
  (booking confirmation? invoice? Form-100). Then wire mail templates.
- **ka.po regeneration** — the reviewer batch added many new EN source strings (buttons,
  errors, lists); regenerate the .pot after a server restart and refill Georgian.
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
- **Scheduling guards live in create/write, keyed on `'start' in vals`** — otherwise
  state-only writes (done/paid) on past visits break. Escape hatch: `clinic_force=1` context
  (schedule checks only, never the overlap constraint). Past-booking bypass = the
  Administrator ACCOUNT (`base.user_admin`), not a group — the `clinic` user carries
  Settings rights, so any group-based gate leaked.
- **`requested` = reserve/waitlist state** — excluded from the board grid and from the
  overlap constraint (both directions); `action_book` flips it to booked, which re-runs the
  overlap check. Dispensary entries are created with `clinic_force` (+182d may hit closed days).
- **Board datetime defaults must be UTC-serialized** (`serializeDateTime(DateTime.local(...))`)
  — naive local strings display +4h on the form. And board geometry: keep `HOUR_PX` in sync
  with the SCSS row height, borders `box-sizing: border-box` or hour lines drift 1px/hour.
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

## Commands (dev loop = live LAN server; there is NO local Odoo)
Passwords/keys are NOT here — they live in local Claude memory only.
- Package: `tar --force-local -czf module.tgz -C <repo> --exclude='__pycache__' --exclude='patient-card-ui' clinic_patient_card`
- Ship (LAN only): `scp module.tgz fmg@192.168.0.235:/tmp/clinic_module.tgz`, extract into `/opt/odoo19/addons/`
- Upgrade module: `docker exec odoo19-odoo-1 odoo -d odoo -u clinic_patient_card --stop-after-init --no-http --db_password=<local memory>`
- Restart: `cd /opt/odoo19 && docker compose restart odoo` · Logs: `docker logs -f odoo19-odoo-1`
- Odoo shell: `docker exec -i odoo19-odoo-1 odoo shell -d odoo --no-http --db_password=<local memory>`
- Smoke tests: JSON-RPC via scratchpad `odoo.js` → `http://192.168.0.235:9494/jsonrpc` (recreate per session)
- Automated tests: none by decision (see `docs/DECISIONS.md` D-11) — verify live via RPC + browser.

## Layout
- `clinic_patient_card/` — the only Odoo addon (models/, views/, wizard/, security/, data/, static/src/, i18n/)
- `docs/` — PRD, SPEC, PLAN, ARCHITECTURE, DECISIONS + source .docx specs + `design_handoff_patient_card/`
- `patient-card-ui/` — React/Vite design reference for the Soft-UI card (never deployed to Odoo)

## Conventions
- Model prefix `clinic.` (`clinic.procedure.history`); core models extended via `_inherit` keep their names.
- XML ids: `view_ / action_ / menu_ / rule_ / cron_` + snake_case (e.g. `action_clinic_visit_history`).
- Fields snake_case; clinic additions on core models flagged `is_clinic` / `clinic_*` (e.g. `clinic_state`).
- UI source strings in English (a few deliberate Georgian button labels); translations in `i18n/ka.po`.
- Commits: `feat(clinic)|fix(clinic)|docs(clinic)|chore(...): ...` + the Claude co-author trailer.

## Workflow
PRD → SPEC → **PLAN (user approves BEFORE any code)** → code → live verification → `/docs-sync`.
Standard-first: name the standard Odoo feature checked; write custom code only after stating why it
doesn't fit and recording it as a `D-<n>` entry in `docs/DECISIONS.md`.
Preference order: configuration → automated action → inherit & extend → new model.

## Docs map
- `docs/PRD.md` — requirements, roles, scope, user stories/AC for remaining work (Georgian)
- `docs/SPEC.md` — data model, business rules, security, standard-first table (English)
- `docs/PLAN.md` — remaining-roadmap milestones; **must be approved by the user**
- `docs/ARCHITECTURE.md` — components, data flow, extension points
- `docs/DECISIONS.md` — ADRs (D-1…)
- `clinic_patient_card/README.md` — install / configuration / known limitations
