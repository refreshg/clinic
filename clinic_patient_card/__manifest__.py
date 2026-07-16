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
    "version": "19.0.2.0.0",
    "license": "LGPL-3",
    "depends": [
        "base",
        "contacts",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
