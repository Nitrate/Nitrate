TC_PRINTABLE_CASE_TEXTS = """
SELECT t1.case_id,
       t1.summary,
       t2.setup,
       t2.action,
       t2.effect,
       t2.breakdown
FROM   test_cases t1
       INNER JOIN test_case_texts t2
               ON ( t1.case_id = t2.case_id )
       INNER JOIN (SELECT t4.case_id,
                          Max(t4.case_text_version) AS max_version
                   FROM   test_case_texts t4
                   WHERE  t4.case_id IN ( %s )
                   GROUP  BY t4.case_id) t3
               ON ( t2.case_id = t3.case_id
                    AND t2.case_text_version = t3.max_version )
WHERE  t2.case_id IN ( %s )
"""

# Get each case' latest text, cases are filtered by case ID.
TC_EXPORT_ALL_CASE_TEXTS = """
SELECT t2.id, t1.case_id, t2.setup, t2.action, t2.effect, t2.breakdown
FROM test_cases AS t1
INNER JOIN test_case_texts t2 ON (t1.case_id = t2.case_id)
INNER JOIN (
    SELECT t4.case_id, Max(t4.case_text_version) AS max_version
    FROM test_case_texts AS t4
    WHERE t4.case_id IN ({})
    GROUP BY t4.case_id
) AS t3
ON t2.case_id = t3.case_id AND t2.case_text_version = t3.max_version
"""

# Get each case' latest text, cases are filtered by plan.
CASES_TEXT_BY_PLANS = """
SELECT t2.id, t1.case_id, t2.setup, t2.action, t2.effect, t2.breakdown
FROM test_cases AS t1
INNER JOIN test_case_texts t2 ON (t1.case_id = t2.case_id)
INNER JOIN (
    SELECT t4.case_id, Max(t4.case_text_version) AS max_version
    FROM test_case_texts AS t4
    INNER JOIN test_cases ON (t4.case_id = test_cases.case_id)
    INNER JOIN test_case_plans ON (test_cases.case_id = test_case_plans.case_id)
    WHERE test_case_plans.plan_id IN ({})
    GROUP BY t4.case_id
) AS t3
ON t2.case_id = t3.case_id AND t2.case_text_version = t3.max_version
"""

GET_TAGS_FROM_CASES_FROM_PLAN = """
SELECT DISTINCT test_tags.tag_id, test_tags.tag_name
FROM test_tags
INNER JOIN test_case_tags ON (test_tags.tag_id = test_case_tags.tag_id)
INNER JOIN test_cases ON (test_case_tags.case_id = test_cases.case_id)
INNER JOIN test_case_plans ON (test_cases.case_id = test_case_plans.case_id)
WHERE test_cases.case_id IN ({0}) AND test_case_plans.plan_id = %s
"""

GET_TAGS_FROM_CASES = """
SELECT DISTINCT test_tags.tag_id, test_tags.tag_name
FROM test_tags
INNER JOIN test_case_tags ON (test_tags.tag_id = test_case_tags.tag_id)
INNER JOIN test_cases ON (test_case_tags.case_id = test_cases.case_id)
WHERE test_cases.case_id IN ({0})
"""
