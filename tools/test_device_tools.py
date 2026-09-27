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

class NativeDiscoveryTests(unittest.TestCase):
    def test_installed_allowlist_and_defaults(self):
        import plistlib
        from backend.device_tools import SUPPORTED
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for key in ('kimi','cursor','stocks','reminders'):
                spec=SUPPORTED[key];app=root/spec['file'];(app/'Contents').mkdir(parents=True)
                (app/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':spec['bundle']}))
            profile=discover([root],root/'missing.json')
            self.assertEqual(profile['defaults']['learning'],'app:kimi')
            self.assertEqual(profile['defaults']['development'],'app:cursor')
            self.assertEqual(profile['defaults']['market'],'app:stocks')
            self.assertFalse(profile['historyCollected'])
    def test_launcher_rejects_unknown_or_missing_app(self):
        from backend.device_tools import launch_app
        with tempfile.TemporaryDirectory() as d:
            with patch('backend.device_tools.subprocess.run') as run:
                for tool in ('../../evil','cursor'):
                    with self.assertRaises(ValueError):launch_app({'tool':tool},[Path(d)])
                run.assert_not_called()

class ChromeSearchTests(unittest.TestCase):
    def test_search_uses_fixed_https_origin_and_argument_array(self):
        import plistlib
        from backend.device_tools import launch_app, SUPPORTED
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);app=root/'Google Chrome.app';(app/'Contents').mkdir(parents=True)
            (app/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'com.google.Chrome'}))
            with patch('backend.device_tools.subprocess.run') as run:
                result=launch_app({'tool':'chrome','query':'傅里叶 & x; $(echo bad)'},[root])
                args=run.call_args.args[0]
                self.assertEqual(args[:3],['open','-a',str(app)])
                self.assertTrue(args[3].startswith('https://www.google.com/search?q='))
                self.assertIn('%26',args[3]);self.assertTrue(result['searchOpened'])
