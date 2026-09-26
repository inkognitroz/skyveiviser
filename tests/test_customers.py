import copy
import json
from pathlib import Path
import sys
import threading
import unittest
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from customers import lookup, validate_register
from engine import ask, load_corpus, retrieve
from app import DemoServer


class CustomerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = load_corpus()
        cls.register = cls.corpus['customer_register']
        cls.source_ids = {s['id'] for s in cls.corpus['sources']}

    def test_620_rows_are_present(self):
        self.assertEqual(len(self.register['rows']), 620)

    def test_dfo_exact_orgnr(self):
        result = lookup('986252932', self.register)
        self.assertEqual(result['customer_match_count'], 1)
        self.assertEqual(result['customer_rows'][0][2:], ['Ja'] * 7)

    def test_dfo_name_abbreviation(self):
        self.assertEqual(lookup('DFØ', self.register)['customer_rows'][0][0], '986252932')

    def test_oslo_values_are_not_generalized(self):
        row = lookup('Oslo kommune', self.register)['customer_rows'][0]
        self.assertEqual(row[2:], ['Nei','Ja','Nei','Nei','Ja','Ja','Nei'])

    def test_via_is_preserved(self):
        row = lookup('Aukra kommune', self.register)['customer_rows'][0]
        self.assertEqual(row[5], 'Via ROR-IKT')

    def test_blank_is_not_no(self):
        rows = lookup('Inderøy kommune', self.register)['customer_rows']
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], '')
        self.assertEqual(rows[0][6], '')

    def test_duplicate_names_not_merged(self):
        result = lookup('Ålesund kommune', self.register)
        self.assertEqual(result['customer_match_count'], 2)
        self.assertIn('Ålesund kommune', result['customer_duplicate_names'])

    def test_two_valer_organizations_retained(self):
        rows = lookup('Våler kommune', self.register)['customer_rows']
        self.assertEqual({r[0] for r in rows}, {'871034222','959272581'})

    def test_unknown_not_denied(self):
        result = lookup('Ukjent demonstrasjonskommune', self.register)
        self.assertEqual(result['status'], 'no_customer_match')
        self.assertEqual(result['customer_rows'], [])
        self.assertNotIn('denied', json.dumps(result))

    def test_cips_listing_only_yes_or_via(self):
        result = lookup('CIPS', self.register)
        self.assertEqual(result['customer_match_count'], 313)
        self.assertEqual(result['customer_columns'][0]['id'], 'cips')
        self.assertTrue(all(r[6]=='Ja' or r[6].startswith('Via ') for r in result['customer_rows']))

    def test_cloud_ra_listing_alias(self):
        self.assertEqual(lookup('Cloud R&A', self.register)['customer_match_count'], 304)

    def test_vm_is_not_marked_active(self):
        result = lookup('VM', self.register)
        self.assertEqual(result['customer_match_count'], 399)
        self.assertIn('Ikke bekreftet inngått', result['customer_columns'][0]['status'])

    def test_dates_are_distinct(self):
        result = lookup('DFØ', self.register)
        self.assertEqual(result['customer_source_updated_at'], '2025-11-11')
        self.assertEqual(result['customer_read_at'], '2026-09-26')

    def test_no_llm_for_membership(self):
        def forbidden(*a, **kw):
            raise AssertionError('A membership lookup must not call a model.')
        for question in ('DFØ','VM','Ukjent virksomhet','CIPS'):
            with self.subTest(question=question):
                result = ask(question, 'customers', 'not-installed', self.corpus, forbidden)
                self.assertIsNone(result['model'])
                self.assertIsNone(result['answer'])
                self.assertEqual(result['sources'][0]['id'], 'S19')

    def test_long_and_invalid_lookup_input(self):
        for question in (None, [], 'a'*1501, ''):
            with self.subTest(question=str(question)[:12]), self.assertRaises(ValueError):
                ask(question, 'customers', '', self.corpus)

    def test_org_number_can_include_spaces(self):
        self.assertEqual(lookup('986 252 932', self.register)['customer_match_count'], 1)

    def test_partial_name_keeps_multiple_matches(self):
        self.assertGreater(lookup('Oslo', self.register)['customer_match_count'], 1)

    def test_bad_column_order_is_rejected(self):
        bad = copy.deepcopy(self.register)
        bad['columns'][2], bad['columns'][3] = bad['columns'][3], bad['columns'][2]
        with self.assertRaises(ValueError): validate_register(bad, self.source_ids)

    def test_bad_status_is_rejected(self):
        bad = copy.deepcopy(self.register)
        bad['rows'][0][2] = 'Godkjent'
        with self.assertRaises(ValueError): validate_register(bad, self.source_ids)

    def test_bad_source_is_rejected(self):
        bad = copy.deepcopy(self.register)
        bad['source_url'] = 'https://example.test'
        with self.assertRaises(ValueError): validate_register(bad, self.source_ids)

    def test_missing_column_is_rejected(self):
        bad = copy.deepcopy(self.register)
        bad['rows'][0].pop()
        with self.assertRaises(ValueError): validate_register(bad, self.source_ids)

    def test_bad_date_is_rejected(self):
        bad = copy.deepcopy(self.register)
        bad['read_at'] = 'tomorrow'
        with self.assertRaises(ValueError): validate_register(bad, self.source_ids)

    def test_old_corpus_without_register_still_valid(self):
        validate_register(None, self.source_ids)
        with self.assertRaises(ValueError): lookup('DFØ', None)

    def test_input_not_interpreted_as_code(self):
        self.assertEqual(lookup('<script>alert(1)</script>', self.register)['customer_rows'], [])

    def test_agreement_retrieval(self):
        examples = [
            ('Hvilke avtaler har MPS inngått?', 'S6'),
            ('Hvordan gjør vi avrop på CIPS?', 'S13'),
            ('Hvordan gjør vi avrop på Cloud R&A?', 'S14'),
            ('Hvordan gjør vi avrop på CRS?', 'S15'),
            ('Hvordan gjør vi avrop på Training Awareness?', 'S16'),
            ('Hvordan gjør vi avrop på TPPCM?', 'S17'),
            ('Hvordan gjør vi avrop på CTI?', 'S18'),
            ('Kan vi gjøre avrop på VM?', 'S23'),
            ('Hvordan gjør vi avrop på GRC?', 'S23'),
        ]
        for q, expected in examples:
            with self.subTest(q=q):
                self.assertIn(expected, [s['id'] for s in retrieve(q, self.corpus)])

    def test_contracts_do_not_borrow_calloff_rules(self):
        result = retrieve('Hvordan gjør vi avrop på CIPS?', self.corpus)
        for source in result:
            self.assertFalse(set(source.get('agreement_ids', [])) - {'cips'})

    def test_general_calloff_has_general_navigation_only(self):
        self.assertEqual([s['id'] for s in retrieve('Hvordan gjør vi avrop?', self.corpus)], ['S24'])

    def test_price_question_finds_no_price_faq(self):
        source = retrieve('Hvilken leverandør har lavest pris akkurat nå?', self.corpus)[0]
        self.assertEqual(source['id'], 'S21')
        self.assertIn('ikke leverandørenes', source['text'])

    def test_original_examples_still_retrieve(self):
        for q, expected in [('Hva er SSA?', 'S5'), ('Hva er FinOps?', 'S4')]:
            self.assertEqual(retrieve(q, self.corpus)[0]['id'], expected)

    def test_data_shape_is_not_a_legal_decision(self):
        for r in self.register['rows']:
            self.assertEqual(len(r), 9)
        self.assertNotIn('can_order', json.dumps(self.register))

    def test_server_roundtrip_without_model(self):
        server = DemoServer(0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            payload = json.dumps({'question':'DFØ','mode':'customers','model':''}).encode()
            request = urllib.request.Request(
                f'http://127.0.0.1:{server.server_port}/api/ask', data=payload,
                headers={'Content-Type':'application/json','X-Demo-Token':server.token})
            with urllib.request.urlopen(request, timeout=5) as response:
                result = json.load(response)
            self.assertEqual(result['customer_rows'][0][0], '986252932')
            self.assertEqual(result['status'], 'customer_matches')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
