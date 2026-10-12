import json
import logging
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from evaluation.collect import ROOT
from evaluation.observer import ObservedApp, Recorder, SSEObserver, active_recorder, install_observers, model_wrapper


class ObserverTests(unittest.IsolatedAsyncioTestCase):
    async def test_wrappers_preserve_arguments_and_results_and_record_usage_and_actual_ids(self):
        calls = []
        response = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=80, completion_tokens=20, total_tokens=100))
        class Chat:
            async def create(self, **kwargs): calls.append(kwargs); return response
        class Embeddings:
            async def create(self, **kwargs): return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=12, total_tokens=12))
        class Collection:
            def get(self, **kwargs): return {'ids': ['p_chunk0', 'p_chunk1'], 'documents': ['private zero', 'private one']}
            def query(self, **kwargs): return {'ids': [['p_chunk1']], 'documents': [['private one']]}
        restore = install_observers(Chat, Embeddings, Collection, lambda: {'stage': 'read'})
        recorder = Recorder(); token = active_recorder.set(recorder)
        try:
            kwargs = {'model': 'fixture', 'messages': [{'content': 'SECRET INPUT'}], 'max_tokens': 10}
            self.assertIs(await Chat().create(**kwargs), response)
            self.assertEqual(calls, [kwargs])
            await Embeddings().create(model='fixture', input=['SECRET EMBEDDING'])
            Collection().get(where={'paper_id': 'p'})
            Collection().query(where={'paper_id': 'p'}, n_results=1)
            self.assertEqual(recorder.data['llm_calls'][0]['total_tokens'], 100)
            self.assertEqual(recorder.data['embedding_calls'][0]['total_tokens'], 12)
            self.assertEqual(recorder.retrievals['p']['ids'], ['p_chunk1'])
            self.assertEqual(recorder.retrievals['p']['method'], 'vector')
            serialized = json.dumps({**recorder.data, 'retrievals': recorder.retrievals})
            self.assertNotIn('SECRET', serialized); self.assertNotIn('private one', serialized)
        finally:
            active_recorder.reset(token); restore()

    async def test_failed_model_call_keeps_original_error_and_unknown_tokens(self):
        error = RuntimeError('original failure')
        async def original(resource, **kwargs): raise error
        recorder = Recorder(); token = active_recorder.set(recorder)
        try:
            with self.assertRaises(RuntimeError) as raised:
                await model_wrapper(original, 'llm', lambda: {})(object(), model='fixture')
            self.assertIs(raised.exception, error)
            self.assertIsNone(recorder.data['llm_calls'][0]['total_tokens'])
            self.assertEqual(recorder.data['llm_calls'][0]['status'], 'failed')
        finally: active_recorder.reset(token)

    async def test_sse_observation_keeps_original_messages_and_http_200_error_is_failure(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            sent, original = [], []
            async def app(scope, receive, send):
                await receive()
                messages = [{'type': 'http.response.start', 'status': 200, 'headers': [(b'content-type', b'text/event-stream'), (b'x-request-id', b'r')]},
                            {'type': 'http.response.body', 'body': b'data: {"event":"stage","stage":"search"}\n\n', 'more_body': True},
                            {'type': 'http.response.body', 'body': b'data: {"event":"error","code":"TEST"}\n\n', 'more_body': False}]
                for message in messages: original.append(message); await send(message)
            async def receive(): return {'type': 'http.request', 'body': b'{"query":"PRIVATE QUESTION"}', 'more_body': False}
            async def send(message): sent.append(message)
            await ObservedApp(app, Path(folder))({'type': 'http', 'method': 'POST', 'path': '/api/research/stream'}, receive, send)
            self.assertEqual(sent, original)
            record = json.loads(next(Path(folder).glob('*.json')).read_text(encoding='utf-8'))
            self.assertEqual(record['status'], 'failed')
            self.assertTrue(record['task_started'])
            self.assertNotIn('PRIVATE QUESTION', json.dumps(record))

    async def test_nonresearch_requests_are_not_observed_and_invalid_json_body_does_not_change_response(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            async def app(scope, receive, send):
                await receive()
                await send({'type': 'http.response.start', 'status': 400, 'headers': [(b'content-type', b'application/json')]})
                await send({'type': 'http.response.body', 'body': b'{"error":"invalid"}'})
            async def receive(): return {'type': 'http.request', 'body': b'[]'}
            async def send(message): pass
            wrapper = ObservedApp(app, Path(folder))
            await wrapper({'type': 'http', 'method': 'GET', 'path': '/health'}, receive, send)
            self.assertEqual(list(Path(folder).glob('*.json')), [])
            await wrapper({'type': 'http', 'method': 'POST', 'path': '/api/research/stream'}, receive, send)
            record = json.loads(next(Path(folder).glob('*.json')).read_text(encoding='utf-8'))
            self.assertFalse(record['task_started']); self.assertEqual(record['status'], 'failed')

    async def test_bytewise_chinese_sse_with_crlf_multiline_and_trailing_frame(self):
        seen = []; parser = SSEObserver(seen.append)
        text = 'data: {"event":"stage",\r\ndata: "label":"中文"}\r\n\r\ndata: {"event":"done","final_answer":"报告"}'
        for byte in text.encode('utf-8'): parser.feed(bytes([byte]))
        parser.feed(b'', final=True)
        self.assertEqual(seen, [{'event': 'stage', 'label': '中文'}, {'event': 'done', 'final_answer': '报告'}])


if __name__ == '__main__': unittest.main()
