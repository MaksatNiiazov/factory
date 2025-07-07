from unittest.mock import MagicMock
from django.test import TestCase

from ops.choices import AttributeType
from ops.exceptions import TopologicalSortException
from ops.models import Attribute, FieldSet, Item, Variant, DetailType
from ops.utils import extract_dependencies, topological_sort


class TopoSortTestCase(TestCase):
    def test_extract_dependencies_with_children_and_filters(self):
        expr1 = "d + d + d + <assembly_unit_SSB>.Sn"
        deps1 = extract_dependencies(expr1)
        self.assertEqual(deps1, {"d"}, msg=deps1)

        expr2 = "d + a + b|to_int + <detail_unit_HDH>.d"
        deps2 = extract_dependencies(expr2)
        self.assertEqual(deps2, {"d", "a", "b"}, msg=deps2)

        expr3 = "{{ X - W }}"
        deps3 = extract_dependencies(expr3)
        self.assertEqual(deps3, {"X", "W"}, msg=deps3)

        expr4 = "VariantN.m"
        deps4 = extract_dependencies(expr4)
        self.assertEqual(deps4, set(), msg=deps4)

        expr5 = "<assembly_unit_FSS 1-11>.s2"
        deps5 = extract_dependencies(expr5)
        self.assertEqual(deps5, set(), msg=deps5)

        expr6 = "<detail_ZOM>.E"
        deps6 = extract_dependencies(expr6)
        self.assertEqual(deps6, set(), msg=deps6)

        expr7 = "<detail_HDH>.m * 2"
        deps7 = extract_dependencies(expr7)
        self.assertEqual(deps7, set(), msg=deps7)

        expr8 = "( <detail_ZZF>.B - <detail_PIP>.OD ) / 2"
        deps8 = extract_dependencies(expr8)
        self.assertEqual(deps8, set(), msg=deps8)

        expr9 = "text_base + lgv + text_base"
        deps9 = extract_dependencies(expr9)
        self.assertEqual(deps9, {"text_base", "lgv"}, msg=deps9)

        expr10 = "A * B * s * 0.000075"
        deps10 = extract_dependencies(expr10)
        self.assertEqual(deps10, {"A", "B", "s"}, msg=deps10)

    def test_topological_sort(self):
        expr1 = "d + d + d + <assembly_unit_SSB>.Sn"
        attribute1 = Attribute(name="E", calculated_value=expr1)
        attribute2 = Attribute(name="d", calculated_value="a + 1")
        attribute3 = Attribute(name="a")
        attributes = [attribute1, attribute2, attribute3]
        sorted_attrs = topological_sort(attributes)
        self.assertEqual(
            sorted_attrs, [attribute3, attribute2, attribute1], msg=sorted_attrs
        )

    def test_topological_sort_2(self):
        attribute_e = Attribute(name="E", calculated_value="d + <assembly_unit_SSB>.x")
        attribute_d = Attribute(name="d", calculated_value="a + b|to_int")
        attribute_b = Attribute(name="b", calculated_value="c + 1")
        attribute_a = Attribute(name="a")
        attribute_c = Attribute(name="c")

        attributes = [attribute_e, attribute_d, attribute_b, attribute_a, attribute_c]

        sorted_attrs = topological_sort(attributes)
        sorted_names = [attr.name for attr in sorted_attrs]

        self.assertEqual(sorted_names, ["a", "c", "b", "d", "E"], msg=sorted_names)

    def test_topological_sort_with_cycle(self):
        attribute_a = Attribute(name="A", calculated_value="B + 1")
        attribute_b = Attribute(name="B", calculated_value="C + 1")
        attribute_c = Attribute(name="C", calculated_value="A + 1")

        attributes = [attribute_a, attribute_b, attribute_c]

        with self.assertRaises(TopologicalSortException) as context:
            topological_sort(attributes)

        exc = context.exception
        self.assertIn("Циклическая зависимость", str(exc))
        self.assertTrue(set(exc.fields) == {"A", "B", "C"})

    def test_topological_sort_with_cycle_and_children_ignored(self):
        attribute_a = Attribute(name="a", calculated_value="b + <assembly_unit_SBS>.x")
        attribute_b = Attribute(name="b", calculated_value="c + <assembly_unit_HDH>.m")
        attribute_c = Attribute(name="c", calculated_value="a + <detail_ZOM>.p")

        attributes = [attribute_a, attribute_b, attribute_c]

        with self.assertRaises(TopologicalSortException) as context:
            topological_sort(attributes)

        exc = context.exception
        self.assertIn("Циклическая зависимость", str(exc))
        self.assertTrue(set(exc.fields) == {"a", "b", "c"})

    def test_clean_sets_parameters_to_none_on_cycle(self):
        detail_type = DetailType.objects.create()
        variant = Variant.objects.create(detail_type=detail_type)
        field_set = FieldSet.objects.create(name="Main")

        attr_a = Attribute.objects.create(
            name="a",
            calculated_value="b + 1",
            variant=variant,
            fieldset=field_set,
            position=1,
        )
        attr_b = Attribute.objects.create(
            name="b",
            calculated_value="c + 1",
            variant=variant,
            fieldset=field_set,
            position=2,
        )
        attr_c = Attribute.objects.create(
            name="c",
            calculated_value="a + 1",
            variant=variant,
            fieldset=field_set,
            position=3,
        )

        item = Item(type=detail_type, variant=variant)
        item.clean()

        assert item.parameters == {"a": None, "b": None, "c": None}
        assert item.parameters_errors is not None
        assert set(item.parameters_errors.keys()) == {"a", "b", "c"}
        for msg in item.parameters_errors.values():
            assert "Циклическая зависимость" in msg

    def test_clean_preserves_valid_parameters_and_nulls_cyclic_ones(self):
        detail_type = DetailType.objects.create()
        variant = Variant.objects.create(detail_type=detail_type)
        field_set = FieldSet.objects.create(name="Main")

        attr_a = Attribute.objects.create(
            name="a",
            calculated_value="b + 1",
            variant=variant,
            fieldset=field_set,
            position=1,
        )
        attr_b = Attribute.objects.create(
            name="b",
            calculated_value="c + 1",
            variant=variant,
            fieldset=field_set,
            position=2,
        )
        attr_c = Attribute.objects.create(
            name="c",
            calculated_value="a + 1",
            variant=variant,
            fieldset=field_set,
            position=3,
        )

        item = Item(type=detail_type, variant=variant)
        item.parameters = {
            "a": 10,
            "b": 20,
            "c": 30,
            "x": 999,
        }
        item.clean()

        assert item.parameters["x"] == 999
        assert item.parameters["a"] is None
        assert item.parameters["b"] is None
        assert item.parameters["c"] is None
        assert item.parameters_errors is not None
        assert set(item.parameters_errors.keys()) == {"a", "b", "c"}
        for msg in item.parameters_errors.values():
            assert "Циклическая зависимость" in msg

    def test_clean_computes_E_with_external_reference_ignored(self):
        detail_type = DetailType.objects.create()
        variant = Variant.objects.create(detail_type=detail_type)
        field_set = FieldSet.objects.create(name="Main")

        attr_e = Attribute.objects.create(
            name="E",
            type=AttributeType.NUMBER,
            calculated_value="d + 5",
            variant=variant,
            fieldset=field_set,
            position=1,
        )
        attr_d = Attribute.objects.create(
            name="d",
            type=AttributeType.NUMBER,
            calculated_value="a * 2",
            variant=variant,
            fieldset=field_set,
            position=2,
        )
        attr_a = Attribute.objects.create(
            name="a",
            type=AttributeType.NUMBER,
            variant=variant,
            fieldset=field_set,
            position=3,
        )

        item = Item(type=detail_type, variant=variant)
        item.parameters = {
            "a": 2
        }

        item.clean()

        assert item.parameters["d"] == 4
        assert item.parameters["E"] == 9
        assert item.parameters_errors is None
