<!-- last-synced: 2026-09-03, commit: 43e00a7 -->
# clinic_patient_card

Dental-clinic management on standard Odoo 19 Community: patient card on `res.partner`,
visit workflow on `calendar.event` with an OWL planning board, payments, supplies shop
with a supplier portal (PO↔SO), waitlist/dispensary flow. UI in Georgian.

## Dependencies
`base, contacts, product, account, mail, calendar, stock, purchase, sale_management, sale_pdf_quote_builder`
(all Community). License LGPL-3.

## Install / upgrade
1. Copy the module into an addons path (prod: `/opt/odoo19/addons/`, mounted at
   `/mnt/extra-addons`).
2. `odoo -d <db> -i clinic_patient_card --stop-after-init` (upgrade: `-u`), then restart.
   Georgian: install with `--load-language=ka_GE`.
3. `post_init_hook` grants both clinic roles to the Administrator automatically.

## Configuration (after install)
- **Roles** (Settings → Users): assign *Clinic Administrator* (reception/manager — full
  clinic menus, Supply Shop, purchase/stock), *Clinic Doctor* (own visits only), *Clinic
  Supplier* (My Shop / My Inventory / My Orders only).
- **Clinic Schedule** (Settings → Companies → company → *Clinic Schedule* tab): working
  days, opening hours, room double-booking toggle. Booking outside them is blocked;
  back-dating is allowed only for the Administrator account (uid 2).
- **Per-dentist defaults**: user form → *Clinic* tab → Default Room + Clinic Direction
  (specialty; drives the free-slot search and booking autofill).
- **Catalog**: procedures = service products flagged *Clinic Procedure*; supplies flagged
  *Clinic Supply* (+ reordering rules for the low-stock alert); insurance companies =
  contacts flagged *Insurance Company*; rooms, appointment types, **directions** and the
  **Referrals** analysis under Clinic → Configuration.
- **Cron jobs** (active by default): low-stock alert (daily), dispensary call reminders
  (daily, T-14d), weekly booking report to administrators.
- New contacts created from the Contacts app default to patients
  (`default_is_patient` context on `contacts.action_contacts`).

## Known limitations
- E-mail sending: none yet — what/when is undecided (docs/PRD.md §9). SMS likewise
  deferred (no provider chosen; batch #2).
- Soft-UI patient-card page is read-only (tooth painting not persisted yet — PLAN M3).
- Odontogram on the partner form is visual-only (clickable version = PLAN M4).
- `i18n/ka.po` is stale for the 28.08.26 batch strings (PLAN M2).
- No automated tests by decision D-11 — verify live (RPC + browser).
- Form-100 / EHR sync not implemented (templates/target unknown).

## Docs
Full documentation in `../docs/`: PRD (requirements, ka), SPEC (technical), PLAN
(remaining roadmap), ARCHITECTURE, DECISIONS (ADRs). Project rules: `../CLAUDE.md`.
