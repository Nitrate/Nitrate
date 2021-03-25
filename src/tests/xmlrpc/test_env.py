# -*- coding: utf-8 -*-

from tcms.xmlrpc.api import env
from tests import factories as f
from tests.xmlrpc.utils import XmlrpcAPIBaseTest


class TestFilterGroups(XmlrpcAPIBaseTest):
    """Test filter_groups"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.grp_1 = f.TCMSEnvGroupFactory(name="group1", is_active=False)
        cls.grp_2 = f.TCMSEnvGroupFactory(name="group2", is_active=False)
        cls.grp_3 = f.TCMSEnvGroupFactory(name="group3")

    @staticmethod
    def serialize_env_group(env_group):
        return {
            "id": env_group.pk,
            "name": env_group.name,
            "is_active": env_group.is_active,
            "manager_id": env_group.manager.pk,
            "manager": env_group.manager.username,
            "modified_by_id": env_group.modified_by.pk,
            "modified_by": env_group.modified_by.username,
            "property": [],
        }

    def test_filter_groups(self):
        result = env.filter_groups(self.request, {"is_active": 0, "name": "group2"})
        self.assertEqual([self.serialize_env_group(self.grp_2)], result)

    def test_get_all_groups(self):
        groups = sorted(env.filter_groups(self.request, {}), key=lambda item: item["id"])
        self.assertListEqual(
            [
                self.serialize_env_group(self.grp_1),
                self.serialize_env_group(self.grp_2),
                self.serialize_env_group(self.grp_3),
            ],
            groups,
        )


class TestPropertiesOperations(XmlrpcAPIBaseTest):
    """Test filter_properties"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.property_1 = f.TCMSEnvPropertyFactory(name="property1")
        cls.property_2 = f.TCMSEnvPropertyFactory(name="property2")
        cls.property_3 = f.TCMSEnvPropertyFactory(name="property3", is_active=False)
        cls.grp_1 = f.TCMSEnvGroupFactory(
            name="group1", property=[cls.property_1, cls.property_2, cls.property_3]
        )

        cls.property_4 = f.TCMSEnvPropertyFactory(name="property4", is_active=False)
        cls.property_5 = f.TCMSEnvPropertyFactory(name="property5")
        cls.grp_2 = f.TCMSEnvGroupFactory(name="group2", property=[cls.property_4, cls.property_5])

    @staticmethod
    def serialize_property(eg_property):
        return {
            "id": eg_property.pk,
            "name": eg_property.name,
            "is_active": eg_property.is_active,
        }

    def test_filter_properties(self):
        result = env.filter_properties(
            self.request,
            {
                "is_active": False,
                "name": "property4",
            },
        )
        self.assertEqual([self.serialize_property(self.property_4)], result)

    def test_get_all_properties(self):
        result = sorted(env.filter_properties(self.request, {}), key=lambda item: item["id"])
        expected_properties = [
            self.serialize_property(self.property_1),
            self.serialize_property(self.property_2),
            self.serialize_property(self.property_3),
            self.serialize_property(self.property_4),
            self.serialize_property(self.property_5),
        ]
        self.assertListEqual(expected_properties, result)

    def test_get_property_by_group_id(self):
        result = sorted(
            env.get_properties(self.request, self.grp_1.pk), key=lambda item: item["id"]
        )
        expected = [
            self.serialize_property(self.property_1),
            self.serialize_property(self.property_2),
        ]
        self.assertListEqual(expected, result)

    def test_get_property_by_active_status(self):
        result = env.get_properties(self.request, self.grp_1.pk, is_active=False)
        expected = [self.serialize_property(self.property_3)]
        self.assertListEqual(expected, result)

    def test_get_active_properties_by_default(self):
        result = sorted(env.get_properties(self.request), key=lambda item: item["id"])
        expected = [
            self.serialize_property(self.property_1),
            self.serialize_property(self.property_2),
            self.serialize_property(self.property_5),
        ]
        self.assertListEqual(expected, result)


class TestValuesOperations(XmlrpcAPIBaseTest):
    """Test filter_values"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.property_1 = f.TCMSEnvPropertyFactory(name="property1")
        cls.value_1 = f.TCMSEnvValueFactory(
            value="value1", is_active=False, property=cls.property_1
        )
        cls.value_2 = f.TCMSEnvValueFactory(value="value2", property=cls.property_1)

        cls.property_2 = f.TCMSEnvPropertyFactory(name="property2")
        cls.value_3 = f.TCMSEnvValueFactory(value="value3", property=cls.property_2)
        cls.value_4 = f.TCMSEnvValueFactory(
            value="value4", is_active=False, property=cls.property_2
        )
        cls.value_5 = f.TCMSEnvValueFactory(value="value5", property=cls.property_2)

    @staticmethod
    def serialize_value(property_value):
        return {
            "id": property_value.pk,
            "value": property_value.value,
            "is_active": property_value.is_active,
            "property_id": property_value.property.pk,
            "property": property_value.property.name,
        }

    def test_filter_values(self):
        values = env.filter_values(
            self.request,
            {
                "is_active": False,
                "value": "value4",
                "property__pk": self.property_2.pk,
            },
        )
        self.assertListEqual([self.serialize_value(self.value_4)], values)

    def test_get_all_values(self):
        values = sorted(env.filter_values(self.request, {}), key=lambda item: item["id"])
        expected = [
            self.serialize_value(self.value_1),
            self.serialize_value(self.value_2),
            self.serialize_value(self.value_3),
            self.serialize_value(self.value_4),
            self.serialize_value(self.value_5),
        ]
        self.assertListEqual(expected, values)

    def test_active_values_by_default(self):
        result = sorted(env.get_values(self.request), key=lambda item: item["id"])
        expected = [
            self.serialize_value(self.value_2),
            self.serialize_value(self.value_3),
            self.serialize_value(self.value_5),
        ]
        self.assertListEqual(expected, result)

    def test_get_values_by_property_id(self):
        result = sorted(
            env.get_values(self.request, self.property_1.pk),
            key=lambda item: item["id"],
        )
        expected = [self.serialize_value(self.value_2)]
        self.assertListEqual(expected, result)

    def test_get_values_by_active_status(self):
        result = sorted(env.get_values(self.request, is_active=False), key=lambda item: item["id"])
        expected = [
            self.serialize_value(self.value_1),
            self.serialize_value(self.value_4),
        ]
        self.assertListEqual(expected, result)
