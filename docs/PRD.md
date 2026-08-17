# PRD — კლინიკის პაციენტის ბარათი (Clinic Patient Card)

| | |
|---|---|
| **პროდუქტი** | პაციენტის ბარათი Odoo-ს კონტაქტის ფორმაზე (სტომატოლოგიური კლინიკა) |
| **მოდული** | `clinic_patient_card` |
| **პლატფორმა** | Odoo **19.0 Community** (server build `19.0-20260630`) |
| **ლიცენზია** | LGPL-3 |
| **რეპოზიტორი** | https://github.com/refreshg/clinic (branch `main`) |
| **ვერსია** | 19.0.25.0.0 |
| **სტატუსი** | Phase 1–2 + Rev-A + Phase 3 (A/B/C) + Phase 4 დასრულებული და ცოცხლად. დამატებით: OWL Planning board, პაციენტის ვიზუალური Dashboard, Supply Shop (custom storefront), მომწოდებლის portal (როლი + სტანდ. Inventory ფუძედ) და **PO↔SO ჯაჭვი**. |
| **ბოლო განახლება** | 2026-08-18 |

> ეს დოკუმენტი პროექტის **source of truth**-ია. კოდის ან scope-ის ცვლილებისას ეს ფაილიც განახლდეს.
> ორიგინალი მოთხოვნები: `პაციენტის ბარათი- 04.07.26 (1).doc` (რეპოს root-ში).

---

## 1. მიმოხილვა და მიზნები

სტომატოლოგიური კლინიკისთვის პაციენტის ერთიანი ბარათი, რომელიც Odoo-ს სტანდარტულ
კონტაქტს (`res.partner`) აფართოებს — ძირითადი/საკონტაქტო ინფო, სამედიცინო და
სტომატოლოგიური ანამნეზი, ფინანსები, დოკუმენტები, ანალიტიკა, თაიმლაინი და სწრაფი
მოქმედებები. ინტერფეისი **ქართულია**.

**მიზნები:** ერთ ბარათზე პაციენტის სრული სურათი; მიღება/ექიმი/ადმინი ერთ ადგილას
მუშაობს; სტანდარტული Odoo-ს ფუნქციონალის მაქსიმალური ხელახალი გამოყენება.

**არა-მიზნები (ამ ეტაპზე):** სრული EHR/EMR სისტემა; გარე ინტეგრაციები (Form-100
გენერაცია და EHR სინქრონი — მოგვიანებით); Enterprise-ფუნქციები.

## 2. მომხმარებლები
- **მიღების ოპერატორი** — რეგისტრაცია, ჯავშნები, ტელეფონები, დოკუმენტები, გადახდები.
- **ექიმი (სტომატოლოგი)** — ანამნეზი, კბილის სქემა, პროცედურები, მკურნალობის გეგმა.
- **ადმინისტრატორი/მფლობელი** — ფინანსები, ანალიტიკა (გაცდენა/LTV/რისკი).

## 3. არქიტექტურა და პრინციპები
- **ერთი ცალკე მოდული** `clinic_patient_card`; ბირთვს არ ვცვლით.
- `res.partner` — მხოლოდ `_inherit`-ით; ფორმა — `inherit_id` + xpath-ით.
- **მთავარი პრინციპი:** ჯერ სტანდარტული Odoo-ს ველი/ფუნქცია გამოვიყენოთ, და მხოლოდ
  რაც არ არსებობს — ის ავაშენოთ.
- **Community შეზღუდვა:** `documents`, `sign`, `appointment` (Enterprise) მიუწვდომელია →
  documents = attachments, signature = სტანდარტული `signature` widget, ჯავშნები =
  custom `clinic.appointment` სტანდარტულ `calendar`-ზე.
- i18n: source strings English + `i18n/ka.po` ქართული.
- Upgrade-safe: ლოგიკა მოდელებში, მინიმალური xpath, ORM (raw SQL მხოლოდ `odoo.tools.SQL`).

## 4. ფუნქციური მოთხოვნები (1.1–1.9)

სვეტები: **წყარო** = სტანდარტი (reuse) / custom; **სტატუსი** = ✅ დასრულებული / 🔜 Phase 3.

### 1.1 ძირითადი ინფორმაცია
| მოთხოვნა | რეალიზაცია | წყარო | სტ. |
|---|---|---|---|
| სახელი/გვარი (ლათინურად თუ უცხოელი) | `name` + `name_latin` | std+custom | ✅ |
| პირადი ნომერი | `vat` (Tax ID, relabel „პირადი ნომერი") | std | ✅ |
| დაბადების თარიღი / ასაკი | `birthdate` + computed `age` | custom | ✅ |
| სქესი | `gender` | custom | ✅ |
| პაციენტის ID / ისტორიის № | `patient_ref` (ir.sequence `P000001`) | custom | ✅ |
| რეგისტრაციის თარიღი | `registration_date` | custom | ✅ |
| მომართვის წყარო | `referral_source` (+`referral_source_other`) | custom | ✅ |
| უცხოელი + ქვეყანა | `is_foreign` + `nationality_country_id` | custom | ✅ |
| პირველადია? | `is_first_visit` | custom | ✅ |

### 1.2 საკონტაქტო ინფორმაცია
| მოთხოვნა | რეალიზაცია | წყარო | სტ. |
|---|---|---|---|
| ტელეფონები (მრავალი, პრიორ., უცხ. ნომერი, მშობელი) | `clinic.patient.phone` (sequence, phone, phone_type, owner_name, is_foreign_number) | custom | ✅ |
| Email / მისამართი | std `email` / address | std | ✅ |
| საგანგებო კონტაქტი | ტელეფონის ცხრილში `is_emergency` + `relation` | custom | ✅ |
| სასურველი კომუნიკაციის არხი | ტელეფონის ცხრილში `channel` (SMS/ზარი/WhatsApp) | custom | ✅ |

### 1.3 სამედიცინო ანამნეზი
| მოთხოვნა | რეალიზაცია | წყარო | სტ. |
|---|---|---|---|
| ალერგიები (მედ./მასალა/ლატექსი) | `clinic.patient.allergy` (type/name/reaction/severity) | custom | ✅ |
| ქრონიკული დაავადებები | `chronic_diseases` | custom | ✅ |
| მიმდინარე მედიკამენტები | `current_medications` | custom | ✅ |
| ორსულობის სტატუსი | `is_pregnant` (bool, ჩანს თუ სქესი=მდედრ.) | custom | ✅ |
| სისხლდენა / კარდიო რისკები | `has_bleeding_disorder`, `has_cardio_risk`, `medical_risk_notes` | custom | ✅ |
| ბოლო განახლება + ვინ | `medical_update_date` / `medical_update_uid` (auto write()) | custom | ✅ |

### 1.4 სტომატოლოგიური ანამნეზი
| მოთხოვნა | რეალიზაცია | წყარო | სტ. |
|---|---|---|---|
| ბოლო ვიზიტის თარიღი | `last_dental_visit_date` (ხელით; auto ჯავშნებიდან) | custom | ✅ / 🔜 auto |
| სტომ. სქემა (FDI ნუმერაცია) | `clinic.patient.tooth` + ვიზუალური `odontogram_html` (computed) | custom | ✅ |
| — დაწკაპუნებადი რედაქტირება | OWL JS widget | custom | 🔜 |
| აქტიური მკურნალობის გეგმის სტატუსი | `treatment_plan_status` | custom | ✅ |
| პროცედურების ისტორია (ვისთან) | `clinic.procedure.history` (date/name/`doctor_id`/tooth/note) | custom | ✅ |
| ბრუქსიზმი / პაროდონტიტი / სხვა | `has_bruxism`, `periodontitis_risk`, `dental_other_notes` | custom | ✅ |

### 1.5 ფინანსური სტატუსი
| მოთხოვნა | რეალიზაცია | წყარო | სტ. |
|---|---|---|---|
| მიმდინარე ბალანსი (დავალიანება/ავანსი) | `credit` / `debit` | std (`account`) | ✅ |
| დაზღვევის ინფორმაცია | `insurance_provider/policy_no/valid_until/notes` | custom | ✅ |
| გადახდის ისტორია | `invoice_ids` (ინვოისები/გადახდები) | std (`account`) | ✅ |
| სასურველი გადახდის მეთოდი | `preferred_payment_method` | custom | ✅ |
| ფასდაკლება (% და თანხა) | `discount_percent` / `discount_fixed` | custom | ✅ |
| ლოიალობის სტატუსი | `loyalty_status` | custom | ✅ |

### 1.6 დოკუმენტები
| მოთხოვნა | რეალიზაცია | წყარო | სტ. |
|---|---|---|---|
| პირადობის სკანი / თანხმობა (ხელმოწერით) / რენტგენი / დაზღვევა | `clinic.patient.document` (`doc_type`, `attachment`, `signature` widget თანხმობაზე) | custom + std attachments | ✅ |

### 1.7 პაციენტის პროფილი
| მოთხოვნა | რეალიზაცია | წყარო | სტ. |
|---|---|---|---|
| გაცდენების % | `no_show_rate` (ხელით; auto ჯავშნებიდან) | custom | ✅ / 🔜 auto |
| LTV პროგნოზი | `ltv_forecast` (ხელით; auto) | custom | ✅ / 🔜 auto |
| რისკების მაჩვენებელი | `risk_level` + `risk_notes` (ხელით; auto) | custom | ✅ / 🔜 auto |

### 1.8 თაიმლაინი
| მოთხოვნა | რეალიზაცია | წყარო | სტ. |
|---|---|---|---|
| ქრონოლოგია (ვიზიტები, ჩანაწერები, გადახდები, დოკ., სტატუსები) | chatter (`mail.thread`) + custom events | std + custom | 🔜 |
| გაუქმებული ვიზიტები (ვისი სურვილით / ვინ გააუქმა) | `clinic.appointment`-ის ველები | custom | 🔜 |

### 1.9 სწრაფი მოქმედებები
8 ღილაკი Patient Card ტაბის თავში. ამჟამად placeholder — `action_clinic_todo` →
„მალე" notification (მომხმარებლის მოთხოვნით ჯერ არაფერს აკეთებენ).
| ღილაკი | რეალური ფუნქცია (Phase 3) |
|---|---|
| ჯავშნის შექმნა | `clinic.appointment` create |
| ჩანაწერის დამატება | chatter log note |
| შეხსენების გაგზავნა | `sms` / activity |
| პირის ღრუს სქემა | odontogram dialog |
| ინვოისის შექმნა | `account.move` (std) |
| ფორმა-100 | QWeb report |
| EHR სინქრონიზაცია | გარე ინტეგრაცია |
| გადახდა / დავალიანებაში | `account.payment` (std) |

### 1.10 ვიზიტის / ჯავშნის ლაივ-ციკლი (Phase 3)
წყარო: `docs/ჯავშანივიზიტი - 12.07.26.docx`; 6 პატერნი → **`docs/booking-visit-patterns.md`**.
ჯავშანი = სტანდარტული `calendar.event` (`is_clinic=True`), გაფართოებული კლინიკური workflow-ით
(Community-ს Enterprise appointment/gantt არ აქვს → სტანდარტული calendar ძრავი + custom visual).

**სტატუსების ლაივ-ციკლი (`clinic_state`):** მოთხოვნილი → დაჯავშნილი → დადასტურებული →
მოსული (checkin_time) → პროცესში (treat_start) → დასრულებული (treat_end) → გადახდილი;
+ გაუქმებული (მიზეზი სავალდებ.), გაცდენა/No-Show. header statusbar + workflow ღილაკები.

**6 პატერნი (`booking-visit-patterns.md`):** (1) state machine; (2) სავალდებ. კარიბჭეები/guards;
(3) ეტაპობრივი დროის აღრიცხვა (მოცდის/სავარძლის დრო); (4) მოვლენაზე-შეტყობინებები (ხმა+toast,
რიმაინდერები delivery-სტატუსით); (5) გეგმა→ფაქტი→ინვოისი შეჯერება; (6) თანხმობა/უსაფრთხოების ფენა.

| მოთხოვნა | რეალიზაცია | სტ. |
|---|---|---|
| ჯავშნის შექმნა + კალენდარი | `calendar.event` + calendar/list view + Clinic→Appointments; „Create Booking" ღილაკი | ✅ 3A |
| სტატუსები + workflow ღილაკები | `clinic_state` statusbar + action_confirm/arrive/start/done/pay/cancel/no_show | ✅ 3A |
| ოთახი / ტიპი (ფერი) | `clinic.room`, `clinic.appointment.type` (color, default_duration) | ✅ 3A |
| ეტაპობრივი დროის აღრიცხვა | checkin/start/end + waiting/chair minutes | ✅ 3A |
| ექიმის ხმა+ვიზუალი (checkin) | `bus.bus` + OWL sound/toast | 🔜 3C |
| ექიმის კალენდარი | calendar filter dentist=uid + custom OWL visual | 🔜 3C |
| პროცედურის auto-შევსება | done → `clinic.procedure.history` | 🔜 3C |
| follow-up / გრძელვადიანი | `parent_appointment_id` | 🟡 ველი (ლოგიკა 3C) |
| გადახდა (ადმინი) | `action_pay` → `account` | 🔜 3C |
| როლები (ექიმი vs ადმინი) | `res.groups` + ACL + record rules | 🔜 3B |

## 5. მონაცემთა მოდელი

**`res.partner` (inherit):** `is_patient` (მთავარი ალამი) + ყველა ზემოთ ჩამოთვლილი ველი.
computed: `age`, `odontogram_html`. write()-ში: `patient_ref` მინიჭება + medical-update stamp.

**ახალი მოდელები (თითოეულს აქვს ACL):**
- `clinic.patient.phone` — ტელეფონები (channel, is_emergency, relation, owner, foreign).
- `clinic.patient.allergy` — ალერგიები.
- `clinic.procedure.history` — ჩატარებული პროცედურები (`doctor_id`-ით).
- `clinic.patient.tooth` — კბილები (FDI `tooth_number` + `status`).
- `clinic.patient.document` — დოკუმენტები (typed + attachment + signature).
- `clinic.procedure.catalog`, `clinic.insurance.company` — Rev-A каталოგები.
- `clinic.room`, `clinic.appointment.type` — ✅ 3A (ოთახები, ჯავშნის ტიპები/ფერი).
- **`calendar.event` (inherit)** — ✅ 3A ჯავშანი/ვიზიტი: is_clinic, patient_id, dentist_id,
  room_id, appointment_type_id, clinic_state, checkin/start/end + waiting/chair minutes,
  parent_appointment_id, cancel_reason.

## 6. არა-ფუნქციური მოთხოვნები
- Odoo **19.0 Community**, Python 3.10+, PostgreSQL.
- LGPL-3; upgrade-safe (core არ იცვლება, uninstall ყველაფერს აბრუნებს).
- i18n ქართული (`ka.po`); source strings English.
- Docker-ზე გაშვება (odoo + postgres + nginx). დეტალები — Claude-ის ლოკალურ მეხსიერებაში
  (`clinic-server-deploy`), **პაროლები რეპოში არ ინახება**.

## 7. ფაზები და სტატუსი (roadmap)
- **Phase 1 — ✅** 1.1–1.4 (ბაზისური/საკონტაქტო/სამედიცინო/სტომატ.).
- **Phase 1 v1.1 — ✅** clinic feedback: vat=პირადი ნომერი header-ში, ტაბი პირველი+default,
  ტელეფონის არხი/საგანგებო ცხრილში, ორსულობა bool, კბილის ცხრილი.
- **Phase 2 — ✅** `account` install; 1.5 ფინანსები, 1.6 დოკუმენტები, 1.7 პროფილი,
  1.9 ღილაკები (placeholder), ვიზუალური ოდონტოგრამა.
- **Rev-A — ✅ (v19.0.3.0.0, deployed)** რეცენზენტების feedback #1: patient_ref ხელით/ავტო;
  მოქალაქეობა/ლათინური ყოველთვის; is_repeat/is_regular; მეურვე (guardian_id + is_minor);
  referral გაფართოება; NOTE; ვრცელი ანამნეზი; რენტ./კტ; ალერგიული სინჯი; treatment_plan_status
  + badge; payment „mixed"; `clinic.insurance.company`/`clinic.procedure.catalog` (m2o);
  ტელეფონი country_code/is_primary; `mail` depend; **view 4 ბლოკად**.
- **Phase 3A — ✅ (v19.0.4.0.0, deployed)** ჯავშნის ბირთვი: `calendar.event` გაფართოება
  (clinic_state state machine + workflow ღილაკები), `clinic.room`, `clinic.appointment.type`,
  calendar/list/form view-ები, Clinic→Appointments მენიუ, „Create Booking" ღილაკი,
  დროის აღრიცხვა. `calendar` install. → იხ. 1.10 + `booking-visit-patterns.md`.
- **Phase 3B — ✅ როლები/წვდომა:** Clinic Doctor vs Administrator (res.groups + ACL + ir.rule +
  field `groups=`): სამედ./კბილი/პროცედურა/ჯავშანი = ექიმი; ფინანს./საბანკო/გადახდა = ადმინი.
  ადმინი ერთდება post_init_hook-ით (`_post_init_grant_admin`).
- **Phase 3C — ✅:** ექიმის bus+ხმა+toast შეტყობინება (checkin → `clinic_arrived_service.js`),
  ექიმის კალენდარი, პროცედურის auto-შევსება (done→`clinic.procedure.history`), follow-up
  („Next Visit"), გადახდა (`clinic.payment.wizard` → account.move), 1.4 ბოლო ვიზიტი auto.
- **Phase 4 — ✅ მარაგები/შეკვეთა:** `stock`+`purchase` reuse → მარაგი, reordering,
  low-stock alert (cron → activity + bus). **Supply Shop** = custom OWL storefront (მომხმარებლის
  არჩევანი — „მაღაზიის იერი პრინციპულია"), არა `website_sale` (ის გაყიდვისთვისაა). checkout →
  `purchase.order` (RFQ) + **სარკე `sale.order`** მომწოდებელზე (PO↔SO ჯაჭვი).
- **Phase 5 — ✅ Planning board / Dashboard / Supplier portal (extras, v19.0.15–25):**
  - **OWL Planning board** (`clinic_planning`, Clinic→Planning, seq 1): მრავალსვეტიანი
    დღის ხედი დენტისტებით, ფერადი ბლოკები appointment_type-ით, mini-cal, room/dentist ფილტრი,
    now-line. **ცარიელ უჯრაზე დაკლიკება** → ახალი ვიზიტი წინასწარ შევსებული (dentist + დრო,
    snap 30წთ) + ripple/ghost ვიზუალური feedback. სვეტები ყოველთვის ჩანს
    (`res.users.clinic_dentists` = Doctor ჯგუფი).
  - **პაციენტის Dashboard** (`clinic_patient_dashboard`): Health-Care დიზაინის ვიზუალი —
    breadcrumb, პროფილის ბარათი, vitals row (ვიზუალი, „not tracked yet"), history table.
    „🩺 Open Dashboard" ღილაკი Patient Card ტაბზე.
  - **მომწოდებლის portal:** ახალი როლი **Clinic Supplier** (implies purchase + stock + sales
    user); record rules → ხედავს მხოლოდ თავის პროდუქტებს (Inventory ფუძედ), თავის RFQ/SO-ებს.
    „My Shop" OWL პანელი (პროდუქტების გამოქვეყნება, სურათით) სტანდ. Inventory-ს ზედნაშენად.
    checkout → SO მომწოდებელზე; მომწოდებელი ადასტურებს SO-ს → PO ავტომატურად დასტურდება +
    კლინიკას toast. მენიუ: My Shop / My Inventory / My Orders.
  - **ვიზიტის ფორმა:** კლინიკურ ვიზიტზე დამალულია meeting-only ველები (Location, Video Link,
    guests/attendees + EMAIL/SMS); Clinic ტაბი ავტომატურად იხსნება.
- **🔜 დარჩენილი:** Form-100, EHR sync, დაწკაპუნებადი ოდონტოგრამა, დემო-პროდუქტების რეალური ფოტოები.

## 8. გადაწყვეტილებების ჟურნალი
- პირადი ნომერი → სტანდარტული `vat` (მომხმარებლის არჩევანი, დუბლის თავიდან ასაცილებლად).
- ფინანსები → სტანდარტული `account` (Community-ში ხელმისაწვდომი).
- ჯავშნები → custom `calendar`-ზე (Enterprise `appointment` მიუწვდომელი).
- დოკუმენტები/ხელმოწერა → attachments + `signature` widget (Enterprise `documents`/`sign` მიუწვდომ.).
- კბილის სქემა → ჯერ ცხრილი + ვიზუალური read-only ოდონტოგრამა; დაწკაპუნებადი JS მოგვიანებით.
- სწრაფი ღილაკები → placeholder, სანამ შესაბამისი ფუნქციონალი არ არსებობს.
- **მაღაზია → custom OWL Supply Shop** (არა `website_sale`): მომხმარებელმა თქვა „მაღაზიის იერი
  პრინციპულია"; `website_sale` გაყიდვისთვისაა (sale.order), ჩვენ ყიდვა გვჭირდება. custom UI
  სტანდარტულ `purchase`-ზე დაშენდა.
- **PO↔SO ჯაჭვი:** კლინიკა ყიდულობს → `purchase.order`; მომწოდებელი ყიდის → `sale.order`
  (სარკე, ერთ DB-ში). ეს „სწორი ჯაჭვია" (მომხმარებლის დაკვირვება). SO-ს delivery გამორთულია
  კლინიკის ორდერებზე (`_action_launch_stock_rule` skip) — საქონელი PO-ს receipt-ით მოდის,
  ასე რომ SO confirm არ საჭიროებს warehouse route-ს.
- **მომწოდებლის პროდუქტები = სტანდარტული Inventory ფუძედ** (მომხმარებლის მოთხოვნა): „My Shop"
  პანელი მხოლოდ მართვის UI-ია; ბაზა/ნაშთი ყველაფერი Inventory-დან, record rule-ით scoped
  („seller_ids.partner_id" == user's vendor). პანელის write-ები `.sudo()`-ით (scoping კოდში).
- **მომწოდებელი ≠ კლინიკის მენიუები:** როლებით — მომწოდებელი ხედავს მხოლოდ My Shop/Inventory/
  Orders; კალენდარი/ვიზიტები დამალულია. (მენიუს ხილვადობა მოწმდება `ir.ui.menu.load_menus`-ით,
  არა raw search-ით — raw search group-gating-ს არ ითვალისწინებს.)
- **vitals ვიზუალი მხოლოდ:** Dashboard-ზე წნევა/პულსი/გლუკოზა/ქოლესტეროლი placeholder-ია
  („not tracked yet") — არ ვინახავთ vitals-ს, გამოგონილ სამედიცინო მაჩვენებლებს არ ვაჩვენებთ.

## 9. ღია საკითხები
- ჯავშნის მოდელის ველების ზუსტი scope (სტატუსები, გაუქმების მიზეზი/ავტორი).
- LTV/no-show/რისკის გამოთვლის ფორმულები (ჯავშნების+ინვოისების მონაცემებზე).
- Form-100-ის ზუსტი შაბლონი; EHR-ის სამიზნე სისტემა/API.
- ოდონტოგრამის ინტერაქციის მოდელი (დაწკაპუნება → სტატუსის ცვლა/popover).
