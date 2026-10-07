# Part of clinic_patient_card. LGPL-3.
"""Visit-page medical catalogs and tables (Dentos parity round).

* clinic.complaint — the selectable complaints catalog (ჩივილები);
  admins extend it, a visit tags the ones that apply.
* clinic.prescription — one prescription/recommendation row on a visit
  (დანიშნულება/რეკომ. table with add/delete). E-recipe sync is out of
  scope — the type is recorded, nothing leaves the system.
"""

from odoo import _, fields, models
from odoo.exceptions import UserError


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


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    # ------------------------------------------------------------------
    # Prescription / recommendation sheet of a visit: print, PDF, e-mail
    # ------------------------------------------------------------------
    def _clinic_report_prescriptions(self):
        self.ensure_one()
        return self.env["clinic.prescription"].search([("visit_id", "=", self.id)], order="id")

    def _clinic_check_prescriptions(self):
        self.ensure_one()
        if not self._clinic_report_prescriptions():
            raise UserError(_("Add at least one prescription / recommendation first."))

    def action_prescription_pdf(self):
        """Download the visit's prescription sheet as a PDF."""
        self._clinic_check_prescriptions()
        return self.env.ref("clinic_patient_card.action_report_clinic_prescription").report_action(self)

    def action_prescription_send(self):
        """Standard e-mail composer with the prescription PDF attached, to the patient."""
        self._clinic_check_prescriptions()
        template = self.env.ref("clinic_patient_card.mail_template_clinic_prescription")
        return {
            "type": "ir.actions.act_window",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_model": "calendar.event",
                "default_res_ids": self.ids,
                "default_template_id": template.id,
                "default_composition_mode": "comment",
                # the comment-mode composer ignores the template's partner_to
                "default_partner_ids": self.patient_id.ids,
                "force_email": True,
            },
        }
