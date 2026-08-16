# -*- coding: utf-8 -*-
from . import models


def _post_init_grant_admin(env):
    """Give the main administrator both clinic roles on install.
    Done in a hook because base.user_admin is noupdate, so an XML write to its
    group_ids is skipped.
    """
    admin = env.ref("base.user_admin", raise_if_not_found=False)
    doctor = env.ref("clinic_patient_card.group_clinic_doctor", raise_if_not_found=False)
    manager = env.ref("clinic_patient_card.group_clinic_admin", raise_if_not_found=False)
    if admin and doctor and manager:
        admin.write({"group_ids": [(4, doctor.id), (4, manager.id)]})
