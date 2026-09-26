"""Regression tests for the four shortcuts and deterministic membership routing."""
import copy
import json
from pathlib import Path
import sys
import threading
import unittest
import urllib.request
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import ask, choose_mode, load_corpus
from customers import lookup
from app import DemoServer


def no_model(*args, **kwargs):
    raise AssertionError('This lookup must not contact a model, even for model discovery.')


class NavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = load_corpus()
        cls.reg = cls.c['customer_register']

    def test_asker_sentence_in_every_mode(self):
        for mode in ('sources', 'ollama', 'customers'):
            with self.subTest(mode=mode):
                result = ask('Jeg jobber i Asker kommune er jeg tilsluttet?', mode, '', self.c, no_model)
                self.assertEqual(result['mode'], 'customers')
                self.assertEqual(result['customer_rows'], [['920125298', 'Asker kommune'] + ['Nei'] * 7])
                self.assertIsNone(result['answer'])
                self.assertIsNone(result['model'])

    def test_asker_sentence_punctuation_and_capitals(self):
        for q in ('Jeg jobber i Asker kommune, er jeg tilsluttet?',
                  'Jeg jobber i Asker kommune – er jeg tilsluttet?',
                  'JEG JOBBER I ASKER KOMMUNE. Er jeg tilsluttet?',
                  'Er Asker kommune tilsluttet?', 'Er Asker tilsluttet?'):
            with self.subTest(q=q):
                self.assertEqual(lookup(q, self.reg)['customer_rows'][0][0], '920125298')

    def test_baerum_raw_memberships(self):
        r = ask('Jeg jobber i Bærum kommune, er vi tilsluttet?', 'ollama', '', self.c, no_model)
        self.assertEqual(r['customer_rows'][0][2:], ['Ja','Ja','Nei','Nei','Ja','Ja','Ja'])
        self.assertIn('Ikke bekreftet inngått', next(c for c in r['customer_columns'] if c['id'] == 'vm')['status'])

    def test_employer_takes_priority_over_unrelated_name(self):
        r = lookup('Jeg jobber i Ukjent kommune, ikke Asker kommune, er vi tilsluttet?', self.reg)
        self.assertEqual(r['customer_rows'], [])

    def test_unknown_employer_never_calls_model(self):
        r = ask('Jeg jobber i Ukjent kommune, er jeg tilsluttet?', 'ollama', '', self.c, no_model)
        self.assertEqual(r['status'], 'no_customer_match')

    def test_no_subject_prompts_for_name_not_agreement_list(self):
        for q in ('Er jeg tilsluttet?', 'Er vi tilsluttet CIPS?', 'Hvilke avtaler kan vi bruke?'):
            with self.subTest(q=q):
                r = ask(q, 'ollama', '', self.c, no_model)
                self.assertEqual(r['status'], 'customer_name_required')
                self.assertEqual(r['customer_rows'], [])

    def test_full_number_in_sentence(self):
        r = ask('Er virksomhet 920 125 298 tilsluttet?', 'ollama', '', self.c, no_model)
        self.assertEqual(r['customer_rows'][0][1], 'Asker kommune')

    def test_unknown_number_not_replaced_by_known_name(self):
        r = lookup('Org.nr. 123456789 Asker kommune', self.reg)
        self.assertEqual(r['customer_rows'], [])

    def test_malformed_number_not_substring(self):
        for q in ('1920125298','9201252980'):
            self.assertEqual(lookup(q, self.reg)['customer_rows'], [])

    def test_ambiguous_name_keeps_rows(self):
        r = ask('Er Våler kommune tilsluttet?', 'ollama', '', self.c, no_model)
        self.assertEqual({row[0] for row in r['customer_rows']}, {'871034222','959272581'})

    def test_via_not_changed_to_yes(self):
        r = ask('Jeg jobber i Aukra kommune, er jeg tilsluttet?', 'ollama', '', self.c, no_model)
        self.assertEqual(r['customer_rows'][0][6], 'Via ROR-IKT')

    def test_partial_name_in_explicit_mode_still_works(self):
        self.assertGreater(ask('Oslo', 'customers', '', self.c, no_model)['customer_match_count'], 1)

    def test_ordinary_cips_question_not_membership(self):
        self.assertEqual(choose_mode('Hvordan gjør vi avrop på CIPS?', 'sources'), 'sources')

    def test_agreement_overview_is_complete_without_model(self):
        r = ask('Hvilke avtaler har MPS inngått?', 'ollama', '', self.c, no_model)
        self.assertEqual(r['status'], 'agreement_overview')
        self.assertEqual([a['id'] for a in r['agreement_catalogue']], ['cips','cloud_ra','crs','training','tppcm','cti'])
        self.assertNotIn('vm', [a['id'] for a in r['agreement_catalogue']])
        self.assertIsNone(r['model'])

    def test_vm_status_never_needs_a_model(self):
        for q in ('Hva er VM, og når er tildeling planlagt?', 'Kan vi gjøre avrop på VM?', 'Hva er sårbarhetshåndtering?'):
            r = ask(q, 'ollama', '', self.c, no_model)
            self.assertEqual(r['status'], 'vm_details')
            self.assertEqual({s['id'] for s in r['sources']}, {'S23', 'S25'})
            self.assertFalse(r['vm_plan']['publicly_confirmed'])
            self.assertEqual(r['vm_plan']['expected_award_month'], '2026-10')
            self.assertIn('ikke bekreftet', r['vm_plan']['provenance'])

    def test_vm_table_query_keeps_distinct_semantics(self):
        r = ask('VM', 'customers', '', self.c, no_model)
        self.assertEqual(r['status'], 'customer_matches')
        self.assertEqual(r['customer_match_type'], 'agreement')

    def test_vm_membership_question_not_status_article(self):
        r = ask('Er Asker kommune tilsluttet VM?', 'ollama', '', self.c, no_model)
        self.assertEqual(r['status'], 'customer_matches')
        self.assertEqual(r['customer_rows'][0][1], 'Asker kommune')

    def test_old_corpus_without_plan_does_not_invent_a_date(self):
        c = copy.deepcopy(self.c); c.pop('vm_plan')
        self.assertIsNone(ask('Hva er VM?', 'sources', '', c, no_model)['vm_plan'])

    def test_http_autorouting_even_when_ollama_disabled(self):
        server = DemoServer(0)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            for q, status in [
                ('Jeg jobber i Asker kommune er jeg tilsluttet?', 'customer_matches'),
                ('Hvilke avtaler har MPS inngått?', 'agreement_overview'),
                ('Hva er VM, og når er tildeling planlagt?', 'vm_details')]:
                with self.subTest(q=q), patch('engine.installed_models', no_model):
                    req = urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/ask',
                        data=json.dumps({'question':q,'mode':'ollama','model':''}).encode(),
                        headers={'Content-Type':'application/json','X-Demo-Token':server.token})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        r = json.load(response)
                    self.assertEqual(r['status'], status)
        finally:
            server.shutdown(); server.server_close(); worker.join()


if __name__ == '__main__':
    unittest.main()
