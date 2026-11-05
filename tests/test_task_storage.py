"""Unified task storage migration and recovery use only isolated directories."""
import json
from pathlib import Path, PureWindowsPath
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import task_state as tasks
from pipeline_state import file_lock


class TaskStorageTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.legacy = self.root / 'dispatched.json'
        self.handled = self.root / 'tools/inbox_handled.json'
        self.queue = self.root / 'work_queue.json'
        self.canonical = self.root / 'task_state.json'
        self.key = 'owner/repo#1'

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json.dumps(value, ensure_ascii=False).encode('utf-8'))

    def fixture(self):
        self.write(self.legacy, {'Owner/Repo#1': {'status': 'running', 'ts': 1, 'extra': [1]},
                                 self.key: {'status': 'pending', 'ts': 2, 'extra': [2]}})
        self.write(self.handled, {self.key: {'at': '2026-01-01T00:00:00Z', 'note': 'Done',
                                          'history': [{'old': True}], 'extension': {'x': 1}}})
        self.write(self.queue, {'version': 1, 'issues': {}, 'prs': {
            self.key: {'action': 'ci', 'at': '2026-01-01T00:00:00Z',
                       'source': 'https://example.com/ci', 'ack': {'head': 'abc'},
                       'events': [{'at': '2026-01-01T00:00:00Z', 'minutes': 7}],
                       'extension': True}}, 'extra': 'preserve'})
        return {p: p.read_bytes() for p in (self.legacy, self.handled, self.queue)}

    def test_first_write_uses_one_file_and_leaves_legacy_bytes_unchanged(self):
        self.write(self.legacy, {self.key: {'status': 'pending', 'ts': 1}})
        original = self.legacy.read_bytes()
        store = tasks.TaskStore(self.legacy)
        self.assertTrue(store.mark(self.key, 'running'))
        self.assertTrue(self.canonical.exists())
        self.assertEqual(store.path, self.canonical)
        self.assertEqual(self.legacy.read_bytes(), original)
        self.assertFalse(self.handled.exists())
        self.assertFalse(self.queue.exists())
        self.assertEqual(tasks.TaskStore(root=self.root).status_of(self.key), 'running')

    def test_reads_do_not_create_files_or_locks(self):
        original = self.fixture()
        before = set(self.root.rglob('*'))
        self.assertTrue(tasks.TaskStore(root=self.root).is_active(self.key))
        self.assertEqual(tasks.load_handled(self.handled)[self.key]['note'], 'Done')
        self.assertEqual(tasks.load_queue_state(self.queue)['prs'][self.key]['ack'], {'head': 'abc'})
        self.assertEqual(set(self.root.rglob('*')), before)
        self.assertEqual({p: p.read_bytes() for p in original}, original)

    def test_migration_preserves_raw_partitions_decisions_and_byte_backups(self):
        original = self.fixture()
        store = tasks.TaskStore(root=self.root)
        before = store.decision(self.key)
        self.assertTrue(store.migrate())
        raw = json.loads(self.canonical.read_bytes())
        self.assertEqual(raw['dispatched'], json.loads(original[self.legacy]))
        self.assertEqual(raw['handled'], json.loads(original[self.handled]))
        self.assertEqual(raw['queue'], json.loads(original[self.queue]))
        self.assertEqual(store.decision(self.key), before)
        backup = self.root / raw['migration']['backup']
        for path, value in original.items():
            self.assertEqual((backup / 'legacy' / path.relative_to(self.root)).read_bytes(), value)
            self.assertEqual(path.read_bytes(), value)
        snapshot = self.canonical.read_bytes()
        self.assertFalse(store.migrate())
        self.assertEqual(self.canonical.read_bytes(), snapshot)

    def test_stale_writers_merge_different_partitions(self):
        first, second = tasks.TaskStore(root=self.root), tasks.TaskStore(root=self.root)
        first.mark(self.key, 'pending')
        tasks.record_handled(self.handled, [self.key], 'Done')
        with second.transaction() as ledger:
            ledger['queue']['extension'] = {'preserved': True}
        latest = tasks.TaskStore(root=self.root)
        self.assertTrue(latest.is_active(self.key))
        self.assertEqual(latest.data[self.key]['status'], 'pending')
        self.assertEqual(latest.handled[self.key]['note'], 'Done')
        self.assertEqual(latest.queue['extension'], {'preserved': True})
        self.assertFalse(self.legacy.exists())
        self.assertFalse(self.handled.exists())

    def test_legacy_helpers_read_and_write_canonical_state(self):
        store = tasks.TaskStore(root=self.root)
        store.mark(self.key, 'dropped')
        tasks.record_handled(self.handled, [self.key], 'New evidence', 'open')
        self.assertFalse(tasks.TaskStore(root=self.root).is_active(self.key))
        self.assertEqual(tasks.load_handled(self.handled)[self.key]['status'], 'open')
        with store.transaction() as ledger:
            ledger['queue']['issues'][self.key] = {
                'stage': 'probe', 'signals': {}, 'events': []}
        self.assertEqual(tasks.issue_states(self.root)[self.key]['stage'], 'probe')
        self.assertFalse(self.queue.exists())

    def test_legacy_drift_including_new_and_deleted_files_fails_closed(self):
        for kind in ('changed', 'created', 'deleted'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder:
                root = Path(folder).resolve()
                old = root / 'dispatched.json'
                if kind != 'created':
                    self.write(old, {})
                store = tasks.TaskStore(root=root)
                store.migrate()
                before = store.path.read_bytes()
                if kind == 'deleted':
                    old.unlink()
                else:
                    self.write(old, {self.key: {'status': 'running'}})
                with self.assertRaisesRegex(RuntimeError, '[Ll]egacy|旧'):
                    tasks.TaskStore(root=root)
                with self.assertRaisesRegex(RuntimeError, '[Ll]egacy|旧'):
                    store.mark(self.key, 'pending')
                self.assertEqual(store.path.read_bytes(), before)

    def test_transaction_failure_or_invalid_data_never_publishes(self):
        store = tasks.TaskStore(root=self.root)
        store.mark(self.key, 'pending')
        before = self.canonical.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'abort'):
            with store.transaction() as ledger:
                ledger['dispatched'][self.key]['status'] = 'running'
                raise RuntimeError('abort')
        self.assertEqual(self.canonical.read_bytes(), before)
        with self.assertRaises(ValueError):
            with store.transaction() as ledger:
                ledger['queue']['issues'][self.key] = {'stage': 'typo'}
        self.assertEqual(self.canonical.read_bytes(), before)
        self.assertEqual(store.status_of(self.key), 'pending')

    def test_atomic_publish_failure_preserves_all_legacy_and_retry_succeeds(self):
        original = self.fixture()
        store = tasks.TaskStore(root=self.root)
        write = tasks.atomic_write_json

        def fail_canonical(path, data):
            if Path(path) == self.canonical:
                raise OSError('disk full')
            return write(path, data)

        with patch.object(tasks, 'atomic_write_json', side_effect=fail_canonical), self.assertRaises(OSError):
            store.migrate()
        self.assertFalse(self.canonical.exists())
        self.assertEqual({p: p.read_bytes() for p in original}, original)
        self.assertTrue(store.migrate())

    def test_invalid_legacy_prevents_migration_and_any_backup(self):
        self.write(self.queue, {'version': 1, 'issues': {self.key: {'stage': 'typo'}}, 'prs': {}})
        with self.assertRaises(ValueError):
            tasks.TaskStore(root=self.root).migrate()
        self.assertFalse(self.canonical.exists())
        self.assertFalse((self.root / 'task_state.backups').exists())

    def test_corrupt_canonical_never_falls_back_to_legacy(self):
        self.fixture()
        self.canonical.write_bytes(b'{}')
        with self.assertRaises(ValueError):
            tasks.TaskStore(root=self.root)
        self.canonical.write_bytes(b'{broken')
        with self.assertRaises(ValueError):
            tasks.TaskStore(root=self.root)

    def test_custom_legacy_path_is_recorded_for_future_root_readers(self):
        path = self.root / 'custom.json'
        self.write(path, {self.key: {'status': 'closed', 'ts': 1}})
        store = tasks.TaskStore(path)
        store.migrate()
        self.assertEqual(tasks.TaskStore(root=self.root).status_of(self.key), 'closed')
        self.write(path, {})
        with self.assertRaises(RuntimeError):
            tasks.TaskStore(root=self.root)

    def test_all_source_locks_protect_migration_and_transactions(self):
        store = tasks.TaskStore(root=self.root)
        for path in (self.canonical, self.legacy, self.handled, self.queue):
            with self.subTest(path=path), file_lock(path), self.assertRaises(RuntimeError):
                store.migrate()
        self.assertFalse(self.canonical.exists())
        store.migrate()
        for path in (self.legacy, self.handled, self.queue):
            with self.subTest(path=path), file_lock(path), self.assertRaises(RuntimeError):
                store.mark(self.key, 'running')

    def test_rejected_mark_does_not_migrate_and_active_reopen_is_protected(self):
        self.write(self.legacy, {self.key: {'status': 'running', 'ts': 1}})
        store = tasks.TaskStore(root=self.root)
        self.assertFalse(store.mark(self.key, 'running', only_if_inactive=True))
        self.assertFalse(self.canonical.exists())
        tasks.record_handled(self.handled, [self.key], 'Resume', 'open')
        self.assertTrue(tasks.TaskStore(root=self.root).is_active(self.key))

    def test_export_uses_latest_data_and_does_not_overwrite_existing_targets(self):
        original = self.fixture()
        store = tasks.TaskStore(root=self.root)
        store.migrate()
        store.mark(self.key, 'closed')
        tasks.record_handled(self.handled, [self.key], 'New evidence', 'open')
        destination = self.root / 'rollback-copy'
        store.export_legacy(destination)
        exported = tasks.TaskStore(root=destination)
        self.assertFalse(exported.is_active(self.key))
        self.assertEqual(exported.status_of(self.key), 'closed')
        self.assertEqual(exported.queue, store.queue)
        self.assertFalse((destination / 'task_state.json').exists())
        self.assertEqual({p: p.read_bytes() for p in original}, original)
        with self.assertRaises((ValueError, FileExistsError)):
            store.export_legacy(destination)
        with self.assertRaises((ValueError, FileExistsError)):
            store.export_legacy(self.root)

    def test_cli_migrate_and_export_are_explicit_and_idempotent(self):
        script = str(Path(tasks.__file__))
        result = subprocess.run([sys.executable, '-S', script, '--root', str(self.root), 'migrate'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        before = self.canonical.read_bytes()
        result = subprocess.run([sys.executable, '-S', script, 'migrate', '--root', str(self.root)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.canonical.read_bytes(), before)
        result = subprocess.run([sys.executable, '-S', script, 'export-legacy',
                                 str(self.root / 'export'), '--root', str(self.root)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / 'export/work_queue.json').exists())

    def test_alias_update_retires_active_alias_without_normalizing_other_tasks(self):
        untouched = {'status': 'pending', 'ts': 2, 'extension': {'x': True}}
        self.write(self.legacy, {'Owner/Repo#1': {'status': 'running', 'ts': 1},
                                 self.key: {'status': 'pending', 'ts': 2},
                                 'Other/Repo#2': untouched})
        store = tasks.TaskStore(root=self.root)
        store.migrate()
        store.mark(self.key, 'closed')
        raw = json.loads(self.canonical.read_bytes())['dispatched']
        self.assertNotIn('Owner/Repo#1', raw)
        self.assertEqual(raw['Other/Repo#2'], untouched)
        self.assertEqual(tasks.TaskStore(root=self.root).status_of(self.key), 'closed')

    def test_handled_update_preserves_extensions_history_and_other_aliases(self):
        previous = {'at': '2026-01-02T00:00:00Z', 'note': 'Newest', 'extension': [1],
                    'history': [{'at': '2025-01-01T00:00:00Z', 'note': 'Old'}]}
        older = {'at': '2026-01-01T00:00:00Z', 'note': 'Alias'}
        self.write(self.handled, {self.key: previous, 'Owner/Repo#1': older})
        tasks.record_handled(self.handled, [self.key], 'Reopen', 'open')
        entry = tasks.load_handled(self.handled)[self.key]
        self.assertEqual(entry['extension'], [1])
        self.assertEqual(len(entry['history']), 3)
        self.assertIn(older, entry['history'])

    def test_backup_failure_leaves_sources_unchanged_and_no_authority(self):
        original = self.fixture()
        store = tasks.TaskStore(root=self.root)
        write = tasks.atomic_write_json

        def fail_manifest(path, data):
            if Path(path).name == 'manifest.json':
                raise OSError('backup interrupted')
            return write(path, data)

        with patch.object(tasks, 'atomic_write_json', side_effect=fail_manifest), self.assertRaises(OSError):
            store.mark(self.key, 'closed')
        self.assertFalse(self.canonical.exists())
        self.assertEqual({p: p.read_bytes() for p in original}, original)
        self.assertEqual(store.status_of(self.key), 'running')
        self.assertTrue(store.migrate())

    def test_backup_manifest_cannot_replace_custom_source_named_manifest(self):
        source = self.root / 'manifest.json'
        self.write(source, {self.key: {'status': 'closed'}})
        original = source.read_bytes()
        store = tasks.TaskStore(source)
        store.migrate()
        raw = json.loads(self.canonical.read_bytes())
        self.assertEqual((self.root / raw['migration']['backup'] / 'legacy/manifest.json').read_bytes(), original)

    def test_transaction_refuses_changed_provenance_and_escaping_paths(self):
        store = tasks.TaskStore(root=self.root)
        store.migrate()
        original = self.canonical.read_bytes()
        with self.assertRaises(ValueError):
            with store.transaction() as ledger:
                ledger['migration']['sources']['handled']['sha256'] = 'f' * 64
        self.assertEqual(self.canonical.read_bytes(), original)
        for path in ('../outside.json', str(self.root.parent / 'outside.json'), 'task_state.json'):
            with self.subTest(path=path):
                raw = json.loads(original)
                raw['migration']['sources']['handled']['path'] = path
                self.write(self.canonical, raw)
                with self.assertRaises(ValueError):
                    tasks.TaskStore(root=self.root)

    def test_missing_sources_have_null_fingerprints(self):
        self.write(self.legacy, {})
        tasks.TaskStore(root=self.root).migrate()
        sources = json.loads(self.canonical.read_bytes())['migration']['sources']
        self.assertIsNotNone(sources['dispatched']['sha256'])
        self.assertIsNone(sources['handled']['sha256'])
        self.assertIsNone(sources['queue']['sha256'])

    def test_export_rejects_directory_containing_a_missing_active_source(self):
        store = tasks.TaskStore(root=self.root)
        with self.assertRaises(ValueError):
            store.export_legacy(self.root / 'tools')
        self.assertFalse(self.handled.exists())
        self.assertFalse(self.canonical.exists())

    def test_export_failure_never_creates_completion_manifest_or_alters_authority(self):
        store = tasks.TaskStore(root=self.root)
        store.mark(self.key, 'running')
        original = self.canonical.read_bytes()
        destination = self.root / 'failed-export'
        write = tasks.atomic_write_json

        def fail_second_file(path, value):
            if Path(path) == destination / 'tools/inbox_handled.json':
                raise OSError('export interrupted')
            return write(path, value)

        with patch.object(tasks, 'atomic_write_json', side_effect=fail_second_file), self.assertRaises(OSError):
            store.export_legacy(destination)
        self.assertFalse((destination / 'manifest.json').exists())
        self.assertEqual(self.canonical.read_bytes(), original)

    def test_legacy_write_during_transaction_is_detected_before_publish(self):
        store = tasks.TaskStore(root=self.root)
        store.migrate()
        original = self.canonical.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'Legacy'):
            with store.transaction() as ledger:
                ledger['dispatched'][self.key] = {'status': 'pending'}
                self.write(self.legacy, {self.key: {'status': 'running'}})
        self.assertEqual(self.canonical.read_bytes(), original)

    def test_cli_invalid_source_returns_failure_without_publication(self):
        self.write(self.queue, {'version': 99, 'issues': {}, 'prs': {}})
        result = subprocess.run([sys.executable, '-S', str(Path(tasks.__file__)),
                                 'migrate', '--root', str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.canonical.exists())

    def test_invalid_dispatch_transaction_never_publishes_an_unreadable_ledger(self):
        store = tasks.TaskStore(root=self.root)
        store.mark(self.key, 'pending')
        original = self.canonical.read_bytes()
        for status in ([], {}, 1):
            with self.subTest(status=status), self.assertRaises(ValueError):
                with store.transaction() as ledger:
                    ledger['dispatched'][self.key]['status'] = status
            self.assertEqual(self.canonical.read_bytes(), original)
            self.assertEqual(tasks.TaskStore(root=self.root).status_of(self.key), 'pending')
        with self.assertRaises(ValueError):
            with store.transaction() as ledger:
                ledger['dispatched'][1] = {'status': 'pending'}
        self.assertEqual(self.canonical.read_bytes(), original)
        with store.transaction() as ledger:
            ledger['dispatched'][self.key]['status'] = 'future_unknown_state'
        self.assertTrue(tasks.TaskStore(root=self.root).is_active(self.key))

    def test_export_cannot_occupy_a_current_or_future_state_file_path(self):
        store = tasks.TaskStore(root=self.root)
        for path in (self.canonical, self.legacy, self.handled, self.queue,
                     self.canonical / 'export', self.legacy / 'export'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                store.export_legacy(path)
            self.assertFalse(path.exists())
        self.assertFalse(self.canonical.exists())

    def test_stale_export_reloads_source_paths_before_validating_destination(self):
        stale = tasks.TaskStore(root=self.root)
        custom = self.root / 'custom-dispatch.json'
        tasks.TaskStore(custom).migrate()
        with self.assertRaises(ValueError):
            stale.export_legacy(custom)
        self.assertFalse(custom.exists())
        self.assertEqual(tasks.TaskStore(root=self.root).data, {})

    def test_separate_processes_preserve_dispatch_and_handled_updates(self):
        script = (
            'import sys, time\n'
            'from pathlib import Path\n'
            'sys.path.insert(0, sys.argv[1])\n'
            'from task_state import TaskStore, record_handled\n'
            'root = Path(sys.argv[2])\n'
            'for attempt in range(100):\n'
            '    try:\n'
            '        if sys.argv[3] == "dispatch":\n'
            '            TaskStore(root=root).mark("owner/repo#1", "pending")\n'
            '        else:\n'
            '            record_handled(root / "tools/inbox_handled.json", ["owner/repo#1"], "Done")\n'
            '        break\n'
            '    except RuntimeError:\n'
            '        if attempt == 99: raise\n'
            '        time.sleep(0.01)\n'
        )
        processes = [subprocess.Popen([sys.executable, '-S', '-c', script,
                                      str(Path(tasks.__file__).parent), str(self.root), mode],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for mode in ('dispatch', 'handled')]
        for process in processes:
            stdout, stderr = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 0, stdout + stderr)
        store = tasks.TaskStore(root=self.root)
        self.assertEqual(store.status_of(self.key), 'pending')
        self.assertEqual(store.handled[self.key]['note'], 'Done')
        self.assertFalse(self.legacy.exists())
        self.assertFalse(self.handled.exists())

    def test_windows_resolve_prefix_variants_keep_the_same_source_identity(self):
        # Simulate the missing-path winerror race without accessing a UNC server.
        for root in (r'C:\tasks', r'\\server\share\tasks'):
            for prefix_root, prefix_source in ((False, False), (False, True), (True, False), (True, True)):
                with self.subTest(root=root, prefix_root=prefix_root, prefix_source=prefix_source):
                    ordinary = PureWindowsPath(root)
                    extended = ('\\\\?\\UNC\\' + root[2:] if root.startswith('\\\\')
                                else '\\\\?\\' + root)
                    store = tasks.TaskStore.__new__(tasks.TaskStore)
                    store.root = Path(extended if prefix_root else root)
                    store.path = store.root / 'task_state.json'
                    source = Path(str(ordinary / 'tools/inbox_handled.json'))

                    def resolve(path, *args, **kwargs):
                        value = PureWindowsPath(str(path))
                        if value == PureWindowsPath(str(source)):
                            return PureWindowsPath(extended if prefix_source else root) / 'tools/inbox_handled.json'
                        return value

                    with patch.object(tasks.Path, 'resolve', autospec=True, side_effect=resolve):
                        self.assertEqual(store._relative(source), 'tools/inbox_handled.json')

    def test_windows_resolve_prefix_never_allows_real_escapes_or_the_canonical_file(self):
        for root, escaped in ((r'C:\tasks', r'\\?\C:\elsewhere\old.json'),
                              (r'C:\tasks', r'\\?\D:\tasks\old.json'),
                              (r'\\server\share\tasks', r'\\?\UNC\other\share\tasks\old.json'),
                              (r'\\server\share\tasks', r'\\?\UNC\server\other\tasks\old.json')):
            with self.subTest(root=root, escaped=escaped):
                store = tasks.TaskStore.__new__(tasks.TaskStore)
                store.root = Path(root)
                store.path = store.root / 'task_state.json'
                source = Path(str(PureWindowsPath(root) / 'old.json'))

                def resolve(path, *args, **kwargs):
                    value = PureWindowsPath(str(path))
                    return PureWindowsPath(escaped) if value == PureWindowsPath(str(source)) else value

                with patch.object(tasks.Path, 'resolve', autospec=True, side_effect=resolve):
                    with self.assertRaises(ValueError):
                        store._relative(source)
                    with self.assertRaises(ValueError):
                        store._relative(store.path)


if __name__ == '__main__':
    unittest.main()
