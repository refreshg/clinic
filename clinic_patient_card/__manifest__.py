# -*- coding: utf-8 -*-
{
    "name": "Clinic Patient Card",
    "summary": "Patient card on the contact form (dental clinic)",
    "description": "Extends the Contact (res.partner) form with a full patient "
                   "card: basic info, contacts, medical and dental history. "
                   "Built incrementally, phase by phase.",
    "author": "refreshg",
    "website": "https://github.com/refreshg/clinic",
    "category": "Healthcare",
    "version": "19.0.10.0.0",
    "license": "LGPL-3",
    "depends": [
        "base",
        "contacts",
        "product",
        "account",
        "mail",
        "calendar",
        "stock",
        "purchase",
    ],
    "data": [
        "security/clinic_groups.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/clinic_cron.xml",
        "views/clinic_catalog_views.xml",
        "views/clinic_appointment_views.xml",
        "views/clinic_planning_views.xml",
        "views/res_partner_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "clinic_patient_card/static/src/clinic_arrived_service.js",
            "clinic_patient_card/static/src/planning/clinic_planning.scss",
            "clinic_patient_card/static/src/planning/clinic_planning.js",
            "clinic_patient_card/static/src/planning/clinic_planning.xml",
        ],
    },
    "installable": True,
    "application": False,
    "post_init_hook": "_post_init_grant_admin",
}
