import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EMPTY_ZIP = b'PK\x05\x06' + b'\0' * 18
ZIP_SHA = '8739c76e681f900923b900c9df0ef75cf421d39cabb54650c4b9ad19b6a76d85'
OLD_ZIP = 'provingkit-rolecasting-0.1.0-alpha.7-agent-plugins.zip'
NEW_ZIP = 'provingkit-rolecasting-0.1.0-alpha.7.zip'
OLD_SIDECAR = (ZIP_SHA + '  provingkit-rolecasting-0.1.0-alpha.7-agent-plugins.zip\n').encode()
NEW_SIDECAR = (ZIP_SHA + '  provingkit-rolecasting-0.1.0-alpha.7.zip\n').encode()


class ArchiveAliasCLITests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source = self.root / 'downloaded'
        self.source.mkdir()
        self.output = self.root / 'prepared'
        (self.source / OLD_ZIP).write_bytes(EMPTY_ZIP)
        (self.source / (OLD_ZIP + '.sha256')).write_bytes(OLD_SIDECAR)
        self.inventory = {
            'release_id': 123,
            'tag': 'v0.1.0-alpha.7',
            'preserve_original_assets': True,
            'original_asset_count': 4,
            'aliases': [{
                'plugin': 'rolecasting',
                'old_zip': OLD_ZIP,
                'old_asset_id': 10,
                'old_sidecar': OLD_ZIP + '.sha256',
                'old_sidecar_id': 11,
                'new_zip': NEW_ZIP,
                'new_sidecar': NEW_ZIP + '.sha256',
                'zip_sha256': ZIP_SHA,
                'zip_size': 22,
                'new_sidecar_sha256': '63a1956ef191c45a26ff6581c57222b95fffb59e3b830c8a8a3cd729da789f42',
                'new_sidecar_size': 107,
            }],
        }
        self.inventory_path = self.root / 'inventory.json'

    def invoke(self, *extra, raw_inventory=None):
        self.inventory_path.write_text(raw_inventory if raw_inventory is not None else json.dumps(self.inventory), encoding='utf-8')
        return subprocess.run([
            sys.executable, str(ROOT / 'scripts/prepare_release_archive_aliases.py'),
            '--inventory', str(self.inventory_path), '--source-dir', str(self.source),
            '--output-dir', str(self.output), *extra,
        ], capture_output=True, text=True, check=False)

    def test_prepares_canonical_names_without_changing_original_payloads(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual((self.output / NEW_ZIP).read_bytes(), EMPTY_ZIP)
        self.assertEqual((self.output / (NEW_ZIP + '.sha256')).read_bytes(), NEW_SIDECAR)
        self.assertEqual((self.source / OLD_ZIP).read_bytes(), EMPTY_ZIP)
        self.assertEqual((self.source / (OLD_ZIP + '.sha256')).read_bytes(), OLD_SIDECAR)
        alias = receipt['aliases'][0]
        self.assertEqual(alias['new_zip'], NEW_ZIP)
        self.assertEqual(alias['new_zip_url'], 'https://github.com/nisavid/provingkit/releases/download/v0.1.0-alpha.7/provingkit-rolecasting-0.1.0-alpha.7.zip')
        self.assertEqual(alias['old_zip_url'], 'https://github.com/nisavid/provingkit/releases/download/v0.1.0-alpha.7/provingkit-rolecasting-0.1.0-alpha.7-agent-plugins.zip')
        self.assertFalse(receipt['release_snapshot_verified'])
        self.assertFalse(receipt['public_downloads_verified'])


    def test_rejects_inventory_that_keeps_the_legacy_basename(self):
        self.inventory['aliases'][0]['new_zip'] = OLD_ZIP
        self.inventory['aliases'][0]['new_sidecar'] = OLD_ZIP + '.sha256'
        result = self.invoke()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('canonical', result.stderr)
        self.assertFalse(self.output.exists())


    def test_rejects_payload_changed_since_the_verified_inventory(self):
        (self.source / OLD_ZIP).write_bytes(EMPTY_ZIP[:-1] + b'X')
        result = self.invoke()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('digest', result.stderr)
        self.assertFalse(self.output.exists())


    def test_rejects_source_checksum_naming_a_different_archive(self):
        (self.source / (OLD_ZIP + '.sha256')).write_bytes(NEW_SIDECAR)
        result = self.invoke()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('source checksum', result.stderr)
        self.assertFalse(self.output.exists())


    def release_snapshot(self):
        release = {
            'id': 123, 'tag_name': 'v0.1.0-alpha.7',
            'assets': [
                {'id': 10, 'name': OLD_ZIP, 'size': 22, 'digest': 'sha256:' + ZIP_SHA},
                {'id': 11, 'name': OLD_ZIP + '.sha256', 'size': len(OLD_SIDECAR),
                 'digest': 'sha256:afae78ac627bcf786a665e4b034d42e07426fe37b831de2342361d77ada41865'},
                {'id': 20, 'name': NEW_ZIP, 'size': 22, 'digest': 'sha256:' + ZIP_SHA},
                {'id': 21, 'name': NEW_ZIP + '.sha256', 'size': 107,
                 'digest': 'sha256:63a1956ef191c45a26ff6581c57222b95fffb59e3b830c8a8a3cd729da789f42'},
            ],
        }
        base = 'https://github.com/nisavid/provingkit/releases/download/v0.1.0-alpha.7/'
        for asset in release['assets']:
            asset['browser_download_url'] = base + asset['name']
        return release

    def invoke_release(self, release):
        path = self.root / 'release.json'
        path.write_text(json.dumps(release))
        return self.invoke('--release', str(path))

    def test_rejects_explicit_null_release_snapshot_before_preparing_files(self):
        result = self.invoke_release(None)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('release snapshot', result.stderr)
        self.assertFalse(self.output.exists())

    def test_checks_release_snapshot_keeps_old_ids_and_canonical_links(self):
        release = self.release_snapshot()
        result = self.invoke_release(release)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt['release_snapshot_verified'])
        self.assertFalse(receipt['public_downloads_verified'])
        self.assertEqual(receipt['aliases'][0]['old_asset_id'], 10)
        self.assertEqual(json.loads((self.root / 'release.json').read_text()), release)


    def test_refuses_conflicting_output_before_writing_any_alias(self):
        self.output.mkdir()
        conflict = self.output / (NEW_ZIP + '.sha256')
        conflict.write_bytes(b'existing unrelated contents')
        result = self.invoke()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(conflict.read_bytes(), b'existing unrelated contents')
        self.assertFalse((self.output / NEW_ZIP).exists())


    def test_rejects_ambiguous_duplicate_json_fields(self):
        text = json.dumps(self.inventory).replace('"release_id": 123', '"release_id": 999, "release_id": 123')
        result = self.invoke(raw_inventory=text)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('duplicate', result.stderr)
        self.assertFalse(self.output.exists())


    def test_reuses_identical_prepared_files(self):
        first = self.invoke()
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self.invoke()
        self.assertEqual(second.returncode, 0, second.stderr)
        receipt = json.loads(second.stdout)
        self.assertEqual(receipt['created_files'], [])
        self.assertEqual(set(receipt['reused_files']), {NEW_ZIP, NEW_ZIP + '.sha256'})
        self.assertEqual((self.output / NEW_ZIP).read_bytes(), EMPTY_ZIP)
        self.assertEqual((self.output / (NEW_ZIP + '.sha256')).read_bytes(), NEW_SIDECAR)

    def test_snapshot_rejects_changed_original_asset_identity(self):
        release = self.release_snapshot()
        release['assets'][0]['id'] = 999
        result = self.invoke_release(release)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('original asset id', result.stderr)
        self.assertFalse(self.output.exists())

    def test_snapshot_rejects_old_url_pointing_to_the_new_alias(self):
        release = self.release_snapshot()
        release['assets'][0]['browser_download_url'] = release['assets'][2]['browser_download_url']
        result = self.invoke_release(release)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('URL', result.stderr)
        self.assertFalse(self.output.exists())

    def test_snapshot_rejects_alias_digest_for_other_bytes(self):
        release = self.release_snapshot()
        release['assets'][2]['digest'] = 'sha256:' + '0' * 64
        result = self.invoke_release(release)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('digest', result.stderr)
        self.assertFalse(self.output.exists())

    def test_rejects_claude_archive_as_a_legacy_standard_source(self):
        self.inventory['aliases'][0]['old_zip'] = 'provingkit-rolecasting-0.1.0-alpha.7-claude.zip'
        result = self.invoke()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('legacy standard', result.stderr)
        self.assertFalse(self.output.exists())

    def test_rejects_duplicate_alias_destinations(self):
        self.inventory['aliases'].append(dict(self.inventory['aliases'][0]))
        result = self.invoke()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('unique', result.stderr)
        self.assertFalse(self.output.exists())

    def test_snapshot_rejects_nonstring_download_url(self):
        release = self.release_snapshot()
        release['assets'][0]['browser_download_url'] = 42
        result = self.invoke_release(release)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('URL must be a string', result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
