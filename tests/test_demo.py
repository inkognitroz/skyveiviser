import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import DemoError, ask, installed_models, load_corpus, retrieve, validate_answer, validate_question, NoRedirect
from app import DemoServer

MODEL = {"name":"qwen2.5-coder:7b","digest":"fixture-not-a-real-model-digest","size":4_700_000_000,
         "details":{"format":"gguf","quantization_level":"Q4_K_M"}}

def fixture(path, payload=None, timeout=240):
    if path == '/api/tags': return {"models":[MODEL]}
    return {"done": True, "message":{"content":json.dumps({"abstain":False,"claims":[
        {"text":"Forbered behov og brukercase.","source_ids":["S2"]}]})},
        "prompt_eval_count":100,"eval_count":20,"eval_duration":2_000_000_000}

class EngineTests(unittest.TestCase):
    def setUp(self): self.c = load_corpus()
    def test_original_sources_retained(self):
        self.assertEqual([s['id'] for s in self.c['sources'][:5]], ['S1','S2','S3','S4','S5'])
        self.assertEqual(len(self.c['sources']), 24)
    def test_sha(self): self.assertEqual(len(self.c['sha256']), 64)
    def test_market_dialog(self): self.assertEqual(retrieve('Hvordan forbereder vi en markedsdialog?',self.c)[0]['id'],'S2')
    def test_security(self): self.assertEqual(retrieve('Hva sier referansearkitekturen om sikkerhet?',self.c)[0]['id'],'S3')
    def test_finops(self): self.assertEqual(retrieve('Hva brukes modenhetsanalyse i FinOps til?',self.c)[0]['id'],'S4')
    def test_ssa(self): self.assertEqual(retrieve('Hva er SSA?',self.c)[0]['id'],'S5')
    def test_mps(self): self.assertEqual(retrieve('Hva gjør MPS?',self.c)[0]['id'],'S1')
    def test_irrelevant(self): self.assertEqual(retrieve('Hva er morgendagens vær?',self.c),[])
    def test_no_network_baseline(self):
        def forbidden(*a,**k): raise AssertionError('network')
        self.assertEqual(ask('Hva er FinOps?','sources','',self.c,forbidden)['status'],'source_matches')
    def test_unknown_no_call(self):
        def forbidden(*a,**k): raise AssertionError('network')
        self.assertEqual(ask('Hvem vant fotballkampen?','ollama','x',self.c,forbidden)['status'],'no_source_match')
    def test_invalid_questions(self):
        for q in [None,[],{},'', 'ab', 'a'*1501]:
            with self.subTest(q=str(q)[:10]),self.assertRaises(DemoError): validate_question(q)
    def test_invalid_mode(self):
        with self.assertRaises(DemoError): ask('Hva er MPS?','cloud','x',self.c)
    def test_llm_contract(self):
        r=ask('Hvordan forbereder vi markedsdialog?','ollama',MODEL['name'],self.c,fixture)
        self.assertEqual(r['status'],'model_answer'); self.assertEqual(r['output_tokens'],20)
        self.assertEqual(r['generation_tokens_per_second'],10); self.assertIsNone(r['cost_nok'])
        self.assertEqual(r['semantic_verification'],'ikke utført')
    def test_local_inventory_only(self):
        cloud={**MODEL,'name':'qwen:cloud'}
        remote={**MODEL,'remote_host':'example.test'}
        missing={**MODEL,'digest':''}
        self.assertEqual(len(installed_models(lambda *a,**k:{'models':[MODEL,cloud,remote,missing]})),1)
    def test_not_installed(self):
        with self.assertRaises(DemoError): ask('Hva er markedsdialog?','ollama','other',self.c,fixture)
    def test_malformed_model_json(self):
        def bad(path,*a,**k): return fixture(path,*a,**k) if path=='/api/tags' else {'done':True,'message':{'content':'no json'}}
        with self.assertRaises(DemoError): ask('Hva er markedsdialog?','ollama',MODEL['name'],self.c,bad)
    def test_incomplete(self):
        def bad(path,*a,**k): return fixture(path,*a,**k) if path=='/api/tags' else {'done':False}
        with self.assertRaises(DemoError): ask('Hva er markedsdialog?','ollama',MODEL['name'],self.c,bad)
    def test_abstention(self):
        self.assertEqual(validate_answer({'abstain':True,'claims':[]},[])['claims'],[])
    def test_bad_answers(self):
        examples=[{}, {'abstain':False,'claims':[]}, {'abstain':'false','claims':[]},
            {'abstain':True,'claims':[{'text':'x','source_ids':['S2']}]},
            {'abstain':False,'claims':[{'text':'x','source_ids':['S99']}]},
            {'abstain':False,'claims':[{'text':'x','source_ids':[]}]},
            {'abstain':False,'claims':[{'text':'http://evil.test','source_ids':['S2']}]},
            {'abstain':False,'claims':[{'text':'x [S99]','source_ids':['S2']}]},
            {'abstain':False,'claims':[{'text':'x','source_ids':['S2','S2']}]},
            {'abstain':False,'claims':[{'text':'x','source_ids':['S2'],'extra':1}]}]
        for e in examples:
            with self.subTest(e=e),self.assertRaises(DemoError): validate_answer(e,[self.c['sources'][1]])
    def test_id_from_other_source_rejected(self):
        with self.assertRaises(DemoError): validate_answer({'abstain':False,'claims':[{'text':'x','source_ids':['S1']}]},[self.c['sources'][1]])
    def test_invalid_corpus_urls_and_duplicates(self):
        for field,value in [('url','https://evil.test'),('id','S2'),('text','')]:
            data=json.loads((Path(__file__).parents[1]/'corpus.json').read_text())
            data['sources'][0][field]=value
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'corpus.json';p.write_text(json.dumps(data))
                with self.assertRaises(DemoError):load_corpus(p)
    def test_redirect_stopped(self):
        with self.assertRaises(DemoError):NoRedirect().redirect_request(None,None,302,'',{},'https://example.test')
    def test_payload_is_bounded(self):
        calls=[]
        def record(path,payload=None,**kw):
            if payload:calls.append(payload)
            return fixture(path,payload,**kw)
        ask('Hva er markedsdialog?','ollama',MODEL['name'],self.c,record)
        self.assertEqual(calls[0]['options']['num_ctx'],4096)
        self.assertEqual(calls[0]['options']['num_predict'],384)
        self.assertNotIn('tools',calls[0])
        self.assertFalse(calls[0]['stream'])

class HttpTests(unittest.TestCase):
    def setUp(self):
        self.s=DemoServer(0);self.t=threading.Thread(target=self.s.serve_forever,daemon=True);self.t.start()
        self.url=f'http://127.0.0.1:{self.s.server_port}'
    def tearDown(self):self.s.shutdown();self.s.server_close();self.t.join()
    def call(self,path='/',data=None,headers=None):
        h={} if headers is None else dict(headers)
        if data is not None:
            h.setdefault('Content-Type','application/json');h.setdefault('X-Demo-Token',self.s.token)
        req=urllib.request.Request(self.url+path,data=None if data is None else json.dumps(data).encode(),headers=h)
        try:r=urllib.request.urlopen(req,timeout=5)
        except urllib.error.HTTPError as e:r=e
        with r:return r.status,r.read(),r.headers
    def test_home(self):
        code,body,h=self.call();self.assertEqual(code,200);self.assertIn(b'Skyveiviser',body)
        self.assertEqual(h['Cache-Control'],'no-store');self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy'])
    def test_assets(self):
        for path in ['/app.js','/style.css']:self.assertEqual(self.call(path)[0],200)
    def test_not_file_server(self):
        for path in ['/corpus.json','/../engine.py','/etc/passwd','/.env']:self.assertEqual(self.call(path)[0],404)
    def test_no_external_origin(self):self.assertEqual(self.call(headers={'Origin':'https://evil.test'})[0],403)
    def test_no_rebinding(self):self.assertEqual(self.call(headers={'Host':'evil.test'})[0],403)
    def test_csrf(self):self.assertEqual(self.call('/api/ask',{'question':'Hva er MPS?'},{'X-Demo-Token':'bad'})[0],403)
    def test_content_type(self):self.assertEqual(self.call('/api/ask',{'question':'Hva er MPS?'},{'Content-Type':'text/plain'})[0],415)
    def test_large_body(self):self.assertEqual(self.call('/api/ask',{'question':'a'*9000})[0],413)
    def test_baseline_end_to_end(self):
        code,body,_=self.call('/api/ask',{'question':'Hva er FinOps?','mode':'sources'})
        self.assertEqual(code,200);self.assertEqual(json.loads(body)['sources'][0]['id'],'S4')
    def test_ollama_disabled(self):self.assertEqual(self.call('/api/ask',{'question':'Hva er MPS?','mode':'ollama'})[0],422)
    def test_busy(self):
        self.s.inference.acquire()
        try:self.assertEqual(self.call('/api/ask',{'question':'Hva er MPS?'})[0],429)
        finally:self.s.inference.release()
    def test_rate(self):
        import time
        self.s.times=[time.monotonic()]*12
        self.assertEqual(self.call('/api/ask',{'question':'Hva er MPS?'})[0],429)
    def test_extra_fields(self):self.assertEqual(self.call('/api/ask',{'question':'Hva er MPS?','url':'http://evil.test'})[0],422)
    def test_config(self):self.assertFalse(json.loads(self.call('/api/config')[1])['ollama_enabled'])
    def test_model_list_disabled(self):self.assertEqual(json.loads(self.call('/api/models')[1])['models'],[])

class OllamaProtocolTests(unittest.TestCase):
    """Real HTTP between demo and a deterministic, local fake API, not real inference."""
    def test_http_protocol_roundtrip(self):
        from http.server import BaseHTTPRequestHandler, HTTPServer
        class FakeOllama(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def reply(self,obj):
                data=json.dumps(obj).encode();self.send_response(200)
                self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
            def do_GET(self): self.reply(fixture(self.path))
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                self.reply(fixture(self.path,body))
        fake=HTTPServer(('127.0.0.1',0),FakeOllama)
        thread=threading.Thread(target=fake.serve_forever,daemon=True);thread.start()
        try:
            with patch('engine.OLLAMA_URL',f'http://127.0.0.1:{fake.server_port}'):
                result=ask('Hvordan forbereder vi markedsdialog?','ollama',MODEL['name'],load_corpus())
                self.assertEqual(result['status'],'model_answer')
                self.assertEqual(result['answer']['claims'][0]['source_ids'],['S2'])
        finally:fake.shutdown();fake.server_close();thread.join()

    def test_nonfinite_or_boolean_inventory_rejected(self):
        for size in [True,float('nan'),float('inf')]:
            self.assertEqual(installed_models(lambda *a,**k:{'models':[{**MODEL,'size':size}]}),[])

if __name__=='__main__':unittest.main(verbosity=2)

