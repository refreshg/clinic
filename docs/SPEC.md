<!-- last-synced: 2026-09-03, commit: f7f4be0 -->
# Technical spec — clinic_patient_card (whole module, v19.0.46.0.0)

Scope: everything live. AC-n refs point to `docs/PRD.md §13` (remaining work only, per user
decision — shipped features trace to PRD §4/§7 tables instead). D-n refs → `docs/DECISIONS.md`.

## Data model

### NEW models (all have `ir.model.access.csv` rows; `_description` set)
**`clinic.room`** — treatment rooms.
| field | type | req | notes |
|---|---|---|---|
| name | Char | ✓ | |
| sequence / note / active | Int / Char / Bool | | `active` toggle |

**`clinic.appointment.type`** — visit types (colour legend on the board).
| field | type | req | notes |
|---|---|---|---|
| name | Char | ✓ | |
| default_duration | Float (h) | | applied by onchange only when no `default_stop` in ctx |
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

**`clinic.patient.document`** | partner_id✓, doc_type(Sel; `consent` shows signature),
name, date, attachment(Binary)+filename, signature(Binary, widget=signature), note.

**`clinic.procedure.history`** | partner_id✓(cascade), appointment_id(M2o calendar.event,
set null), procedure_id(M2o product.product, domain is_clinic_procedure), name, status(Sel,
default done), qty, planned_date, procedure_date, doctor_id(M2o res.users), tooth, note.
create() backfills partner from appointment.

**`clinic.payment.wizard`** (TransientModel) | event_id, partner_id, payment_method(Sel:
cash/card/transfer/insurance/mixed), amount_total(compute), amount_cash, amount_terminal,
summary(Html), note. Mixed: cash+terminal must equal total (float_compare).

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
| search | `_rec_names_search += phone, patient_ref` (+vat via base); `_compute_display_name` appends `· vat · phone` under ctx `clinic_show_ids` |
| constrains | `_check_patient_email` (latin `EMAIL_RE`), `_check_patient_phone` (digits), `_check_patient_vat` (digits + unique among patients, python search_count) |

**`calendar.event`** (clinic visit when `is_clinic=True`):
| group | fields |
|---|---|
| core | is_clinic, patient_id(M2o partner — required via constrain when is_clinic), dentist_id(M2o users), assistant_id(M2o users), room_id, appointment_type_id, clinic_state(Sel: requested/booked/confirmed/arrived/in_progress/done/paid/cancelled/no_show; tracked) |
| medical | diagnosis, procedure_line_ids(o2m clinic.procedure.history), tooth_display(compute) |
| money | currency_id, amount_paid, amount_cash, amount_terminal, payment_method |
| tracking | checkin_time, treat_start_time, treat_end_time, waiting_minutes, chair_minutes, parent_appointment_id, parent_visit_info(compute), was_rescheduled, duration_edited, cancel_reason |
| dispensary | is_dispensary, dispensary_notified |

**`res.users`**: default_room_id (M2o clinic.room; "Clinic" tab on user form) + `clinic_dentists()`
(board columns: admins get all doctors, a plain doctor only themself).
**`res.company`**: clinic_workday_mon..sun(Bool), clinic_work_start/_end(Float, widget
float_time), clinic_block_room_overlap(Bool, default True); "Clinic Schedule" tab; helper
`_clinic_workdays()`.
**`product.template`**: is_clinic_procedure, is_clinic_supply; `_clinic_notify_low_stock()`
(cron); supplier self-service API `clinic_supplier_products / _save_product / _unpublish`
(sudo writes, vendor-scoped in code, D-3).
**`purchase.order`**: is_clinic_order, clinic_sale_id; `clinic_create_rfqs(cart)` (one RFQ per
vendor + mirror SO), `_clinic_notify_vendor/_confirmed`, button_confirm hook.
**`sale.order`**: is_clinic_order, clinic_supplier_id, clinic_purchase_id;
`action_confirm` → `_clinic_notify_clinic_confirmed` (mirror-confirms PO).
`sale.order.line._action_launch_stock_rule` → no-op for clinic orders (D-2).

## Business logic (trigger → condition → action; Standard coverage per row)
| # | trigger | condition | action | std coverage |
|---|---|---|---|---|
| B1 | create/write on calendar.event | `'start' in vals`, not `clinic_force`, is_clinic | `_clinic_validate_schedule`: block outside company workdays/hours; block past (>5-min grace) unless user == `base.user_admin` | custom (D-4, D-5) — resource.calendar rejected |
| B2 | constrains start/stop/dentist/room/state | is_clinic, state not in requested/cancelled/no_show | `_check_clinic_overlap`: same-dentist clash always blocked; same-room behind `clinic_block_room_overlap`; sudo() search (doctor rule can't hide clashes) | custom (D-4) — std calendar has no overlap guard |
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

## Standard-first check
| requirement | standard feature checked | covers? | if no → custom + ref |
|---|---|---|---|
| appointments | Enterprise `appointment`/`planning` | no (Community) | calendar.event + clinic_state (D-8) |
| procedures/price | product.product service | yes | flag is_clinic_procedure only (D-9) |
| insurance companies | res.partner | yes | flag is_insurance_company (D-9) |
| working hours | resource.calendar | partial (heavy, per-resource) | 9 fields on res.company (D-4) |
| double-booking | std calendar | no | constrains B2 (D-4) |
| clinic buying UI | website_sale | no (it sells) | OWL Supply Shop over purchase (D-1) |
| supplier side | purchase portal | partial | mirror sale.order + record rules (D-2, D-3) |
| retail to patient | sale_management | yes | "რეალიზაცია" tab = plain sale.order |
| notifications | mail.activity + bus.bus | yes | thin custom OWL chime service |
| invoicing/payments | account | yes | wizard only orchestrates |
| signature | `signature` widget | yes | on clinic.patient.document |
| vat uniqueness | base_vat | no (format-checks EU vat) | python constrain B15 |
| Georgian UI | i18n ka.po | yes | regen pending (PLAN M2) |

## Views / UI
| view / action | xml id | key points |
|---|---|---|
| Partner form inherit | `view_partner_form_patient_card` | header fields (vat/birthdate/insurance/referral/Workplace), Patient Card page autofocus, nested notebook (Basic/Medical/Financial(admin)/History), quick buttons (📅 დაჯავშნე primary, 🪪 card page, dashboard), "რეალიზაცია" page replaces `sales_purchases` for patients; function/website/tags/company_type/parent_id hidden for patients |
| Visit form inherit | `view_clinic_appointment_form` (inherits `calendar.view_calendar_event_form`) | workflow buttons per state+group; Clinic page autofocus with 👤/🪪 jump buttons; meeting UI hidden for is_clinic (Send email, Going?, show_as/privacy, location, videocall, attendees block); cancel_reason visible pre-cancel |
| Visit history list/search | `view_clinic_visit_history_list/_search`, `action_clinic_visit_history` | date/patient/dentist/name/diagnosis/tooth_display/state/amount_paid(sum); dentist + 1w/2w/1m filters |
| Cancelled list | `view_clinic_visit_cancelled_*`, `action_clinic_visit_cancelled` | cancelled/no_show OR was_rescheduled; cancel_reason; today/date filters |
| Planning board (OWL) | tag `clinic_planning`, `action_clinic_planning` | 10-min grid (HOUR_PX=96), hover cell, drag-to-size (1 cell=10min), popup form (target=new, UTC-serialized defaults), off-hours hatch via `clinic_board_config()`, Reserve side panel (+Add/✓), status pills (paid≠done), ✎ edited badge, dispensary dashed outline |
| Supply Shop / Supplier portal / Dashboard / Card page (OWL) | tags `clinic_supply_shop`, `clinic_supplier_portal`, `clinic_patient_dashboard`, `clinic_patient_card_page` | see ARCHITECTURE.md |
| Company form inherit | "Clinic Schedule" tab | workdays, hours, room-overlap toggle |
| Users form inherit | "Clinic" tab | default_room_id |
| Menus | Clinic root: staff=Planning/Configuration/Supply Shop; supplier=My Shop/My Inventory/My Orders | gated by groups |

## Security
- Groups (`security/clinic_groups.xml`): `group_clinic_admin` (implies partner_manager,
  purchase_user, stock_user), `group_clinic_doctor` (partner_manager), `group_clinic_supplier`
  (purchase_user, stock_user, sale_salesman). Privilege `privilege_clinic`.
- ACL (`ir.model.access.csv`): CRUD for the 8 clinic models (user read / manager rw pattern);
  supplier rows for product.template/product/supplierinfo/category.
- Record rules: `rule_clinic_event_visibility` (GLOBAL: non-clinic OR own dentist OR admin-all,
  D-7); supplier own-PO / own-SO / own-template / own-product / own-supplierinfo.
- post_init_hook `_post_init_grant_admin` → grants both clinic roles to base.user_admin.

## Integrations
- External: **none live**. EHR + Form-100 unknown targets (PRD §9, blocked).
- Internal live channels (bus.bus → `clinic_arrived_service.js` toasts+chimes):
  `clinic_patient_arrived`, `clinic_low_stock`, `clinic_new_order`, `clinic_order_confirmed`,
  `clinic_dispensary_due`.
- Dev access: JSON-RPC (`/jsonrpc`, password auth). JSON-2 available but unused.

## Migration / data
- `data/ir_sequence.xml` (patient_ref), `data/clinic_cron.xml` (3 crons above).
- Upgrade = `-u clinic_patient_card` in-place; no data migrations needed so far; ctx override
  on `contacts.action_contacts` re-asserted on every upgrade.
- Demo data (patients/doctors/suppliers/products) was seeded via RPC, NOT in module data.

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
