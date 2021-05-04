# -*- coding: utf-8 -*-
TP_PRINTABLE_CASE_TEXTS = """
SELECT t3.plan_id,
       test_cases.case_id,
       test_cases.summary,
       test_case_texts.setup,
       test_case_texts.action,
       test_case_texts.effect,
       test_case_texts.breakdown
FROM   test_cases
INNER JOIN test_case_plans ON ( test_case_plans.case_id = test_cases.case_id )
INNER JOIN test_case_texts ON ( test_cases.case_id = test_case_texts.case_id )
INNER JOIN (
    SELECT t5.plan_id, t4.case_id, Max(t4.case_text_version) AS max_version
    FROM test_case_texts t4
    INNER JOIN test_case_plans t5 ON ( t5.case_id = t4.case_id )
    INNER JOIN test_cases t6 ON ( t5.case_id = t6.case_id )
    WHERE t5.plan_id IN (%s) AND t6.case_status_id IN (1,2,4)
    GROUP BY t4.case_id, t5.plan_id
) t3
ON (
    test_case_texts.case_id = t3.case_id
    AND test_case_texts.case_text_version = t3.max_version
    AND test_case_plans.plan_id = t3.plan_id
)
WHERE test_case_plans.plan_id IN (%s)
"""

TP_EXPORT_ALL_CASES_COMPONENTS = """
SELECT test_case_plans.plan_id,
       test_case_components.case_id,
       components.id as component_id,
       components.name as component_name,
       products.name as product_name
FROM components
INNER JOIN test_case_components ON (components.id = test_case_components.component_id)
INNER JOIN products ON (products.id = components.product_id)
INNER JOIN test_case_plans ON (test_case_components.case_id = test_case_plans.case_id)
WHERE test_case_plans.plan_id IN (%s)
"""
