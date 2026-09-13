<!-- last-synced: 2026-09-13, commit: 91e1c22 -->
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
| family | family_member_ids (M2m self, clinic_family_member_rel — linked patient profiles) |
| search | `_rec_names_search += phone, patient_ref` (+vat via base); `_compute_display_name` appends `· vat · phone` under ctx `clinic_show_ids` |
| constrains | `_check_patient_email` (latin `EMAIL_RE`), `_check_patient_phone` (digits), `_check_patient_vat` (digits + unique among patients, python search_count) |

**`calendar.event`** (clinic visit when `is_clinic=True`):
| group | fields |
|---|---|
| core | is_clinic, patient_id(M2o partner — required via constrain when is_clinic), dentist_id(M2o users), assistant_id(M2o users), room_id, appointment_type_id, clinic_state(Sel: requested/booked/confirmed/arrived/in_progress/done/paid/cancelled/no_show; tracked) |
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
**`product.category`**: image_128 (storefront tile photo) + clinic_shop_visible (default on —
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
| B31 | supplier toggles 👁/🚫 on a product | own product | clinic_shop_published soft-hide — offers skipped by clinic_shop_data, vendor line kept | custom flag (batch #2) |
| B32 | Place Order from a request | vendor lacks a supplierinfo on the product | the line is auto-created (last price) — ordering FROM a vendor makes them a vendor OF the product; without it the supplier's own order crashed on the unreadable product | custom glue (v19.0.53.21) |
| B33 | supplier warehouse chain | D-19 | count (std quant Apply) → In Transit ships to the transit shelf → clinic receipt drains transit (property_stock_supplier) → returns land back in their warehouse; shop/pre-order qty = SUPPLIER's own stock | std locations/quants/pickings + thin glue (D-19) |
| B34 | received order without a rating | admin | it queues in Stock → შესაფასებელი (inline ★ columns); a rated row leaves the tray | custom list over std POs |
| B35 | shop compare tray | user picks ⇄ (max 4) | side-by-side table (price/vendor+★/delay/brand/category/stock) with per-column add-to-cart; cart+compare persist per-user in localStorage | custom UI |

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
| Patients menu | `action_clinic_patients`, `menu_clinic_patients` | Clinic → Patients: kanban/list/form over is_patient (admin+doctor), default_is_patient ctx — reviewer could not find the card via Contacts |
| Partner Soft-UI (CSS) | `static/src/scss/clinic_partner_soft.scss` | :has()-scoped: mint header card, stat-button cards, group cards (all-invisible groups hidden), pill tabs; zero logic (D-21) |
| Clinic PO (B4) | `view_purchase_order_form_clinic_b4` | supplier-status field, Received On, 48h 🔄 Return button, Rating page, Returns page |
| Supplier SO (B4) | `view_sale_order_form_clinic_b4` | 5 sequential status buttons + statusbar (supplier group) |
| Returns | `view_clinic_purchase_return_form/list`, menus Stock→Returns (admin) + root Returns (supplier) | statusbar flow, photo, reverse-picking link |
| Stock Dashboard | tag `clinic_stock_dashboard`, menu Stock→📊 Dashboard (admin) | 11 cards over clinic_dashboard_data |
| Company form inherit | "Clinic Schedule" tab | workdays, hours, room-overlap toggle |
| Users form inherit | "Clinic" tab | default_room_id |
| Menus | Clinic root: staff=Planning/Configuration/Supply Shop; supplier=My Shop/My Inventory/My Orders | gated by groups |

## Security
- Groups (`security/clinic_groups.xml`): `group_clinic_admin` (implies partner_manager,
  purchase_user, stock_user, production_lot, multi_locations — batch #2 B1), `group_clinic_doctor` (partner_manager), `group_clinic_supplier`
  (purchase_user, stock_user, sale_salesman). Privilege `privilege_clinic`.
- ACL (`ir.model.access.csv`): CRUD for the 20 clinic models (+supplier.move wizard;
  supplier rwc on stock.location scoped by rule; doctor read-only purchase.order(+line)) (banner user-r/admin-rwcu;
  wishlist user-rwcu; return admin-rwcu/supplier-rw) (user read / manager rw
  pattern; brand user-r/system-rwcu; purchase request admin-rwcu/doctor-rwc);
  supplier rows for product.template/product/supplierinfo/category; doctor rows: sale.order
  (r/w/c), sale.order.line (rwcu), read-only sale.order.template(+line), quotation.document,
  and READ-ONLY stock.move / stock.move.line / stock.picking / stock.quant /
  account.move / account.move.line (sale_stock + invoicing computes fire on SO save).
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
- `data/ir_sequence.xml` (patient_ref), `data/clinic_cron.xml` (3 crons above).
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
