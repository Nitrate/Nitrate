from typing import Dict

from tcms.testcases.models import TestCase


def assert_new_case(new_case: TestCase, expected: Dict) -> None:
    assert expected["summary"] == new_case.summary
    assert expected["is_automated"] == new_case.is_automated
    assert expected["is_automated_proposed"] == new_case.is_automated_proposed
    assert expected["script"] == new_case.script
    assert expected["arguments"] == new_case.arguments
    assert expected["extra_link"] == new_case.extra_link
    assert expected["notes"] == new_case.notes
    assert expected["default_tester"] == new_case.default_tester
    assert expected["estimated_time"] == new_case.estimated_time
    assert expected["category"] == new_case.category
    assert expected["priority"] == new_case.priority
    assert expected["case_status"] == new_case.case_status
    assert set(expected["tag"]) == set(new_case.tag.all())
    assert sorted(item.pk for item in expected["component"]) == sorted(
        item.pk for item in new_case.component.all()
    )

    if all(item in expected for item in ["action", "effect", "setup", "breakdown"]):
        text = new_case.latest_text()
        assert expected["action"] == text.action
        assert expected["effect"] == text.effect
        assert expected["setup"] == text.setup
        assert expected["breakdown"] == text.breakdown
