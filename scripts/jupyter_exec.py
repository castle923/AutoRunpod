#!/usr/bin/env python3
"""RunPod 포드에서 코드를 원격 실행한다 (Jupyter 커널 웹소켓 경유).

이 세션의 모든 포드 조작이 이 경로를 통한다. Jupyter REST API는 토큰 인증 없이
_xsrf 쿠키만으로 커널을 만들 수 있어서, SSH 없이도 포드 안에서 임의의 파이썬
코드를 돌릴 수 있다.

  1. GET /lab            → _xsrf 쿠키 획득
  2. POST /api/kernels   → 커널 id (헤더에 X-XSRFToken)
  3. wss://.../api/kernels/{id}/channels → execute_request 로 코드 실행
  4. 끝나면 DELETE /api/kernels/{id}  (닫지 않으면 커널이 계속 쌓인다)

사용법:
  python3 jupyter_exec.py 'print(1)'
  cat script.py | python3 jupyter_exec.py
  POD_ID=xxxx python3 jupyter_exec.py 'print(1)'

주의: 코드에 f-string 과 중첩 따옴표가 섞이면 커널에서 SyntaxError 가 난다.
% 포매팅을 쓸 것.
"""
import json, os, sys, uuid, requests, websocket

POD_ID = os.environ.get("RUNPOD_POD_ID", "xyru66nh4emucs")
JUPYTER_URL = f"https://{POD_ID}-8888.proxy.runpod.net"
WS_URL = f"wss://{POD_ID}-8888.proxy.runpod.net"

def execute(code, timeout=600):
    sess = requests.Session()
    r = sess.get(f"{JUPYTER_URL}/lab", allow_redirects=True, timeout=30)
    xsrf = sess.cookies.get("_xsrf", "")
    headers = {"X-XSRFToken": xsrf}
    r = sess.post(f"{JUPYTER_URL}/api/kernels", headers=headers, timeout=30)
    r.raise_for_status()
    kernel_id = r.json()["id"]
    cookie_str = "; ".join(f"{k}={v}" for k, v in sess.cookies.items())
    ws = websocket.create_connection(
        f"{WS_URL}/api/kernels/{kernel_id}/channels",
        header={"Cookie": cookie_str, "X-XSRFToken": xsrf},
        timeout=timeout,
    )
    msg_id = str(uuid.uuid4())
    ws.send(json.dumps({
        "header": {"msg_id": msg_id, "msg_type": "execute_request", "username": "", "session": "", "version": "5.3"},
        "parent_header": {}, "metadata": {},
        "content": {"code": code, "silent": False, "store_history": False},
        "channel": "shell",
    }))
    output = []
    while True:
        raw = ws.recv()
        msg = json.loads(raw)
        msg_type = msg.get("msg_type", "")
        parent = msg.get("parent_header", {}).get("msg_id", "")
        if parent != msg_id:
            continue
        if msg_type == "stream":
            output.append(msg["content"]["text"])
        elif msg_type == "error":
            output.append("\n".join(msg["content"]["traceback"]))
        elif msg_type == "execute_reply":
            break
    ws.close()
    sess.delete(f"{JUPYTER_URL}/api/kernels/{kernel_id}", headers=headers, timeout=10)
    return "".join(output)

if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    print(execute(code))
