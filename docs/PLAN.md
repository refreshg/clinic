<!-- last-synced: 2026-10-05, commit: f8406c7 (+ uncommitted work) -->
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
- [ ] U open: periodontal chart (6 points per tooth) — explained to the user, not approved yet

## Small chores (any time)
- [ ] Clinic to confirm: insurer + city lists (written from memory), "primary/unique" definitions, what "non-resident" means (PRD §9)
- [ ] Real photos for demo supply products (user drops files into scratchpad)
- [ ] Delete empty untracked dirs `Custom Module/`, `clinic_processes/` (user to confirm)

## Status
Approved 2026-09-03 (user). NOTE: reviewer batch #2 (docs/ჯავშნები.docx + docs/მაღაზიამარაგები.docx) takes priority over M1-M6 — its approved phase plan lives in the session plan file; M1 (emails) and SMS stay deferred pending the clinic’s decision.
Last session 2026-10-05: milestone U (tooth chart, imaging / exam-result / allergy documents, radiologist user, curator, one-day pregnancy answer, doctor double-booking) — all deployed live, NOT committed (v19.0.62.0 still); the parallel chat also changed the treatment-plan doctors (D-33). Earlier: Last session 2026-10-02 (later): staff schedules S1-S3 (schedule screen, attendance + worked hours + Excel, booking guard, Planning-board shift overlay, 12 colours) + patient card rework, all live and committed locally up to 101440c; PLUS uncommitted milestone T (payment methods + card types, retail in the bill, health answers, patient-card re-layout, treatment plan) — v19.0.62.0.
Next (2026-10-05): user browser-checks milestone U; decides staff arrival/departure on log-in and whether the periodontal chart is built; then the commit. Earlier next: user browser-checks the schedule screens, worked hours/Excel, board overlay, patient buttons and gets the clinic answers (PRD §9); then M2 ka.po regen (first unblocked), S4 only if the clinic wants a weekly pattern.
Watch out: nothing pushed (5 local commits on main); D-24/D-25/D-27/D-29 unverified in the browser; worked hours = raw clock time, lateness = >5 min; public holidays not modelled; admin must NOT carry group_clinic_doctor; supplier on a SEPARATE account.
