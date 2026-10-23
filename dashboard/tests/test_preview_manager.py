"""Local authorization boundary, session isolation and real-only UI behavior."""
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from streamlit.runtime.pages_manager import PagesManager
from streamlit.util import calc_md5

DASHBOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DASHBOARD))
from components import preview_manager as m, technical_preview as t, q01_real_preview as q


class BoundaryTests(unittest.TestCase):
    def config(self, root):
        return dict(enabled=True, authorization=m.AUTHORIZATION, source_root=str(root))

    def test_disabled_or_non_loopback_never_reads_packages_and_clears_state(self):
        for config, address in [({}, '127.0.0.1'), (self.config(Path.cwd()), '0.0.0.0'),
                                (self.config(Path.cwd()), None), (self.config(Path.cwd()), 'localhost')]:
            state = {'Q01': {'status': 'READY', 'result': object()}}
            with patch.object(m, 'discover') as discover:
                m.synchronize(state, config, address)
            discover.assert_not_called()
            self.assertEqual(set(state), set(m.QUERIES))
            self.assertTrue(all(v['status'] == 'ERROR' and 'result' not in v for v in state.values()))

    def test_only_six_queries_and_strict_config(self):
        self.assertEqual(m.QUERIES, ('Q01','Q02','Q03','Q04','Q06','Q08'))
        cfg = self.config(Path.cwd())
        for bad in [dict(cfg, enabled=False), dict(cfg, authorization='old'), dict(cfg, Q07='x'),
                    dict(cfg, source_root='relative'), dict(cfg, source_root='//server/share')]:
            self.assertFalse(m.configuration_allowed(bad, '127.0.0.1'))

    def test_missing_and_wrong_hash_do_not_call_receiver(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = {}
            with patch.object(t, 'load_preview') as load, patch.object(q, 'load_q01_preview') as load_q01:
                m.synchronize(state, self.config(tmp), '127.0.0.1')
                self.assertTrue(all(v['issue'] == 'MISSING_PACKAGE' for v in state.values()))
                (Path(tmp) / m.filename('Q02')).write_bytes(b'wrong')
                m.synchronize(state, self.config(tmp), '127.0.0.1')
                self.assertEqual(state['Q02']['issue'], 'ARCHIVE_HASH_MISMATCH')
            load.assert_not_called(); load_q01.assert_not_called()

    def test_no_broad_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            extra = Path(tmp) / 'unapproved'; extra.mkdir()
            (extra / m.filename('Q01')).write_bytes(b'irrelevant')
            self.assertEqual(m.discover('Q01', tmp)[2], 'MISSING_PACKAGE')

    def test_validation_failure_isolated_and_exception_sanitized(self):
        with patch.object(m, 'discover', return_value=(Path('/pinned.zip'), 'digest', '')):
            with patch.object(q, 'load_q01_preview', return_value=q.PreviewResult(True, "")), patch.object(t, 'load_preview', side_effect=RuntimeError('private path')):
                state = m.synchronize({}, self.config(Path.cwd()), '127.0.0.1')
        self.assertEqual(state['Q01']['status'], 'READY')
        self.assertEqual(state['Q02'], {'status':'ERROR','issue':'VALIDATION_FAILED'})


@unittest.skipUnless((Path.home() / 'Desktop/t' / m.filename('Q01')).is_file(), 'External demo packages required')
class ActualSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        source = Path.home() / 'Desktop/t'
        for query in m.QUERIES:
            path, _, issue = m.discover(query, source)
            self.assertFalse(issue)
            shutil.copyfile(path, self.root / m.filename(query))
        self.config = dict(enabled=True, authorization=m.AUTHORIZATION, source_root=str(self.root))

    def sync(self, state):
        return m.synchronize(state, self.config, '127.0.0.1')

    def test_fresh_sessions_validate_and_navigation_reuses(self):
        with patch.object(q, 'load_q01_preview', wraps=q.load_q01_preview) as one, patch.object(t, 'load_preview', wraps=t.load_preview) as others:
            first = self.sync({}); original = first['Q01']['result']
            self.sync(first)
            self.assertIs(first['Q01']['result'], original)
            self.assertEqual((one.call_count, others.call_count), (1,5))
            second = self.sync({})
            self.assertEqual((one.call_count, others.call_count), (2,10))
            self.assertIsNot(second['Q01']['result'], original)
            self.assertTrue(all(v['status'] == 'READY' for v in second.values()))

    def test_missing_then_restore_isolated_and_no_stale(self):
        state = self.sync({}); original = state['Q01']['result']
        path = self.root / m.filename('Q02'); data = path.read_bytes(); path.unlink()
        self.sync(state)
        self.assertEqual(state['Q02']['issue'], 'MISSING_PACKAGE')
        self.assertNotIn('result', state['Q02'])
        self.assertIs(state['Q01']['result'], original)
        path.write_bytes(data); self.sync(state)
        self.assertEqual(state['Q02']['status'], 'READY')

    def test_same_size_corruption_detected_even_with_restored_mtime(self):
        import os
        state = self.sync({}); p = self.root / m.filename('Q03'); stamp = p.stat()
        data = bytearray(p.read_bytes()); data[-1] ^= 1; p.write_bytes(data)
        os.utime(p, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        self.sync(state)
        self.assertEqual(state['Q03']['issue'], 'ARCHIVE_HASH_MISMATCH')
        self.assertNotIn('result', state['Q03'])

    def test_schema_failure_from_receiver_blocks_only_query(self):
        original = t._table
        def invalid(payload, name, info):
            if name == 'q02_experience':
                raise t.Rejected('SCHEMA_MISMATCH')
            return original(payload, name, info)
        with patch.object(t, '_table', side_effect=invalid):
            state = self.sync({})
        self.assertIn('SCHEMA', state['Q02']['issue'])
        self.assertNotIn('result', state['Q02'])
        self.assertEqual(sum(v['status'] == 'READY' for v in state.values()), 5)

    def test_duplicate_wrong_hash_does_not_shadow_valid_package(self):
        query = 'Q04'; nested = self.root / ('TV2_HANDOFF_TV3_' + query); nested.mkdir()
        shutil.copyfile(self.root / m.filename(query), nested / m.filename(query))
        (self.root / m.filename(query)).write_bytes(b'wrong')
        self.assertEqual(self.sync({})[query]['status'], 'READY')

    def app_context(self):
        from contextlib import ExitStack
        stack = ExitStack()
        stack.enter_context(patch.object(m, 'read_config', return_value=self.config))
        import streamlit as st
        get_option = st.get_option
        stack.enter_context(patch.object(st, 'get_option', side_effect=lambda key: '127.0.0.1' if key == 'server.address' else get_option(key)))
        stack.enter_context(patch.object(PagesManager, 'get_page_script_byte_code', lambda _, path: compile(Path(path).read_text(encoding='utf-8-sig'), str(path), 'exec')))
        return stack

    def test_real_shell_home_all_routes_without_forms_and_no_reloads(self):
        with self.app_context(), patch.object(t, 'load_preview', wraps=t.load_preview) as loader:
            app = AppTest.from_file(str(DASHBOARD/'app.py')).run(timeout=20)
            self.assertFalse(app.exception)
            self.assertEqual([v.value for v in app.metric], ['5,206','10','6/6'])
            for route in ('Q01_Real_Preview','Experience','Locations','Work_Type','Skills','Time_Trends'):
                app._page_hash = calc_md5(route); app.run(timeout=20)
                self.assertFalse(app.exception, route)
                self.assertTrue(app.metric, route); self.assertTrue(app.dataframe, route)
                self.assertFalse(app.text_input); self.assertFalse(app.checkbox)
                self.assertTrue(app.get('arrow_vega_lite_chart'), route)
            self.assertEqual(loader.call_count, 5)

    def test_legacy_deep_routes_and_q07_never_render_fixtures(self):
        with self.app_context(), patch('components.analytics_demo.build_demo', side_effect=AssertionError('synthetic')):
            app = AppTest.from_file(str(DASHBOARD/'app.py')).run(timeout=20)
            for route in ('Overview','Query_Demo','Demo_Analytics','Q01_Synthetic_Demo','Salary_Quality'):
                app._page_hash = calc_md5(route); app.run(timeout=20)
                self.assertFalse(app.exception)
                self.assertFalse(app.toggle); self.assertFalse(app.checkbox)
                # Unknown deep routes resolve to real Home, not their old script.
                self.assertEqual(app.title[0].value, 'IT Recruitment Analytics')

    def test_home_missing_q01_has_no_population_and_other_query_works(self):
        with self.app_context():
            app = AppTest.from_file(str(DASHBOARD/'app.py')).run(timeout=20)
            (self.root/m.filename('Q01')).unlink(); app.run(timeout=20)
            self.assertFalse(app.metric); self.assertFalse(app.get('arrow_vega_lite_chart'))
            self.assertIn('MISSING_PACKAGE', app.error[0].value)
            app._page_hash = calc_md5('Experience'); app.run(timeout=20)
            self.assertFalse(app.exception); self.assertEqual(app.metric[0].value, '5,206')

    def test_q06_business_and_gate_unchanged(self):
        from components import artifact_gate
        with self.app_context():
            app = AppTest.from_file(str(DASHBOARD/'app.py')).run(timeout=20)
            app._page_hash = calc_md5('Skills'); app.run(timeout=20)
            self.assertTrue(any('NOT BUSINESS ACCEPTED' in x.value for x in app.caption))
            self.assertTrue(any('Production Gate CLOSED' in x.value for x in app.warning))
        self.assertEqual(artifact_gate.real_artifact_status(exists=True), 'BLOCKED')


if __name__ == '__main__':
    unittest.main()
