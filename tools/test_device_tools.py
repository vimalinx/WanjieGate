import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.device_tools import discover, launch_obsidian

class DeviceToolsTests(unittest.TestCase):
    def test_discovery_only_reads_app_and_vault_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'Obsidian.app').mkdir(); vault=root/'Notes'; vault.mkdir()
            config=root/'obsidian.json'; config.write_text(json.dumps({'vaults':{'abc':{'path':str(vault)}}}))
            profile=discover([root], config)
            self.assertTrue(profile['obsidian']['installed'])
            self.assertEqual(profile['obsidian']['vaults'],[{'id':'abc','name':'Notes'}])
            self.assertNotIn(str(vault),json.dumps(profile))
    def test_handoff_is_deduplicated_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);vault=root/'Notes';vault.mkdir();config=root/'obsidian.json'
            config.write_text(json.dumps({'vaults':{'abc':{'path':str(vault)}}}))
            with patch('backend.device_tools.subprocess.run') as run:
                request={'vault':'abc','id':'bubble-1','title':'../title','content':'note with spaces'}
                first=launch_obsidian(request,root,config)
                second=launch_obsidian(request,root,config)
                self.assertEqual(run.call_count,1)
                self.assertTrue(second['reused'])
                uri=run.call_args.args[0][-1]
                self.assertIn('obsidian://new?',uri)
                self.assertNotIn('overwrite',uri)
                self.assertNotIn('+',uri)
                self.assertIn('note%20with%20spaces',uri)
                with self.assertRaises(ValueError):launch_obsidian({**request,'vault':'unknown'},root,config)
