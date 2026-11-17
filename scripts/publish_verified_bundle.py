from pathlib import Path
import argparse,json,hashlib,shutil
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('folder');p.add_argument('old_exe');a=p.parse_args()
build=json.loads((root/f'docs/validation/{a.label}-build.json').read_text(encoding='utf-8'))
assert build['exit_code']==0 and build['offscreen_smoke_exit_code']==0
source=root/build['exe'];dest=root/'dist'/a.folder
assert dest.resolve().parent==(root/'dist').resolve() and not dest.exists()
shutil.copytree(source.parent,dest)
manifest=json.loads((root/f'docs/validation/{a.label}-artifact-manifest.json').read_text(encoding='utf-8'))
for item in manifest:
    file=dest/item['path'];assert file.stat().st_size==item['bytes']
    assert hashlib.sha256(file.read_bytes()).hexdigest()==item['sha256'],item['path']
new=(dest/'HAND-v2.exe').relative_to(root).as_posix()
for name in ('start_hand.bat','README.html'):
    path=root/name;text=path.read_text(encoding='utf-8');old=a.old_exe;replacement=new
    if name.endswith('.bat'):old=old.replace('/','\\');replacement=replacement.replace('/','\\')
    assert old in text;path.write_text(text.replace(old,replacement),encoding='utf-8')
files=sorted(set(root.glob('src/**/*.py'))|set(root.glob('tests/**/*.py'))|{root/'run.py',root/'requirements-lock.txt'})
(root/f'docs/validation/{a.label}-source-manifest.json').write_text(json.dumps([{'path':f.relative_to(root).as_posix(),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in files],indent=2),encoding='utf-8')
path=root/f'docs/validation/{a.label}.json';report=json.loads(path.read_text(encoding='utf-8'))
report['build']={'exe':new,'exe_sha256':build['exe_sha256'],'verified_copy_files':len(manifest),'bytes':build['bundle_bytes'],'offscreen_smoke_exit_code':0,'manifest':f'{a.label}-artifact-manifest.json','source_manifest':f'{a.label}-source-manifest.json'}
path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report['build'],indent=2))
