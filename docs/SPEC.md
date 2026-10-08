<!-- last-synced: 2026-10-07, commit: 7f9b391 -->
# Technical spec — clinic_patient_card (whole module, v19.0.55.1.0)

Scope: everything live. AC-n refs point to `docs/PRD.md §13` (remaining work only, per user
decision — shipped features trace to PRD §4/§7 tables instead). D-n refs → `docs/DECISIONS.md`.

## Data model

### NEW models (all have `ir.model.access.csv` rows; `_description` set)
**`clinic.direction`** — specialty catalogue (batch #2). name✓(translate), sequence, active.
Seeded: თერაპია/ქირურგია/ორთოდონტია/ორთოპედია (`data/clinic_direction_data.xml`, noupdate).

**`clinic.cancel.wizard`** (Transient) — event_id✓, reason✓(Text); `action_confirm` writes
cancel_reason + state=cancelled (reason typed in the Cancel popup, batch #2).

**`clinic.slot.finder`(+`.line`)** (Transient) — LEGACY since v19.0.51.10: the visit form
uses the pure client-side finder dialog instead (D-16); the wizard remains as an RPC
fallback only (action_search fills lines + message; action_pick stores
picked_start/stop/dentist on the wizard — nothing writes the event directly).

**`clinic.brand`** — supply brand (batch #2 B1). name✓(translate, unique via
models.Constraint), logo(Image), active. 3 seeds in `data/clinic_stock_data.xml`.

**`clinic.purchase.request`(+`.line`)** — purchase pipeline in front of standard
purchase.order (batch #2 B2, D-15). Request: name(PRQ ir.sequence), source(low_stock/doctor/
manager/planned), requester_id, date_planned, state(draft→requested→review→approved|rejected→
ordered→in_transit→delivered→received→closed), reject_reason, purchase_order_ids(o2m via
purchase.order.clinic_request_id), mail.thread+activity. Line: product_id(domain
is_clinic_supply)✓, qty, location_id(internal), vendor_id + recommendation computes (sudo):
qty_on_hand at the target location, qty_other_cabinets, suggested_vendor_id + last_price
(last confirmed POL), recommended_qty (location min/max refill); `action_redistribute`
builds a prefilled internal transfer from the cabinet that has stock.

**`clinic.request.reject.wizard`** (Transient) — request_id✓, reason✓(required); a request
cannot be rejected without a comment (reviewer item 88).

**`clinic.product.media`** (D-38) — gallery item of a product: tmpl_id✓(cascade), sequence, image / image_1024 / image_128, video_url (YouTube / Vimeo / file; picture OR video required). **`clinic.shop.review`** (+ **`.image`**, D-38) — stars (rating 1-5), text, photos, author, optional order; unique per (user, product). `product.template.clinic_media_ids`; `purchase.order.clinic_rating_image_ids` (photos of the received goods, mirrored into the reviews). `clinic.shop.banner` also has video_url, size (auto/third/half/two_thirds/full), height (px) (D-41); image optional when a video is given.
**`clinic.shop.banner`** (batch #2 B3) — storefront promo banner. name✓, image✓(≤1600×500),
note, link_url (opens in a new tab on click), show_text (untick when the artwork carries its
own text), sequence, active. Two fixed slots side-by-side; 3+ banners rotate as a pair every
6s with arrows. Managed in Clinic → Configuration → Shop Banners.

**`clinic.shop.wishlist`** (batch #2 B3) — per-user shop wishlist. user_id✓(default self),
product_id✓, unique(user, product); GLOBAL own-rows rule (private per-user data).

**`clinic.supplier.move`** (Transient, v19.0.55) — supplier's internal move strictly inside
their OWN warehouse tree: product✓, src/dest (both ownership-checked), qty; builds and
validates a standard internal picking (full stock.move trail, visible in My Transfers).

**`clinic.purchase.return`** (batch #2 B4, D-18) — return/exchange of a delivered clinic
order. purchase_id✓, vendor_id(related stored), reason✓(Text), image(photo),
state(requested→review→approved|rejected→return_transit→closed), decision_note (REQUIRED to
reject), return_picking_id; mail.thread. Approve builds a reverse outgoing picking
stock→vendor by hand (the stock.return.picking wizard internals shift between versions).
The PO's Return button exists only 48h after the receipt and only without an open return.

**`clinic.room`** — treatment rooms.
| field | type | req | notes |
|---|---|---|---|
| name | Char | ✓ | |
| sequence / note / active | Int / Char / Bool | |  toggle |
| location_id | M2o stock.location | | auto-created under WH/Stock/Cabinets on room create; renamed with the room; backfilled by `_clinic_sync_locations` (function tag on every upgrade) |

**`clinic.appointment.type`** — visit types (colour legend on the board).
| field | type | req | notes |
|---|---|---|---|
| name | Char | ✓ | |
| default_duration | Float (h) | | float_time widget (HH:MM); onchange ALWAYS applies it on type change (guard removed v19.0.51.7) |
| procedure_id | M2o product.product | | domain `is_clinic_procedure` |
| color / active | Int / Bool | | board palette index |

**`clinic.patient.phone`** — patient phone lines (o2m from partner).
| field | type | req | notes |
|---|---|---|---|
| partner_id | M2o res.partner | ✓ | cascade |
| phone | Char | | constrained digits-only (`PHONE_RE`) |
| sequence, phone_type, channel, country_code | — | | channel: call/sms/whatsapp |
| is_primary, is_emergency, is_foreign_number | Bool | | |
| owner_name, relation, note | Char | | emergency contact info |

**`clinic.patient.allergy`** | partner_id✓, allergy_type(Sel), name, reaction, severity(Sel),
test_done(Bool), test_result, note.

**`clinic.patient.tooth`** — FDI chart rows. partner_id✓, tooth_number(Char, FDI), status(Sel:
healthy/caries/filled/crown/root_canal/implant/missing/to_extract/other), note.

**`clinic.patient.document`** (inherits `mail.thread`, D-36) | partner_id✓, doc_type(Sel: id_scan/consent/xray/exam_result/allergy_doc/insurance/other; `consent` shows signature),
name, date, attachment(Binary)+filename, signature(Binary, widget=signature), note, result_text(Text, typed exam result), uploaded_by_id(M2o users, default creator); upload time = `create_date`; `action_open_full` / `action_add_next`. `res.partner` exposes the filtered o2m `xray_ids`, `exam_result_ids`, `allergy_doc_ids` (Medical tab).

**`clinic.procedure.history`** | partner_id✓(cascade), appointment_id(M2o calendar.event,
set null), procedure_id(M2o product.product, domain is_clinic_procedure), name, status(Sel,
default done), qty, planned_date, procedure_date, doctor_id(M2o res.users), tooth, note.
create() backfills partner from appointment.

**`clinic.payment.wizard`** (TransientModel) | event_id, partner_id, payment_method(Sel:
cash/card/transfer/insurance/mixed), amount_total(compute), amount_cash, amount_terminal,
summary(Html), note. Mixed: cash+terminal must equal total (float_compare).

#### Dentos-parity batch (D-22, v19.0.56–60)
- **clinic.consent** — per-visit consent sheets: visit_id, patient_id (related),
  consent_type (personal_data|medical), body snapshot, agree_data,
  agree_marketing_terms, marketing_sms (yes/no, recorded only — SMS deferred),
  signature (binary, Community `signature` widget), state draft/signed,
  signed_date/uid. action_confirm guards (agreement / signature required),
  chains personal_data → medical, posts to visit chatter, stores the first
  medical signature on the partner as clinic_signature_sample.
- **clinic.icd10** — code (unique) + name + `tooth_condition` (Sel, picture on the tooth chart, D-35); 24 dental K00–K14 codes seeded
  (data/clinic_icd10_seed.xml, noupdate); menu Configuration → ICD-10 (admin).
- **tooth chart (D-35)** — `models/clinic_tooth.py`: `product.template.clinic_tooth_treatment` (Sel), `res.partner.clinic_tooth_states()` (RPC: {fdi: cond/treat/labels} from the procedure lines), tables `ICD_PREFIX` / `TREATMENT_RULES`.
- **clinic.complaint** — complaints catalog (name); 9 seeded; admin CRUD,
  doctor read.
- **clinic.prescription** — visit_id, rec_type (e_recipe|prescription|
  recommendation — recorded only, no external sync), medicament, period, qty,
  directions. Add/delete from the visit page's დანიშნულება section.

### MODIFIED (inherited) models — key additions
**`res.partner`** (~60 patient fields, abridged by group):
| group | fields |
|---|---|
| master | is_patient(indexed), patient_ref(ir.sequence P%05d), can_edit_medical(compute) |
| basic | name_latin, birthdate, age(compute), gender, registration_date, referral_source(+_other), is_foreign, nationality_country_id, is_first_visit/is_repeat/is_regular/is_minor(compute), guardian_id, patient_note |
| medical | allergy_ids, anamnesis_general, chronic_diseases, current_medications, is_pregnant, smoker, alcohol, family_history, has_bleeding_disorder, has_cardio_risk, medical_risk_notes, has_xray, has_ct, imaging_source, medical_update_date/_uid (auto-stamped in write()) |
| dental | last_dental_visit_date, treatment_plan_status, tooth_ids, odontogram_html(compute), has_bruxism, periodontitis_risk, dental_other_notes, procedure_history_ids |
| financial | preferred_payment_method, discount_percent/_fixed, loyalty_status, insurance_company_id(M2o partner, domain is_insurance_company)/policy_no/valid_until/notes, is_insurance_company |
| profile | document_ids, no_show_rate, ltv_forecast, risk_level, risk_notes |
| family | family_member_ids (M2m self, clinic_family_member_rel — linked patient profiles) |
| search | `_rec_names_search += phone, patient_ref` (+vat via base); `_compute_display_name` appends `· vat · phone` under ctx `clinic_show_ids` |
| constrains | `_check_patient_email` (latin `EMAIL_RE`), `_check_patient_phone` (digits), `_check_patient_vat` (digits + unique among patients, python search_count) |

**`calendar.event`** (clinic visit when `is_clinic=True`):
| group | fields |
|---|---|
| core | is_clinic, patient_id(M2o partner — required via constrain when is_clinic), dentist_id(M2o users), assistant_id(M2o users), curator_id(M2o users, "Curator", same user list; shown on the visit page), room_id, appointment_type_id, clinic_state(Sel: requested/booked/confirmed/arrived/in_progress/done/paid/cancelled/no_show; tracked) |
| medical | diagnosis (string **Comment**, batch #2), procedure_line_ids(o2m clinic.procedure.history), tooth_display(compute) |
| money | currency_id, amount_paid, amount_cash, amount_terminal, payment_method |
| tracking | checkin_time, treat_start_time, treat_end_time, waiting_minutes, chair_minutes, parent_appointment_id, parent_visit_info(compute), was_rescheduled, duration_edited, cancel_reason |
| dispensary | is_dispensary, dispensary_notified |
| batch #2 | direction_id(M2o clinic.direction; auto from dentist), family_link_id(M2o partner, domain = patient family), family_member_domain_ids(compute), referral_source(related patient, rw) |

**`res.users`**: default_room_id (M2o clinic.room) + direction_id (M2o clinic.direction —
doctor specialty for slot search/autofill); both on the "Clinic" tab + `clinic_dentists()`
(board columns: admins get all doctors, a plain doctor only themself).
**`res.company`**: clinic_workday_mon..sun(Bool), clinic_work_start/_end(Float, widget
float_time), clinic_block_room_overlap(Bool, default True); "Clinic Schedule" tab; helper
`_clinic_workdays()`.
**`product.category`** (D-40): clinic_shop_pinned (tile / menu node stays while empty) + `_clinic_seed_shop_categories` (tree in `models/clinic_shop_tree.py`); image_128 (storefront tile photo) + clinic_shop_visible (default on —
untick to keep the category tile/chips out of the shop even while it holds products).
**`stock.location`**: clinic_supplier_id (D-19 — which supplier owns this location; children
created under a supplier location inherit it, keeping the scoping rules airtight).
**`product.template`**: is_clinic_procedure, is_clinic_supply; batch #2 B3:
clinic_sponsored + clinic_preorder storefront flags, `clinic_shop_data()` (one RPC feeding
the whole shop v2: offers with brand/badges/vendor-rating, categories+images, banners,
bestseller ids [90-day PO qty], wishlist ids, last order for repeat) and
`clinic_wishlist_toggle(product_id)`; batch #2 B1:
clinic_brand_id(M2o clinic.brand — the SUPPLIER picks/creates brands in My Shop, name-
deduplicated case-insensitively; the Brands dictionary menu is base.group_system only),
clinic_shop_published (soft hide from the shop, supplier-toggled — the vendor line stays,
unlike Remove), clinic_avg_consumption (sudo compute — 90-day outgoing
internal→customer/production/inventory moves ÷ 3), clinic_last_purchase_price (sudo compute —
last confirmed POL, fallback first seller price); `_clinic_notify_low_stock()` (cron; B2:
also auto-drafts a source=low_stock purchase request unless an open one covers the product);
supplier self-service API `clinic_supplier_products / _save_product / _unpublish`
(sudo writes, vendor-scoped in code, D-3).
**`purchase.order`**: is_clinic_order, clinic_sale_id, clinic_request_id (batch #2 B2);
batch #2 B4: clinic_delivery_status(related from the mirror SO), clinic_receipt_date +
clinic_return_allowed (48h window computes), clinic_return_ids, star ratings
clinic_rating_product / clinic_rating_vendor (1-5) + note (vendor averages feed the shop and
the dashboard), `action_clinic_return`, and `clinic_dashboard_data()` — the manager
dashboard RPC (11 blocks: low/excess per location, requests to approve, ongoing orders with
supplier status, late deliveries, monthly spend, spend by category, top-used, expiry-risk
lots ≤30d, vendor performance rating+on-time %, planned requests);
`clinic_create_rfqs(cart)` (one RFQ per vendor + mirror SO), `_clinic_notify_vendor/_confirmed`,
button_confirm hook.
**`stock.picking`** (batch #2 B2/B4): `button_validate` hook — a DONE incoming receipt flips
its linked purchase request(s) to received, pings admins about rejected-deficit arrivals,
and AUTO-DRAFTS the vendor bill for clinic orders without one (item 16, user decision:
invoice auto, waybill attached by hand; billing failures never block the receipt).
**`sale.order`**: is_clinic_order, clinic_supplier_id, clinic_purchase_id;
batch #2 B4: clinic_delivery_status (availability/preparing/ready/in_transit/delivered) +
five supplier buttons — advanced BY HAND (no courier, user decision); every step posts to
the linked PO chatter and toasts admins over `clinic_order_confirmed`. Pressing In Transit
also SHIPS: a validated internal picking moves the ordered qty supplier-warehouse →
their transit shelf (reserved from shelves first, forced negative if uncounted) — the
supplier's stock drops at shipping time, the clinic's rises only on receipt (D-19).
`action_confirm` → `_clinic_notify_clinic_confirmed` (mirror-confirms PO).
Batch #2: is_clinic_retail flag; create() FORCES user_id to the drafting plain doctor (the web form sends the partner salesperson — v19.0.51.18) + notifies
admins (activity + bus `clinic_sale_request`); action_confirm auto-invoices retail orders;
default_get skips sale_pdf_quote_builder's salesman-gated default for non-salesmen;
`_compute_available_quotation_document_ids` runs sudo (D-14).
`sale.order.line._action_launch_stock_rule` → no-op for clinic orders (D-2).

### Dentos-parity field additions (v19.0.56–60)
| model | additions |
|---|---|
| res.partner | first_name/last_name (create/write joins into `name`; a typed name wins), address_latin, clinic_signature_sample (binary), clinic_visit_ids (o2m calendar.event, is_clinic domain); vat check: foreign patients may hold an alphanumeric passport no. (digits-only + unique stays for locals) |
| calendar.event | observer_ids (M2M res.users), referral_user_id, consent_ids/consent_signed (compute), clinic_case_type (planned/urgent), clinic_complaint_ids (M2M) + clinic_complaints_other + clinic_complaints (anamnesis), clinic_obj_* ×7 (bite/mucosa/periodontium/pocket depth/plaque/exam plan/other), clinic_exam_results, clinic_prescription→prescription_ids (o2m), clinic_epicrisis; methods: clinic_visit_page_data (one-round-trip page payload), action_open_visit_page, action_open_consents, clinic_visit_register_payment (cash+terminal must equal the discounted total; reuses _create_invoice_from_procedures; sets paid) |
| clinic.procedure.history | icd10_id, currency_id, price_unit (defaults from product lst_price), discount_percent, amount_total (stored compute qty·price·(1−disc%)) |

### 2026-09-30 additions (morning commit 506b4f4 + uncommitted afternoon work)
| model | additions |
|---|---|
| res.partner | `_compute_display_name`: a patient with a parent (workplace) shows their OWN name — base's "Company, Person" prefix dropped (the `clinic_show_ids` ` · vat · phone` suffix is kept); `company_type` switch `invisible="is_patient"` on the form |
| res.partner (quick form) | `view_clinic_patient_quick_form` is now MINIMAL (user, 2026-10-01): foreign-citizen toggle, `first_name`✱, `last_name`✱, `phone`✱, `insurance_company_id` (view ctx creates an insurer) — everything else (birth date, personal no., referral source, gender, foreign data, health) is filled on the card at arrival; the view was full-featured earlier the same day and shrunk on request |
| calendar.event | `family_link_id` domain = any patient except the booked one (was: only linked family); m2o carries `form_view_ref` = quick form + `default_is_patient`; `patient_id`: `no_quick_create`, ctx `default_is_patient`; done/paid hides new-patient/slot buttons, appointment_type, family link, referral, dentist, assistant, room |
| clinic.patient.allergy | ACL row: `group_clinic_admin` rwcu (was doctor-only writes) |
| data | `data/clinic_insurers_seed.xml` — 7 Georgian insurers (`is_insurance_company`, noupdate), list from memory, clinic to confirm |
| static | `gender_widget/` (clinic_gender_icons, avatar cards), `live_search/clinic_live_search.js`, `img/tooth-sparkle.svg` (planning open-page button) |

### 2026-10-01 additions (uncommitted on top of d4ec77a)
| model | additions |
|---|---|
| res.partner | `allergy_answer` / `pregnancy_answer` Selection yes/no (tracked in MEDICAL_TRACKED_FIELDS; `pregnancy_answer` also writes `is_pregnant`, create+write `_clinic_sync_pregnancy`); `clinic_done_visits` (Integer) + `clinic_patient_status` (Selection primary/unique) — stored computes over `clinic_visit_ids.clinic_state` (done/paid: 1 → primary, 2+ → unique, 0 → none); `_compute_display_name` now strips the workplace prefix for EVERY patient (company_name text as well as parent_id); `action_back_to_visit` |
| res.partner (card) | required for patients: `first_name`, `last_name`, `vat`, `birthdate`, header `phone`, `referral_source`, `allergy_answer`, `pregnancy_answer` (hidden for men; required when gender != male); `allergy_ids` moved from the doctor-only Medical group to the header (shown when `allergy_answer=yes`, required then, editable by admin+doctor); `name_latin`/`nationality_country_id` only when `is_foreign`; stat-button box, company switch and `is_patient` hidden for patients; Create Invoice / Payment buttons admin-group only; "← back" bars driven by ctx `clinic_return_visit_id` (+ `clinic_return_page`) |
| res.partner (address) | separate inherit `view_partner_form_patient_address` (priority 20): street = residence, street2 = legal, city = std `city_id` dropdown (Create allowed, default country GE), state hidden, ZIP+country only for foreign patients |
| data | `data/clinic_cities_seed.xml` — 17 Georgian `res.city` rows (noupdate, list from memory) |
| controllers | `controllers/patient_export.py` — `/clinic/patients/export?status=primary|unique` (auth user, admin or doctor group) streams an .xlsx built with xlsxwriter |
| static | planning board re-opens a visit when its client-action ctx carries `open_visit_id`; visit page `openPatient` passes the return ctx; gender cards shrunk to 70px |
| manifest | v19.0.61.0.0; depends += `base_address_extended` |

### 2026-10-01 staff schedules (S1)
| model | additions |
|---|---|
| clinic.shift | name/hours (stored compute "09:30–15:00"), staff_kind (doctor/assistant/admin), start_hour, end_hour, color 0-11 (12-colour palette: pink, green, yellow, blue, purple, orange, teal, red, lime, indigo, sand, slate; new times take the first unused colour, the admin can pick one), sequence, active; 12 seed rows (noupdate) |
| clinic.schedule.line | employee_id (hr.employee), date, day_type (shift/off/vacation/sick), shift_id; one row per employee-day (python constraint); RPC `clinic_schedule_data(kind, from, to)` / `clinic_schedule_set(employee, date, day_type, shift)` (admin only, sudo) |
| hr.employee | `clinic_staff_kind` (puts the person on the schedule); `clinic_sync_staff()` creates employees for active clinic doctor/administrator users (skips base.user_admin and login `clinic`) |
| security | ACL: shift/line user read, admin rwcu; rules: doctor reads only own days (employee.user_id), admin all |
| views | client action `clinic_schedule` (`static/src/schedule/`), menu Clinic → გრაფიკი (admin+doctor), Configuration → Shifts (admin), `hr.view_employee_form` + Clinic Role |

### 2026-10-01 worked hours (S2)
| model | additions |
|---|---|
| clinic.schedule.line | RPC `clinic_hours_data(kind, from, to, mode)`: per employee planned (shift hours), planned-to-date, worked (hr.attendance, local day of check-in; an open attendance counts until now, max 16 h), diff, overtime (per-day excess), lateness (first check-in later than shift start + 5 min), absent days (shift day before today with no attendance), vacation/sick/off counts, completion %, in/out of the day; chart buckets (day/week → days, month → weeks, year → months) |
| controllers | `/clinic/worked_hours/export?kind&mode&date_from&date_to` → .xlsx of the same rows (admin or doctor; a doctor gets only their own row) |
| security | `group_clinic_admin` implies `hr_attendance.group_hr_attendance_user` (corrects any attendance); doctors check in/out through the standard systray / kiosk |
| views | client action `clinic_worked_hours` (`static/src/hours/`), menu Clinic → ნამუშევარი საათები; manifest depends += `hr_attendance` |

### 2026-10-01 booking guard + shift editing (S3)
| model | additions |
|---|---|
| calendar.event | `_clinic_staff_window(dentist, date)` → None (no schedule entry: clinic hours rule only) / False (off, vacation, sick) / (start_h, end_h); `_clinic_validate_staff_schedule` on create (needs dentist_id, not reserve) and on write when start/stop/duration/dentist change; `clinic_free_slots` intersects the shift and skips non-working days; `clinic_force=1` skips |
| clinic.schedule.line | `clinic_shift_save(kind, shift_id, start, end)` (admin; new time or edit — an edit applies from TODAY: if the old shift has past days, a new template takes today/future days and the old one is archived), `clinic_shift_delete`, `clinic_schedule_set` now returns `{conflicts: n}` (live visits of that doctor/day outside the new window — warned, never moved) |

### 2026-10-01 schedule extras (after S1-S3)
| area | additions |
|---|---|
| clinic.schedule.line RPC | `clinic_schedule_data` also returns `kind`, `visible_kinds`, `closed_weekdays` (from `res.company._clinic_workdays`; Sunday today), archived shifts still referenced; non-admin is forced to their own staff group (`_clinic_resolve_kind`: a doctor always opens "ექიმები", an administrator "ადმინისტრაცია", Administrator → doctors); `clinic_schedule_set(..., start, end)` accepts custom hours (find-or-create `clinic.shift`, `_clinic_custom_shift`), refuses closed weekdays, returns `{conflicts}` |
| clinic.shift colour | `_clinic_next_color(kind)` (first unused of 12), `clinic_shift_save(kind, id, start, end, color)` (colour-only change = in place), SHIFT_PALETTE mirrors `$cs_palette` in clinic_schedule.scss |
| calendar.event | `clinic_board_staff(date)` → {user_id: shift (start/end/name/colours) \| off/vacation/sick (label)} for the Planning board |
| Planning board | per-doctor column: shift chip in the header, shift band tinted with the shift colour, everything else hatched (`.cp_stzone`), whole column hatched on off/vacation/sick; hover / drag / click disabled outside the shift (`_isWorkTime(hour, dentistId)`), a drag-sized visit cannot pass the shift end |
| schedule screen | day / week / month, grid + matrix looks, toolbar ＋ დამატება, "საკუთარი დრო" inputs, sidebar shift editor with colour palette, closed days hatched "უქმე" |

### 2026-10-02 payment, health answers, patient card, treatment plan (uncommitted on top of 101440c, v19.0.62.0)
| area | additions |
|---|---|
| clinic.card.type (new) | name (translate), sequence, active; seed Visa / Mastercard / American Express / UnionPay / სხვა (noupdate, from memory); Configuration → Card Types (admin); ACL user r / admin rwcu |
| calendar.event | `card_type_id` (m2o), `visit_pregnancy` (yes/no, frozen at arrival), `health_pregnancy_alert` / `health_allergy_alert` / `health_allergy_info` (computes, POSITIVE answers only); `clinic_visit_register_payment(cash, terminal, method, card_type_id)` — methods cash / card / transfer / insurance / mixed (transfer + insurance = whole total, no amounts); total = procedures + `_clinic_pending_retail()`; unpaid same-day retail sales are confirmed (std approval raises their invoice) and tied via `sale.order.clinic_visit_id`; `_clinic_clear_card_pregnancy` (on done) / `_clinic_reset_pregnancy` (on booking); `action_pay` redirects admins to the visit page (old wizard kept as fallback, its form button removed); visit page payload adds `card_types`, `retail`, `patient.health` |
| res.partner | `allergy_answer` / `pregnancy_answer` yes/no (pregnancy only for gender = female), `_clinic_missing_health_answers`, `_clinic_health_warning`; `is_pregnant` follows the answer; both answers are required on the card and checked at "მოსული" and at start (`_check_patient_data_complete`) and before adding a procedure (`clinic.procedure.history.create` → `_check_patient_health_answers`) |
| patient card layout | order: address → tabs; Patient Card tab = booking button, quick buttons (by role), identity block (+ allergy list), former Basic block (flat), Contact info, Financial sub-tab (admin); Medical (doctor only) + History moved to the OUTER tab bar after Notes; Contacts tab shows guardian + family members (editable) instead of child contacts; "Partner Assignment" (geo) tab hidden; quick-action buttons: reminder / invoice / payment admin-only, oral chart / EHR doctor-only |
| quick registration | name, surname, mobile, insurance + foreign toggle; `name_latin` required when `is_foreign` |
| clinic.treatment.plan (+ .line) (new) | printable "TREATMENT PLAN": patient_name (typed), optional patient_id, date, doctor lines `clinic.treatment.plan.doctor` (profession + doctor + printed name, removable, "Add doctor"; D-33) + chief_doctor, free-text lines (visit / department / tooth / procedure / unit price / price), note, schedule, 2 totals, payment note; lines auto-pulled from the patient's `planned` procedures (`procedure_history_id` prevents duplicates); QWeb PDF with logo + contact icons (data URIs), repeating header via paperformat, fixed header + "Approved by" block; Clinic menu "მკურნალობის გეგმა"; ACL admin + doctor rwcu |

### 2026-10-07 additions (uncommitted on top of 0e91ff5)
| area | additions |
|---|---|
| clinic.treatment.plan.doctor (new, D-33) | plan_id✓(cascade), sequence, role (compute from the doctor's Clinic Direction, editable), doctor_id (Clinic Doctor group), name (printed, follows the doctor, editable); plan default = 2 empty lines Implantologist / Prosthodontist; legacy `implantologist` / `prosthodontist` Char moved in by `_clinic_migrate_doctor_lines` (idempotent) |
| calendar.event | `clinic_visit_kind` (first / repeat, hidden on the form, set by the board chooser — D-43); `_clinic_treated_now_domain` (arrived / in progress AND started < 12 h ago); `_check_visit_page_open` (page only from arrived on); write refuses `clinic_state = cancelled` once in progress / done / paid; `action_done` turns only `planned` lines done (in-progress lines stay — D-47); visit-page payload: `patient.child` (age < 14), `exam_docs`, full allergy columns; prescription sheet: `_clinic_report_prescriptions`, `action_prescription_pdf`, `action_prescription_send` (models/clinic_visit_medical.py) |
| res.partner | `is_first_visit` / `is_repeat` / `is_regular` = stored computes over `clinic_done_visits` (0 / 1+ / N+, N = param `clinic.regular_patient_visits`, temp 5 — D-45); `allergy_answered_on` + 6-month expiry (D-44); `health_pregnancy_alert` / `health_allergy_alert` / `health_allergy_info` (form banner); `allergy_doc_card_ids` (2nd o2m on the allergy documents) + `allergy_doc_count`; tooth table RPCs `clinic_tooth_rows` / `clinic_tooth_row_delete`; `perio_chart_ids` |
| clinic.procedure.history | `plan_line_id` / `visit_line_ids` (visit row ↔ treatment-plan row, D-47); `_clinic_link_plan`, `_clinic_sync_plan_status`, `_clinic_visit_locked` (sudo read of the visit state) |
| clinic.patient.document | `_onchange_filename_title` (title from the file name) |
| clinic.perio.chart (new, D-48) | partner_id✓, date, doctor_id, appointment_id, `data` (Json per FDI tooth), note; stored summary teeth_present / mean_pd / mean_cal / bop_pct / plaque_pct / deep_sites |
| reports | `report_clinic_prescription` (clinic header like the treatment plan, the plan's paperformat) + `mail_template_clinic_prescription` (PDF attached, to the patient) |
| widgets / JS | board chooser `clinic_booking_chooser` (existing / new patient), `clinic_image_click` (empty image "+" opens the file chooser, product form), `clinic_allergy_upload` (card button), `clinic_perio_chart` (Medical tab), tooth chart widget = chart + plan table |

## Business logic (trigger → condition → action; Standard coverage per row)
| # | trigger | condition | action | std coverage |
|---|---|---|---|---|
| B1 | create/write on calendar.event | `'start' in vals`, not `clinic_force`, is_clinic | `_clinic_validate_schedule`: block outside company workdays/hours; block past (>5-min grace) unless user == `base.user_admin` | custom (D-4, D-5) — resource.calendar rejected |
| B2 | constrains start/stop/dentist/room/state | is_clinic, state not in requested/cancelled/no_show | `_check_clinic_overlap`: a doctor MAY have overlapping visits (D-34); same-room clash only against ANOTHER doctor's visit, behind `clinic_block_room_overlap`; sudo() search (doctor rule can't hide clashes) | custom (D-4, narrowed by D-34) |
| B3 | `action_arrive` | admin | state→arrived, checkin_time; bus `clinic_patient_arrived` + activity to dentist | std bus/mail.activity + custom |
| B4 | `action_start` | doctor | guard `_check_patient_data_complete` (vat+phone+birthdate) then in_progress | custom (reviewer) |
| B5 | `action_done` | doctor | push procedure_line_ids → clinic.procedure.history, stamp last_dental_visit_date | custom |
| B6 | `action_pay` → wizard confirm | done | draft invoice from procedure products (std account.move), state→paid, store amount_cash/terminal (mixed split validated) | std invoicing + custom split |
| B7 | write start/duration | state booked..in_progress | set was_rescheduled / duration_edited (✎ badge on board) | custom (reviewer) |
| B8 | `action_next_visit` / `action_dispensary_next` | done/paid | prefill new visit +7d / create `requested` reserve +182d (clinic_force, is_dispensary) | custom |
| B9 | `action_book` / `action_to_reserve` | requested / booked-confirmed | requested↔booked (book re-runs B2) | custom (D-6) |
| B10 | daily cron `cron_clinic_dispensary` | reserve starts ≤14d, not notified | to-do + bus `clinic_dispensary_due` to admins; idempotent flag | std ir.cron/activity/bus |
| B11 | weekly cron `cron_clinic_booking_report` | — | booking summary activity on each admin's partner (res.users has no chatter) | std |
| B12 | daily cron `cron_clinic_low_stock` | orderpoint qty < min, is_clinic_supply | activity on product + bus `clinic_low_stock` | std reordering rules + custom alert |
| B13 | shop checkout `clinic_create_rfqs` | cart lines | PO per vendor (state→sent) + mirror SO; notify supplier (activity+bus on SO) | std purchase/sale + custom chain (D-1, D-2) |
| B14 | SO `action_confirm` by supplier | is_clinic_order | mirror-confirm PO, notify clinic (`clinic_order_confirmed`) | custom (D-2) |
| B15 | partner create/write | is_patient | validations (latin email, digit phone/vat, unique vat) | custom (reviewer) — base_vat not used |
| B16 | Contacts app create | — | `default_is_patient=True` via ctx override on `contacts.action_contacts` | std context config |
| B17 | „🕐 თავისუფალი დროები" / `clinic_free_slots(direction, duration, date_from, days, dentist_id)` | client dialog on the visit form | free 10-min slots inside company schedule minus busy visits (sudo, tz-aware, no past, base.user_admin excluded); opens PRE-FILTERED by the visit's direction+doctor+date (doctor chip removable); pick lands in the OPEN form via record.update — nothing saved until Save | custom (no Community slot engine — D-8/D-16; batch #2 plan) |
| B18 | doctor creates sale.order `is_clinic_retail` | plain doctor | admins get to-do + `clinic_sale_request` toast; doctor auto-follows; admin Confirm → auto draft invoice; Cancel+comment visible to doctor; own-drafts rules block self-confirm | std sale/invoice + custom flow (D-13, D-14) |
| B19 | `action_cancel` | is_clinic | opens clinic.cancel.wizard popup (reason required) → cancelled | custom (reviewer: reason on the button itself) |
| B20 | onchange dentist / create | is_clinic | auto room (default_room_id) + auto direction (users.direction_id); subject auto "Patient — Type" (field hidden) | custom (batch #2) |
| B21 | room create/rename; module upgrade | — | stock.location auto-created/renamed under WH/Stock/Cabinets; sync function backfills old rooms | std stock.location tree + thin auto-create (batch #2 B1) |
| B22 | purchase request lifecycle | see clinic.purchase.request | submit→admin activities; review→approve/reject(comment wizard); Place Order→RFQ per vendor; receipt validate→received; stock changes ONLY on the standard receipt ("delivered ≠ received") | custom pipeline (D-15) over std purchase/stock |
| B23 | incoming receipt validated | product has a REJECTED request line | bus clinic_low_stock toast to admins + note on the request ("back in stock") | custom (batch #2 item 29) |
| B24 | daily low-stock cron | orderpoint qty < min | in addition to B12: auto-draft a source=low_stock purchase request (idempotent while one is open) | custom (batch #2 B2) |
| B25 | Supply Shop v2 storefront | — | banners / sponsored / new (≤30d) / bestseller strips, category tiles+subcat chips, brand filter, wishlist, pre-order badge, repeat-last-order, similar-products strip, vendor price comparison | custom OWL over std data (batch #2 B3, D-1 umbrella) |
| B26 | supplier advances delivery status | mirror SO, own | 5 manual steps → PO chatter + admin toast (no courier — user decision) | custom on the D-2 mirror chain |
| B27 | receipt validated | clinic PO without bills | vendor bill auto-drafted (item 16, user decision) | std purchase invoicing, auto-triggered |
| B28 | „🔄 დაბრუნება" on the PO | ≤48h after receipt, no open return | reason(+photo) → supplier review → approve (auto reverse picking stock→vendor) / reject (comment required) → return-transit → closed | custom pipeline over std picking (D-18) |
| B29 | manager rates a received order | clinic PO received | ★1-5 product + vendor + note; vendor averages in shop cards/comparison/dashboard | custom (item 28) |
| B30 | 📊 Stock Dashboard | admin | one clinic_dashboard_data RPC renders 11 monitoring blocks | custom OWL over std data (items 102-114) |
| B50 | shop product window opens | clinic user | `clinic_shop_detail`: gallery + options + variants with the vendor's price and OWN stock; cart carries the chosen variant, qty clamped to its stock (pre-order excepted); `clinic_create_rfqs` refuses an oversize variant line (D-38) | custom over std attributes / variants |
| B51 | clinic reviews a product | admin / doctor, product RECEIVED by the clinic | `clinic_shop_review_save` (stars, text, photos); the order rating mirrors into a review on each product of the order; numbers: sold, orders, average, breakdown, returns (D-38) | custom model |
| B52 | clinic places an order | — | the mirror sale.order gets `user_id` = the placing clinic user; `_clinic_fix_unassigned_orders` repaired old rows (D-39) | custom fix over the std "Personal Orders" rule |
| B53 | supplier opens My Orders / an order | supplier group | list: ordered items, ordered by, status, filter To confirm; buttons Send / Print / Preview / Create Invoice hidden (D-42) | view inheritance |
| B54 | board slot click / + New Appointment | clinic user | chooser "existing / new patient": existing → booking form (kind repeat); new → quick registration (optional birth date + age) → booking form with the patient (kind first); cancel = no booking (D-43) | custom OWL dialog over std forms |
| B55 | a clinic visit becomes done / paid (or not) | is_patient | First Visit / Repeat / Regular recounted from completed visits (D-45) | stored compute |
| B56 | allergy answered | — | stamp `allergy_answered_on`; daily cron clears answers > 6 months (skips patients treated now), the doctor is asked again; list + red warning kept (D-44) | custom over std cron |
| B57 | visit page / board icon / history button | state < arrived | page refused (button hidden, server UserError) | custom guard |
| B58 | cancel a visit | in progress / done / paid | refused (button hidden, write guard) | custom guard |
| B59 | tooth row added on the card (chart click / + add) | — | planned plan row; a visit row with the same tooth + procedure links to it; status follows the visit rows (planned → in progress → done); rows of closed visits read-only (D-46/D-47) | custom over clinic.procedure.history |
| B60 | prescription print / PDF / e-mail on the visit page | ≥1 prescription | std report action / `/report/pdf` tab / std mail composer with the PDF (no SMTP server yet → recorded only) | std report + mail composer |
| B61 | periodontal exam saved | doctor | json stored, summary recomputed (D-48) | custom model |
| B31 | supplier toggles 👁/🚫 on a product | own product | clinic_shop_published soft-hide — offers skipped by clinic_shop_data, vendor line kept | custom flag (batch #2) |
| B32 | Place Order from a request | vendor lacks a supplierinfo on the product | the line is auto-created (last price) — ordering FROM a vendor makes them a vendor OF the product; without it the supplier's own order crashed on the unreadable product | custom glue (v19.0.53.21) |
| B33 | supplier warehouse chain | D-19 | count (std quant Apply) → In Transit ships to the transit shelf → clinic receipt drains transit (property_stock_supplier) → returns land back in their warehouse; shop/pre-order qty = SUPPLIER's own stock | std locations/quants/pickings + thin glue (D-19) |
| B34 | received order without a rating | admin | it queues in Stock → შესაფასებელი (inline ★ columns); a rated row leaves the tray | custom list over std POs |
| B35 | shop compare tray | user picks ⇄ (max 4) | side-by-side table (price/vendor+★/delay/brand/category/stock) with per-column add-to-cart; cart+compare persist per-user in localStorage | custom UI |
| B36 | create/write on calendar.event | `family_link_id` in vals | `_clinic_remember_family_link`: link → patient.family_member_ids AND patient → link.family_member_ids (sudo); a non-patient link is flagged `is_patient` (2026-09-30, D-24) | custom (std partner has no family link) |
| B37 | „მოსული" (`action_arrive`) on a clinic visit | — | `_check_patient_data_complete`: birth date + personal no. required (506b4f4) | custom guard |
| B38 | planning board drag | visit is started/done/paid/cancelled | drag blocked, cursor shows grab vs default (506b4f4) | custom (board is OWL) |
| B39 | visit page opens | user in `group_clinic_admin` (payload `is_admin`) | admin: no Procedures tab, opens on Billing (itemised procedure table); doctor: no Billing tab (506b4f4) | custom OWL |
| B40 | typing in the Patients search bar (action ctx `clinic_live_search`) | query non-empty, after 200 ms | patients matching name/phone/email/vat (max 8) REPLACE the generic "Search X for" entries; click opens the card; no match → generic entries stay (D-25) | custom SearchBar patch — std needs Enter |
| B41 | visit state changes / patient flagged | any | `clinic_patient_status` recomputed: 1 completed visit → primary, 2+ → unique, none → empty (user's naming, 2026-10-01) | custom stored compute |
| B42 | Patients control-panel „ექსპორტი" button (menu items removed 2026-10-01) | admin or doctor | GET `/clinic/patients/export?status=primary|unique|all` builds the .xlsx from the DB and downloads it; status = the active primary/unique button, none → all patients | custom route (std Export needs a manual selection) — D-27 |
| B43 | „პაციენტის ანკეტა" on the booking / visit page | ctx `clinic_return_visit_id` | patient form shows „← back"; button saves, then re-opens the booking dialog (planning ctx `open_visit_id`) or the visit page | custom (D-24 follow-up) |
| B44 | patient card save | `is_patient` | first/last name, personal no., birth date, phone, referral source, allergy answer (+ list when yes), pregnancy answer (non-men) must be filled — enforced by view `required=`, not by constraints, so non-UI writes are unaffected (D-26) | custom |
| B45 | schedule screen opens (admin) | — | `clinic_sync_staff` ensures employees for doctor/admin users; doctors get only their own employee | custom over std hr |
| B46 | admin clicks a cell / block | — | popover → `clinic_schedule_set` upsert / clear of one employee-day; screen reloads | custom |
| B47 | employee checks in / out | std `hr_attendance` (systray, kiosk) | creates the `hr.attendance` row — nothing custom | standard |
| B48 | „ნამუშევარი საათები" opens / period changes | admin (all) or doctor (self) | `clinic_hours_data` compares schedule vs attendance (see S2 table); Excel link downloads the same figures | custom report over std attendance |
| B49 | booking / move / re-time / change doctor of a clinic visit | doctor has a schedule entry that day | day off/vacation/sick → refused; outside the shift → refused (start before it or end after it); no entry → clinic hours only | custom guard (D-29) |
| B50 | admin edits a shift time in the schedule sidebar | admin | in-place when never used in the past, else new template from today + old archived (past hours stay true) | custom |
| B51 | Planning board loads a day | doctors with schedule entries | `clinic_board_staff` colours each doctor's shift band + header chip, hatches non-working time, blocks click/drag there; no entry = clinic hours only | custom (S3 visual) |
| B52 | schedule screen opens | any clinic user | opens on the user's own staff group; closed weekdays (company config) render as უქმე and cannot be edited (server also refuses) | custom |
| B53 | payment on the visit page | admin | method select (cash / card / transfer / insurance / mixed) + card type for card / mixed; amounts must equal procedures + same-day retail; invoice(s) created, retail sale approved + linked to the visit (D-30) | custom over std sale + account |
| B54 | „მოსული" / „დაწყება" / adding a procedure | patient lacks allergy answer, or (female) pregnancy answer | refused with the missing items named; pregnancy is cleared when a new visit is booked and when a visit is done, so it is asked again every visit (D-31) | custom guard |
| B55 | visit form opens | patient pregnant / allergic | red sign + text: „პაციენტი ორსულია" (pregnant.svg) / „ალერგია: <allergen — reaction>" (allergy.svg); nothing shown when both are negative | custom |
| B56 | treatment plan created / „დაგეგმილი პროცედურების წამოღება" | patient chosen | the patient's `planned` procedures become lines (visit n by appointment date, department = visit direction, tooth, price text); PDF via „🖨 PDF" (D-32) | custom + std QWeb report |

## Standard-first check
| requirement | standard feature checked | covers? | if no → custom + ref |
|---|---|---|---|
| Excel of patients by status | list → Actions → Export | partial (manual selection each time) | menu items + export route (D-27) |
| city picker | `res.city` + `city_id` (base_address_extended) | yes | reused; only a seed + view tweaks (D-28) |
| patient status (primary/unique) | none | no | stored compute on res.partner (D-27) |
| card type of a payment | none (account.payment.method is about journals) | no | small catalog `clinic.card.type` (D-30) |
| retail goods sold at settle-up | sale_management (the რეალიზაცია tab) | yes | reused; only the same-day pull into the visit total is custom (D-30) |
| treatment plan document | none (Enterprise sign/documents) | no | `clinic.treatment.plan` + QWeb report (D-32) |
| shift colours | none | no | 12-colour palette (scss + python mirror) with auto-unique assignment (D-29) |
| doctor schedule on the booking board | Enterprise `planning` | no (Community) | `clinic_board_staff` + OWL zones on the existing board (D-29) |
| check-in / out + worked hours | `hr_attendance` | yes | used as is; only the plan-vs-fact screen and Excel are custom (D-29) |
| staff schedule / shifts | Enterprise `planning`, std `resource.calendar` | no (Community; calendars are per-resource weekly patterns, no per-day shifts/leave types) | `clinic.shift` + `clinic.schedule.line` on std `hr.employee` (D-29) |
| family link between patients | res.partner parent_id/child_ids | no (company/address hierarchy) | `family_member_ids` M2m + B36 hook (D-24) |
| search-as-you-type | web SearchBar | no (needs Enter; per-field entries) | SearchBar patch, opt-in by action ctx (D-25) |
| gender picker | radio/selection widget | partial | avatar-card widget (design handoff, 506b4f4) |
| appointments | Enterprise `appointment`/`planning` | no (Community) | calendar.event + clinic_state (D-8) |
| procedures/price | product.product service | yes | flag is_clinic_procedure only (D-9) |
| insurance companies | res.partner | yes | flag is_insurance_company (D-9) |
| working hours | resource.calendar | partial (heavy, per-resource) | 9 fields on res.company (D-4) |
| double-booking | std calendar | no | constrains B2 (D-4; one doctor may overlap since D-34) |
| clinic buying UI | website_sale | no (it sells) | OWL Supply Shop over purchase (D-1) |
| supplier side | purchase portal | partial | mirror sale.order + record rules (D-2, D-3) |
| retail to patient | sale_management | yes | "რეალიზაცია" tab = plain sale.order |
| notifications | mail.activity + bus.bus | yes | thin custom OWL chime service |
| invoicing/payments | account | yes | wizard only orchestrates |
| signature | `signature` widget | yes | on clinic.patient.document |
| vat uniqueness | base_vat | no (format-checks EU vat) | python constrain B15 |
| Georgian UI | i18n ka.po | yes | regen pending (PLAN M2) |
| free-slot search | Enterprise appointment | no (Community) | clinic_free_slots + wizard (batch #2 plan) |
| doctor sale request | sale.order draft flow | yes (reused) | flag + notify only (D-13) |
| specialty catalogue | hr.job / hr | no (hr not installed; doctors = users) | clinic.direction config model (batch #2 plan) |
| family links | partner parent_id/child_ids | no (that models company/address hierarchy) | family_member_ids M2m (batch #2 plan) |
| cabinet warehouse tree | stock.location + multi-locations | yes | config/data only; rooms auto-link (batch #2 plan) |
| write-off reasons | scrap → usage='inventory' locations | yes | 3 seeded locations (Write-off/Damaged/Expired) |
| min/max per cabinet | stock.warehouse.orderpoint.location_id | yes | menu shortcut only |
| expiry dates | product_expiry module | yes | new dependency |
| supply brand | — (no brand model in Community) | no | clinic.brand + product field (batch #2 plan) |
| avg consumption / last price | — (no std product KPIs) | no | 2 sudo computes on product.template (batch #2 plan) |
| purchase requests | purchase.order states; purchase_requisition | no (no review/recommendations/reject-comment/receipt-gated pipeline) | clinic.purchase.request (D-15) |
| Save/Discard everywhere | form status indicator (cloud/✕) | partial (icons unnoticed) | template extension relabels them (D-17) |
| shop banners/sponsored | website_sale marketing | no (website not installed; shop is custom OWL) | clinic.shop.banner + 2 product flags (batch #2 plan) |
| wishlist | website_sale_wishlist | no (website stack) | minimal clinic.shop.wishlist (batch #2 plan) |
| category photos | product.category | no image field in std | image_128 inherit (batch #2 plan) |
| returns to vendor | stock reverse picking | partial (no reason/photo/review pipeline, wizard API unstable) | clinic.purchase.return + manual reverse picking (D-18) |
| supplier delivery status | — (no vendor portal status in Community) | no | selection + buttons on the mirror SO (batch #2 plan) |
| vendor rating | rating.mixin (website-oriented) | partial (portal/website machinery) | two selection fields on the PO, averaged in RPCs (batch #2 plan) |
| manager dashboard | std dashboards (spreadsheet is Enterprise) | no | OWL client action over one RPC (batch #2 plan) |
| supplier warehouse | stock locations/quants/pickings/transit + property_stock_supplier | yes (engine 100% std) | thin glue: owner tag on locations, scoped menus, ship-at-transit hook, Move wizard (D-19) |
| supplier product access | per-supplier read scoping | no (foreign refs crash pages) | READ open to internal users, WRITE scoped (D-20) |
| treatment-plan doctors list | none (plain Char fields) | no | small line model `clinic.treatment.plan.doctor` (D-33) |
| first / repeat / regular patient | none | no | stored computes over completed visits (D-45) |
| booking "existing or new patient" | std calendar quick-create | no | OWL chooser before the std form (D-43) |
| treatment-plan status from visits | none | no | plan_line_id link + derived status (D-47) |
| prescription print / mail | std QWeb report + mail composer | yes | reused; only the sheet template + buttons are custom (B60) |
| periodontal chart | none in Community | no | `clinic.perio.chart` + OWL grid (D-48) |
| one-click image / allergy upload | std image / binary widgets (hover pencil, 2-step list) | partial | small widgets `clinic_image_click`, `clinic_allergy_upload` (no D-entry yet) |

## Views / UI
| view / action | xml id | key points |
|---|---|---|
| Partner form inherit | `view_partner_form_patient_card` | header fields (vat/birthdate/insurance/referral/Workplace), Patient Card page autofocus, nested notebook (Basic/Medical/Financial(admin)/History), quick buttons (📅 დაჯავშნე primary — 🪪 card-page/dashboard buttons REMOVED v19.0.55.9; card page still opens from the visit form), "რეალიზაცია" page replaces `sales_purchases` for patients; function/website/tags/parent_id hidden for patients (Individual/Company toggle VISIBLE again — v19.0.51.14); header company field labelled „სამუშაო ადგილი"; Soft-UI hook: marker `<div class="o_clinic_soft"/>` inside sheet (D-21) |
| Visit form inherit | `view_clinic_appointment_form` (inherits `calendar.view_calendar_event_form`) | workflow buttons per state+group; Clinic page autofocus with 👤/🪪 jump buttons; meeting UI hidden for is_clinic (Send email, Going?, show_as/privacy, location, videocall, attendees block); cancel_reason visible pre-cancel |
| Visit history list/search | `view_clinic_visit_history_list/_search`, `action_clinic_visit_history` | date/patient/dentist/name/diagnosis/tooth_display/state/amount_paid(sum); dentist + 1w/2w/1m filters |
| Cancelled list | `view_clinic_visit_cancelled_*`, `action_clinic_visit_cancelled` | cancelled/no_show OR was_rescheduled; cancel_reason; today/date filters |
| Planning board (OWL) | tag `clinic_planning`, `action_clinic_planning` | 10-min grid (HOUR_PX=96), hover cell, drag-to-size (1 cell=10min), popup form (target=new, UTC-serialized defaults), off-hours hatch via `clinic_board_config()`, Reserve side panel (+Add/✓), status pills (paid≠done), ✎ edited badge, dispensary dashed outline; Soft-UI restyle v55.3-.7 (D-21): dotted 10-min micro-grid, avatar header chips, white cards + state accent bar (in-progress = filled), duration size classes cp_small ≤15min / cp_mid ≤35min (vat·procedure folded to one line) so no card clips |
| Supply Shop / Supplier portal / Dashboard / Card page (OWL) | tags `clinic_supply_shop`, `clinic_supplier_portal`, `clinic_patient_dashboard`, `clinic_patient_card_page` | see ARCHITECTURE.md |
| Visit form (batch #2) | same inherit | Subject hidden — PATIENT sits in the h1 title at Subject size; Duration row MOVED above Start (2× position=move); notebook invisible → clinic_body div (direction/type/family-link/referral/comment + procedures [visible from booking] /time-tracking/previous-visit); 🕐 widget +👤/🪪 buttons; cancel via popup; videocall_location_div ('+ Odoo meeting') hidden |
| Referrals | `view_clinic_referral_list/_search`, `action_clinic_referrals`, menu Configuration→Referrals (admin) | patients grouped by referral_source, month/30d filters |
| Directions | `view_clinic_direction_list`, `action_clinic_direction`, menu Configuration→Directions | editable list, seq handle |
| Brands | `view_clinic_brand_list`, menu Configuration→Brands (admin) | editable list |
| Stock menu (admin) | `menu_clinic_stock` + 4 actions | Internal Transfers / Write-off-Scrap / Min-Max Rules / Warehouse Structure — plain windows over STANDARD models |
| Purchase Requests | `view_clinic_purchase_request_form/list/calendar/search`, menus admin (Stock) + doctor "Supply Requests" | statusbar+state buttons, line recommendations + Redistribute, planned-date calendar, reject wizard form |
| Appointment types | `view_clinic_appointment_type_form` + list open_form_view | duration as float_time (HH:MM) everywhere |
| Slot finder (client) | widget `clinic_slot_finder_btn` + OWL `ClinicSlotFinderDialog` | stacked Dialog; direction/duration/date controls; doctor chip; empty-result explanations |
| Global Save/Discard | `static/src/clinic_form_buttons.xml` (t-inherit web.FormStatusIndicator) | labelled შენახვა/გაუქმება buttons on every form, visible only while dirty/new (D-17) |
| Supply Shop v2 | `static/src/shop/` (rewritten) | banner carousel, category tiles+chips, brand filter, ⭐/🆕/🔥 strips, ♥ wishlist, 🔁 repeat order, similar strip, vendor comparison table with ★ |
| Shop Banners | `view_clinic_shop_banner_list/form`, menu Configuration→Shop Banners (admin) | image upload |
| Patients search | `view_clinic_patient_search` (action `search_view_id`) | filters primary/unique + name/phone/email/vat search; the left side panel was dropped; kanban + list are primary inherits of the Contacts views with `js_class` `clinic_patients_kanban/list` (`ClinicPatientButtons`: პირველადი / უნიკალური toggle buttons + ექსპორტი, rendered after the breadcrumb through the `control-panel-additional-actions` slot) bound with `ir.actions.act_window.view` (B42, D-27) |
| Patients menu | `action_clinic_patients`, `menu_clinic_patients` | Clinic → Patients: kanban/list/form over is_patient (admin+doctor), default_is_patient ctx — reviewer could not find the card via Contacts |
| Patient quick registration | `view_clinic_patient_quick_form` | Dentos popup: standalone foreign-citizen toggle row, split names, gender avatar cards (506b4f4), birthdate, personal/passport no., primary + extra phones (patient_phone_ids inline), insurance + policy, latin block; opened ONLY from the booking's ➕ widget (a form_view_ref on the field hijacked every open — D-23) |
| Consent sheets | `view_clinic_consent_form/list` | one form serves both types; personal-data checkboxes + marketing radio; medical signature pad; footer confirm buttons chain the two sheets |
| Visit working page (OWL) | tag `clinic_visit_page`, `static/src/visit_page/` | Dentos layout: header info cards, ← calendar pill, tabs (Procedures/Billing; materials + EHR placeholders), left medical sections with red/green dots — ჩივილები (case type + catalog chips + other + anamnesis), objective grid ×7, exam results & epicrisis text, prescriptions table, allergies table (writes clinic.patient.allergy on the PATIENT); FDI odontogram → ICD-10 → priced procedure → add; per-row discount %, status, delete; billing: live დავალიანება card, cash/card inputs, გადახდა + ვიზიტის დასრულება |
| Booking popup (Dentos look) | same visit form inherit | attendees row hidden for clinic; ALL lifecycle chrome (12 buttons + statusbar) hidden while unsaved (`not id or …`); ➕ new-patient widget + slot finder; green save button via .o_clinic_visit_body marker CSS; patient m2o no_create + normal internal link (full card) |
| Partner Soft-UI (CSS) | `static/src/scss/clinic_partner_soft.scss` | :has()-scoped: mint header card, stat-button cards, group cards (all-invisible groups hidden), pill tabs; zero logic (D-21) |
| Clinic PO (B4) | `view_purchase_order_form_clinic_b4` | supplier-status field, Received On, 48h 🔄 Return button, Rating page, Returns page |
| Supplier SO (B4) | `view_sale_order_form_clinic_b4` | 5 sequential status buttons + statusbar (supplier group) |
| Returns | `view_clinic_purchase_return_form/list`, menus Stock→Returns (admin) + root Returns (supplier) | statusbar flow, photo, reverse-picking link |
| Stock Dashboard | tag `clinic_stock_dashboard`, menu Stock→📊 Dashboard (admin) | 11 cards over clinic_dashboard_data |
| Company form inherit | "Clinic Schedule" tab | workdays, hours, room-overlap toggle |
| Users form inherit | "Clinic" tab | default_room_id |
| Menus | Clinic root: staff=Planning/Configuration/Supply Shop; supplier=My Shop/My Inventory/My Orders | gated by groups |
| Booking form (2026-10-07) | visit form inherit | "existing / new patient" chooser (xl dialog) before it; new-patient button hidden once the chooser decided; visit-page button only from arrived; Cancel only before treatment; status bar + workflow buttons in the legend colours (light tint, next step full colour; Start keeps std primary); quick buttons light Odoo-purple tint |
| Planning board colours | `clinic_planning.scss` | cards painted with the status-legend palette (one `$cp_state_colors` map) |
| Patient form (2026-10-07) | partner form inherit | red pregnancy / allergy banner; Notes tab hidden for patients; gender: only the picked card shows; allergy-test upload button + list under the allergy answer; inactive tabs light purple; Medical tab: tooth chart + plan table (auto status), old manual statuses below, periodontal chart |
| Visit page (2026-10-07) | `clinic_visit_page` | health banner on every tab; materials / EHR tabs doctor-only; milk teeth only for a child < 14; exam-result files upload; allergy table with all card columns; prescription 🖨 / ⬇ PDF / ✉ |

## Security
- Groups (`security/clinic_groups.xml`): `group_clinic_admin` (implies partner_manager,
  purchase_user, stock_user, production_lot, multi_locations — batch #2 B1), `group_clinic_doctor` (partner_manager), `group_clinic_radiologist` (internal user only; "Radiology" menu — Patients + X-ray uploads; D-36), `group_clinic_supplier`
  (purchase_user, stock_user, sale_salesman). Privilege `privilege_clinic`.
- ACL (`ir.model.access.csv`): CRUD for the 20 clinic models (+supplier.move wizard;
  supplier rwc on stock.location scoped by rule; doctor read-only purchase.order(+line)) (banner user-r/admin-rwcu;
  wishlist user-rwcu; return admin-rwcu/supplier-rw) (user read / manager rw
  pattern; brand user-r/system-rwcu; purchase request admin-rwcu/doctor-rwc);
  supplier rows for product.template/product/supplierinfo/category; doctor rows: sale.order
  (r/w/c), sale.order.line (rwcu), read-only sale.order.template(+line), quotation.document,
  and READ-ONLY stock.move / stock.move.line / stock.picking / stock.quant /
  account.move / account.move.line (sale_stock + invoicing computes fire on SO save).
- `/clinic/patients/export`: HTTP route, `auth='user'`, 404 unless the user is in the admin or doctor group.
- `clinic.patient.allergy`: user read; doctor rwcu; admin rwcu (added 2026-09-30 so the
  registration form can save allergies).
- `clinic.treatment.plan.doctor`: admin + doctor rwcu. `clinic.perio.chart`: doctor rwcu, admin read (D-48).
- Supplier product/template rules are WRITE-scoped only since v19.0.53.22 (D-20): reading
  any product never crashes their pages; My Inventory is a separately scoped action.
  Supplier location rule: edit own subtree only. Server actions behind supplier menus
  carry group_ids (Odoo 19: ungrouped server actions run for admins only).
- Record rules: doctor own-DRAFT sale write rules (`rule_clinic_doctor_sale_write`/`_line_write`, write/create only — read stays open for patient history); purchase-request rules
  (doctor sees/edits own requests, admin all); wishlist own-rows GLOBAL rule; supplier
  own-returns rule; `rule_clinic_event_visibility` (GLOBAL: non-clinic OR own dentist OR admin-all,
  D-7); supplier own-PO / own-SO / own-template / own-product / own-supplierinfo.
- post_init_hook `_post_init_grant_admin` → grants both clinic roles to base.user_admin.

## Integrations
- External: **none live**. EHR + Form-100 unknown targets (PRD §9, blocked).
- Internal live channels (bus.bus → `clinic_arrived_service.js` toasts+chimes):
  `clinic_patient_arrived`, `clinic_low_stock`, `clinic_new_order`, `clinic_order_confirmed`,
  `clinic_dispensary_due`, `clinic_sale_request`.
- Dev access: JSON-RPC (`/jsonrpc`, password auth). JSON-2 available but unused.

## Migration / data
- `data/ir_sequence.xml` (patient_ref), `data/clinic_cron.xml` (3 crons above + `cron_clinic_reset_pregnancy`, daily — forgets yesterday's pregnancy answers (D-37) and 6-month-old allergy answers (D-44)); since 2026-10-07 it also holds the param `clinic.regular_patient_visits` (noupdate, 5) and the idempotent upgrade functions `_clinic_stamp_allergy_answers`, `_clinic_recompute_visit_flags`, `_clinic_link_existing_plans`; `views/clinic_treatment_plan_views.xml` calls `_clinic_migrate_doctor_lines`.
- Upgrade = `-u clinic_patient_card` in-place; no data migrations needed so far; ctx override
  on `contacts.action_contacts` re-asserted on every upgrade.
- Demo data (patients/doctors/suppliers/products) was seeded via RPC, NOT in module data.
- v19.0.49 adds dependency `sale_pdf_quote_builder` (auto-installed with sale — D-14).
- v19.0.50 adds dependency `product_expiry`; `data/clinic_stock_data.xml` seeds the
  location tree (Cabinets/Sterilization/Write-off/Damaged/Expired) + 3 brands and calls
  `clinic.room._clinic_sync_locations` on every upgrade; the Storage-Locations + Lots
  settings were enabled once live (activates the shipped-inactive Internal Transfers
  picking type). v19.0.51 adds the PRQ ir.sequence. v19.0.52 seeds 7 Georgian shop
  categories (`data/clinic_shop_seed.xml`, noupdate). v19.0.53 needs nothing special.

## Drift log
- 2026-10-02: QWeb PDF bodies must be wrapped in `<div class="article" t-att-data-oe-model=… data-oe-id=…>`; otherwise Odoo does not put them in the minimal layout (`<meta charset>`) and wkhtmltopdf decoded Georgian / € as Latin-1 ("áƒ¥…"). Dynamic text additionally goes through `clinic.treatment.plan._ent` (numeric entities).
- 2026-10-02: pregnancy moved from "a card field" to "asked per visit": the card keeps the field (required for women) but it is cleared on booking a new visit and when a visit is done; `visit_pregnancy` freezes the answer at arrival. Earlier the same day a visit-form variant (editable row on the form) was built and removed on request.
- 2026-10-02: the primary / unique status names were kept; the patient-card buttons "Create Invoice" / "Make Payment" and the "Send Reminder" are admin-only, "Open Oral Chart" / "Sync EHR" doctor-only; the "Individual / Company" switch and `is_patient` stay hidden for patients.
- 2026-10-02: `base_geolocalize` came in through `hr_attendance` and added a "Partner Assignment" tab to the partner form — hidden in the priority-20 address view (the tab's own inherit is applied later than ours).
- 2026-10-01: shift colours grew from 4 to 12 (`clinic.shift.color` 0-3 → 0-11); two shifts created with the old modulo-4 rule duplicated colours — recoloured by hand in the live DB (data fix only, no migration code).
- 2026-10-01: my own live tests wrote/cleared schedule rows on real dates before the clinic started entering data; the user confirmed that losing them is fine. Tests now use far-future dates.
- 2026-10-01: before S3 the doctor's own schedule was NOT checked at booking (only the clinic-wide hours) — a visit could be booked at 16:00 for a doctor working until 15:00 (user report). Fixed by B49.
- 2026-10-01: worked hours are RAW clock time (check-out − check-in). Odoo's own `hr.attendance.worked_hours` deducts the employee's calendar lunch break (09:20–15:30 → 5.17 h in the standard field vs 6.17 h on our screen); the clinic has no lunch rule — to confirm.
- 2026-10-01: staff schedules (S1) — `hr` is now a dependency; the 'clinic' and Administrator accounts are NOT staff (excluded from the employee sync). Assistants do not exist as users yet: they are added as employees with Clinic Role = Assistant.
- 2026-10-01 (later): the primary/unique Excel menu items under Clinic and the left status side panel were REMOVED; the same function now lives in the Patients control panel (buttons პირველადი / უნიკალური / ექსპორტი) — user request.
- 2026-10-01: the quick-registration form went full → minimal → full → minimal within two days; the FINAL state is minimal (name, phone, insurance, foreign toggle). The "required" list the user gave (names, personal no., birth date, phone, referral source) applies to the patient CARD, not to the popup.
- 2026-10-01: address fields of the partner form cannot be patched from the main patient-card view: `city_id` is added by base_address_extended's own inherit (priority 16, loaded after ours) — the patch lives in a separate view with priority 20.
- 2026-10-01: the workplace shown in names comes from the free-text `company_name` as well as `parent_id`; the display-name fix must not key on `parent_id` only.
- 2026-10-01: patient statuses count completed visits only — 57 of 80 patients (no visit, booked, arrived…) have no status, so the two Excel lists never add up to all patients.
- 2026-09-30: a Many2one's `context=` declared on the PYTHON field is NOT sent by the web
  client — only the view's `context` attr is. The first "Create insurer" fix (Python
  context) was a no-op until the context moved into the views.
- 2026-09-30: D-23 partly superseded (D-24, user request): booking `patient_id` is no longer
  `no_create` (Create-and-edit is back, quick Create off); `family_link_id` again uses
  `form_view_ref` (registration form) — side effect: its internal link may open the short
  form for an existing member (not verified in the browser).
- 2026-09-30: patient display names no longer carry the workplace prefix; the suffix
  ` · vat · phone` appears only in clinic pickers.
- 2026-09-30: the "individual/company" switch is hidden on patient forms (it stays for
  insurers/vendors); whether a patient may be a company is an open clinic question (PRD §9).
- 2026-09-30: this SPEC's title still says whole-module v19.0.55.1.0 — the real version is far ahead.
- 2026-09-17: OWL gotchas that broke the visit page: template expressions have no JS
  globals (`String()` → ctx.String crash); `t-model` with a computed key generates
  invalid JS; comments between t-if/t-elif siblings break the chain.
- 2026-09-17: Odoo 19 relational model takes m2o updates as {id, display_name}
  OBJECTS — [id, name] tuples are silently dropped (fixed in ➕ widget and slot finder).
- 2026-09-17: a board-opened dialog can close AFTER navigation destroyed the board;
  its onClose reload must swallow the protected-ORM rejection (safeLoad).
- 2026-09-17: visit form's editable procedures table removed — procedures live on the
  visit page; the form shows a read-only summary only when done/paid. Partner History
  tab likewise: visits list (per-row 🧾 opens the page) replaced the procedures table.
- 2026-09-13: the Odoo 19 form compiler DROPS class attributes on `<sheet>` — a view-set
  class never reaches the DOM; scope sheet styling via an invisible marker div + :has() (D-21).
- 2026-09-13: partner-form 🪪 card-page / dashboard buttons removed (user request); the OWL
  card page remains reachable from the visit form's 🪪 jump button.
- 2026-09-03: `diagnosis` field relabelled "Comment" (batch #2) — column unchanged.
- 2026-09-03: `cancel_reason` removed from the form; set only via clinic.cancel.wizard.
- 2026-09-03: card page / dashboard JS fetch credit/debit/total_invoiced in a guarded
  separate read (doctors lack accounting groups) — pages open for every role.
- 2026-09-05: Odoo 19 dropped stock.location.scrap_location and the virtual-locations
  xmlid — a scrap destination is simply a usage='inventory' location (picked per reason).
- 2026-09-05: appointment-type duration onchange now ALWAYS applies (the default_stop
  guard silenced it on board-opened forms).
- 2026-09-05: clinic.slot.finder wizard superseded by the client-side dialog (D-16);
  kept as RPC fallback.
- 2026-09-05: RPC gotchas — stock.picking.move_ids_without_package and stock.move.name
  removed in 19; done qty = write {quantity, picked:true} then button_validate.
- 2026-09-12: Odoo 19 renames — ir.actions.server.groups_id → group_ids (ParseError on
  upgrade otherwise); a readonly list field needs force_save="1" or the client drops it
  from create vals (stock.quant KeyError).
- 2026-09-12: shop "stock" now means the SUPPLIER's own stock, not the clinic's (D-19).
- 2026-09-11: REGRESSION (v19.0.51→53): the StockPicking class added in B2 sat MID-FILE, so
  every purchase.order method below it (clinic_create_rfqs, mirror chain, button_confirm
  hook) silently re-parented to stock.picking — shop checkout was broken until B4. Fixed by
  moving the class to EOF; convention added to CLAUDE.md.

- 2026-10-05: D-4's "same-dentist clash always blocked" is obsolete — one doctor may hold overlapping visits (user request); the room check now compares only with other doctors (D-34). The Planning board draws overlaps in lanes.
- 2026-10-05: a pregnancy answer is valid for ONE day (`pregnancy_answered_on` + daily cron); before this the card kept an old visit's answer and the question was not asked again (D-37, amends D-31).
- 2026-10-05: the old `odontogram_html` block and the doctor-only "Open Oral Chart" placeholder button are gone from the patient card — the tooth chart widget (D-35) replaced them; PLAN M4 is superseded.
- 2026-10-05: the Financial tab moved to the OUTER tab bar next to Notes (the nested notebook was removed).
- 2026-10-05: "Referral source" stays hidden on the booking form (only its referral_user_id modifier needs it) — a visible variant was built and removed on request.

- 2026-10-06: SECURITY — suppliers could read every other supplier's mirror sale orders (the mirror had no salesperson and the std "Personal Orders" rule exposes such orders to every salesman); fixed in D-39, verified by RPC (visible orders 32 → 18, all own).
- 2026-10-06: the home page of the shop no longer shows the best-sellers strip; sponsored / new strips + banners only (user).
- 2026-10-06: a banner can be a video; options typed with `/` are split like commas (the first user test typed "S / M / L" and got one value).
- 2026-10-06: "Create Invoice", "Send", "Print", "Preview" are hidden for the supplier on the sale form; the supplier-side invoice is not created automatically yet (open decision).
- 2026-10-07: First Visit / Repeat / Regular are no longer manual checkboxes — computed from completed visits (D-45); the chooser's answer (D-43) no longer writes the card.
- 2026-10-07: closing a visit no longer forces every procedure line to done — "in progress" lines stay (D-47).
- 2026-10-07: "being treated now" = arrived / in progress AND started within 12 h; old visits left open had kept yesterday's pregnancy answer alive and blocked "Arrived".
- 2026-10-07: the visit page opens only from "Arrived" on; a visit in progress / done / paid can't be cancelled.

## Tests
Decision (2026-09-03, user): **no automated suite** — verification = live JSON-RPC scenarios +
browser checks after each deploy (documented per commit). Remaining-work ACs will be verified
the same way:
| AC | verification |
|---|---|
| AC-1 emails | RPC: trigger event → mail.mail created; chatter entry |
| AC-2 ka.po | browser as ka_GE user over new screens |
| AC-3 write-back | RPC read-back of tooth_ids/patient_note after UI save |
| AC-4 odontogram | browser click → clinic.patient.tooth row |
| AC-5 Form-100 | report renders PDF, attached to clinic.patient.document |
| AC-6 EHR | mock endpoint receives payload; failure → activity |

## Traceability (remaining work)
| AC | models/fields touched | verification above |
|---|---|---|
| AC-1 | mail.template(new), calendar.event hooks | AC-1 |
| AC-2 | i18n/ka.po only | AC-2 |
| AC-3 | clinic.patient.tooth, res.partner.patient_note + card-page JS | AC-3 |
| AC-4 | res.partner.odontogram_html → interactive widget, clinic.patient.tooth | AC-4 |
| AC-5 | QWeb report (new), clinic.patient.document | AC-5 |
| AC-6 | new integration model/queue (TBD) | AC-6 |
