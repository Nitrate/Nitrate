# -*- coding: utf-8 -*-

import logging
import warnings
from typing import Dict

from tcms.core.task import Task

logger = logging.getLogger(__name__)


@Task
def bugzilla_external_track(
    tracker_api_url: str,
    tracker_credential: Dict[str, str],
    issue_key: str,
    case_id: int,
):
    """Link issue to a bug's external tracker"""
    try:
        import bugzilla
    except ModuleNotFoundError:
        logger.error("python-bugzilla is not installed. Skip adding external link to a bug.")
        return
    try:
        bz = bugzilla.Bugzilla(
            tracker_api_url,
            user=tracker_credential["username"],
            password=tracker_credential["password"],
        )
        bz.add_external_tracker(
            int(issue_key),
            case_id,
            # Note that, this description should be updated if it is changed in
            # remote Bugzilla service.
            ext_type_description="Nitrate Test Case",
        )
    except Exception as e:
        warnings.warn(f"{e.__class__.__name__}: {e}")
