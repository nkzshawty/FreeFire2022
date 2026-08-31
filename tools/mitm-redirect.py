"""
mitmproxy script: intercepta requests do Free Fire e redireciona pro servidor local.

Uso:
  mitmdump -s tools/mitm-redirect.py -p 8082 --set block_global=false --ssl-insecure --set connection_strategy=lazy
"""
from mitmproxy import http, ctx

LOCAL_SERVER = "192.168.1.2"
LIVE_PORT = 19134
LOGIN_PORT = 19132
MAIN_PORT = 19133

def request(flow: http.HTTPFlow) -> None:
    host = flow.request.pretty_host
    path = flow.request.path
    method = flow.request.method
    content_type = flow.request.headers.get("content-type", "")

    # CDN downloads — let these pass through to the real server
    # (game resources, language files, textures, etc.)
    if "dl.cdn.freefiremobile" in host or "cdn.freefiremobile" in host:
        ctx.log.info(f"[CDN-PASS] {method} {host}{path}")
        return

    # version.common.freefiremobile.com — our game server
    if "freefiremobile" in host or "ggblueshark" in host:
        # ver.php -> live server
        if "ver.php" in path:
            port = LIVE_PORT
        # ABHotUpdates fileinfo -> live server (returns empty so game skips)
        elif "ABHotUpdates" in path and "fileinfo" in path:
            port = LIVE_PORT
        # ABHotUpdates actual file downloads -> pass through to real CDN
        elif "ABHotUpdates" in path:
            ctx.log.info(f"[CDN-PASS] {method} {host}{path}")
            return
        # Protobuf POST requests (MajorLogin, GetLoginData, etc) -> login server
        elif method == "POST":
            port = LOGIN_PORT
            # Strip /login/ prefix so /login/MajorLogin -> /MajorLogin
            if path.startswith("/login/"):
                flow.request.path = path[6:]
        else:
            # Default: login server
            port = LOGIN_PORT
            if path.startswith("/login/"):
                flow.request.path = path[6:]

        flow.request.scheme = "http"
        flow.request.host = LOCAL_SERVER
        flow.request.port = port
        ctx.log.info(f"[FF] {method} {host}{path} -> :{port}")

    # Garena Connect (auth endpoints)
    elif "garenanow.com" in host or "connect.garena.com" in host:
        port = MAIN_PORT
        flow.request.scheme = "http"
        flow.request.host = LOCAL_SERVER
        flow.request.port = port
        ctx.log.info(f"[FF-AUTH] {method} {host}{path} -> :{port}")

    else:
        ctx.log.info(f"[PASS] {method} {host}")
