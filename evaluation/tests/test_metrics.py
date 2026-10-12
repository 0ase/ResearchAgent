import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from evaluation.collect import ROOT, atomic_json, collect, historical_runs, read_sessions, result_summary
from evaluation.evaluate import evaluate, load_labels, percentile


def value(report, identifier):
    return next(m for group in report['groups'] for m in group['metrics'] if m['id'] == identifier)


def run(identifier='r', status='completed', duration=1):
    return {'run_id': identifier, 'request_id': identifier, 'task_started': True, 'status': status,
            'kind': 'observed', 'started_at': '2026-10-11T00:00:00+00:00', 'ended_at': '2026-10-11T00:00:01+00:00',
            'server_elapsed_seconds': duration, 'usage_observed': True, 'retrieval_observed': True, 'retrieval_top_k': 6,
            'llm_calls': [{'status': 'completed', 'total_tokens': 100}], 'embedding_calls': [],
            'stage_events': [], 'retrievals': [], 'result': {'has_report': True, 'selected_available': True,
                                                           'selected_paper_ids': ['a'], 'read_paper_ids': ['a']}}


class MetricsTests(unittest.TestCase):
    def test_windows_locked_publication_can_rewrite_without_weakening_observation_writes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            path = Path(folder) / 'public.json'
            atomic_json(path, {'count': 1})
            with patch('evaluation.collect.os.replace', side_effect=PermissionError()), patch('evaluation.collect.time.sleep'), patch('evaluation.collect.os.name', 'nt'):
                with self.assertRaises(PermissionError): atomic_json(path, {'count': 2})
                self.assertEqual(json.loads(path.read_text()), {'count': 1})
                atomic_json(path, {'count': 2}, allow_locked_rewrite=True)
                self.assertEqual(json.loads(path.read_text()), {'count': 2})

    def test_percentiles_and_failure_denominators(self):
        report = evaluate({'runs': [run('a', duration=1), run('b', duration=2), run('c', duration=100),
                                    run('d', 'failed', 200), run('e', 'cancelled', 200), run('f', 'incomplete', 900)]})
        self.assertEqual(value(report, 'latency_p50')['value'], 2)
        self.assertEqual(value(report, 'latency_p99')['value'], 100)
        self.assertEqual(value(report, 'latency_p99')['samples'], 3)
        self.assertAlmostEqual(value(report, 'mean_completion_seconds')['value'], 103 / 3, places=3)
        self.assertEqual(value(report, 'task_completion_rate')['value'], 60)
        self.assertAlmostEqual(value(report, 'terminal_coverage')['value'], 100 * 5 / 6, places=3)
        self.assertIsNone(percentile([], 99))

    def test_partial_usage_never_becomes_whole_task_mean(self):
        old = run('old'); old['usage_observed'] = False
        bad = run('bad'); bad['llm_calls'].append({'status': 'failed', 'total_tokens': None})
        complete = run('good'); complete['llm_calls'].append({'status': 'completed', 'total_tokens': 300})
        report = evaluate({'runs': [old, bad, complete]})
        self.assertEqual(value(report, 'mean_llm_tokens')['value'], 400)
        self.assertEqual(value(report, 'mean_llm_tokens')['samples'], 1)
        self.assertAlmostEqual(value(report, 'token_usage_coverage')['value'], 100 / 3, places=3)
        self.assertEqual(value(report, 'mean_recorded_llm_tokens')['status'], 'partial')
        self.assertIsNone(value(evaluate({'runs': [old]}), 'mean_llm_tokens')['value'])

    def test_rag_gold_counts_missing_reference_papers_and_preserves_rank(self):
        observed = run()
        observed['retrievals'] = [{'paper_id': 'a', 'ids': ['irrelevant', 'gold-a'], 'ids_available': True}]
        labels = [{'request_id': 'r', 'rag_k': 6, 'rag': [
            {'paper_id': 'a', 'relevant_chunk_ids': ['gold-a', 'gold-b']},
            {'paper_id': 'missing', 'relevant_chunk_ids': ['gold-missing']}]}]
        report = evaluate({'runs': [observed]}, labels)
        self.assertEqual(value(report, 'rag_hit_rate')['value'], 50)
        self.assertEqual(value(report, 'rag_recall')['value'], 25)
        self.assertEqual(value(report, 'rag_mrr')['value'], 0.25)
        self.assertEqual(value(report, 'rag_hit_rate')['samples'], 2)
        observed['retrieval_observed'] = False
        self.assertIsNone(value(evaluate({'runs': [observed]}, labels), 'rag_hit_rate')['value'])
        observed['retrieval_observed'] = True
        observed['retrievals'][0]['ids_available'] = False
        self.assertIsNone(value(evaluate({'runs': [observed]}, labels), 'rag_hit_rate')['value'])

    def test_duplicates_and_missing_slots_do_not_increase_precision(self):
        observed = run()
        observed['result'] = result_summary({'selected_papers': [{'source_id': 'a'}, {'source_id': 'a'}, {'source_id': 'b'}], 'paper_insights': []})
        labels = [{'request_id': 'r', 'papers': {'k': 3, 'judgments': {'a': 1, 'b': 1}, 'reference_paper_ids': ['a', 'b', 'c']}}]
        report = evaluate({'runs': [observed]}, labels)
        self.assertAlmostEqual(value(report, 'paper_precision')['value'], 200 / 3, places=3)
        labels[0]['papers']['judgments'].pop('b')
        self.assertIsNone(value(evaluate({'runs': [observed]}, labels), 'paper_precision')['value'])

    def test_missing_and_pending_labels_are_not_zero_or_perfect(self):
        observed = run()
        report = evaluate({'runs': [observed]})
        self.assertIsNone(value(report, 'rag_hit_rate')['value'])
        self.assertIsNone(value(report, 'fact_support_rate')['value'])
        labels = [{'request_id': 'r', 'facts': [{'status': 'supported', 'has_resolved_citation': True},
                                               {'status': 'partial', 'has_resolved_citation': True}]}]
        report = evaluate({'runs': [observed]}, labels)
        self.assertEqual(value(report, 'fact_support_rate')['value'], 50)
        self.assertEqual(value(report, 'citation_coverage')['value'], 100)
        labels[0]['facts'][1]['status'] = 'pending'
        self.assertIsNone(value(evaluate({'runs': [observed]}, labels), 'fact_support_rate')['value'])

    def test_sse_http_200_without_report_is_not_success_and_usage_is_deduplicated(self):
        common = {'request_id': 'r', 'process_id': 1, 'path': '/api/research/stream', 'method': 'POST'}
        events = [{'message': 'request.started', 'timestamp': '2026-10-11T00:00:00+00:00'},
                  {'message': 'stage.started', 'stage': 'analyze', 'session_id': 's', 'timestamp': '2026-10-11T00:00:01+00:00'},
                  {'message': 'analysis.response.received', 'response_id': 'same', 'total_tokens': 50, 'timestamp': '2026-10-11T00:00:02+00:00'},
                  {'message': 'analysis.response.received', 'response_id': 'same', 'total_tokens': 50, 'timestamp': '2026-10-11T00:00:03+00:00'},
                  {'message': 'analysis.output.failed', 'stage': 'analyze', 'timestamp': '2026-10-11T00:00:04+00:00'},
                  {'message': 'request.completed', 'status_code': 200, 'outcome': 'completed', 'duration_ms': 5000, 'timestamp': '2026-10-11T00:00:05+00:00'}]
        rows, _ = historical_runs([{**common, **event} for event in events], [])
        self.assertEqual(rows[0]['status'], 'failed')
        self.assertEqual(len(rows[0]['llm_calls']), 1)
        events.pop(-2)
        rows, _ = historical_runs([{**common, **event} for event in events], [])
        self.assertEqual(rows[0]['status'], 'incomplete')

    def test_collect_is_read_only_and_observed_run_replaces_log_duplicate(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            directory = Path(folder); db = directory / 'source.db'
            with sqlite3.connect(db) as connection:
                connection.execute('CREATE TABLE sessions(session_id TEXT, query TEXT, result_json TEXT)')
                connection.execute('INSERT INTO sessions VALUES(?,?,?)', ('s', 'private research question', json.dumps({'request_id': 'r', 'final_answer': 'PRIVATE REPORT', 'selected_papers': [{'source_id': 'a'}]})))
            connection.close()
            before = db.read_bytes()
            observations = directory / 'observed'; observations.mkdir()
            observed = run(); observed.update({'schema_version': 1, 'session_id': 's'})
            atomic_json(observations / 'r.json', observed)
            snapshot = collect([], db, observations)
            self.assertEqual(len(snapshot['runs']), 1)
            self.assertEqual(snapshot['runs'][0]['result']['selected_paper_ids'], ['a'])
            self.assertEqual(db.read_bytes(), before)
            self.assertNotIn('PRIVATE REPORT', json.dumps(snapshot))
            self.assertNotIn('private research question', json.dumps(snapshot))
            absent = directory / 'absent.db'; read_sessions(absent)
            self.assertFalse(absent.exists())

    def test_example_labels_and_query_wide_fact_labels_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            path = Path(folder) / 'labels.jsonl'
            path.write_text('{"query_hash":"example","example_only":true}\n', encoding='utf-8')
            with self.assertRaises(ValueError): load_labels(path)
            path.write_text('{"query_hash":"some-query","facts":[{"status":"supported"}]}\n', encoding='utf-8')
            with self.assertRaises(ValueError): load_labels(path)


if __name__ == '__main__': unittest.main()
