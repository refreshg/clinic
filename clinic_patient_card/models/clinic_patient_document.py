# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ClinicPatientDocument(models.Model):
    _name = "clinic.patient.document"
    _description = "Patient Document"
    _inherit = ["mail.thread"]  # comments on an X-ray = the standard chatter
    _order = "create_date desc, id desc"

    partner_id = fields.Many2one(
        "res.partner", string="Patient", required=True, ondelete="cascade", index=True,
    )
    doc_type = fields.Selection(
        [
            ("id_scan", "ID Scan"),
            ("consent", "Consent Form"),
            ("xray", "X-ray / Diagnostic"),
            ("exam_result", "Examination result"),
            ("allergy_doc", "Allergy document"),
            ("insurance", "Insurance Document"),
            ("other", "Other"),
        ],
        string="Document Type",
        required=True,
        default="other",
    )
    name = fields.Char(string="Title", required=True)
    date = fields.Date(string="Date", default=fields.Date.context_today)
    # X-ray / photo: the upload moment is the record's own create_date
    uploaded_by_id = fields.Many2one(
        "res.users", string="Uploaded by", default=lambda s: s.env.user,
        readonly=True, copy=False)
    attachment = fields.Binary(string="File", attachment=True)
    filename = fields.Char(string="Filename")
    # Drawn signature for consent forms (standard signature widget, Community).
    signature = fields.Binary(string="Signature")
    note = fields.Char(string="Note")
    # Examination result typed by hand (a file may be attached instead / as well)
    result_text = fields.Text(string="Result (typed)")

    @api.onchange("filename")
    def _onchange_filename_title(self):
        """One-step upload: the title defaults to the file's name."""
        if self.filename and not self.name:
            self.name = self.filename.rsplit(".", 1)[0]

    def action_add_next(self):
        """Saved picture -> a fresh empty page for the SAME patient (next picture)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "res_model": self._name,
            "view_mode": "form", "target": "current",
            "views": [(self.env.ref("clinic_patient_card.view_clinic_xray_form").id, "form")],
            "context": {
                "default_partner_id": self.partner_id.id,
                "default_doc_type": self.doc_type,
                "default_name": self.name,
            },
        }

    def action_open_full(self):
        """Full page of one picture (with the comments chatter)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "res_model": self._name,
            "res_id": self.id, "view_mode": "form",
            "views": [(self.env.ref("clinic_patient_card.view_clinic_xray_form").id, "form")],
            # a dialog: closing it returns to the exact tab of the patient card
            "target": "new",
            "context": {"dialog_size": "extra-large"},
        }
