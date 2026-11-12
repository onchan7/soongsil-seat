from pathlib import Path
import zipfile
root=Path(__file__).resolve().parents[1]
files=[root/'README.md',root/'.gitignore',root/'.github/workflows/pages.yml']
for directory in ['dist','backend','firmware','tools','tests']:
 files += [p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.zip','.pyc']]
with zipfile.ZipFile(root/'dist/soongsil-seat-kit.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,Path('soongsil-seat')/p.relative_to(root))
print('Packaged',len(files),'source files')
