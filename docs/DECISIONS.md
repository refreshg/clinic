<!-- last-synced: 2026-10-08, commit: f031de9 (+ uncommitted work) -->
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

### D-22: Dentos parity = new OWL visit page over existing models
Date 2026-09-17 (e321912..5b75dd5) · Context: the client supplied Dentos™ screen
recordings and asked to mirror the visit / patient-registration / procedures flows
exactly. · Decision (user-approved 4-way): scope = the three flows only; the visit
working page is a NEW OWL client action (clinic_visit_page) over the existing
calendar.event/procedure models rather than a rebuilt form; consents ship now with
the Community `signature` widget; patients get split first/last names with `name`
auto-joined. New thin catalogs (clinic.icd10, clinic.complaint, clinic.prescription,
clinic.consent) instead of external packages; e-recipe/EHR stay recorded-only.
· Rejected: form-view-only rework (cannot reach the Dentos layout), external ICD-10
dependency (Community has none), partial payments (full-amount guard + live debt
display instead — revisit if asked). · Consequences: procedures/billing are edited on
the page; the visit form keeps a read-only closed-visit summary.

### D-23: Quick-create m2o via widget + FormViewDialog, not form_view_ref
Date 2026-09-17 (682d072, db46b2e, 677c4d3) · Context: putting form_view_ref in the
patient field's context sent EVERY open — including the internal link to an existing
patient — to the registration popup; and the saved patient never landed in the
booking because Odoo 19's relational model silently drops [id, name] tuples in
record.update (it wants {id, display_name}). · Decision: the field keeps its normal
link (full card) with no_create; a view widget (clinic_new_patient_btn) stacks
FormViewDialog with the quick form and writes the m2o back as an object; the slot
finder's dentist update was migrated to the object shape too. · Consequences: the
widget pattern (slot finder, new patient) is the way to put custom dialogs on a form
without hijacking navigation. **Partly superseded by D-24** (2026-09-30).

### D-24: Patient / family m2o creation UX on the booking form (reverses part of D-23)
Date 2026-09-30 (uncommitted) · Context: user requests — `no_create` on Patient hid the
way to register someone missing from the list; the Family Member Link dropdown only
offered already-linked members and its "Create and edit" opened the bare contact form
(company/person switch, Contacts/Sales tabs); a parent picked there stayed a plain
contact (not in the client base) and never reached the patient's card. · Decision:
(1) `patient_id`: `no_quick_create` (name-only patients are useless), Create-and-edit
restored; the ➕ widget stays for the quick form. (2) `family_link_id`: any patient is
selectable; its Create-and-edit uses `form_view_ref` = quick registration form; saving
the visit runs B36 (two-way `family_member_ids`, link flagged `is_patient`).
(3) the Individual/Company switch is hidden for patients. · Consequences: D-23's "never
form_view_ref on the field" is knowingly broken for `family_link_id` — its internal link
may open the short form for an existing member; a `clinic_new_family_btn` widget was
built and dropped on user request. Pending clinic answers: company patients, guardian
for minors (PRD §9).

### D-25: Patients search bar = suggestions, not filtering-on-Enter
Date 2026-09-30 (uncommitted) · Context: user wanted matching clients in the search
dropdown while typing (name, surname, phone, e-mail). Standard Odoo lists only
"Search X for: …" entries and filters after Enter. · Decision: a patch of web's
`SearchBar` (computeState/selectItem) in `static/src/live_search/`, opt-in through the
action context `clinic_live_search`; matching patients (max 8, 200 ms debounce) replace
the generic entries, click opens the card; no match → standard entries. An earlier
variant (live-filtering the kanban via a SearchModel patch) was dropped as the wrong
reading of the request. · Consequences: Enter now opens the first patient instead of
filtering; the patch relies on SearchBar internals (`items`, `state.query`) — re-check on
Odoo upgrades. Rationale is the user's request; no standard alternative covers it.

### D-26: Quick form minimal; "required" lives on the patient card; explicit yes/no for allergy and pregnancy
Date 2026-10-01 (uncommitted) · Context: first-visit booking needs speed; the clinic's
mandatory set is name, surname, personal no., birth date, mobile, referral source, and
allergy + pregnancy answers — to be filled on the card at arrival. An empty allergy list or
an unticked box cannot be told apart from "never asked". · Decision: the booking popup
keeps only first/last name, mobile, insurance (+ foreign toggle); the card makes the six
fields plus two new yes/no selections (`allergy_answer`, `pregnancy_answer`, pregnancy
hidden for men) required for patients through view `required=` expressions, NOT model
constraints; `is_pregnant` stays in step with the answer; the allergy list (required when
the answer is yes) moved out of the doctor-only group so the administrator can fill it.
Names became two required fields on the card (`first_name`/`last_name`), and 29 existing
patients had them back-filled from `name` (first word / rest). · Consequences: existing
patients with empty fields are forced to complete them on the next card save; 9 one-word
names still lack a surname; UI-only enforcement means RPC/imports bypass it.

### D-27: Patient status by completed visits + Excel via menu items
Date 2026-10-01 (uncommitted) · Context: user wanted ready-made patient lists (template
filters) whose click downloads an Excel, with their own terms: primary = came once,
unique = came several times. · Decision: stored computes `clinic_done_visits` /
`clinic_patient_status` (done/paid visits; 1 → primary, 2+ → unique, 0 → none), a
dedicated Patients search view (status side panel + filters), and two Clinic menu items
(`ir.actions.act_url`) hitting `/clinic/patients/export` which builds the .xlsx with
xlsxwriter. Download-on-filter-click was NOT built — it would save a file on every click;
menu items were chosen instead. · Consequences: 57 of 80 patients have no status; the
standard list Export remains for any other selection.
**Revised 2026-10-01 (same day, user request):** the menu items and the side panel were dropped; the
status filters and the Export became buttons in the Patients control panel (`js_class` views,
`ClinicPatientButtons`, export route kept and extended with `status=all`).

### D-28: Patient address via standard res.city (new dependency base_address_extended)
Date 2026-10-01 (uncommitted) · Context: user asked for residence / legal address, a city
dropdown with Create, ZIP + country only for non-residents. · Decision: depend on the
standard `base_address_extended` (already installed) and reuse `city_id`/`res.city`;
seed 17 Georgian cities; place the view tweaks in a separate priority-20 inherit because
`city_id` is added after our main inherit. "Non-resident" is implemented as the existing
`is_foreign` flag — to be confirmed. · Consequences: the city domain is cleared
(`[]`) for all partners on this form; ZIP/country/state fields stay in the model.

### D-29: Staff schedules on standard hr + two small custom models
Date 2026-10-01 · Context: the clinic wants per-person schedules for doctors / assistants /
administration (shifts, days off, vacation, sick leave), worked hours, check-in/out inside
Odoo, and no bookings outside a doctor's schedule. Enterprise `planning` is unavailable and
the clinic-wide hours of D-4 cannot express per-person days. · Decision: depend on the
standard `hr` (employees; `hr_attendance` joins in phase 2 for check-in/out and worked hours);
add only `clinic.shift` (editable templates, seeded from the user's mock-ups) and
`clinic.schedule.line` (employee-day: shift / off / vacation / sick). `hr_holidays` was NOT
used (its approval workflow is overkill). The screen is a custom OWL client action with two
interchangeable looks (hour grid and per-employee matrix) because the user wanted to choose
the visual side. Editing is admin-only; a doctor sees only their own days (ACL + ir.rule).
**Extras (2026-10-01):** shift colours are a 12-colour palette with auto-unique assignment (python mirror of the scss list); the Planning board overlays the doctor's shift on the existing OWL board (colour band + hatched rest) instead of a new screen; closed weekdays come live from the company's Clinic Schedule, never hard-coded; custom hours entered in the day popover become shift templates.
**S3 (2026-10-01):** the booking guard reads the doctor's schedule live (no cache) and only when an entry exists for that day; existing visits are never moved when the schedule changes, the admin gets a warning count. Shift-time edits apply from today so past worked-hours history stays true.
**S2 (2026-10-01):** `hr_attendance` added; check-in/out stays 100% standard; the plan-vs-fact screen and Excel are custom over
`hr.attendance`; hours are raw clock time (the standard `worked_hours` subtracts a lunch break the clinic does not use); a check-in more
than 5 minutes after the shift start counts as late. · Consequences: new standard module `hr` on the live DB (adds an Employees app); shift lists
are from memory/mock-ups and editable; the booking guard (phase 3) will be keyed on the
dentist's schedule and falls back to the clinic hours when the schedule is empty.

### D-30: Payment method + card type on the visit page; same-day retail joins the bill
Date 2026-10-02 (uncommitted) · Context: the administrator settles up on the visit page; the clinic wants the payment method (cash / card / bank transfer / insurance / mixed), the card type for card payments, and goods sold at the till (e.g. a toothbrush) added to the total. · Decision: the billing tab gets a method select and, for card / mixed, a card-type dropdown backed by a small editable catalog `clinic.card.type` (list from memory, Configuration → Card Types); transfer / insurance pay the whole total without amounts. `clinic_visit_register_payment` takes `method` + `card_type_id`; the amount due = procedures + the patient's unpaid retail sales (`is_clinic_retail`) made on the VISIT'S day — they are approved with the payment (standard confirmation raises the invoice) and linked by `sale.order.clinic_visit_id` so later visits do not pull them again. The visit form's "Register Payment" button was removed (the old wizard stays in code, reachable by `action_pay` only as a fallback). · Consequences: older unpaid retail sales are not pulled in; card-type names must be confirmed by the clinic; the invoice for retail goods follows the standard approval, not the procedure invoice.

### D-31: Allergy / pregnancy answers are mandatory and pregnancy is asked at every visit
Date 2026-10-02 (uncommitted) · Context: the clinic wants the administration to be unable to send a patient to the doctor without the allergy and pregnancy answers (like a missing surname or personal no.), pregnancy applies to women only, and pregnancy must not carry over to the next visit. · Decision: explicit yes / no selections on the card (`allergy_answer`, `pregnancy_answer`; the latter required only for female patients) checked in `_check_patient_data_complete` (arrival + start) and before a procedure is added; pregnancy is cleared on the card when a new visit is booked and when a visit is done (unless the patient is being treated right now) and frozen on the visit (`visit_pregnancy`) at arrival; the doctor sees a red sign + text on the visit form only for POSITIVE answers (clinic's sign icons from the user). · Consequences: any card save of a woman without a pregnancy answer is refused after a booking cleared it; enforcement is view `required=` plus these checks, not an SQL constraint; the icons are the first variant of each set (footprints, sneezing face).

### D-32: Treatment plan = free-text document with auto-pulled planned procedures
Date 2026-10-02 (uncommitted) · Context: the clinic fills a "TREATMENT PLAN" document by hand per person (often not yet a client); only the clinic header and the "Approved by" block are fixed. · Decision: `clinic.treatment.plan` (+ lines of free text, because prices come as "500 GEL // 250 GEL", "+ 196 EURO", …) and a QWeb PDF modelled on the user's file (logo + icons embedded as data URIs, repeating header through a paperformat, teal table, boxed totals). The patient link is optional; when set, the doctor's `planned` procedures are pulled in automatically (no duplicates). The patient name printed on the document is typed by hand. The prices follow the company currency (USD in this DB) until the clinic's currency is changed — to be done last. · Consequences: the fixed header text and CEO block are in the report template (editable via the view), not in settings; the PDF is not translated.

### D-33: Treatment-plan doctors = removable lines + "Add doctor"
Date 2026-10-05 (uncommitted) · Context: not every plan needs both an Implantologist and a Prosthodontist, and sometimes another clinic doctor has to be named. · Decision: the two Char fields become `clinic.treatment.plan.doctor` lines (profession text + optional `res.users` doctor from the Clinic Doctor group + printed name that follows the doctor and can be typed). New plans start with two empty lines (Implantologist, Prosthodontist) that can be deleted; "Add doctor" adds more; profession pre-fills from the doctor's Clinic Direction. The PDF prints every named line in order. Chief Medical Officer stays a single field. Old texts are moved into lines by an idempotent `<function>` on upgrade. · Consequences: the legacy Char fields stay on the model (empty) only for that move.

### D-34: Doctor double-booking is allowed (overlap guard narrowed); the board shows overlaps side by side
Date 2026-10-05 (uncommitted) · Context: the clinic wants one doctor to take two patients at the same time (one waiting, one in the chair); D-4's "same-dentist clash always blocked" stopped that. · Decision: `_check_clinic_overlap` no longer compares the doctor's own visits; a ROOM clash is raised only against a visit of ANOTHER doctor (the doctor's default room is the same room for both of his patients). The Planning board lays overlapping visits of a column out in lanes (`_layoutLanes` — equal-width side-by-side cards, up to 3 classes `cp_lanes/cp_lanes3`). The staff-schedule guard (S3) is unchanged. · Consequences: SPEC B2 / "double-booking" no longer describe a hard block; the room-overlap toggle still applies between different doctors.

### D-35: Tooth chart = the clinic's SVG chart driven by the procedure lines (supersedes the "clickable odontogram" milestone M4)
Date 2026-10-05 (uncommitted) · Context: the user supplied a healthy-teeth chart and a sheet of 14 diseases + 8 treatments; the plan (what to treat) and the work done must show the same picture on the visit page and on the patient card. · Decision: one OWL component `ClinicToothChart` (`static/src/tooth_chart/`) draws all 32 teeth (generated `tooth_chart_data.js`, side + occlusal view) and overlays drawn in code (no raster). The state is computed server-side by `res.partner.clinic_tooth_states()` from `clinic.procedure.history` rows: a planned / in-progress / postponed row with an ICD-10 → the DISEASE picture; a done row → the TREATMENT picture (done wins, the disease is dropped). ICD-10 → disease is `clinic.icd10.tooth_condition` (empty = prefix table `ICD_PREFIX` in `models/clinic_tooth.py`); done procedure → treatment is `product.template.clinic_tooth_treatment` (empty = keyword rules `TREATMENT_RULES`, with a veto list for "removal / fixing" names). Two layouts per user choice, "ვიზუალი 1" rows (default) and "ვიზუალი 2" arch with gum band and jaws from above (`arch_layout.js`), remembered in the browser's `localStorage`. The whole chart is ONE svg string rendered with `t-out` (injected fragments would land in the HTML namespace and not draw). On the card a tooth click opens an add dialog (diagnosis + procedure → planned row); on the visit page it selects the tooth as before. Milk teeth stay buttons. · Consequences: the manual `clinic.patient.tooth` statuses are only a low-priority fallback (the old `odontogram_html` is no longer shown); the design-2 overlays are approximations of the supplied sheet; the view choice is per browser, not per user.

### D-36: Pictures, examination results and allergy documents reuse `clinic.patient.document`
Date 2026-10-05 (uncommitted) · Context: X-ray / photo gallery with comments, examination results (file and/or typed), allergy documents, uploaded by doctors and by a new radiologist account. · Decision: no new model — `clinic.patient.document` gets `doc_type` values `exam_result` and `allergy_doc`, `result_text`, `uploaded_by_id`, and inherits `mail.thread` (comments on a picture = the standard chatter in a dialog form; upload time = the record's `create_date`). Medical tab (doctor only): "ალერგიის საბუთები", "გამოკვლევის შედეგები" lists and an X-ray / Photos kanban gallery with a full-screen viewer (`clinic_lightbox.js`); the visit page allergy section uploads allergy documents. Group `group_clinic_radiologist` (internal user + the "Radiology" menu: Patients list + "X-ray uploads"); the empty picture "+" opens a multi-file chooser (`clinic_image_upload` widget: first file fills the record, the rest become own records of the same patient). · Consequences: all document types share one ACL (`base.group_user` rwcu) — hiding is by view groups only; the radiologist has no write rights on patients; the "Documents" list in History still shows X-rays.

### D-37: A pregnancy answer is valid for one day (amends D-31)
Date 2026-10-05 (uncommitted) · Context: the answer kept on the card from an old visit made the system think it had been asked again. · Decision: `res.partner.pregnancy_answered_on` is stamped on every answer; `_clinic_missing_health_answers` treats an answer from an earlier day as missing; the daily cron `cron_clinic_reset_pregnancy` clears yesterday's answers (except for patients arrived / in progress). The booking / done clearing of D-31 stays. · Consequences: a woman cannot be started on a visit until the pregnancy question is answered that day.

### D-38: Product window = options (standard variants) + a small gallery model + reviews
Date 2026-10-05/06 (partly committed in ac54c92) · Context: the clinic wants the supply shop to behave like a marketplace product page (several pictures / a video, colour / size chosen BEFORE ordering, the supplier's own stock per option, stars / comments / photos of the received goods, sold / reviewed / returned numbers). · Decision: options = the STANDARD product attributes and variants (`product.attribute`, `product.template.attribute.line`); the supplier edits them in the panel as "name + values" (separated by comma, `;`, `/`, `|` or a new line) and `_clinic_apply_options` keeps the attribute lines equal to that list. The gallery is a tiny custom model `clinic.product.media` (picture or video link) because Community has no `product.image` without website_sale. Stock per variant = the supplier's own location tree (`stock.quant` under their warehouse), set from the same panel through a standard inventory adjustment (`_clinic_set_supplier_stock`, leaves a stock.move). `product.template.clinic_shop_detail` feeds the window (media, options, variants with the vendor price and own stock); the cart carries the CHOSEN variant, the cart clamps the quantity to that stock (pre-order products excepted) and `clinic_create_rfqs` refuses an oversize line on the server. Reviews: `clinic.shop.review` (+ `.image`), one per user and product, only for a product the clinic has RECEIVED (admin and doctor may review, suppliers may not); the order's own rating page also takes photos of the received goods and mirrors the rating into a review on every product of the order. Numbers shown: received units (sold), orders, review count / average / breakdown, the returns of the orders that contained the product. · Consequences: "returns" are per ORDER (the return model is per order), so every product of that order shows it; the stock check uses the current stock only (open, unshipped orders do not reserve it); the card button says "არჩევა" for products with options.

### D-39: Every clinic sale order gets a salesperson (supplier privacy fix)
Date 2026-10-06 (uncommitted) · Context: found by testing — a supplier saw 15 mirror orders of OTHER suppliers. The standard "Personal Orders" rule shows every order without a salesperson to every salesman, and the supplier group implies that role; the mirror sale.order was created with no `user_id`. · Decision: `_clinic_create_supplier_sale` sets `user_id` to the clinic user who placed the order (never a supplier); an idempotent `sale.order._clinic_fix_unassigned_orders` (called from `clinic_shop_seed.xml` on upgrade) repaired the 14 existing orders. The record rule "Clinic Supplier: own sales orders only" stays. · Consequences: any other code that creates a clinic sale.order must set `user_id` too.

### D-40: Shop category tree is seeded from code, pinned, and shown as a tree menu
Date 2026-10-05 (committed in ac54c92) · Context: the clinic gave a list of 15 material groups plus dentistry gaps; every comma-separated item is its own subcategory, only a "name: a, b, c" line makes a parent. · Decision: `models/clinic_shop_tree.py` holds the tree (20 top categories, ~226 nodes); `product.category._clinic_seed_shop_categories` creates the missing ones by name + parent on every upgrade, never renames, removes pinned nodes that left the tree (their products move up first) and gives each top category a starter picture only when it has none. `clinic_shop_pinned` keeps a node visible while no supplier has listed a product in it. The shop shows a left column ("🏠 მთავარი გვერდი" button + a text tree menu that opens the branch of the selection level by level) and big photo tiles on the "all categories" page. · Consequences: editing the tree = editing the Python file; the 13 new starter pictures are drawn placeholders (the clinic replaces them in Configuration → Categories).

### D-41: Home page and banner slots (video, width, height)
Date 2026-10-06 (uncommitted) · Context: the shop opens on a home page with ads only; banners may be a picture or a video (e.g. a YouTube Shorts link) in different sizes, orderable by the clinic. · Decision: `clinic.shop.banner` gets `video_url`, `size` (auto / third / half / two_thirds / full) and `height` (px); a picture OR a video is required; a YouTube / Vimeo link typed into "Link (URL)" is moved to `video_url`. The home page shows banners (6-column CSS grid; "auto" = position pattern small + wide, two medium, one full) then sponsored and new strips; the order is the list's drag handle (`sequence`). Videos play muted and looping (browsers only autoplay muted). · Consequences: a vertical Shorts video in a wide slot gets black bars from the YouTube player; the best-sellers strip was removed from the home page.

### D-42: Supplier's "My Orders" and order form show only what a supplier needs
Date 2026-10-06 (uncommitted) · Context: the supplier confirms the clinic's order and moves it through five delivery steps; the standard quotation buttons confuse. · Decision: a dedicated list view (what was ordered, quantity, ordered by, status, default filter "To confirm", no "New") over the mirror sale.order (`clinic_items`, `clinic_total_qty` computes); on the sale form the supplier group loses Send / Print / Preview / Create Invoice (invoices are not made by hand — their automatic creation is a later decision), Confirm is the strong button, "შეწყვეტა" a light-red one, and the delivery-step buttons are strong. · Consequences: the standard quotation statusbar is still shown; a supplier-side customer invoice is not generated automatically yet.

### D-43: New booking starts with "existing or new patient?"; the answer ticks First Visit / Repeat
Date 2026-10-07 (uncommitted) · Context: reception must record whether a visit is the patient's first (new patient) or a repeat one; the patient card already has the manual First Visit / Repeat Patient checkboxes. · Decision: both board entry points (slot click and "+ New Appointment") first open a small OWL chooser. "Existing patient" opens the booking form as before; "New patient (first visit)" opens the quick registration form and, once saved, the booking form with that patient pre-filled. The answer is stored on the visit (`calendar.event.clinic_visit_kind`: first/repeat, hidden on the form — the card shows it; the form's own "➕ new patient" button is hidden once the chooser decided) and, on create/write, ticks the card's `is_first_visit` / `is_repeat` accordingly. Cancelling the registration creates no booking. · Consequences: bookings created elsewhere (patient card "book" button, RPC) have no visit kind unless set on the form; the card flags follow the latest visit that carries a kind.

### D-44: An allergy answer is valid for 6 months (same pattern as D-37)
Date 2026-10-07 (uncommitted) · Context: like pregnancy, the allergy yes/no answer must be re-confirmed — but every 6 months, not every day. · Decision: `res.partner.allergy_answered_on` is stamped whenever `allergy_answer` is set; the existing daily cron (`_cron_reset_stale_pregnancy`) also clears allergy answers older than 6 months (skipping patients being treated right now), and `_clinic_missing_health_answers` treats such an answer as missing, so the doctor is asked again before a procedure. The recorded allergy list is kept, and the red allergy warning stays on while the answer is empty but allergies are on file. Answers given before this change were stamped with the upgrade day. · Consequences: the 6-month clock restarts on every new answer.

### D-45: First Visit / Repeat / Regular are counted from completed visits, never ticked by hand (amends D-43)
Date 2026-10-07 (uncommitted) · Context: the clinic wants these card flags computed by the programme from the visits. · Decision: `res.partner.is_first_visit / is_repeat / is_regular` become stored computes over `clinic_done_visits` (done/paid clinic visits): 0 → First Visit, 1+ → Repeat Patient, N+ → Regular Patient, where N is the system parameter `clinic.regular_patient_visits` (temporary 5 — the clinic has not decided yet). Non-patients get none. The booking chooser no longer writes the card (its answer stays on the visit as `clinic_visit_kind`). "Foreign Patient" stays manual; "Minor" was already computed. The Patients-list status (primary = 1, unique = 2+) is left as it is. · Consequences: changing N needs a recount (`_clinic_recompute_visit_flags`, run on every upgrade).

### D-46: The card's tooth chart and the table under it are one list of procedure rows (amends D-35)
Date 2026-10-07 (uncommitted) · Context: marking a tooth on the chart did not show in the table under it (that table was the separate manual `clinic.patient.tooth`), and the visit page's work had to show in both. · Decision: the card widget renders, under the chart, a table of the patient's `clinic.procedure.history` rows that name a tooth (`res.partner.clinic_tooth_rows`): tooth, diagnosis, procedure, status, date, doctor. A tooth click or "+ add" (tooth + diagnosis + procedure + status) creates a row; the status is changed inline and a row is deleted with 🗑 (`clinic_tooth_row_status` / `clinic_tooth_row_delete`; "done" stamps today + the doctor) — every change reloads both the table and the chart; rows of the visit page are the same rows, so they show too. Rows of a done / paid visit are read-only there (billing). The tooth tooltip shows the latest row's status. The old manual statuses stay below as "ხელით მითითებული სტატუსები (ძველი)" (still a low-priority chart fallback). · Consequences: the visit-lock check reads the visit with sudo, because a doctor may not read another doctor's visit.

### D-47: Treatment-plan rows get their status from the visits (amends D-46)
Date 2026-10-07 (uncommitted) · Context: the card chart/table is the doctor's treatment plan (e.g. 10 teeth); a visit may treat one tooth, or start one and finish it on a later visit — the status must follow the visit page, never be typed. · Decision: a plan row = a tooth row without a visit. A visit row with the same patient + tooth + procedure is linked to the oldest open plan row written before it (`clinic.procedure.history.plan_line_id`, on create/write; existing rows linked once on upgrade). The plan row's status is derived: a linked visit row done → done (date + doctor of that visit row); any other linked row → in progress; none → planned. Closing a visit (`action_done`) now turns only "planned" lines into done — a line the doctor left "in progress" (not finished) stays so and the plan row keeps waiting for the next visit. The card table shows plan rows + unlinked visit rows, status as a read-only badge with the number of visits; the add dialog always creates a planned row; a plan row already worked on cannot be deleted. · Consequences: the link needs the same procedure product on the visit as in the plan (a different procedure on the same tooth stays a separate row).

### D-48: Periodontal chart = one record per examination with a json of measurements (Medical tab)
Date 2026-10-07 (uncommitted) · Context: the doctor needs a periodontal (Bern-style, periodontalchart-online.com) chart in the patient's Medical tab. · Decision: model `clinic.perio.chart` (patient, date, doctor, optional visit, note) whose measurements are ONE `fields.Json` dict keyed by FDI tooth: missing, implant, mobility, and per side (buccal `b` / oral `o`) furcation (molars) plus 3 sites each of bleeding, plaque, gingival margin and probing depth. Gingival margin is in mm from the CEJ, positive = recession; CAL = PD + GM. Stored summary computes: teeth present, mean PD, mean CAL, BOP %, plaque %, sites ≥ 4 mm. UI: OWL view widget `clinic_perio_chart` on the Medical tab — history list + an editor grid per jaw (oral sides facing each other), live summary, PD ≥ 4 / ≥ 6 mm colouring; no `t-model` on computed keys (handlers instead). ACL: doctor rwcd, admin read. · Consequences: next steps (not built): graphical lines over the tooth drawing, PDF print, recession classifications, opening from the visit page.

### D-49: Medical card = the Ministry form IV-220/ა + IV-220-1/ა, filled only from existing data (step 1: vocabularies)
Date 2026-10-08 (uncommitted) · Context: the clinic needs the official dental patient card (cover, Annex N1 IV-220/ა, examination sheet N2 IV-220-1/ა, next-visits table) as a PDF, never typed by hand, always current; the examination sheet has fixed checkbox lists the visit page did not record. · Decision: step 1 — `clinic.complaint` gets `sequence` + `form_item` (one of the form's 18 complaint checkboxes or empty → "სხვა"); the clinic's own 38-item list (ჩივილები.pdf) + 4 form-only items are seeded (noupdate, editable in Configuration → ჩივილები), the old seeds were deleted on the clinic's request (2026-10-08) except "ქვისა და რბილი ნადების არსებობა" (a form checkbox) — 43 complaints in all. The visit gets `clinic_complaint_teeth` and `clinic_obj_checks` (json: perio / plaque / exam plan keys from the form); the old Char fields stay as each group's "სხვა". Profession = std `res.partner.function`. Step 2 (done the same day): `report_clinic_med_card` on res.partner (cover + Annex N1 + Annex N2 from the FIRST visit that took place + next-visits table, epicrisis and advice of the last visit; tooth scheme = the chart's current pictures as the legend's letter codes + mobility from the latest perio chart), built live by `_clinic_med_card_data` (sudo over the visits, access checked: doctor / admin only, report `group_ids` too); tab "🩺 სამედიცინო ბარათი" (missing-data list, PDF / print / refresh, live HTML preview in an iframe) and a 🩺 PDF link on the Patients kanban (user, 2026-10-08). · Consequences: the complaint → checkbox mapping is my reading of the two lists — the clinic must check it.

### D-50: Treatment plan has no patient link on the form (amends D-32)
Date 2026-10-08 (uncommitted) · Context: the user: the treatment plan is written for NON-clients, the administrator types everything on the doctor's instruction. · Decision: the "Patient (client card)" field and the "⟳ pull planned procedures" button are removed from the form, list and search; the model field and the pull code stay (old plans keep their link, nothing breaks). · Consequences: no automatic lines or prices — all amounts and totals are typed.
