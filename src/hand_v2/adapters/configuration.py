from dataclasses import dataclass
from pathlib import Path
import json,os,tempfile,uuid
from hand_v2.domain.configuration import merge_leaves,validate_config
from .resources import resource_root


def strict_json(text):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('중복 설정 키: '+key)
            result[key]=value
        return result
    return json.loads(text,object_pairs_hook=pairs,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('비유한 숫자')))


def read_defaults():return validate_config(strict_json((resource_root()/'config/defaults.json').read_text(encoding='utf-8')))


def user_data_dir():return Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share')))/'HAND-v2'


@dataclass(frozen=True)
class LoadedConfig:
    config: dict
    error: str=''


class ConfigStore:
    def __init__(self,defaults,path):
        self.defaults=validate_config(defaults);self.path=Path(path);self.current=validate_config(defaults)
        self.corrupt_bytes=None;self.last_backup=None

    def load(self):
        try:
            if self.path.exists():
                raw=self.path.read_bytes();patch=strict_json(raw.decode('utf-8'))
                if type(patch) is not dict:raise ValueError('설정 객체가 필요합니다.')
                # A user document must identify the schema; leaf defaults are merged only afterwards.
                if patch.get('schema_name')!='hand-v2-config' or type(patch.get('version')) is not int or patch['version']!=1:
                    raise ValueError('HAND v2 설정 버전이 아닙니다.')
                self.current=validate_config(merge_leaves(self.defaults,patch))
            self.corrupt_bytes=None
            return LoadedConfig(self.current)
        except (OSError,ValueError,UnicodeError) as exc:
            try:self.corrupt_bytes=self.path.read_bytes()
            except OSError:self.corrupt_bytes=None
            self.current=validate_config(self.defaults)
            return LoadedConfig(self.current,f'{type(exc).__name__}: {exc}')

    def save(self,patch):
        candidate=validate_config(merge_leaves(self.current,patch))
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,temp=tempfile.mkstemp(prefix='.settings-',suffix='.tmp',dir=self.path.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as stream:
                json.dump(candidate,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.flush();os.fsync(stream.fileno())
            if self.corrupt_bytes is not None:
                backup=self.path.with_name(self.path.name+'.invalid-'+uuid.uuid4().hex)
                with backup.open('xb') as stream:stream.write(self.corrupt_bytes);stream.flush();os.fsync(stream.fileno())
                self.last_backup=backup
            os.replace(temp,self.path)
            self.current=candidate;self.corrupt_bytes=None
            return candidate
        finally:Path(temp).unlink(missing_ok=True)
