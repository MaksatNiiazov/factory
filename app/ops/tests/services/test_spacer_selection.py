from django.test import TestCase
import django

# django.setup()

from catalog.models import SSGCatalog
from ops.services.spacer_selection import SpacerSelectionAvailableOptions


class SpacerSelectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SSGCatalog.objects.create(fn=13, l_min=150, l_max=500)
        SSGCatalog.objects.create(fn=13, l_min=440, l_max=750)
        SSGCatalog.objects.create(fn=13, l_min=700, l_max=2500)

    def setUp(self):
        self.project_item = type('obj', (), {
            'selection_params': SpacerSelectionAvailableOptions.get_default_params()
        })()

    def test_load_calculation(self):
        params = self.project_item.selection_params
        params['load_and_move']['load'] = 30
        params['load_and_move']['load_type'] = 'hz'
        params['pipe_options']['spacer_counts'] = 2
        selector = SpacerSelectionAvailableOptions(self.project_item)
        result = selector.get_load()
        # print('calculated load', result)
        self.assertAlmostEqual(result, 10)

    def test_available_counts_vertical(self):
        params = self.project_item.selection_params
        params['pipe_options']['location'] = 'vertical'
        selector = SpacerSelectionAvailableOptions(self.project_item)
        counts = selector.get_available_spacer_counts()
        # print('available counts', counts)
        self.assertEqual(counts, [2])

    def test_get_suitable_entry(self):
        params = self.project_item.selection_params
        params['load_and_move']['load'] = 6
        params['load_and_move']['load_type'] = 'h'
        params['pipe_options']['spacer_counts'] = 1
        params['load_and_move']['installation_length'] = 500
        selector = SpacerSelectionAvailableOptions(self.project_item)
        entry = selector.get_suitable_entry()
        # print('suitable entry', entry.id if entry else None)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.fn, 13)

    def test_example_without_length(self):
        params = self.project_item.selection_params
        params['load_and_move']['load'] = 10
        params['load_and_move']['load_type'] = 'h'
        params['load_and_move']['mounting_length'] = 135
        selector = SpacerSelectionAvailableOptions(self.project_item)
        result = selector.get_available_options()['suitable_entry']
        # print('result without length', result)
        self.assertIsNotNone(result)
        self.assertEqual(result['marking'], 'SSG 0013.0285.1')

    def test_example_with_length(self):
        params = self.project_item.selection_params
        params['load_and_move']['load'] = 10
        params['load_and_move']['load_type'] = 'h'
        params['load_and_move']['installation_length'] = 800
        params['load_and_move']['mounting_length'] = 135
        selector = SpacerSelectionAvailableOptions(self.project_item)
        result = selector.get_available_options()['suitable_entry']
        # print('result with length', result)
        self.assertIsNotNone(result)
        self.assertEqual(result['marking'], 'SSG 0013.0800.2')