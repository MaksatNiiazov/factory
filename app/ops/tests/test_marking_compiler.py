from django.test import SimpleTestCase
from jinja2 import Environment, StrictUndefined

from ops.marking_compiler import normalize_designation, preprocess_template


class NormalizeDesignationTests(SimpleTestCase):
    def test_normalization_variants(self):
        cases = [
            ("HDH", "normalized_hdh"),
            ("HDH-12", "normalized_hdh_12"),
            ("HDH (тип 1)", "normalized_hdh_tip_1"),
            ("  123  ", "normalized__123"),
            ("ZOM__!!__22", "normalized_zom_22"),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_designation(raw), expected)


class PreprocessTemplateTests(SimpleTestCase):
    BASE_CASES = [
        ("{{ <HDH>.E + 5 }}",
         "{{ normalized_hdh.E + 5 }}",
         {"normalized_hdh": "HDH"}),

        ("{{ <HDH-12>.E + 5 }}",
         "{{ normalized_hdh_12.E + 5 }}",
         {"normalized_hdh_12": "HDH-12"}),

        ("{{ <HDH (тип 1)>.E + 5 }}",
         "{{ normalized_hdh_tip_1.E + 5 }}",
         {"normalized_hdh_tip_1": "HDH (тип 1)"}),

        ("{% if 5 < <HDH (тип 1)>.E < 10 %}OK{% endif %}",
         "{% if 5 < normalized_hdh_tip_1.E < 10 %}OK{% endif %}",
         {"normalized_hdh_tip_1": "HDH (тип 1)"}),

        ("{{ 5 < <HDR-22>.s }}",
         "{{ 5 < normalized_hdr_22.s }}",
         {"normalized_hdr_22": "HDR-22"}),

        ("<div>Вес:</div> {{ <ZOM-1>.m }}",
         "<div>Вес:</div> {{ normalized_zom_1.m }}",
         {"normalized_zom_1": "ZOM-1"}),

        ("{% if 5 <<HDH (тип 1)>.E> 10 %}OK{% endif %}",
         "{% if 5 <normalized_hdh_tip_1.E> 10 %}OK{% endif %}",
         {"normalized_hdh_tip_1": "HDH (тип 1)"}),
    ]

    def test_preprocess_cases(self):
        for src, expected_tpl, expected_map in self.BASE_CASES:
            with self.subTest(src=src):
                patched, mapping = preprocess_template(src)
                self.assertEqual(patched, expected_tpl)
                self.assertEqual(mapping, expected_map)


class RenderSmokeTest(SimpleTestCase):
    def test_rendering_works(self):
        raw_tpl = "{{ 5 * <HDH-12>.e }}"
        patched_tpl, _ = preprocess_template(raw_tpl)
        template = Environment(undefined=StrictUndefined).from_string(patched_tpl)

        ctx = {"normalized_hdh_12": {"e": 2}}
        self.assertEqual(template.render(**ctx), "10")
