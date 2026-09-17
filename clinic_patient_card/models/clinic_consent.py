# Part of clinic_patient_card. LGPL-3.
"""Patient consents (Dentos-style, batch D2).

Two consent sheets belong to every visit:

* ``personal_data`` — personal-data processing terms: two confirmation
  checkboxes plus the marketing-SMS yes/no choice.
* ``medical`` — written informed consent for medical services, signed
  on screen (standard Odoo ``signature`` widget — Community).

The visit's "თანხმობის ფურცელი" button materialises both records and
walks reception through them in order. Signing the medical sheet also
stores the drawing on the partner as their signature sample (first time
only). SMS itself stays deferred project-wide — the choice is recorded,
nothing is sent.
"""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

PERSONAL_DATA_TEXT = (
    "დარწმუნებული ვარ, რომ მომხმარებელი გაეცნო და დაეთანხმა პერსონალურ "
    "მონაცემთა დამუშავების პირობებს. კლინიკა პერსონალურ მონაცემებს "
    "ამუშავებს მხოლოდ სამედიცინო მომსახურების გაწევის, ჩანაწერების "
    "წარმოებისა და კანონმდებლობით გათვალისწინებული ვალდებულებების "
    "შესრულების მიზნით. მონაცემები არ გადაეცემა მესამე პირებს პაციენტის "
    "თანხმობის ან კანონისმიერი საფუძვლის გარეშე."
)
MEDICAL_TEXT = (
    "მიმდინარე ინფორმაცია სამედიცინო მომსახურების გაწევის შესახებ "
    "მიღებული მაქვს. მკურნალობის ეთაპები, მოსალოდნელი შედეგები, შესაძლო "
    "გართულებები და თანმდევი რისკები ჩემთვის განმარტებულია. ვაძლევ "
    "თანხმობას ჩემთვის შემოთავაზებულ სამედიცინო მომსახურებაზე."
)


class ClinicConsent(models.Model):
    _name = "clinic.consent"
    _description = "Patient Consent Sheet"
    _order = "id desc"
    _rec_name = "display_name"

    visit_id = fields.Many2one(
        "calendar.event", string="Visit", required=True, ondelete="cascade",
        index=True,
    )
    patient_id = fields.Many2one(
        "res.partner", string="Patient",
        related="visit_id.patient_id", store=True, index=True,
    )
    consent_type = fields.Selection(
        [
            ("personal_data", "Personal Data Terms"),
            ("medical", "Informed Medical Consent"),
        ],
        string="Type", required=True, default="personal_data",
    )
    body = fields.Text(
        string="Consent Text",
        help="Snapshot of the text the patient agreed to.",
    )
    # personal-data sheet
    agree_data = fields.Boolean(
        string="Agrees to personal-data processing terms")
    agree_marketing_terms = fields.Boolean(
        string="Agrees to marketing-SMS terms")
    marketing_sms = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Wants marketing SMS", default="yes",
    )
    # medical sheet
    signature = fields.Binary(string="Signature", attachment=True, copy=False)
    state = fields.Selection(
        [("draft", "Draft"), ("signed", "Signed")],
        string="Status", default="draft", required=True, copy=False,
    )
    signed_date = fields.Datetime(string="Signed On", readonly=True, copy=False)
    signed_uid = fields.Many2one(
        "res.users", string="Registered By", readonly=True, copy=False,
    )

    @api.depends("consent_type", "patient_id")
    def _compute_display_name(self):
        labels = dict(self._fields["consent_type"].selection)
        for c in self:
            c.display_name = "%s — %s" % (
                c.patient_id.name or "?",
                labels.get(c.consent_type, c.consent_type),
            )

    @api.model
    def _default_body(self, consent_type):
        return (
            PERSONAL_DATA_TEXT if consent_type == "personal_data"
            else MEDICAL_TEXT
        )

    def action_confirm(self):
        """Sign/confirm the sheet; on the personal-data sheet continue to
        the medical one (Dentos order)."""
        self.ensure_one()
        if self.consent_type == "personal_data":
            if not self.agree_data:
                raise ValidationError(_(
                    "The patient must agree to the personal-data terms first."
                ))
        elif not self.signature:
            raise ValidationError(_("Please sign before confirming."))
        self.write({
            "state": "signed",
            "signed_date": fields.Datetime.now(),
            "signed_uid": self.env.uid,
        })
        self.visit_id.message_post(body=_(
            "Consent signed: %s", dict(
                self._fields["consent_type"].selection)[self.consent_type],
        ))
        # keep the first drawing as the patient's signature sample
        if (self.consent_type == "medical" and self.signature
                and not self.patient_id.clinic_signature_sample):
            self.patient_id.sudo().clinic_signature_sample = self.signature
        # personal data signed → open the medical sheet next
        if self.consent_type == "medical":
            return {"type": "ir.actions.act_window_close"}
        nxt = self.visit_id.consent_ids.filtered(
            lambda c: c.consent_type == "medical")[:1]
        if not nxt:
            return {"type": "ir.actions.act_window_close"}
        return {
            "type": "ir.actions.act_window",
            "name": _("თანხმობა"),
            "res_model": "clinic.consent",
            "res_id": nxt.id,
            "view_mode": "form",
            "target": "new",
        }
