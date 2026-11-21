"""Package the separately verified M09 candidate; preserve the published M08."""
from pathlib import Path
import json,re,hashlib,zipfile

ROOT=Path(__file__).resolve().parents[1]
report_path=ROOT/'docs/validation/m09.json'
report=json.loads(report_path.read_text(encoding='utf-8'));build=report['build']
folder=(ROOT/build['exe']).parent
assert folder.resolve().parent==(ROOT/'dist').resolve()
assert hashlib.sha256((folder/'HAND-v2.exe').read_bytes()).hexdigest()==build['exe_sha256']
guide=(ROOT/'docs/user-guide.html').read_text(encoding='utf-8')
guide=re.sub(r'<nav>.*?</nav>','',guide,flags=re.S)
guide=guide.replace('../start_hand.bat','HAND-v2.exe').replace('href="continuous-review.html"','href="검증결과.html"')
(folder/'사용안내.html').write_text(guide,encoding='utf-8')
review=(ROOT/'docs/continuous-review.html').read_text(encoding='utf-8')
review=re.sub(r'<nav>.*?</nav>','',review,flags=re.S)
# Packaged report is self-contained text; source artifacts remain in the repo.
review=re.sub(r'<a[^>]+>(.*?)</a>',r'\1',review,flags=re.S)
(folder/'검증결과.html').write_text(review,encoding='utf-8')
info={'version':'HAND v2 M09 continuous gestures candidate 2026-11-21','exe_sha256':build['exe_sha256'],
    'automated_tests':report['automatic']['passed'],'synthetic_expected_steps':240,
    'new_pc_acceptance':'NOT_RUN','human_accuracy_acceptance':'NOT_RUN',
    'instructions':'Extract entire folder. Keep HAND-v2.exe and _internal together. Open 사용안내.html.'}
(folder/'BUILD-INFO.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
archive=folder.with_suffix('.zip')
with archive.open('xb') as raw:
    with zipfile.ZipFile(raw,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
        for file in sorted(folder.rglob('*')):
            if file.is_file():bundle.write(file,file.relative_to(folder.parent).as_posix())
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    files=len(bundle.infolist())
report['portable_archive']={'path':archive.relative_to(ROOT).as_posix(),'bytes':archive.stat().st_size,
    'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':files,'crc_verified':True}
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report['portable_archive'],indent=2))
