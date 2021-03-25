# -*- coding: utf-8 -*-
class RawSQL:
    """
    Record the Raw SQL for operate the database directly.
    """

    # Following SQL use for count case and run in plan
    num_cases = (
        "SELECT COUNT(*) FROM test_case_plans WHERE test_case_plans.plan_id = test_plans.plan_id"
    )

    num_runs = "SELECT COUNT(*) FROM test_runs WHERE test_runs.plan_id = test_plans.plan_id"

    num_child_plans = (
        "SELECT COUNT(*) "
        "FROM test_plans AS ch_plans "
        "WHERE ch_plans.parent_id = test_plans.plan_id"
    )

    num_case_issues = (
        "SELECT COUNT(*) FROM issue_tracker_issues "
        "WHERE issue_tracker_issues.case_id = test_cases.case_id"
    )

    num_case_run_issues = (
        "SELECT COUNT(*) FROM issue_tracker_issues "
        "WHERE issue_tracker_issues.case_run_id = test_case_runs.case_run_id"
    )

    # Following SQL use for test case run
    completed_case_run_percent = """\
SELECT ROUND(no_idle_count / total_count * 100, 0)
FROM
    (
    SELECT tr1.run_id AS run_id, count(tcr1.case_run_id) AS no_idle_count
    FROM test_runs tr1
    LEFT JOIN test_case_runs tcr1 ON tr1.run_id = tcr1.run_id
    WHERE tcr1.case_run_status_id NOT IN (1, 4, 5, 6)
    GROUP BY tr1.run_id
    ORDER BY tr1.run_id
) AS table1,
    (
    SELECT tr2.run_id AS run_id, count(tcr2.case_run_id) AS total_count
    FROM test_runs tr2
    LEFT JOIN test_case_runs tcr2 ON tr2.run_id = tcr2.run_id
    GROUP BY tr2.run_id ORDER BY tr2.run_id
) AS table2
WHERE table1.run_id = table2.run_id AND table1.run_id = test_runs.run_id
"""

    total_num_caseruns = (
        "SELECT COUNT(*) FROM test_case_runs WHERE test_case_runs.run_id = test_runs.run_id"
    )

    failed_case_run_percent = """\
SELECT ROUND(no_idle_count / total_count * 100, 0)
FROM
    (
    SELECT tr1.run_id AS run_id, count(tcr1.case_run_id) AS no_idle_count
    FROM test_runs tr1
    LEFT JOIN test_case_runs tcr1 ON tr1.run_id = tcr1.run_id
    WHERE tcr1.case_run_status_id = 3
    GROUP BY tr1.run_id ORDER BY tr1.run_id
) AS table1,
    (
    SELECT tr2.run_id AS run_id, count(tcr2.case_run_id) AS total_count
    FROM test_runs tr2
    LEFT JOIN test_case_runs tcr2 ON tr2.run_id = tcr2.run_id
    GROUP BY tr2.run_id
    ORDER BY tr2.run_id
) AS table2
WHERE table1.run_id = table2.run_id AND table1.run_id = test_runs.run_id
"""

    passed_case_run_percent = """\
SELECT ROUND(no_idle_count / total_count * 100, 0)
FROM (
    SELECT tr1.run_id AS run_id, count(tcr1.case_run_id) AS no_idle_count
    FROM test_runs tr1
    LEFT JOIN test_case_runs tcr1 ON tr1.run_id = tcr1.run_id
    WHERE tcr1.case_run_status_id = 2
    GROUP BY tr1.run_id
    ORDER BY tr1.run_id
) AS table1,
    (
    SELECT tr2.run_id AS run_id, count(tcr2.case_run_id) AS total_count
    FROM test_runs tr2
    LEFT JOIN test_case_runs tcr2 ON tr2.run_id = tcr2.run_id
    GROUP BY tr2.run_id
    ORDER BY tr2.run_id
) AS table2
WHERE table1.run_id = table2.run_id AND table1.run_id = test_runs.run_id
"""

    total_num_review_cases = (
        "SELECT COUNT(*) FROM tcms_review_cases "
        "WHERE tcms_reviews.id = tcms_review_cases.review_id"
    )
