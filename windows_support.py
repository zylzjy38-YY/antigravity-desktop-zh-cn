"""Small Windows adapter: process ownership, version, shortcuts and worker mutex."""
from pathlib import Path
import ctypes
import ctypes.wintypes as wt
import os

import psutil
import win32api
import win32com.client


def app_pids(app: Path) -> set[int]:
    expected = os.path.normcase(str(app.resolve()))
    found = set()
    for process in psutil.process_iter(['pid', 'name']):
        if (process.info['name'] or '').lower() != 'antigravity.exe':
            continue
        try:
            if os.path.normcase(process.exe()) == expected:
                found.add(process.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return found


def app_ports(app: Path) -> set[int]:
    pids = app_pids(app)
    if not pids:
        return set()
    return {connection.laddr.port for connection in psutil.net_connections(kind='tcp4')
            if connection.pid in pids and connection.status == psutil.CONN_LISTEN
            and connection.laddr.ip == '127.0.0.1'}


def file_version(app: Path) -> str:
    info = win32api.GetFileVersionInfo(str(app), '\\')
    high, low = info['FileVersionMS'], info['FileVersionLS']
    return f'{high >> 16}.{high & 65535}.{low >> 16}'


def desktop_dir() -> Path:
    # Windows resolves redirected/OneDrive desktops without guessing their paths.
    shell = win32com.client.Dispatch('WScript.Shell')
    return Path(shell.SpecialFolders('Desktop'))


def create_shortcut(link: Path, target: Path, arguments: str, icon: Path) -> None:
    shortcut = win32com.client.Dispatch('WScript.Shell').CreateShortcut(str(link))
    shortcut.TargetPath = str(target)
    shortcut.Arguments = arguments
    shortcut.WorkingDirectory = str(target.parent)
    shortcut.IconLocation = str(icon) + ',0'
    shortcut.Description = 'Antigravity Desktop 简体中文界面'
    shortcut.Save()


def shortcut_matches(link: Path, target: Path, arguments: str) -> bool:
    shortcut = win32com.client.Dispatch('WScript.Shell').CreateShortcut(str(link))
    return (os.path.normcase(shortcut.TargetPath) == os.path.normcase(str(target))
            and shortcut.Arguments == arguments)


def acquire_worker_lock():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
    kernel.CreateMutexW.restype = wt.HANDLE
    kernel.CloseHandle.argtypes = [wt.HANDLE]
    handle = kernel.CreateMutexW(None, False, 'Local\\AntigravityDesktopZhCnWorker')
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:
        kernel.CloseHandle(handle)
        return None
    return handle


def release_worker_lock(handle) -> None:
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CloseHandle.argtypes = [wt.HANDLE]
    kernel.CloseHandle(handle)


def notify(text: str, *, error: bool = False) -> None:
    ctypes.windll.user32.MessageBoxW(None, text, 'Antigravity 中文', 0x10 if error else 0x40)
