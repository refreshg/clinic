<!-- last-synced: 2026-09-03, commit: f7f4be0 -->
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

## Milestone 4 — Clickable odontogram on the partner form (US-4 / AC-4)
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

## Small chores (any time)
- [ ] Real photos for demo supply products (user drops files into scratchpad)
- [ ] Delete empty untracked dirs `Custom Module/`, `clinic_processes/` (user to confirm)

## Status
Approved 2026-09-03 (user). NOTE: reviewer batch #2 (docs/ჯავშნები.docx + docs/მაღაზიამარაგები.docx) takes priority over M1-M6 — its approved phase plan lives in the session plan file; M1 (emails) and SMS stay deferred pending the clinic’s decision.
