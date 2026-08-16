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
    "version": "19.0.5.0.0",
    "license": "LGPL-3",
    "depends": [
        "base",
        "contacts",
        "product",
        "account",
        "mail",
        "calendar",
    ],
    "data": [
        "security/clinic_groups.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "views/clinic_catalog_views.xml",
        "views/clinic_appointment_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
    "post_init_hook": "_post_init_grant_admin",
}
