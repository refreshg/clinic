<!-- last-synced: 2026-10-05, commit: f9cde26 -->
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
  (daily, T-14d), weekly booking report to administrators, daily reset of yesterday's
  pregnancy answers (a woman is asked again at every visit day).
- **Radiology account**: add a user to the group "Clinic Radiologist" — they see only
  Radiology → Patients / X-ray uploads and upload pictures for a patient (click the empty
  picture "+" to pick one or many files). Doctors see them in the patient card, Medical tab.
- Patients also live under **Clinic → Patients** (kanban/list/form over is_patient) —
  same Soft-UI form as in Contacts.
- **Real users (2026-09-18)**: 4 administrators (გ. ბიჭაშვილი, თ. გეგია, ს. ტეფნაძე,
  ნ. გოლაშვილი), 2 doctors (ა. მეტრეველი — ორთოდონტია, ნ. სეფიაშვილი — თერაპია) and
  ნ. გოლაშვილის supplier account (own warehouse auto-created). The three demo doctors
  are archived (history kept); base admin (uid 2) is out of the doctor group, so the
  board columns are exactly the real doctors. Passwords are handed over privately —
  never stored in the repo.
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
- Tooth chart (D-35): the diseases / treatments are approximated drawings, the layout choice
  ("ვიზუალი 1 / 2") is stored per browser, milk teeth are still plain buttons; the pictures
  follow ICD-10 / procedure names (editable: ICD-10 list column, product field).
- `i18n/ka.po` is stale for the 28.08.26 batch strings (PLAN M2).
- No automated tests by decision D-11 — verify live (RPC + browser).
- Payment (visit page): card-type list is a starting point (Configuration → Card Types); only SAME-DAY unpaid retail sales join a visit's total. Allergy / pregnancy answers are mandatory (pregnancy women-only, cleared after every visit). Treatment-plan PDF prices follow the company currency (USD here) — change the currency last; the PDF engine needs the body wrapped in `div.article` or Georgian text is garbled.
- Staff schedule (S1) + worked hours (S2): shift lists are from the user's mock-ups, assistants must be added as employees with Clinic Role; check-in/out is the standard Odoo attendance; worked hours are raw clock time (no lunch deduction), lateness = more than 5 min after the shift start; the booking guard (S3) refuses bookings outside a doctor's scheduled shift on days where their schedule is filled in (empty day = clinic hours only); the Planning board shows each doctor's shift colour. Closed weekdays follow Settings → Companies → Clinic Schedule; public holidays are not modelled.
- Form-100 / EHR sync not implemented (templates/target unknown).
- Insurer list (`data/clinic_insurers_seed.xml`) and city list (`data/clinic_cities_seed.xml`) are unconfirmed — written from memory.
- Patient status counts COMPLETED visits only; the Patients Export button downloads the active status (primary/unique) or all patients (57 of 80 have no status). Required card fields are enforced by the form, not by constraints.
- Booking form: the Family Member Link uses `form_view_ref` (D-24); its internal link may
  show the short registration form for an existing member. Patients search: Enter opens the
  first suggested patient (D-25). Both unverified in the browser at time of writing.

## Docs
Full documentation in `../docs/`: PRD (requirements, ka), SPEC (technical), PLAN
(remaining roadmap), ARCHITECTURE, DECISIONS (ADRs). Project rules: `../CLAUDE.md`.
