"""Build an offline Windows x64 release; never publishes it."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

root = Path(__file__).resolve().parent
output = root / 'dist'
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed',
                '--name', 'Antigravity中文', '--add-data', 'localization;localization',
                '--add-data', 'LICENSE;.', '--add-data', 'THIRD-PARTY-LICENSE.txt;.',
                '--add-data', 'runtime-licenses;runtime-licenses',
                '--hidden-import', 'win32timezone', 'tool.py'], cwd=root, check=True)
bundle = output / 'antigravity-desktop-zh-cn-v1.0.0'
if bundle.exists():
    raise RuntimeError('Release folder exists; move it aside before rebuilding.')
bundle.mkdir()
for name in ['Antigravity中文.exe']:
    shutil.copy2(output / name, bundle / name)
for name in ['一键安装.bat', '一键卸载.bat', 'README.md', 'LICENSE', 'THIRD-PARTY-LICENSE.txt',
             'PROVENANCE.md', 'VALIDATION.md']:
    shutil.copy2(root / name, bundle / name)
shutil.copytree(root / 'runtime-licenses', bundle / 'runtime-licenses')
archive = output / (bundle.name + '.zip')
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as handle:
    for file in sorted(bundle.rglob('*')):
        if file.is_file():
            handle.write(file, file.relative_to(output))
checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
(output / 'SHA256SUMS.txt').write_text(checksum + '  ' + archive.name + '\n', encoding='ascii')
print(f'Built {archive.name}: {archive.stat().st_size} bytes; SHA256 {checksum}')
