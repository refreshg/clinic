<!-- last-synced: 2026-10-07, commit: 0e91ff5 (+ uncommitted work) -->
# PLAN — clinic_patient_card: remaining roadmap

All previously approved work is shipped (v19.0.46.0.0). This plan covers ONLY what's left,
in the priority order the user confirmed (2026-09-03). No deadlines set.
**The user approves this file before any implementation step starts.**
Verification for every step = live RPC + browser (no automated tests — D-11).

## Milestone 0 — Standard-first verification (do first, record results in SPEC §Standard-first)
- [ ] M1 emails: list standard `mail.template` triggers already available on calendar.event /
      account.move (confirmation, invoice send) — decide what standard sending covers before
      any custom hook. Record as D-13.
- [ ] M4 odontogram: check if any Community widget/lib in Odoo 19 web supports clickable SVG
      maps before writing a custom OWL widget. Record findings.
- [ ] M5 Form-100: confirm QWeb report (std reporting engine) suffices once the template
      arrives (expected yes — no custom engine).
- [ ] M6 EHR: no standard connector exists for an unknown target — blocked until the clinic
      names the system (PRD §9).

## Milestone 1 — Emails (US-1 / AC-1) — ⚠ blocked on the clinic's "what/when" decision
- [ ] Get the decision (what is sent, when, to whom) → record as D-13 in `docs/DECISIONS.md`
- [ ] `data/mail_templates.xml` — Georgian templates per decided event
- [ ] Hooks in `models/clinic_appointment.py` (e.g. action_confirm) / payment wizard
- [ ] Verify AC-1 live; bump version; `/docs-sync`

## Milestone 2 — ka.po regeneration (US-2 / AC-2)
- [ ] Restart server, export fresh `.pot` via `base.language.export` (lang `__new__`)
- [ ] Merge & fill Georgian msgstr for all new batch strings → `clinic_patient_card/i18n/ka.po`
- [ ] Deploy with `--load-language=ka_GE` update; verify AC-2 in browser as ka_GE user

## Milestone 3 — Patient-card page write-back (US-3 / AC-3)
- [ ] `static/src/patient_card_page/clinic_patient_card_page.js`: save tooth paints →
      create/update/unlink `clinic.patient.tooth` (map root↔root_canal, extract↔to_extract)
- [ ] Save note → `res.partner.patient_note`; flags → partner booleans (debounced orm.write)
- [ ] "+ დამატება" for contacts/procedures → dialogs on `clinic.patient.phone` /
      `clinic.procedure.history`
- [ ] Verify AC-3 (RPC read-back); version bump; `/docs-sync`

## Milestone 4 — Clickable odontogram on the partner form (US-4 / AC-4) — superseded by Milestone U (D-35)
- [ ] Replace read-only `odontogram_html` with an OWL field widget
      (`static/src/odontogram/`, registered as a field widget on the partner form)
- [ ] Click tooth → status popover → write `clinic.patient.tooth`; keep list in sync
- [ ] Verify AC-4; version bump; `/docs-sync`

## Milestone 5 — Form-100 (US-5 / AC-5) — ⚠ blocked on the template
- [ ] Receive the official template from the clinic (PRD §9)
- [ ] QWeb report `report/form100_report.xml` + PDF layout; button on the visit
- [ ] Auto-attach result to `clinic.patient.document` (doc_type new value `form100`)
- [ ] Verify AC-5; version bump; `/docs-sync`

## Milestone 6 — EHR sync (US-6 / AC-6) — ⚠ blocked on target system
- [ ] Clinic names the EHR + API docs → record integration decision (D-1x)
- [ ] Design: outbound queue model + retry/backoff; then implement
- [ ] Verify AC-6 against a mock endpoint; version bump; `/docs-sync`

## Milestone S — Staff schedules (doctors / assistants / administration) — approved 2026-10-01 ("go" with defaults)
Source: the user's mock-ups (hour-grid "სამუშაო გრაფიკი", per-person weekly cards, "ნამუშევარი საათები").
Standard-first: `hr` (+ `hr_attendance` in phase 2) for employees / check-in-out; custom only the shift
templates + per-day lines (Community has no planning app) — D-29.
- [x] S1 models `clinic.shift`, `clinic.schedule.line`, `hr.employee.clinic_staff_kind`; shift seed (from the
      mock-ups); OWL screen `clinic_schedule` (menu Clinic → გრაფიკი): doctor/assistant/admin tabs,
      day/week/month, hour-grid + matrix looks, admin click-to-assign popover; Configuration → Shifts
- [x] S1 extras (user): custom start–end time, toolbar "＋ დამატება", closed clinic days (Sunday) shown as უქმე from the company config
- [ ] S1 browser check by the user (both looks, month, assignment, doctor sees only self)
- [x] S2 `hr_attendance` (check-in/out inside Odoo: systray / kiosk, admin corrects in Attendances) + "ნამუშევარი საათები"
      screen (plan vs actual, difference, overtime, lateness, absence, vacation/sick, day/week/month/year, chart, Excel)
- [ ] S2 browser check by the user (systray check-in/out for a doctor, the hours screen, Excel download)
- [x] S3 booking guard: no booking for a doctor on off/vacation/sick days or outside their shift
      (when their schedule is filled; empty = old clinic-hours rule) — `_clinic_validate_staff_schedule` on create/write,
      `clinic_free_slots` respects the shift; admin gets a warning when a schedule change leaves live visits outside it
- [x] S1 extra (user): shift times editable / addable from the schedule sidebar (change applies from today, past days keep the old hours)
- [x] S3 visual (user): the Planning board shows each doctor's shift (colour chip + tinted band, rest hatched, no click/drag outside it); shift colours = 12-colour palette, auto-unique, admin-pickable
- [ ] S3 browser check by the user (booking at 16:00 for a doctor working until 15:00 is refused)
- [ ] S4 "ძირითადი გრაფიკი" (weekly pattern applied to a range) — only if the clinic wants it

## Milestone T — Payment, health answers, patient card, treatment plan (2026-10-02, requested by the user in the browser tests)
- [x] T1 payment on the visit page: method select, card types catalog, same-day retail added to the bill (D-30); "Register Payment" removed from the visit form
- [x] T2 allergy + pregnancy mandatory on the card, checked at arrival / start / procedure, pregnancy re-asked every visit, red sign warning on the visit form (D-31)
- [x] T3 patient card re-layout (identity block, flat Basic, Medical / History in the outer tabs, role-based buttons, Contacts = guardian + family), quick form minimal, latin name for foreigners
- [x] T4 treatment plan document + PDF (D-32)
- [ ] T browser check by the user (payment methods + card types, retail in the bill, arrival refusal, pregnancy on a repeat visit, PDF print incl. Georgian text)
- [ ] T currency: treatment-plan prices follow the company currency (USD) — the user will change it last

## Milestone U — Tooth chart, imaging/documents, radiologist, small booking changes (2026-10-05, requested by the user)
- [x] U1 doctor double-booking allowed + side-by-side lanes on the Planning board (D-34)
- [x] U2 tooth chart: 14 diseases + 8 treatments from the procedure lines, ICD-10 / product pickers, two layouts, click-to-add on the card (D-35)
- [x] U3 X-ray / photo gallery with comments + full-screen viewer, examination results (file + typed), allergy documents (card + visit page), radiologist account + multi-file upload (D-36)
- [x] U4 booking form: Curator field; pregnancy answer valid one day + nightly cron (D-37); Financial tab moved to the outer tab bar
- [ ] U browser check by the user (both tooth-chart layouts on the card and the visit page, the add dialog, radiology login + multi-upload, lightbox, comments dialog, exam results, allergy documents, curator, pregnancy asked on a repeat visit)
- [ ] U open: staff arrival / departure ("მოსვლა / წასვლა") on log-in — waiting for the user's choice (auto at log-in vs. manual button); the standard hr_attendance systray exists but has never been used (0 rows)
- [x] U open: periodontal chart — approved 2026-10-07, first version built (milestone W, D-48)

## Milestone V — Supply shop v3: category tree, home page, product window, reviews, supplier order screen (2026-10-05/06, requested by the user)
- [x] V1 category tree (20 tops, ~226 nodes) + pinned tiles + tree menu + home button (D-40)
- [x] V2 home page: banners (video, width, height, drag order) + sponsored + new (D-41)
- [x] V3 product window: gallery / video, options with the supplier's stock per variant, qty guard in cart and RFQ (D-38)
- [x] V4 reviews with photos, sold / rating / return numbers, order-rating photos (D-38)
- [x] V5 supplier panel: gallery, options, stock per variant; supplier "My Orders" screen and clean order form (D-42)
- [x] V6 security fix: suppliers saw each other's orders (D-39)
- [ ] V browser check by the user, step by step (in progress): supplier steps 1-12 done (login, panel, stock, My Orders, confirm); step 13 — delivery steps Availability → Preparing → Ready → In Transit (stock leaves here) → Delivered — NOT yet walked through; then the clinic side: receipt, rating with photos, return
- [ ] V open: duplicate test orders S00070/71/72 + P00053/54/51 (user to say cancel / keep); old demo "gloves" products (8.00) still in the shop
- [ ] V open: open (unshipped) orders do not reserve stock; automatic supplier-side invoice (when: at shipping or at receipt?) undecided

## Milestone W — Booking flow, health answers, tooth plan, perio chart, prescriptions (2026-10-07, requested by the user in the browser tests)
- [x] W1 booking: "existing / new patient" chooser before the form (D-43); quick registration with optional birth date + age; treatment-plan doctor lines + "Add doctor" (D-33)
- [x] W2 First Visit / Repeat / Regular computed from completed visits (D-45); allergy answer valid 6 months (D-44); "treated now" = started within 12 h (fixes the stuck pregnancy answer)
- [x] W3 health banner on the patient form and on every visit-page tab; allergy-test upload on the card (+ shared with the Medical tab and the visit page); full allergy columns on the visit page; exam-result files on the visit page
- [x] W4 visit page only from "Arrived"; no cancel after treatment started; materials / EHR tabs doctor-only; milk teeth only for children < 14
- [x] W5 status colours = legend everywhere (board cards, status bar, workflow buttons: next step full colour, others a light tint; Start std primary); light Odoo-purple quick buttons and card tabs; gender shows only the picked card; Notes tab hidden for patients; product image "+" opens the file chooser
- [x] W6 card tooth chart + plan table, status from the visits, partial treatment stays "in progress" across visits (D-46/D-47)
- [x] W7 prescription: print / PDF / e-mail with the clinic header (B60)
- [x] W8 periodontal chart v1 on the Medical tab (D-48)
- [ ] W browser check by the user (chooser + quick registration, card flags, allergy expiry test on P000152, tooth plan across two visits, perio grid, prescription PDF look)
- [ ] W next: perio chart v2 — lines over the tooth drawing, PDF, recession classifications, opening from the visit page
- [ ] W open (clinic): regular-patient threshold (param = 5 for now); outgoing mail server + patient e-mails; treatment-plan translation ka / en / ru (Claude API recommended — key, cost, privacy) — postponed by the user
- [ ] W open (user): Elene Janezashvili's visits #341 (arrived 10-06) and #335 (in progress 10-05) are still open — close or cancel

## Small chores (any time)
- [ ] Clinic to confirm: insurer + city lists (written from memory), "primary/unique" definitions, what "non-resident" means (PRD §9)
- [ ] Real photos for demo supply products (user drops files into scratchpad)
- [ ] Delete empty untracked dirs `Custom Module/`, `clinic_processes/` (user to confirm)

## Status
Approved 2026-09-03 (user). NOTE: reviewer batch #2 (docs/ჯავშნები.docx + docs/მაღაზიამარაგები.docx) takes priority over M1-M6 — its approved phase plan lives in the session plan file; M1 (emails) and SMS stay deferred pending the clinic’s decision.
Last session 2026-10-07: milestone W (see above), all deployed live on 19.0.64 and NOT committed (D-43..D-48 in DECISIONS). Earlier: Last session 2026-10-06: milestone V — supply shop v3 (category tree, home page + video banners with size / order, product window with options + own stock per variant + reviews, supplier My Orders screen, cart / RFQ stock guard) and a supplier-privacy fix (D-38..D-42); committed and pushed up to 0e91ff5; version bumped to 19.0.64.0 (this bump + handoff note not yet committed).
Next (2026-10-07): user browser-checks milestone W; commit the session; perio chart v2 when asked. Earlier next: the manual walk-through step 13 — supplier delivery steps Availability → Preparing → Ready → In Transit (stock leaves) → Delivered on S00072, then the clinic side (receipt, rating with photos, return); decide the duplicate test orders, invoice timing and stock reservation; then M2 ka.po regen.
Watch out: upgrades ran with --i18n-overwrite (module translations re-read from ka.po); the calendar "hours" / "or" terms are translated through cross-module entries in our ka.po; the perio GM sign convention (positive = recession) still needs a doctor's confirmation; duplicate test orders S00070/71/72 + P00051/53/54 and old demo "gloves" (8.00) are in the shop; patient-primary/unique PNGs and docs/Design preview are untracked on purpose; the tooth-chart layout choice is per browser; admin must NOT carry group_clinic_doctor.
