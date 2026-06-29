# app/media.py
import ipaddress, socket
from urllib.parse import urlparse, urljoin
import httpx
from . import config

class MediaError(Exception):
    pass

def _is_private_host(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return True  # no resuelve -> trata como inseguro
    for info in infos:
        ip = info[4][0]
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return True
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            return True
    return False

def host_allowed(url: str) -> bool:
    try:
        u = urlparse(url)
    except Exception:
        return False
    if u.scheme != "https":
        return False
    host = (u.hostname or "").lower()
    if not host:
        return False
    allowed = host in config.ALLOWED_VIDEO_HOSTS or any(host.endswith(s) for s in config.ALLOWED_VIDEO_SUFFIXES)
    if not allowed:
        return False
    return not _is_private_host(host)

def rewrite_playlist(text: str, final_url: str) -> str:
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            out.append(line); continue
        if s.startswith("#"):
            if 'URI="' in s:
                pre, rest = s.split('URI="', 1)
                uri, post = rest.split('"', 1)
                line = pre + 'URI="' + urljoin(final_url, uri) + '"' + post
            out.append(line); continue
        out.append(urljoin(final_url, s))
    return "\n".join(out) + "\n"

async def fetch_playlist(url: str) -> str:
    if not host_allowed(url):
        raise MediaError("host_not_allowed")
    async with httpx.AsyncClient(timeout=30, follow_redirects=False,
                                 headers={"User-Agent": config.UA, "Accept": "*/*"}) as c:
        r = await c.get(url)
        # seguir 302 manualmente, re-validando el destino (anti SSRF/rebind)
        hops = 0
        while r.status_code in (301, 302, 303, 307, 308) and hops < 4:
            loc = r.headers.get("location", "")
            nxt = urljoin(url, loc)
            if not host_allowed(nxt):
                raise MediaError("redirect_not_allowed")
            r = await c.get(nxt); url = nxt; hops += 1
        r.raise_for_status()
        return rewrite_playlist(r.text, str(r.url))
