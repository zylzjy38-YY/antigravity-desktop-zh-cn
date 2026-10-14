"""Windows installer, localized launcher and uninstaller. No PowerShell required."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import windows_support as windows

PACKAGE = 'antigravity-desktop-zh-cn'
VERSION = '1.0.0'
ROOT = Path(os.environ['LOCALAPPDATA']) / 'AntigravityDesktopZhCn'
ASSETS = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
SOURCE_FILES = ['tool.py', 'worker.py', 'protocol.py', 'windows_support.py', 'requirements.txt']


def command(root: Path, mode: str) -> list[str]:
    if getattr(sys, 'frozen', False):
        return [str(root / 'Antigravity中文.exe'), mode]
    return [sys.executable, str(root / 'tool.py'), mode]


def find_app(selected: str | None = None) -> Path:
    candidates = [Path(selected)] if selected else [
        Path(os.environ['LOCALAPPDATA']) / 'Programs/antigravity/Antigravity.exe',
        Path(os.environ['ProgramFiles']) / 'Antigravity/Antigravity.exe']
    app = next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)
    if app is None and selected is None:
        import tkinter as tk
        from tkinter.filedialog import askopenfilename
        window = tk.Tk(); window.withdraw()
        try:
            value = askopenfilename(title='选择 Antigravity Desktop 的 Antigravity.exe', filetypes=[('Antigravity.exe', 'Antigravity.exe')])
        finally:
            window.destroy()
        app = Path(value).resolve() if value else None
    if app is None or not app.is_file() or app.name.lower() != 'antigravity.exe':
        raise RuntimeError('未找到 Antigravity Desktop，请先安装独立桌面客户端。')
    version = windows.file_version(app)
    if version != '2.23.0':
        raise RuntimeError(f'当前仅验证 Desktop 2.23.0，检测到 {version}，已停止安装。')
    return app


def install(app: Path, root: Path = ROOT, desktop: Path | None = None):
    desktop = desktop or windows.desktop_dir()
    root = root.absolute()
    link = desktop / 'Antigravity 中文.lnk'
    if root.exists() or root.is_symlink():
        raise RuntimeError('汉化目录已存在。请先用一键卸载入口卸载旧版，不会覆盖已有文件。')
    if link.exists():
        raise RuntimeError('桌面已有“Antigravity 中文”入口，请先移开同名入口。')
    dictionary = json.loads((ASSETS / 'localization/zh-CN.json').read_text(encoding='utf-8'))
    if len(dictionary) < 100 or not all(isinstance(k, str) and isinstance(v, str) for k, v in dictionary.items()):
        raise RuntimeError('汉化词典无效，请重新下载完整包。')
    (ASSETS / 'localization/runtime.js').read_text(encoding='utf-8')
    root.mkdir(parents=True)
    owned_link = False
    try:
        if getattr(sys, 'frozen', False):
            shutil.copy2(sys.executable, root / 'Antigravity中文.exe')
        else:
            for name in SOURCE_FILES:
                shutil.copy2(ASSETS / name, root / name)
            shutil.copytree(ASSETS / 'localization', root / 'localization')
        for name in ['LICENSE', 'THIRD-PARTY-LICENSE.txt']:
            shutil.copy2(ASSETS / name, root / name)
        if (ASSETS / 'runtime-licenses').is_dir():
            shutil.copytree(ASSETS / 'runtime-licenses', root / 'runtime-licenses')
        arguments = subprocess.list2cmdline(command(root, '--launch')[1:])
        config = {'package': PACKAGE, 'version': VERSION, 'appPath': str(app),
                  'shortcut': str(link), 'shortcutArgs': arguments, 'shortcutTarget': command(root, '--launch')[0]}
        config['files'] = {file.relative_to(root).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
                           for file in root.rglob('*') if file.is_file()}
        (root / 'install.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
        owned_link = True
        windows.create_shortcut(link, Path(config['shortcutTarget']), arguments, app)
    except Exception:
        if owned_link and link.exists():
            link.unlink()
        if root.resolve() != root or root.is_symlink() or root.is_junction():
            raise RuntimeError('安装失败且目录边界改变，请人工检查安装目录。')
        shutil.rmtree(root)
        raise


def read_config(root: Path) -> dict:
    config = json.loads((root / 'install.json').read_text(encoding='utf-8'))
    if config.get('package') != PACKAGE:
        raise RuntimeError('目录不是本汉化包的安装目录。')
    return config


def launch(root: Path = ROOT) -> int:
    config = read_config(root)
    app = Path(config['appPath'])
    if not app.is_file():
        raise RuntimeError('Antigravity 已移动或卸载，请重新安装汉化。')
    if windows.file_version(app) != '2.23.0':
        raise RuntimeError('Antigravity 版本已变化。请核实新版本兼容性后更新汉化包。')
    running = windows.app_pids(app)
    if running and not windows.app_ports(app):
        raise RuntimeError('汉化已安装。请保存工作并完全退出 Antigravity，再用桌面“Antigravity 中文”入口启动。')
    if not running:
        # No redirected app stdout: some Electron builds fail with EPIPE after launcher exit.
        subprocess.Popen([str(app), '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0'], cwd=app.parent,
                         creationflags=subprocess.CREATE_NO_WINDOW)
    worker_environment = os.environ.copy()
    if getattr(sys, 'frozen', False):
        # The background worker outlives this launcher and needs its own onefile extraction.
        worker_environment['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    subprocess.Popen(command(root, '--worker'), cwd=root, env=worker_environment, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=subprocess.CREATE_NO_WINDOW)
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        try:
            state = json.loads((root / 'status.json').read_text(encoding='utf-8'))
            if time.time() - state['at'] < 6 and state['healthyPages'] > 0:
                return state['healthyPages']
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(0.5)
    raise RuntimeError('文件已安装，但尚未验证页面汉化。请检查客户端版本，并退出后用中文入口重试。')


def uninstall(root: Path = ROOT):
    root = root.absolute()
    if not root.exists():
        return
    if root.resolve() != root or root.is_symlink() or root.is_junction() or root == Path(root.anchor):
        raise RuntimeError('拒绝删除目录联接、符号链接或根目录。')
    config = read_config(root)
    if windows.app_pids(Path(config['appPath'])):
        raise RuntimeError('请保存工作并完全退出 Antigravity，然后等待约 35 秒再卸载。')
    lock = windows.acquire_worker_lock()
    if lock is None:
        raise RuntimeError('汉化助手仍在自动退出，请等待约 35 秒后再次卸载。')
    try:
        children = list(root.rglob('*'))
        if any(child.is_symlink() or child.is_junction() for child in children):
            raise RuntimeError('安装目录包含链接，已停止。')
        manifest = config.get('files', {})
        if not manifest:
            raise RuntimeError('缺少安装文件清单，已停止自动删除。')
        expected_dirs = {parent.as_posix() for name in manifest for parent in Path(name).parents if str(parent) != '.'}
        for child in children:
            relative = child.relative_to(root).as_posix()
            if child.is_dir():
                if relative not in expected_dirs | {'__pycache__'}:
                    raise RuntimeError('汉化目录含额外目录，已停止，避免删除个人文件。')
            elif relative in manifest:
                if hashlib.sha256(child.read_bytes()).hexdigest() != manifest[relative]:
                    raise RuntimeError('已安装文件被修改，已停止，避免删除用户改动。')
            elif relative in {'install.json', 'status.json', 'status.tmp'}:
                continue
            elif (child.parent == root / '__pycache__' and child.suffix == '.pyc'
                  and child.name.split('.')[0] + '.py' in SOURCE_FILES):
                continue
            else:
                raise RuntimeError('汉化目录含额外文件，已停止，避免删除个人文件。')
        if getattr(sys, 'frozen', False) and Path(sys.executable).resolve().is_relative_to(root):
            raise RuntimeError('请从下载包中的“一键卸载.bat”运行卸载，以便删除已安装程序。')
        link = Path(config['shortcut'])
        if link.exists() and windows.shortcut_matches(link, Path(config['shortcutTarget']), config['shortcutArgs']):
            link.unlink()
        shutil.rmtree(root)
    finally:
        windows.release_worker_lock(lock)


def main():
    parser = argparse.ArgumentParser(description='Antigravity Desktop 简体中文汉化')
    group = parser.add_mutually_exclusive_group()
    for mode in ['install', 'launch', 'worker', 'uninstall', 'check']:
        group.add_argument('--' + mode, action='store_true')
    parser.add_argument('--app', help='Antigravity.exe 路径')
    parser.add_argument('--no-launch', action='store_true', help='安装文件与入口，稍后自行启动')
    args = parser.parse_args()
    try:
        if args.worker:
            from worker import run_worker
            run_worker(ROOT, ASSETS)
        elif args.uninstall:
            uninstall()
            windows.notify('汉化已卸载。以后可使用官方入口启动。')
        elif args.launch:
            launch()
        elif args.check:
            app = find_app(args.app)
            print(json.dumps({'package': PACKAGE, 'version': VERSION, 'appVersion': windows.file_version(app),
                              'dictionaryEntries': len(json.loads((ASSETS / 'localization/zh-CN.json').read_text(encoding='utf-8')))}))
        else:
            install(find_app(args.app))
            pages = 0 if args.no_launch else launch()
            windows.notify('安装完成，桌面已创建“Antigravity 中文”入口。' + (f'\n已验证 {pages} 个页面的汉化脚本运行。' if pages else '\n请使用中文入口启动。'))
    except Exception as exc:
        if args.worker:
            return 1
        windows.notify(str(exc), error=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
