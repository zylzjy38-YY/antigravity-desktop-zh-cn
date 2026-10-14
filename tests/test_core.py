import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import protocol
import tool
import worker
import windows_support as windows


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='antigravity-zh-test-')
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / 'installed'
        self.desktop = self.base / 'desktop'
        self.desktop.mkdir()
        self.app = self.base / 'Antigravity.exe'
        self.app.write_bytes(b'test fixture; not an application')

    def tearDown(self):
        self.temporary.cleanup()

    def install(self):
        tool.install(self.app, self.root, self.desktop)

    def uninstall(self):
        with patch.object(windows, 'app_pids', return_value=set()):
            tool.uninstall(self.root)

    def test_real_shortcut_and_install_uninstall(self):
        self.install()
        config = tool.read_config(self.root)
        link = Path(config['shortcut'])
        self.assertTrue(windows.shortcut_matches(link, Path(config['shortcutTarget']), config['shortcutArgs']))
        self.assertEqual(json.loads((self.root/'localization/zh-CN.json').read_text(encoding='utf-8'))['Save'], '保存')
        self.uninstall()
        self.assertFalse(self.root.exists())
        self.assertFalse(link.exists())

    def test_existing_directory_is_preserved(self):
        self.root.mkdir(); (self.root/'personal.txt').write_text('keep')
        with self.assertRaises(RuntimeError): self.install()
        self.assertEqual((self.root/'personal.txt').read_text(), 'keep')

    def test_existing_desktop_link_is_preserved(self):
        link = self.desktop/'Antigravity 中文.lnk'; link.write_bytes(b'keep')
        with self.assertRaises(RuntimeError): self.install()
        self.assertEqual(link.read_bytes(), b'keep')
        self.assertFalse(self.root.exists())

    def test_failed_shortcut_creation_rolls_back(self):
        with patch.object(windows, 'create_shortcut', side_effect=OSError('fixture failure')):
            with self.assertRaises(OSError): self.install()
        self.assertFalse(self.root.exists())

    def test_extra_file_prevents_uninstall(self):
        self.install(); (self.root/'personal.txt').write_text('keep')
        with self.assertRaises(RuntimeError): self.uninstall()
        self.assertEqual((self.root/'personal.txt').read_text(), 'keep')

    def test_nested_personal_file_prevents_uninstall(self):
        self.install(); personal=self.root/'localization/notes.txt'; personal.write_text('keep')
        with self.assertRaises(RuntimeError): self.uninstall()
        self.assertEqual(personal.read_text(),'keep')

    def test_modified_installed_file_prevents_uninstall(self):
        self.install(); file=self.root/'localization/runtime.js'; file.write_text('personal change')
        with self.assertRaises(RuntimeError): self.uninstall()
        self.assertEqual(file.read_text(),'personal change')

    def test_changed_shortcut_is_preserved(self):
        self.install(); config=tool.read_config(self.root); link=Path(config['shortcut'])
        windows.create_shortcut(link, self.app, '--custom', self.app)
        self.uninstall()
        self.assertTrue(link.exists())

    def test_running_app_prevents_uninstall(self):
        self.install()
        with patch.object(windows,'app_pids',return_value={999}):
            with self.assertRaises(RuntimeError): tool.uninstall(self.root)
        self.assertTrue(self.root.exists())

    def test_single_worker_lock(self):
        lock = windows.acquire_worker_lock()
        try: self.assertIsNone(windows.acquire_worker_lock())
        finally: windows.release_worker_lock(lock)

    def test_launch_does_not_stop_running_app(self):
        self.install()
        with patch.object(windows, 'file_version', return_value='2.23.0'), \
             patch.object(windows, 'app_pids', return_value={999}), \
             patch.object(windows, 'app_ports', return_value=set()), \
             patch.object(tool.subprocess, 'Popen') as spawn:
            with self.assertRaises(RuntimeError): tool.launch(self.root)
            spawn.assert_not_called()

    def test_new_version_refused_on_launch(self):
        self.install()
        with patch.object(windows, 'file_version', return_value='9.0.0'), patch.object(tool.subprocess,'Popen') as spawn:
            with self.assertRaises(RuntimeError): tool.launch(self.root)
            spawn.assert_not_called()

    def test_nonlocal_targets_rejected(self):
        for url in ['https://example.org/', 'file:///local', 'https://127.0.0.1.evil.test/', 'bad']:
            self.assertFalse(protocol.local_page({'type':'page','url':url}))
        self.assertTrue(protocol.local_page({'type':'page','url':'http://127.0.0.1:8000/'}))
        self.assertFalse(protocol.local_page({'type':'worker','url':'http://127.0.0.1:8000/'}))

    def test_remote_or_wrong_port_websocket_rejected_before_connect(self):
        with patch.object(protocol.websocket,'create_connection') as connect:
            for url in ['ws://example.com:1234/x', 'ws://127.0.0.1:9999/x', 'wss://127.0.0.1:1234/x', 'ws://user:pass@127.0.0.1:1234/x']:
                with self.assertRaises(ValueError): protocol.Cdp(url, 1234)
            connect.assert_not_called()

    def test_injection_and_refresh_registration(self):
        client=MagicMock(); client.script_id=None
        client.call.side_effect=[{}, {'identifier':'script'}, {'result':{'value':False}}, {}, {'result':{'value':True}}]
        self.assertTrue(worker.ensure_translation(client,'fixture'))
        self.assertEqual(client.script_id,'script')
        self.assertEqual(client.call.call_args_list[0].args[0],'Page.enable')
        self.assertEqual(client.call.call_args_list[1].args[0],'Page.addScriptToEvaluateOnNewDocument')

    def test_script_exception_cannot_count_as_success(self):
        client=MagicMock(); client.script_id='script'
        client.call.side_effect=[{'result':{'value':False}}, {'exceptionDetails':{}}]
        # Non-empty exception details match real CDP errors.
        client.call.side_effect=[{'result':{'value':False}}, {'exceptionDetails':{'text':'error'}}]
        with self.assertRaises(RuntimeError): worker.ensure_translation(client,'fixture')

    def test_healthy_page_is_not_reinjected(self):
        client=MagicMock(); client.script_id='script'; client.call.return_value={'result':{'value':True}}
        self.assertTrue(worker.ensure_translation(client,'fixture'))
        client.call.assert_called_once()


if __name__ == '__main__':
    unittest.main(verbosity=2)
