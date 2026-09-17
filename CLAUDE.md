<!-- last-synced: 2026-09-17, commit: 677c4d3 -->
# Clinic — project notes for Claude

## Platform
- Odoo **19.0 Community** custom addon (server build `19.0-20260630`), LGPL-3.
- Community only — NEVER depend on Enterprise modules (web_studio, documents, sign,
  appointment, planning…); check every `depends`.
- Odoo 19 syntax: no `attrs`/`states` (direct `invisible="expr"`); `<list>` not `<tree>`;
  `display_name` not `name_get()`; `env.cr/context/uid`; JSON-2 API available.

## Product / plan (history lives in docs/ — don't re-read it here)
- `docs/PRD.md` = source of truth for requirements; `docs/DECISIONS.md` = ADRs D-1…D-23.
- DONE & live, user-tested: Phases 1–4 + patient card/dashboard/shop/supplier portal;
  reviewer batch 28.08.26 (v30–46); reviewer batch #2 ჯავშნები+მაღაზია/მარაგები (v47–55,
  D-16…D-20 incl. supplier warehouses); Soft-UI restyles (v55.x, D-21); Dentos-parity
  batch — booking popup, quick registration, consents with signature, OWL visit page,
  billing, coloured board (v56–60.4, D-22/D-23).
- Deferred: emails + SMS (clinic must decide what/when), ka.po regen (M2, first
  unblocked), patient-card page write-back, Form-100, EHR sync, clickable odontogram.
- Roles: Clinic Administrator / Doctor / Supplier; doctors see only their own visits
  (global ir.rule) and only their own board column; admin sees all.

## Key architecture decisions (details: docs/DECISIONS.md)
- Shop = custom OWL over standard `purchase` (clinic BUYS; website_sale sells).
- PO↔SO mirror chain: checkout makes RFQ + mirror SO; supplier confirms SO →
  mirror-confirms PO; mirror SO lines skip delivery routes (D-2).
- Supplier products/stock = standard Inventory scoped by ir.rule; panel writes sudo
  with vendor scoping in code; product READ open, write scoped (D-20); supplier
  warehouses deduct at shipping via transit locations (D-19).
- Custom OWL Planning board IS the calendar (std calendar menus removed); dynamic hour
  window; board owns its vertical scroll; HOUR_PX=96 must match SCSS row heights.
- Dentos-parity: visit work happens on the OWL visit page (`clinic_visit_page`) over
  existing models; thin catalogs clinic.icd10/complaint/prescription/consent (D-22).
- Design handoffs → rebuild native OWL; never embed React into the Odoo backend.
- Scheduling guards live in create/write keyed on `'start' in vals`; escape hatch
  `clinic_force=1`; past-booking bypass = the Administrator ACCOUNT, not a group.
- `requested` = reserve state: excluded from board grid and overlap checks.
- Board datetime defaults must be UTC-serialized (`serializeDateTime`).
- **OWL gotchas (Odoo 19)**: template expressions have NO JS globals (`String()`
  crashes); no `t-model` with a computed key; no comments between t-if/t-elif
  siblings; `record.update` m2o values are `{id, display_name}` OBJECTS (tuples
  silently dropped); custom form dialogs go through a view WIDGET + FormViewDialog,
  never `form_view_ref` on the field context (it hijacks the internal link) — D-23.
- Form compiler drops class attrs on `<sheet>` — scope CSS via an invisible marker
  div + `:has()` (D-21). Odoo 19 renames: ir.actions.server `group_ids`; readonly
  list fields need `force_save="1"`; domain always-false trick `(1,'=',0)` rejected —
  use `('id','=',False)`.

## How to work here
- Use the **odoo-development** skill for Odoo questions; read `references/official/`
  before precise API answers.
- Never modify core; `_inherit` models, `inherit_id`+xpath views; minimal xpath.
- Standard Odoo features FIRST; custom only with a stated reason recorded as D-<n>.
- Every new model gets `security/ir.model.access.csv` rows; two layers: ACL + ir.rule.
- **Append new `_inherit` classes at EOF** — mid-file classes silently re-parent every
  def below (broke the RFQ chain once); `grep '^class '` after structural edits.
- UI strings English (+ some Georgian labels); translations in `i18n/ka.po` (export
  .pot after a restart).
- **Never commit secrets** — credentials live only in local Claude memory. Videos and
  other >50MB files never enter git (`docs/Videos/` is gitignored; GitHub hard-blocks
  >100MB and the push fails for the whole history).

## Commands (dev loop = live LAN server; NO local Odoo; passwords in local memory)
- Package: `tar --force-local -czf module.tgz -C <repo> --exclude='__pycache__' --exclude='patient-card-ui' clinic_patient_card`
- Ship: `scp module.tgz fmg@192.168.0.235:/tmp/clinic_module.tgz`, extract to `/opt/odoo19/addons/`
- Upgrade: `docker exec odoo19-odoo-1 odoo -d odoo -u clinic_patient_card --stop-after-init --no-http --db_password=<local memory>`
- Restart: `cd /opt/odoo19 && docker compose restart odoo` · Logs: `docker logs -f odoo19-odoo-1`
- Smoke tests: JSON-RPC via scratchpad node script → `http://192.168.0.235:9494/jsonrpc`
  (host `tfs.fmgsoft.ge:9494` works without VPN; SSH needs VPN).
- No automated tests by decision (D-11) — verify live via RPC + browser.
- Bash heredocs end `&&` chains — later commands run unconditionally; write node edit
  scripts to the scratchpad instead of inline quoting.

## Layout
- `clinic_patient_card/` — the only addon (models/, views/, wizard/, security/, data/, static/src/, i18n/)
- `docs/` — PRD, SPEC, PLAN, ARCHITECTURE, DECISIONS + source .docx + design refs; `docs/Videos/` untracked
- `patient-card-ui/` — React design reference (never deployed)

## Conventions
- Models `clinic.*`; xml ids `view_/action_/menu_/rule_/cron_` snake_case; fields
  snake_case, core-model additions flagged `is_clinic`/`clinic_*`.
- Commits: `feat(clinic)|fix(clinic)|docs(clinic)|chore(...)` + Claude co-author trailer.

## Workflow
PRD → SPEC → **PLAN (user approves BEFORE code)** → code → live verification →
`/docs-sync`. Per change: deploy → RPC/browser verify → commit → push. Reports to the
user are point-by-point, in Georgian.

## Docs map
- `docs/PRD.md` requirements (Georgian) · `docs/SPEC.md` data model/rules/security
- `docs/PLAN.md` roadmap (user-approved) · `docs/ARCHITECTURE.md` components/flows
- `docs/DECISIONS.md` ADRs · `clinic_patient_card/README.md` install/config/limitations
