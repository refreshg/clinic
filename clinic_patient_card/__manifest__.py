# -*- coding: utf-8 -*-
{
    "name": "Clinic Patient Card",
    "summary": "Patient card on the contact form (dental clinic)",
    "description": """
Clinic Patient Card
===================
Extends the Contact (res.partner) form with a full patient card:
basic info, contacts, medical & dental history, financials, documents,
patient analytics, timeline and quick actions.

Built incrementally, phase by phase.
""",
    "author": "refreshg",
    "website": "https://github.com/refreshg/clinic",
    "category": "Healthcare",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": [
        "base",
        "contacts",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
