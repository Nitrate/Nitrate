# -*- coding: utf-8 -*-

from collections import namedtuple

SQLStatement = namedtuple("SQLStatement", "sql_template, default_joins, default_where")

### SQL for custom report ###


custom_builds = SQLStatement(
    sql_template="""
SELECT DISTINCT test_builds.build_id, test_builds.name
FROM test_builds
%(joins)s
WHERE %(where)s""",
    default_joins=(),
    default_where=(),
)

custom_builds_runs_subtotal = SQLStatement(
    sql_template="""
SELECT test_builds.build_id, COUNT(DISTINCT test_runs.run_id) AS total_count
FROM test_builds
%(joins)s
WHERE %(where)s
GROUP BY test_builds.build_id""",
    default_joins=("INNER JOIN test_runs ON (test_builds.build_id = test_runs.build_id)",),
    default_where=(),
)


custom_builds_plans_subtotal = SQLStatement(
    sql_template="""
SELECT test_builds.build_id, COUNT(DISTINCT test_runs.plan_id) AS total_count
FROM test_builds
%(joins)s
WHERE %(where)s
GROUP BY test_builds.build_id""",
    default_joins=("INNER JOIN test_runs ON (test_builds.build_id = test_runs.build_id)",),
    default_where=(),
)


custom_builds_cases_isautomated_subtotal = SQLStatement(
    sql_template="""
SELECT test_cases.isautomated, COUNT(DISTINCT test_cases.case_id) AS total_count
FROM test_builds
%(joins)s
WHERE %(where)s
GROUP BY test_cases.isautomated""",
    default_joins=(
        "INNER JOIN test_runs ON (test_builds.build_id = test_runs.build_id)",
        "INNER JOIN test_case_runs ON (test_runs.run_id = test_case_runs.run_id)",
        "INNER JOIN test_cases ON (test_case_runs.case_id = test_cases.case_id)",
    ),
    default_where=(),
)


# Percentage of passed and failed case runs
custom_builds_case_runs_subtotal_by_status = SQLStatement(
    sql_template="""
SELECT test_builds.build_id, test_case_runs.case_run_status_id,
    COUNT(DISTINCT test_case_runs.case_run_id) AS total_count
FROM test_builds
%(joins)s
WHERE %(where)s
GROUP BY test_builds.build_id, test_case_runs.case_run_status_id""",
    default_joins=(
        "INNER JOIN test_runs ON (test_builds.build_id = test_runs.build_id)",
        "INNER JOIN test_case_runs ON (test_runs.run_id = test_case_runs.run_id)",
    ),
    default_where=("test_case_runs.case_run_status_id IN (2, 3)",),
)


custom_builds_case_runs_subtotal = SQLStatement(
    sql_template="""
SELECT test_builds.build_id, COUNT(DISTINCT test_case_runs.case_run_id) AS total_count
FROM test_builds
%(joins)s
WHERE %(where)s
GROUP BY test_builds.build_id""",
    default_joins=(
        "INNER JOIN test_runs ON (test_builds.build_id = test_runs.build_id)",
        "INNER JOIN test_case_runs ON (test_runs.run_id = test_case_runs.run_id)",
    ),
    default_where=(),
)


#### Testing report #######

testing_report_plans_total = """
select count(distinct test_plans.plan_id) as total_count
from test_runs
inner join test_plans on (test_runs.plan_id = test_plans.plan_id)
inner join test_builds on (test_runs.build_id = test_builds.build_id)
where {0}"""

testing_report_runs_total = """
SELECT COUNT(*) AS total_count
FROM test_builds
INNER JOIN test_runs ON (test_builds.build_id = test_runs.build_id)
WHERE {0}"""

testing_report_case_runs_total = """
SELECT COUNT(*) AS total_count
FROM test_builds
INNER JOIN test_runs ON (test_runs.build_id = test_builds.build_id)
INNER JOIN test_case_runs ON (test_case_runs.run_id = test_runs.run_id)
WHERE {0}
"""

testing_report_runs_subtotal = """
select test_runs.build_id, count(*) as total_count
from test_runs
inner join test_builds on (test_runs.build_id = test_builds.build_id)
where {0}
group by test_runs.build_id"""

# SQLs for report "By Case-Run Tester"

### Report data group by builds ###

by_case_run_tester_status_matrix_groupby_build = """
select test_builds.build_id, test_case_runs.tested_by_id, test_case_run_status.name, count(*) as total_count
from test_builds
inner join test_runs on (test_builds.build_id = test_runs.build_id)
inner join test_case_runs on (test_runs.run_id = test_case_runs.run_id)
inner join test_case_run_status on (test_case_run_status.case_run_status_id = test_case_runs.case_run_status_id)
where {0}
group by test_builds.build_id, test_case_runs.tested_by_id, test_case_run_status.name
order by test_builds.build_id, test_case_runs.tested_by_id, test_case_run_status.name
"""

by_case_run_tester_runs_subtotal_groupby_build = """
select build_id, tested_by_id, count(*) as total_count
from (
    select test_builds.build_id, test_case_runs.tested_by_id, test_case_runs.run_id
    from test_builds
    inner join test_runs on (test_builds.build_id = test_runs.build_id)
    inner join test_case_runs on (test_runs.run_id = test_case_runs.run_id)
    where {0}
    group by test_builds.build_id, test_case_runs.tested_by_id, test_case_runs.run_id
) as t1
group by build_id, tested_by_id"""

### Report data WITHOUT selecting builds ###

by_case_run_tester_status_matrix = """
select test_case_runs.tested_by_id, test_case_run_status.name, count(*) as total_count
from test_builds
inner join test_runs on (test_builds.build_id = test_runs.build_id)
inner join test_case_runs on (test_runs.run_id = test_case_runs.run_id)
inner join test_case_run_status on (test_case_run_status.case_run_status_id = test_case_runs.case_run_status_id)
where {0}
group by test_case_runs.tested_by_id, test_case_run_status.name
order by test_case_runs.tested_by_id, test_case_run_status.name
"""

by_case_run_tester_runs_subtotal = """
select tested_by_id, count(*) as total_count
from (
    select test_case_runs.tested_by_id, test_case_runs.run_id
    from test_builds
    inner join test_runs on (test_builds.build_id = test_runs.build_id)
    inner join test_case_runs on (test_runs.run_id = test_case_runs.run_id)
    where {0}
    group by test_case_runs.tested_by_id, test_case_runs.run_id
) as t1
group by tested_by_id"""

### Report data By Case Priority ###

by_case_priority_subtotal = """
select
    test_builds.build_id,
    priority.id as priority_id, priority.value as priority_value,
    test_case_run_status.name, count(*) as total_count
from test_builds
inner join test_runs on (test_builds.build_id = test_runs.build_id)
inner join test_case_runs on (test_runs.run_id = test_case_runs.run_id)
inner join test_cases on (test_case_runs.case_id = test_cases.case_id)
inner join test_case_run_status on (
    test_case_runs.case_run_status_id = test_case_run_status.case_run_status_id)
inner join priority on (test_cases.priority_id = priority.id)
where {0}
group by test_builds.build_id, priority.id, test_case_run_status.name"""

### Report data By Plan Tags ###

by_plan_tags_plans_subtotal = """
select test_plan_tags.tag_id, count(distinct test_plans.plan_id) as total_count
from test_builds
inner join test_runs on (test_builds.build_id = test_runs.build_id)
inner join test_plans on (test_runs.plan_id = test_plans.plan_id)
left join test_plan_tags on (test_plans.plan_id = test_plan_tags.plan_id)
where {0}
group by test_plan_tags.tag_id"""

by_plan_tags_runs_subtotal = """
select test_plan_tags.tag_id, count(distinct test_runs.run_id) as total_count
from test_builds
inner join test_runs on (test_builds.build_id = test_runs.build_id)
inner join test_plans on (test_runs.plan_id = test_plans.plan_id)
left join test_plan_tags on (test_plans.plan_id = test_plan_tags.plan_id)
where {0}
group by test_plan_tags.tag_id"""

by_plan_tags_passed_failed_case_runs_subtotal = """
select test_plan_tags.tag_id, test_case_run_status.name, count(distinct test_case_runs.case_run_id) as total_count
from test_plans
inner join test_runs on (test_plans.plan_id = test_runs.plan_id)
inner join test_case_runs on (test_runs.run_id = test_case_runs.run_id)
inner join test_case_run_status on (test_case_run_status.case_run_status_id = test_case_runs.case_run_status_id)
inner join test_builds on (test_builds.build_id = test_runs.build_id)
left join test_plan_tags on (test_plans.plan_id = test_plan_tags.plan_id)
where test_case_run_status.name in ('PASSED', 'FAILED') and {0}
group by test_plan_tags.tag_id, test_case_run_status.name
order by test_plan_tags.tag_id, test_case_run_status.name
"""

### Report data of details of By Plan Tags ###

by_plan_tags_detail_status_matrix = """
select
    test_plan_tags.tag_id,
    test_builds.build_id, test_builds.name as build_name,
    test_plans.plan_id, test_plans.name as plan_name,
    test_runs.run_id, test_runs.summary,
    test_case_run_status.name as status_name, count(*) as total_count
from test_builds
inner join test_runs on (test_builds.build_id = test_runs.build_id)
inner join test_plans on (test_runs.plan_id = test_plans.plan_id)
inner join test_case_runs on (test_runs.run_id = test_case_runs.run_id)
inner join test_case_run_status on (test_case_runs.case_run_status_id = test_case_run_status.case_run_status_id)
left join test_plan_tags on (test_plans.plan_id = test_plan_tags.plan_id)
where {0}
group by test_plan_tags.tag_id, test_builds.build_id, test_plans.plan_id,
         test_runs.run_id, test_case_run_status.name
order by test_plan_tags.tag_id, test_builds.build_id, test_plans.plan_id,
         test_runs.run_id, test_case_run_status.name
"""

### Report data of By Plan Build ###

by_plan_build_builds_subtotal = """
select test_runs.plan_id, count(distinct test_builds.build_id) as total_count
from test_builds
inner join test_runs on (test_runs.build_id = test_builds.build_id)
inner join test_plans on (test_runs.plan_id = test_plans.plan_id)
where {0}
group by test_runs.plan_id"""

by_plan_build_runs_subtotal = """
select test_runs.plan_id, count(distinct test_runs.run_id) as total_count
from test_builds
inner join test_runs on (test_runs.build_id = test_builds.build_id)
inner join test_plans on (test_runs.plan_id = test_plans.plan_id)
where {0}
group by test_runs.plan_id"""

by_plan_build_status_matrix = """
select test_runs.plan_id, test_case_run_status.name,
       count(distinct test_runs.run_id) as total_count
from test_builds
inner join test_runs on (test_runs.build_id = test_builds.build_id)
inner join test_plans on (test_runs.plan_id = test_plans.plan_id)
inner join test_case_runs on (test_case_runs.run_id = test_runs.run_id)
inner join test_case_run_status on (
    test_case_runs.case_run_status_id = test_case_run_status.case_run_status_id)
where test_case_run_status.name in ('PASSED', 'FAILED')  AND {0}
group by test_runs.plan_id, test_case_run_status.name"""

### Report data of By Plan Build detail ###

by_plan_build_detail_status_matrix = """
SELECT test_runs.plan_id,
       test_runs.build_id,
       test_runs.run_id,
       test_case_run_status.name AS status_name,
       COUNT(*) AS total_count
FROM test_builds
INNER JOIN test_runs ON (test_runs.build_id = test_builds.build_id)
INNER JOIN test_plans ON (test_runs.plan_id = test_plans.plan_id)
INNER JOIN test_case_runs ON (test_case_runs.run_id = test_runs.run_id)
INNER JOIN test_case_run_status ON (
    test_case_runs.case_run_status_id = test_case_run_status.case_run_status_id)
WHERE {0}
GROUP BY test_runs.plan_id, test_runs.build_id,
         test_runs.run_id, test_case_run_status.name"""
