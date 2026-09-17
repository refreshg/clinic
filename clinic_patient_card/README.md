<!-- last-synced: 2026-09-17, commit: 677c4d3 -->
# clinic_patient_card

Dental-clinic management on standard Odoo 19 Community: patient card on `res.partner`,
visit workflow on `calendar.event` with an OWL planning board, payments, supplies shop
with a supplier portal (PO↔SO), waitlist/dispensary flow. UI in Georgian.

## Dependencies
`base, contacts, product, account, mail, calendar, stock, product_expiry, purchase, sale_management, sale_pdf_quote_builder`
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
  *Clinic Supply* (+ reordering rules for the low-stock alert; brand / avg-consumption /
  last-price fields); insurance companies = contacts flagged *Insurance Company*; rooms,
  appointment types, **directions**, **brands** and the **Referrals** analysis under
  Clinic → Configuration.
- **Warehouse (batch #2)**: every room auto-owns a stock location under
  WH/Stock/Cabinets; Sterilization + Write-off/Damaged/Expired locations seeded; Clinic →
  Stock menu = Internal Transfers / Scrap / Min-Max Rules / Warehouse Structure (all
  standard models). Storage-Locations + Lots settings must be ON (enabled on prod).
- **Purchase requests (batch #2)**: Clinic → Stock → Purchase Requests (admin) and
  "Supply Requests" (doctors, own only): draft→…→received pipeline, low-stock cron
  auto-drafts, rejection requires a comment, receipt validation completes the request.
- **Shop v2 (batch #2)**: category photos (Inventory → Product Categories → Image),
  banners (Clinic → Configuration → Shop Banners), Sponsored / Pre-order flags on the
  product; wishlist and repeat-last-order are per-user, no setup.
- **Supplier warehouse (D-19)**: every supplier company auto-gets Suppliers/<name> +
  In Transit; supplier menus: My Locations (shelves), ↔ Move Stock, My Warehouse
  (count/Apply), My Transfers (read-only history). Shop availability = supplier stock;
  In Transit ships (their stock drops), the clinic receipt drains the transit shelf.
- **Receive/returns (batch #2)**: supplier advances 5 delivery statuses on their order;
  receipt validation auto-drafts the vendor bill (waybill attached by hand); the PO's
  Return button lives 48h; ratings on the received PO feed shop/dashboard averages;
  manager board under Clinic → Stock → 📊 Dashboard.
- **Dentos-parity visit flow (v56–60)**: book from the board (➕ ახალი პაციენტი
  registers without leaving the popup; foreign citizens get passport/latin fields);
  "📄 თანხმობის ფურცელი" walks the two consent sheets (medical one signed on
  screen); "🧾 ვიზიტის გვერდი" (or ➜ on a board card) opens the working page —
  sections, FDI→ICD-10→procedures with prices/discounts, billing (გადახდა needs
  the full amount; live debt shown). Catalogs: Configuration → ICD-10 Diagnoses;
  complaints seeded (clinic.complaint). Procedures dropdown = service products
  flagged "Clinic Procedure".
- **Cron jobs** (active by default): low-stock alert (daily), dispensary call reminders
  (daily, T-14d), weekly booking report to administrators.
- Patients also live under **Clinic → Patients** (kanban/list/form over is_patient) —
  same Soft-UI form as in Contacts.
- New contacts created from the Contacts app default to patients
  (`default_is_patient` context on `contacts.action_contacts`).

## Known limitations
- E-recipe / prescription sync: recorded locally only (rec_type kept); no external
  transmission until EHR lands.
- Visit billing takes the FULL amount (cash+card must equal the total); partial
  payments are not supported yet.
- Visit page tabs "გახარჯული მასალები" and "EHR სინქრონიზაცია" are placeholders.
- E-mail sending: none yet — what/when is undecided (docs/PRD.md §9). SMS likewise
  deferred (no provider chosen; batch #2).
- Soft-UI patient-card page is read-only (tooth painting not persisted yet — PLAN M3);
  it opens from the visit form's 🪪 button — the partner-form buttons were removed (v55.9).
- Odontogram on the partner form is visual-only (clickable version = PLAN M4).
- `i18n/ka.po` is stale for the 28.08.26 batch strings (PLAN M2).
- No automated tests by decision D-11 — verify live (RPC + browser).
- Form-100 / EHR sync not implemented (templates/target unknown).

## Docs
Full documentation in `../docs/`: PRD (requirements, ka), SPEC (technical), PLAN
(remaining roadmap), ARCHITECTURE, DECISIONS (ADRs). Project rules: `../CLAUDE.md`.
