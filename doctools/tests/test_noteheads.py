"""Validate notehead constraints against the schema generated from the metaspec.

Run from doctools with: python -m unittest discover -s tests
"""

import copy
import json
import os
from pathlib import Path
import unittest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'docgenerator.settings')

import django
django.setup()

from jsonschema import Draft202012Validator
from spectools.utils.jsonschema import make_json_schema


class NoteheadSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = make_json_schema()
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema)
        path = Path(__file__).resolve().parents[1] / 'media/examples/json/hello-world.json'
        cls.document = json.loads(path.read_text())

    def with_head(self, head, kit=False, duration='quarter'):
        document = copy.deepcopy(self.document)
        part = document['parts'][0]
        event = part['measures'][0]['sequences'][0]['content'][0]
        event['duration']['base'] = duration
        if kit:
            part['kit'] = {'cymbal': {'staffPosition': 4}}
            event.pop('notes')
            event['kitNotes'] = [{'kitComponent': 'cymbal', 'notehead': head}]
        else:
            event['notes'][0]['notehead'] = head
        return document

    def test_shape_families_at_each_displayed_duration(self):
        for kit in (False, True):
            for shape in ('default', 'oval', 'x', 'diamond', 'triangle', 'slash', 'plus', 'circleX', 'square'):
                for duration in ('quarter', 'half', 'whole', 'breve'):
                    with self.subTest(kit=kit, shape=shape, duration=duration):
                        self.validator.validate(self.with_head({'shape': shape}, kit, duration))

    def test_independent_display_controls_and_glyphs(self):
        for kit in (False, True):
            for head in (
                {}, {'parentheses': True}, {'hide': True},
                {'shape': 'diamond', 'parentheses': True, 'hide': False},
                {'shape': 'x', 'glyph': 'noteheadXOrnateEllipse'},
                {'shape': 'custom', 'glyph': 'noteheadBlack'},
            ):
                with self.subTest(kit=kit, head=head):
                    self.validator.validate(self.with_head(head, kit))

    def test_invalid_heads(self):
        for kit in (False, True):
            for head in (
                {'shape': 'custom'}, {'glyph': 'noteheadBlack'},
                {'shape': 'normal'}, {'shape': 'cluster'}, {'shape': 'unknown'},
                {'size': 'cue'}, {'color': '#ff0000'},
                {'hide': 'true'}, {'parentheses': 1}, {'filled': True},
                {'unknown': True},
            ):
                with self.subTest(kit=kit, head=head):
                    self.assertFalse(self.validator.is_valid(self.with_head(head, kit)))

    def test_optional_enum_defaults(self):
        for slug, prop in (
            ('notehead', 'shape'), ('kit-notehead', 'shape'),
            ('notehead', 'durationVariant'), ('kit-notehead', 'durationVariant'),
        ):
            with self.subTest(slug=slug, prop=prop):
                attribute = self.schema['$defs'][slug]['properties'][prop]
                self.assertEqual(attribute['default'], 'default')
                definition = self.schema['$defs'][attribute['$ref'].split('/')[-1]]
                self.assertIn(attribute['default'], definition['enum'])

    def test_kit_component_designs(self):
        for head in (
            {}, {'shape': 'default'}, {'shape': 'oval'}, {'shape': 'x'},
            {'shape': 'triangle', 'pointing': 'down'},
            {'shape': 'x', 'glyph': 'noteheadXOrnateEllipse'},
            {'shape': 'custom', 'glyph': 'noteheadBlack'},
        ):
            document = self.with_head({}, kit=True)
            document['parts'][0]['kit']['cymbal']['notehead'] = head
            for duration in ('quarter', 'half', 'whole', 'breve'):
                event = document['parts'][0]['measures'][0]['sequences'][0]['content'][0]
                event['duration']['base'] = duration
                with self.subTest(head=head, duration=duration):
                    self.validator.validate(document)
        for head in (
            {'hide': False}, {'parentheses': False},
            {'shape': 'custom'}, {'glyph': 'noteheadBlack'},
            {'pointing': 'down'}, {'shape': 'x', 'pointing': 'down'},
            {'shape': 'triangle', 'pointing': 'left'},
            {'shape': 'unknown'}, {'size': 'cue'}, {'color': '#ff0000'},
        ):
            document = self.with_head({}, kit=True)
            document['parts'][0]['kit']['cymbal']['notehead'] = head
            with self.subTest(head=head):
                self.assertFalse(self.validator.is_valid(document))
        pointing = self.schema['$defs']['kit-notehead']['properties']['pointing']
        self.assertEqual(pointing['default'], 'up')

    def test_kit_component_and_per_note_designs(self):
        for component in (
            {'shape': 'x'},
            {'shape': 'triangle', 'pointing': 'down'},
            {'shape': 'custom', 'glyph': 'noteheadXOrnateEllipse'},
        ):
            for override in (
                None, {}, {'shape': 'default'}, {'parentheses': True},
                {'hide': True}, {'shape': 'oval'},
                {'shape': 'triangle'},
                {'shape': 'default', 'glyph': 'noteheadBlack'},
            ):
                document = self.with_head(override, kit=True)
                document['parts'][0]['kit']['cymbal']['notehead'] = component
                if override is None:
                    event = document['parts'][0]['measures'][0]['sequences'][0]['content'][0]
                    event['kitNotes'][0].pop('notehead')
                with self.subTest(component=component, override=override):
                    self.validator.validate(document)
        # A component's glyph does not satisfy the local custom-shape constraint.
        document = self.with_head({'shape': 'custom'}, kit=True)
        document['parts'][0]['kit']['cymbal']['notehead'] = {
            'shape': 'custom', 'glyph': 'noteheadBlack',
        }
        self.assertFalse(self.validator.is_valid(document))

    def test_duration_variants(self):
        for location in ('pitched', 'kit-note', 'kit-component'):
            for variant in ('default', 'closed', 'half', 'whole', 'breve'):
                for duration in ('quarter', 'half', 'whole', 'breve', 'duplexMaxima'):
                    head = {'shape': 'diamond', 'durationVariant': variant}
                    document = self.with_head(
                        head if location != 'kit-component' else {},
                        kit=location != 'pitched', duration=duration)
                    if location == 'kit-component':
                        document['parts'][0]['kit']['cymbal']['notehead'] = head
                    with self.subTest(location=location, variant=variant, duration=duration):
                        self.validator.validate(document)
            for invalid in ('open', 'quarter', 'black', 'white', 'unknown', None, True, 1):
                head = {'durationVariant': invalid}
                document = self.with_head(head, kit=location != 'pitched')
                if location == 'kit-component':
                    event = document['parts'][0]['measures'][0]['sequences'][0]['content'][0]
                    event['kitNotes'][0]['notehead'] = {}
                    document['parts'][0]['kit']['cymbal']['notehead'] = head
                with self.subTest(location=location, invalid=invalid):
                    self.assertFalse(self.validator.is_valid(document))

    def test_duration_variant_with_component_design_and_glyph(self):
        for head in (
            {}, {'shape': 'default', 'durationVariant': 'default'},
            {'durationVariant': 'closed'},
            {'shape': 'diamond', 'durationVariant': 'default'},
            {'shape': 'oval', 'durationVariant': 'whole'},
            {'shape': 'default', 'durationVariant': 'breve', 'glyph': 'noteheadBlack'},
            {'shape': 'custom', 'durationVariant': 'half', 'glyph': 'noteheadBlack'},
        ):
            document = self.with_head(head, kit=True)
            document['parts'][0]['kit']['cymbal']['notehead'] = {
                'shape': 'diamond', 'durationVariant': 'half',
            }
            with self.subTest(head=head):
                self.validator.validate(document)

    def test_clusters_are_not_supported(self):
        document = copy.deepcopy(self.document)
        event = document['parts'][0]['measures'][0]['sequences'][0]['content'][0]
        event['noteheadClusters'] = [{'notes': ['lower', 'upper']}]
        self.assertFalse(self.validator.is_valid(document))

    def test_triangle_pointing(self):
        attribute = self.schema['$defs']['notehead']['properties']['pointing']
        self.assertEqual(attribute['default'], 'up')
        definition = self.schema['$defs'][attribute['$ref'].split('/')[-1]]
        self.assertIn(attribute['default'], definition['enum'])
        for kit in (False, True):
            for pointing in ('up', 'down'):
                for duration in ('quarter', 'half', 'whole', 'breve', 'longa', 'maxima', 'duplexMaxima'):
                    with self.subTest(kit=kit, pointing=pointing, duration=duration):
                        self.validator.validate(self.with_head(
                            {'shape': 'triangle', 'pointing': pointing}, kit, duration))
                self.validator.validate(self.with_head(
                    {'shape': 'triangle', 'pointing': pointing,
                     'glyph': 'noteheadTriangleDownBlack'}, kit))
            for shape in (None, 'default', 'oval', 'diamond', 'x', 'slash',
                          'plus', 'circleX', 'square', 'custom'):
                head = {'pointing': 'down'}
                if shape is not None:
                    head['shape'] = shape
                if shape == 'custom':
                    head['glyph'] = 'noteheadTriangleDownBlack'
                with self.subTest(kit=kit, head=head):
                    self.assertFalse(self.validator.is_valid(self.with_head(head, kit)))
            for pointing in ('auto', 'left', 'right', None, 1):
                with self.subTest(kit=kit, pointing=pointing):
                    self.assertFalse(self.validator.is_valid(self.with_head(
                        {'shape': 'triangle', 'pointing': pointing}, kit)))


if __name__ == '__main__':
    unittest.main()
