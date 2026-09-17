# Part of clinic_patient_card. LGPL-3.
"""Visit-page medical catalogs and tables (Dentos parity round).

* clinic.complaint — the selectable complaints catalog (ჩივილები);
  admins extend it, a visit tags the ones that apply.
* clinic.prescription — one prescription/recommendation row on a visit
  (დანიშნულება/რეკომ. table with add/delete). E-recipe sync is out of
  scope — the type is recorded, nothing leaves the system.
"""

from odoo import fields, models


class ClinicComplaint(models.Model):
    _name = "clinic.complaint"
    _description = "Complaint Catalog"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)


class ClinicPrescription(models.Model):
    _name = "clinic.prescription"
    _description = "Visit Prescription / Recommendation"
    _order = "id desc"

    visit_id = fields.Many2one(
        "calendar.event", string="Visit", required=True, ondelete="cascade",
        index=True,
    )
    rec_type = fields.Selection(
        [
            ("e_recipe", "E-Recipe"),
            ("prescription", "Prescription"),
            ("recommendation", "Recommendation"),
        ],
        string="Type", default="prescription", required=True,
    )
    medicament = fields.Char(string="Medicament", required=True)
    period = fields.Char(string="Intake Period")
    qty = fields.Float(string="Quantity", default=1.0)
    directions = fields.Text(string="Directions")
