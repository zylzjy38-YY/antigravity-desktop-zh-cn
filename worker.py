import json
from pathlib import Path
import time

from protocol import Cdp, list_targets, local_page
import windows_support as windows

CHECK = 'Boolean(document.body && globalThis.__antigravityChineseVersion===1 && globalThis.__antigravityChineseObserver)'


def ensure_translation(client: Cdp, source: str) -> bool:
    if not client.script_id:
        client.call('Page.enable')
        client.script_id = client.call('Page.addScriptToEvaluateOnNewDocument', {'source': source})['identifier']
    check = client.call('Runtime.evaluate', {'expression': CHECK, 'returnByValue': True})
    if check.get('result', {}).get('value') is not True:
        injected = client.call('Runtime.evaluate', {'expression': source, 'returnByValue': True})
        if injected.get('exceptionDetails'):
            raise RuntimeError('Localization script failed')
        check = client.call('Runtime.evaluate', {'expression': CHECK, 'returnByValue': True})
    return check.get('result', {}).get('value') is True


def run_worker(root: Path, assets: Path):
    lock = windows.acquire_worker_lock()
    if lock is None:
        return
    clients = {}
    try:
        config = json.loads((root / 'install.json').read_text(encoding='utf-8'))
        app = Path(config['appPath'])
        dictionary = json.loads((assets / 'localization/zh-CN.json').read_text(encoding='utf-8'))
        runtime = (assets / 'localization/runtime.js').read_text(encoding='utf-8')
        source = '(' + runtime + ')(' + json.dumps({'dictionary': dictionary}, ensure_ascii=False) + ');'
        last_seen = time.monotonic()
        while True:
            if windows.app_pids(app):
                last_seen = time.monotonic()
            if time.monotonic() - last_seen > 30:
                break
            alive, healthy, errors = set(), 0, 0
            for port in windows.app_ports(app):
                try:
                    targets = list_targets(port)
                except Exception:
                    continue
                for target in targets:
                    if not local_page(target):
                        continue
                    key = (port, target.get('id'))
                    alive.add(key)
                    try:
                        if key not in clients:
                            clients[key] = Cdp(target['webSocketDebuggerUrl'], port)
                        healthy += int(ensure_translation(clients[key], source))
                    except Exception:
                        client = clients.pop(key, None)
                        if client:
                            client.close()
                        errors += 1
            for key in list(clients):
                if key not in alive:
                    clients.pop(key).close()
            state = {'at': time.time(), 'healthyPages': healthy, 'failedPages': errors}
            temporary = root / 'status.tmp'
            temporary.write_text(json.dumps(state), encoding='utf-8')
            temporary.replace(root / 'status.json')
            time.sleep(3)
    finally:
        for client in clients.values():
            client.close()
        windows.release_worker_lock(lock)
