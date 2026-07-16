# Clinic — Odoo 19 addons

Custom Odoo 19 modules for a dental clinic. All changes are versioned here.

## Modules

### `clinic_patient_card`
Extends the Contact (`res.partner`) form with a full **patient card**, built
phase by phase from the specification (`პაციენტის ბარათი`):

| Phase | Section | Status |
|------|---------|--------|
| 1 | 1.1 Basic info · 1.2 Contacts · 1.3 Medical history · 1.4 Dental history | 🚧 in progress |
| 2 | 1.5 Financials · 1.6 Documents | ⏳ planned |
| 3 | 1.7 Patient analytics/LTV · 1.8 Timeline · 1.9 Quick actions · Form-100 · EHR sync | ⏳ planned |

## Target environment
- Odoo **19.0**
- Database: `odoo` @ `tfs.fmgsoft.ge:9494`

## Localization
UI in Georgian with `.po` translations (`i18n/`).
