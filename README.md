# Clinic — Odoo 19 addons

Custom Odoo 19 modules for a dental clinic. All changes are versioned here.

## Modules

### `clinic_patient_card`
Extends the Contact (`res.partner`) form with a full **patient card**, built
phase by phase from the specification (`პაციენტის ბარათი`):

| Phase | Section | Status |
|------|---------|--------|
| 1 | 1.1 Basic info · 1.2 Contacts · 1.3 Medical history · 1.4 Dental history | ✅ done |
| 2 | 1.5 Financials · 1.6 Documents · 1.7 Profile · visual odontogram | ✅ done |
| 3 | Appointment cycle (calendar.event state machine, roles, doctor notify, procedure auto-fill, payment, follow-up) | ✅ done |
| 4 | Supplies & ordering: `stock`+`purchase` reuse, low-stock alert, custom **Supply Shop** | ✅ done |
| 5 | Extras: OWL Planning board · patient Dashboard · supplier portal · **PO↔SO chain** | ✅ done |

Current module version: **19.0.25.0.0**. See `docs/PRD.md` for the full spec, data
model and decision log, and root `CLAUDE.md` for the key architecture decisions.

### Highlights
- **Planning board** (Clinic → Planning): multi-column day view; click an empty slot to
  book a visit (with a ripple/ghost cue).
- **Supply Shop** + **supplier portal**: suppliers publish products (standard Inventory as
  the base) into a custom OWL storefront; clinic checkout creates a `purchase.order` and a
  mirror `sale.order` for the supplier, who confirms it — which confirms the PO back.
- **Roles**: Clinic Administrator / Doctor / Supplier, with menus gated per role.

## Target environment
- Odoo **19.0**
- Database: `odoo` @ `tfs.fmgsoft.ge:9494`

## Localization
UI in Georgian with `.po` translations (`i18n/`).
