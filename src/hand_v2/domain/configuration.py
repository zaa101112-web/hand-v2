from copy import deepcopy
import math


def merge_leaves(base, patch):
    if type(base) is dict and type(patch) is dict:
        result=deepcopy(base)
        for key,value in patch.items():result[key]=merge_leaves(base[key],value) if key in base else deepcopy(value)
        return result
    return deepcopy(patch)


SCHEMA={
    'schema_name':('fixed','hand-v2-config'),'version':('fixed',1),
    'camera':{'index':('int',0,3),'width':('fixed',640),'height':('fixed',480),'max_hands':('fixed',2)},
    'timing':{k:('fixed',v) for k,v in {'activate_ms':600,'stop_ms':350,'rearm_ms':180,'cooldown_ms':600,'confirmation_cooldown_ms':1500,'event_ttl_ms':250}.items()},
    'gestures':{'swipe_min_ms':('fixed',150),'swipe_max_ms':('fixed',600),'swipe_distance':('number',.10,.25),
                'axis_ratio':('fixed',1.8),'straightness':('fixed',.9),'zoom_step_ratio':('number',1.10,1.30),
                'capture_hold_ms':('fixed',800),'smoothing_tau_ms':('int',30,120),
                'pinch_enter':('number',.20,.35),'pinch_exit':('number',.40,.60)},
    'display':{'preview':('bool',)},'capture':{'folder':('nullable_string',)},
    'logging':{'level':('choice','DEBUG','INFO','WARNING','ERROR')},
}


def validate_config(config):
    def check(value,schema,path):
        if type(schema) is dict:
            if type(value) is not dict or set(value)!=set(schema):raise ValueError(f'{path}: 알 수 없는 키 또는 누락된 키')
            for key,child in schema.items():check(value[key],child,f'{path}.{key}')
            return
        kind,*bounds=schema;ok=False
        if kind=='fixed':ok=type(value) is type(bounds[0]) and value==bounds[0]
        elif kind=='int':ok=type(value) is int and bounds[0]<=value<=bounds[1]
        elif kind=='number':ok=type(value) in (int,float) and math.isfinite(value) and bounds[0]<=value<=bounds[1]
        elif kind=='bool':ok=type(value) is bool
        elif kind=='nullable_string':ok=value is None or (type(value) is str and bool(value.strip()) and '\x00' not in value)
        elif kind=='choice':ok=type(value) is str and value in bounds
        if not ok:raise ValueError(f'{path}: 값 또는 형식이 올바르지 않습니다 ({schema})')
    check(config,SCHEMA,'설정')
    if config['gestures']['pinch_enter']>=config['gestures']['pinch_exit']:raise ValueError('집기 시작값은 해제값보다 작아야 합니다.')
    return deepcopy(config)
