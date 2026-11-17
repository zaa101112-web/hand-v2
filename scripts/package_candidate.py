"""Package the verified candidate with a standalone Korean guide; preserve old builds."""
from pathlib import Path
import json,re,hashlib,zipfile
ROOT=Path(__file__).resolve().parents[1]
report_path=ROOT/'docs/validation/m08-final.json'
report=json.loads(report_path.read_text(encoding='utf-8'));build=report['build']
folder=(ROOT/build['exe']).parent
assert folder.resolve().parent==(ROOT/'dist').resolve()
assert hashlib.sha256((folder/'HAND-v2.exe').read_bytes()).hexdigest()==build['exe_sha256']
guide=(ROOT/'docs/user-guide.html').read_text(encoding='utf-8')
guide=re.sub(r'<nav>.*?</nav>','',guide,flags=re.S)
guide=guide.replace('../start_hand.bat','HAND-v2.exe').replace('<a href="release-review.html">검증 보고서</a>','프로젝트의 검증 보고서')
(folder/'사용안내.html').write_text(guide,encoding='utf-8')
info={'version':'HAND v2 M08 acceptance candidate 2026-11-17','exe_sha256':build['exe_sha256'],
      'model_sha256':'fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1',
      'automated_tests':report['automatic']['passed'],'new_pc_acceptance':'NOT_RUN','human_accuracy_acceptance':'NOT_RUN',
      'instructions':'Extract the entire folder. Keep HAND-v2.exe and _internal together. Open 사용안내.html.'}
(folder/'BUILD-INFO.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
archive=folder.with_suffix('.zip')
with archive.open('xb') as raw:
    with zipfile.ZipFile(raw,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
        for file in sorted(folder.rglob('*')):
            if file.is_file():bundle.write(file,file.relative_to(folder.parent).as_posix())
with zipfile.ZipFile(archive) as bundle:
    error=bundle.testzip();assert error is None,error
    files=len(bundle.infolist())
report['portable_archive']={'path':archive.relative_to(ROOT).as_posix(),'bytes':archive.stat().st_size,
                            'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':files,'crc_verified':True}
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report['portable_archive'],indent=2))
