"""Tarball preparation preserves existing paths and confines temporary extraction."""
from concurrent.futures import ThreadPoolExecutor
import io
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import auto_run as a


class TarballCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(a, 'WORKDIR', str(self.root)))

    def archive(self, extra=(), root='project-main'):
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode='w:gz') as archive:
            content = os.urandom(2048)
            member = tarfile.TarInfo(f'{root}/source.py')
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
            for member, content in extra:
                archive.addfile(member, io.BytesIO(content) if content is not None else None)
        payload = output.getvalue()
        self.assertGreater(len(payload), 1000)
        return SimpleNamespace(returncode=0, stdout=payload)

    def directories(self):
        return sorted(path.name for path in self.root.iterdir() if path.is_dir())

    def test_invalid_repositories_do_not_download_or_create_paths(self):
        for repo in ('../project', 'owner/.', 'owner/..', 'owner/project/extra',
                     'owner//project', 'owner/C:\\outside', 'owner\\project', ''):
            with self.subTest(repo=repo), patch.object(a.subprocess, 'run') as download:
                with self.assertRaises(ValueError):
                    a._clone_via_tarball(repo)
                download.assert_not_called()
                self.assertEqual(list(self.root.iterdir()), [])

    def test_existing_directory_and_file_are_rejected_before_download(self):
        for kind in ('directory', 'file'):
            with self.subTest(kind=kind):
                target = self.root / f'project-{kind}'
                if kind == 'directory':
                    target.mkdir()
                    marker = target / 'unfinished.py'
                else:
                    marker = target
                marker.write_bytes(b'local work')
                with patch.object(a.subprocess, 'run',
                                  return_value=self.archive(root=f'project-{kind}-main')) as download:
                    with self.assertRaises((RuntimeError, FileExistsError)):
                        a._clone_via_tarball(f'another-owner/project-{kind}')
                download.assert_not_called()
                self.assertEqual(marker.read_bytes(), b'local work')

    def test_dangling_symlink_is_rejected_before_download(self):
        target = self.root / 'project'
        try:
            target.symlink_to(self.root / 'missing')
        except (OSError, NotImplementedError) as error:
            self.skipTest(f'Symlink creation is unavailable: {error}')
        with patch.object(a.subprocess, 'run', return_value=self.archive()) as download:
            with self.assertRaises((RuntimeError, FileExistsError)):
                a._clone_via_tarball('owner/project')
        download.assert_not_called()
        self.assertTrue(target.is_symlink())

    def test_fresh_checkout_keeps_the_existing_fixer_path_and_cleans_staging(self):
        with patch.object(a.subprocess, 'run', return_value=self.archive()):
            result = Path(a._clone_via_tarball('owner/project'))
        self.assertEqual(result, self.root / 'project')
        self.assertTrue((result / 'source.py').is_file())
        self.assertEqual(self.directories(), ['project'])

    def test_invalid_archives_and_source_roots_leave_no_staging(self):
        extra = tarfile.TarInfo('unrelated/file.py')
        for response in (SimpleNamespace(returncode=0, stdout=b'invalid' * 400),
                         self.archive(root='other-main'), self.archive(((extra, b''),))):
            with self.subTest(response=response.stdout[:10]), \
                    patch.object(a.subprocess, 'run', return_value=response):
                with self.assertRaises((RuntimeError, tarfile.TarError)):
                    a._clone_via_tarball('owner/project')
                self.assertEqual(self.directories(), [])

    def test_archive_cannot_write_outside_its_staging(self):
        member = tarfile.TarInfo('../escaped.py')
        member.size = 6
        with patch.object(a.subprocess, 'run', return_value=self.archive(((member, b'escape'),))):
            with self.assertRaises((RuntimeError, tarfile.TarError)):
                a._clone_via_tarball('owner/project')
        self.assertFalse((self.root / 'escaped.py').exists())
        self.assertEqual(self.directories(), [])

    def test_relocated_link_boundary_without_symlink_creation(self):
        # Simulate link metadata after real extraction, including a symlink followed by '..'.
        member = tarfile.TarInfo('project-main/link.py')
        alias = tarfile.TarInfo('project-main/a')
        nested = tarfile.TarInfo('project-main/sub/nested-link.py')
        response = self.archive(((member, b''), (alias, b''), (nested, b'')))
        islink, realpath, readlink = os.path.islink, os.path.realpath, os.readlink
        def simulated_islink(path):
            return Path(path).name in {'link.py', 'a', 'nested-link.py'} or islink(path)
        def simulated_realpath(path):
            if Path(path).name == 'link.py':
                return str(Path(path).with_name('source.py'))
            if Path(path).name == 'a':
                return str(Path(path).parent)
            if Path(path).name == 'nested-link.py':
                return str(Path(path).parent.parent / 'source.py')
            return realpath(path)
        def simulated_readlink(path):
            return {'link.py': target, 'a': '.', 'nested-link.py': '../source.py'}.get(
                Path(path).name) or readlink(path)
        for target, rejected in (('../project-main/source.py', True),
                                 ('a/../project-main/source.py', True), ('source.py', False)):
            with self.subTest(target=target), \
                    patch.object(a.subprocess, 'run', return_value=response), \
                    patch.object(a.os.path, 'islink', side_effect=simulated_islink), \
                    patch.object(a.os.path, 'realpath', side_effect=simulated_realpath), \
                    patch.object(a.os, 'readlink', side_effect=simulated_readlink):
                if rejected:
                    with self.assertRaisesRegex(RuntimeError, '链接越出'):
                        a._clone_via_tarball('owner/project')
                    self.assertEqual(self.directories(), [])
                else:
                    result = Path(a._clone_via_tarball('owner/project'))
                    self.assertTrue((result / 'source.py').is_file())
                    self.assertTrue((result / 'sub/nested-link.py').is_file())

    def test_real_links_remain_inside_the_relocated_checkout(self):
        probe = self.root / 'symlink-probe'
        try:
            probe.symlink_to(self.root / 'missing')
        except (OSError, NotImplementedError) as error:
            self.skipTest(f'Symlink creation is unavailable: {error}')
        probe.unlink()
        for target, rejected in (('../project-main/source.py', True),
                                 ('a/../project-main/source.py', True), ('source.py', False)):
            member = tarfile.TarInfo('project-main/link.py')
            member.type, member.linkname = tarfile.SYMTYPE, target
            alias = tarfile.TarInfo('project-main/a')
            alias.type, alias.linkname = tarfile.SYMTYPE, '.'
            nested = tarfile.TarInfo('project-main/sub/nested-link.py')
            nested.type, nested.linkname = tarfile.SYMTYPE, '../source.py'
            with self.subTest(target=target), patch.object(
                    a.subprocess, 'run', return_value=self.archive(
                        ((member, None), (alias, None), (nested, None)))):
                if rejected:
                    with self.assertRaisesRegex(RuntimeError, '链接越出'):
                        a._clone_via_tarball('owner/project')
                    self.assertEqual(self.directories(), [])
                else:
                    result = Path(a._clone_via_tarball('owner/project'))
                    self.assertTrue((result / 'link.py').is_symlink())
                    self.assertEqual((result / 'link.py').resolve(), result / 'source.py')
                    self.assertEqual((result / 'sub/nested-link.py').resolve(), result / 'source.py')

    def test_target_created_during_download_is_preserved(self):
        target = self.root / 'project'
        response = self.archive()
        def download(*args, **kwargs):
            target.mkdir()
            (target / 'other-call.py').write_bytes(b'other work')
            return response
        with patch.object(a.subprocess, 'run', side_effect=download):
            with self.assertRaises((RuntimeError, FileExistsError)):
                a._clone_via_tarball('owner/project')
        self.assertEqual((target / 'other-call.py').read_bytes(), b'other work')
        self.assertFalse((target / 'source.py').exists())
        self.assertEqual(self.directories(), ['project'])

    def test_publish_failure_preserves_target_files_and_cleans_only_staging(self):
        target = self.root / 'project'
        second = tarfile.TarInfo('project-main/second.py')
        response = self.archive(((second, b''),))
        rename = os.rename
        published = []
        def fail_after_one_file(source, destination):
            if published:
                (target / 'external.py').write_bytes(b'keep this too')
                raise OSError('publish interrupted')
            rename(source, destination)
            published.append(Path(destination))
        with patch.object(a.subprocess, 'run', return_value=response), \
                patch.object(a.os, 'rename', side_effect=fail_after_one_file):
            with self.assertRaisesRegex(OSError, 'publish interrupted'):
                a._clone_via_tarball('owner/project')
        self.assertTrue(published[0].is_file())
        self.assertEqual((target / 'external.py').read_bytes(), b'keep this too')
        self.assertEqual(self.directories(), ['project'])

    def test_second_call_cannot_replace_the_first_calls_checkout(self):
        entered, release = threading.Event(), threading.Event()
        counter_lock = threading.Lock()
        calls = 0
        response = self.archive()
        def download(*args, **kwargs):
            nonlocal calls
            with counter_lock:
                calls += 1
                first_call = calls == 1
            if first_call:
                entered.set()
                if not release.wait(5):
                    raise RuntimeError('Timed out waiting for the competing call')
            return response
        with patch.object(a.subprocess, 'run', side_effect=download), \
                ThreadPoolExecutor(max_workers=1) as executor:
            first = executor.submit(a._clone_via_tarball, 'owner/project')
            try:
                self.assertTrue(entered.wait(5))
                with self.assertRaises((RuntimeError, FileExistsError)):
                    a._clone_via_tarball('another-owner/project')
            finally:
                release.set()
            result = Path(first.result(timeout=5))
        self.assertEqual(calls, 1)
        self.assertTrue((result / 'source.py').is_file())
        self.assertEqual(self.directories(), ['project'])


if __name__ == '__main__':
    unittest.main()
