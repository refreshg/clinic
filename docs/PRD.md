# PRD — კლინიკის პაციენტის ბარათი (Clinic Patient Card)

| | |
|---|---|
| **პროდუქტი** | პაციენტის ბარათი Odoo-ს კონტაქტის ფორმაზე (სტომატოლოგიური კლინიკა) |
| **მოდული** | `clinic_patient_card` |
| **პლატფორმა** | Odoo **19.0 Community** (server build `19.0-20260630`) |
| **ლიცენზია** | LGPL-3 |
| **რეპოზიტორი** | https://github.com/refreshg/clinic (branch `main`) |
| **სტატუსი** | Phase 1–2 დასრულებული, Phase 3 იგეგმება |
| **ბოლო განახლება** | 2026-07-16 |

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

## 5. მონაცემთა მოდელი

**`res.partner` (inherit):** `is_patient` (მთავარი ალამი) + ყველა ზემოთ ჩამოთვლილი ველი.
computed: `age`, `odontogram_html`. write()-ში: `patient_ref` მინიჭება + medical-update stamp.

**ახალი მოდელები (თითოეულს აქვს ACL):**
- `clinic.patient.phone` — ტელეფონები (channel, is_emergency, relation, owner, foreign).
- `clinic.patient.allergy` — ალერგიები.
- `clinic.procedure.history` — ჩატარებული პროცედურები (`doctor_id`-ით).
- `clinic.patient.tooth` — კბილები (FDI `tooth_number` + `status`).
- `clinic.patient.document` — დოკუმენტები (typed + attachment + signature).
- 🔜 `clinic.appointment` — ჯავშნები/ვიზიტები (`calendar`-ზე).

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
- **Rev-A — 🟡 კოდი მზადაა (v19.0.3.0.0), deploy-ს ელოდება** (რეცენზენტების feedback #1):
  patient_ref ხელით/ავტო; მოქალაქეობა/ლათინური ყოველთვის; ალმები is_repeat/is_regular;
  მეურვე (guardian_id + is_minor); referral გაფართოება; NOTE (patient_note); ანამნეზი
  ვრცლად (smoker/alcohol/family_history/anamnesis); რენტ./კტ (has_xray/has_ct/imaging_source);
  ალერგიული სინჯი; treatment_plan_status გაფართოება + badge ფერები; payment „mixed";
  დაზღვევა → `clinic.insurance.company` (m2o); პროცედურა → `clinic.procedure.catalog` (m2o)
  + status/planned_date (დაგეგმ.+ჩატარებ.); ტელეფონი country_code/is_primary + channel=email;
  `mail` depend (chatter/კომუნიკაცია); **view 4 ბლოკად** (ძირითადი/სამედიცინო/ფინანსები/ისტორია).
  *დარჩა (server offline იყო): ცოცხალი deploy + `-u` + ka.po regen + verify.*
- **Rev-B — 🔜 როლები/წვდომა:** Clinic Doctor vs Administrator (res.groups + ACL + ir.rule +
  field `groups=`): სამედ./კბილი/პროცედურა = ექიმი; ფინანს./საბანკო შეზღუდული.
- **Phase 3 — 🔜** `clinic.appointment` (calendar) → 1.4 ბოლო ვიზიტი auto, 1.7 auto-გამოთვლა,
  პროცედურის auto-შევსება; 1.8 თაიმლაინი; ავტ. შეხსენებები; Form-100; EHR; დაწკაპ. ოდონტოგრამა.

## 8. გადაწყვეტილებების ჟურნალი
- პირადი ნომერი → სტანდარტული `vat` (მომხმარებლის არჩევანი, დუბლის თავიდან ასაცილებლად).
- ფინანსები → სტანდარტული `account` (Community-ში ხელმისაწვდომი).
- ჯავშნები → custom `calendar`-ზე (Enterprise `appointment` მიუწვდომელი).
- დოკუმენტები/ხელმოწერა → attachments + `signature` widget (Enterprise `documents`/`sign` მიუწვდომ.).
- კბილის სქემა → ჯერ ცხრილი + ვიზუალური read-only ოდონტოგრამა; დაწკაპუნებადი JS მოგვიანებით.
- სწრაფი ღილაკები → placeholder, სანამ შესაბამისი ფუნქციონალი არ არსებობს.

## 9. ღია საკითხები
- ჯავშნის მოდელის ველების ზუსტი scope (სტატუსები, გაუქმების მიზეზი/ავტორი).
- LTV/no-show/რისკის გამოთვლის ფორმულები (ჯავშნების+ინვოისების მონაცემებზე).
- Form-100-ის ზუსტი შაბლონი; EHR-ის სამიზნე სისტემა/API.
- ოდონტოგრამის ინტერაქციის მოდელი (დაწკაპუნება → სტატუსის ცვლა/popover).
