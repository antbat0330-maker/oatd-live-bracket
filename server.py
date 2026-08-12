# -*- coding: utf-8 -*-
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote
from pathlib import Path
import copy, json, os, secrets, threading, time, mimetypes

BASE = Path(__file__).resolve().parent
HOST = '0.0.0.0'
PORT = int(os.environ.get('PORT', '10000'))
PIN = os.environ.get('ADMIN_PIN', '0919')
BUILD = 'RENDER-V2-20260813'
CENTRAL_ID = 'kimjinseo'
PARTICIPANTS = json.loads((BASE/'participants.json').read_text(encoding='utf-8'))
BY_ID = {p['id']: p for p in PARTICIPANTS}
IDS = set(BY_ID)
LOCK = threading.RLock()
HISTORY = []
STATE_FILE = Path(os.environ.get('STATE_FILE', '/tmp/oatd_live_state.json'))

def fresh_state():
    return {'mode':'bracket','current_pick':None,'matches':[[None,None] for _ in range(6)],'held':[],
            'updated':int(time.time()*1000),'revision':0,'build':BUILD}

def valid_state(s):
    if not isinstance(s, dict): return False, '상태 형식 오류'
    ms=s.get('matches')
    if not isinstance(ms,list) or len(ms)!=6: return False,'대진 형식 오류'
    seen=[]
    for m in ms:
        if not isinstance(m,list) or len(m)!=2: return False,'대진 형식 오류'
        for x in m:
            if x is not None and x not in IDS: return False,'알 수 없는 참가자'
            if x: seen.append(x)
    if len(seen)!=len(set(seen)): return False,'한 참가자가 중복 배치되었습니다.'
    cur=s.get('current_pick')
    if cur is not None and cur not in IDS: return False,'현재 참가자 오류'
    held=s.get('held',[])
    if not isinstance(held,list) or any(x not in IDS for x in held): return False,'보류 목록 오류'
    return True,''

def load_state():
    try:
        s=json.loads(STATE_FILE.read_text(encoding='utf-8'))
        ok,_=valid_state(s)
        if ok:
            s.setdefault('revision',0); s['build']=BUILD
            return s
    except Exception:
        pass
    return fresh_state()

STATE=load_state()

def save_state():
    STATE['revision']=int(STATE.get('revision',0))+1
    STATE['updated']=int(time.time()*1000)
    STATE['build']=BUILD
    try: STATE_FILE.write_text(json.dumps(STATE,ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception: pass

def snapshot():
    HISTORY.append(copy.deepcopy(STATE))
    if len(HISTORY)>30: HISTORY.pop(0)

def used_set(): return {x for m in STATE['matches'] for x in m if x}

def first_empty_match():
    for i,m in enumerate(STATE['matches']):
        if not m[0] and not m[1]: return i
    return None

def apply_action(data):
    global STATE
    action=str(data.get('action',''))
    with LOCK:
        if action=='undo':
            if not HISTORY: raise ValueError('되돌릴 작업이 없습니다.')
            STATE=HISTORY.pop(); save_state(); return copy.deepcopy(STATE)
        snapshot()
        try:
            used=used_set()
            if action=='show_bracket': STATE['mode']='bracket'
            elif action=='show_draw':
                if not STATE.get('current_pick'): raise ValueError('현재 공개된 참가자가 없습니다.')
                STATE['mode']='draw'
            elif action=='draw_random':
                if STATE.get('current_pick'): raise ValueError('현재 참가자의 대진 확정 또는 보류를 먼저 진행해주세요.')
                held=set(STATE.get('held',[]))
                pool=[p['id'] for p in PARTICIPANTS if not p.get('central') and p['id'] not in used and p['id'] not in held]
                if not pool: raise ValueError('새 제비 대상이 없습니다. 보류 참가자를 다시 호출해주세요.')
                STATE['current_pick']=secrets.choice(pool); STATE['mode']='draw'
            elif action=='manual_pick':
                pid=str(data.get('participant',''))
                if STATE.get('current_pick'): raise ValueError('현재 참가자의 대진 확정 또는 보류를 먼저 진행해주세요.')
                if pid not in IDS or pid==CENTRAL_ID or pid in used: raise ValueError('선택할 수 없는 참가자입니다.')
                STATE['held']=[x for x in STATE.get('held',[]) if x!=pid]
                STATE['current_pick']=pid; STATE['mode']='draw'
            elif action=='call_held':
                pid=str(data.get('participant',''))
                if STATE.get('current_pick'): raise ValueError('현재 참가자의 대진 확정 또는 보류를 먼저 진행해주세요.')
                if pid not in STATE.get('held',[]) or pid in used: raise ValueError('호출할 수 없는 보류 참가자입니다.')
                STATE['held']=[x for x in STATE['held'] if x!=pid]
                STATE['current_pick']=pid; STATE['mode']='draw'
            elif action=='hold_current':
                pid=STATE.get('current_pick')
                if not pid: raise ValueError('현재 공개된 참가자가 없습니다.')
                if pid not in STATE['held']: STATE['held'].append(pid)
                STATE['current_pick']=None; STATE['mode']='bracket'
            elif action=='confirm_match':
                p1=STATE.get('current_pick'); p2=str(data.get('opponent',''))
                if not p1: raise ValueError('먼저 제비를 뽑아주세요.')
                if p1 in used: raise ValueError('현재 참가자가 이미 다른 대진에 포함되어 있습니다.')
                if p2 not in IDS or p2==CENTRAL_ID or p2==p1 or p2 in used: raise ValueError('선택할 수 없는 상대입니다.')
                idx=first_empty_match()
                if idx is None: raise ValueError('6개 대진이 이미 모두 채워졌습니다.')
                STATE['matches'][idx]=[p1,p2]
                STATE['held']=[x for x in STATE.get('held',[]) if x not in (p1,p2)]
                STATE['current_pick']=None; STATE['mode']='bracket'
            elif action=='auto_central':
                if CENTRAL_ID in used: raise ValueError('중앙대가 이미 포함되어 있습니다.')
                rem=[p['id'] for p in PARTICIPANTS if not p.get('central') and p['id'] not in used]
                if len(rem)!=1: raise ValueError(f'현재 미매칭 현장 참가자가 {len(rem)}명입니다. 1명일 때 실행해주세요.')
                idx=first_empty_match()
                if idx is None: raise ValueError('빈 MATCH가 없습니다.')
                STATE['matches'][idx]=[rem[0],CENTRAL_ID]; STATE['held']=[]; STATE['current_pick']=None; STATE['mode']='bracket'
            elif action=='manual_matches':
                ms=data.get('matches')
                tmp=copy.deepcopy(STATE); tmp['matches']=ms
                ok,msg=valid_state(tmp)
                if not ok: raise ValueError(msg)
                STATE['matches']=ms; now_used=used_set()
                STATE['held']=[x for x in STATE.get('held',[]) if x not in now_used]
                if STATE.get('current_pick') in now_used: STATE['current_pick']=None
                STATE['mode']='bracket'
            elif action=='restore_state':
                incoming=data.get('state'); ok,msg=valid_state(incoming)
                if not ok: raise ValueError('백업 복구 실패: '+msg)
                restored=fresh_state(); restored['mode']=incoming.get('mode','bracket') if incoming.get('mode') in ('bracket','draw') else 'bracket'
                restored['current_pick']=incoming.get('current_pick'); restored['matches']=copy.deepcopy(incoming['matches'])
                restored['held']=list(dict.fromkeys(incoming.get('held',[]))); STATE=restored
            elif action=='reset': STATE=fresh_state()
            else: raise ValueError('알 수 없는 작업입니다.')
            save_state(); return copy.deepcopy(STATE)
        except Exception:
            if HISTORY: HISTORY.pop()
            raise

class Handler(BaseHTTPRequestHandler):
    server_version='OATDLive/1.0'
    def log_message(self,fmt,*args): print('%s - %s'%(self.address_string(),fmt%args))
    def _send(self,code,ctype,data,cache=False):
        if isinstance(data,str): data=data.encode('utf-8')
        self.send_response(code); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(data))); self.send_header('X-OATD-Build',BUILD)
        if not cache:
            self.send_header('Cache-Control','no-store, no-cache, must-revalidate'); self.send_header('Pragma','no-cache')
        self.end_headers(); self.wfile.write(data)
    def _json(self,code,obj): self._send(code,'application/json; charset=utf-8',json.dumps(obj,ensure_ascii=False))
    def do_GET(self):
        path=urlparse(self.path).path
        if path in ('/','/index.html'): return self._send(200,'text/html; charset=utf-8',(BASE/'templates/index.html').read_bytes())
        if path=='/display': return self._send(200,'text/html; charset=utf-8',(BASE/'templates/display.html').read_bytes())
        if path=='/admin': return self._send(200,'text/html; charset=utf-8',(BASE/'templates/admin.html').read_bytes())
        if path=='/api/state':
            with LOCK: s=copy.deepcopy(STATE)
            return self._json(200,s)
        if path=='/api/participants': return self._json(200,PARTICIPANTS)
        if path=='/health': return self._json(200,{'ok':True,'build':BUILD,'time':int(time.time())})
        if path.startswith('/static/'):
            rel=unquote(path[len('/static/'):]); f=(BASE/'static'/rel).resolve(); root=(BASE/'static').resolve()
            if root not in f.parents and f!=root: return self._send(403,'text/plain','Forbidden')
            if not f.is_file(): return self._send(404,'text/plain','Not found')
            return self._send(200,mimetypes.guess_type(str(f))[0] or 'application/octet-stream',f.read_bytes(),cache=True)
        return self._send(404,'text/plain; charset=utf-8','Not found')
    def do_POST(self):
        path=urlparse(self.path).path
        if self.headers.get('X-Admin-PIN','')!=PIN: return self._json(401,{'error':'PIN 오류','build':BUILD})
        try:
            n=int(self.headers.get('Content-Length','0') or 0); data=json.loads(self.rfile.read(n) or b'{}')
        except Exception: return self._json(400,{'error':'JSON 오류'})
        if path=='/api/auth': return self._json(200,{'ok':True,'build':BUILD})
        if path=='/api/action':
            try: return self._json(200,apply_action(data))
            except ValueError as e: return self._json(400,{'error':str(e),'build':BUILD})
            except Exception as e:
                print('ACTION ERROR',repr(e)); return self._json(500,{'error':'서버 처리 오류','build':BUILD})
        return self._json(404,{'error':'Not found'})

if __name__=='__main__':
    print('='*64); print('OATD LIVE 12 / Render-ready'); print('Build:',BUILD); print('Port:',PORT); print('='*64)
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
