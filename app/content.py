# app/content.py
import asyncio, base64, json, httpx
from . import config

def uv(v: dict):
    k = next(iter(v)); val = v[k]
    if k == "mapValue":   return {kk: uv(vv) for kk, vv in val.get("fields", {}).items()}
    if k == "arrayValue": return [uv(x) for x in val.get("values", [])]
    if k == "integerValue": return int(val)
    if k == "doubleValue":  return float(val)
    if k == "booleanValue": return val
    if k == "nullValue":  return None
    return val

def _wk(s):
    try: return int(s[1:])
    except Exception: return 999

def _dk(s):
    try: return int(s[1:])
    except Exception: return 9

def walk_calendar(data: dict):
    out = []
    for w in sorted((data or {}).keys(), key=_wk):
        days = data[w] or {}
        for d in sorted(days.keys(), key=_dk):
            for wid in (days[d] or {}).get("wo", []):
                if wid and wid != "rest":
                    out.append((wid, w, d))
    return out

def _name_from_token(id_token: str) -> str:
    try:
        p = id_token.split(".")[1]; p += "=" * (-len(p) % 4)
        return json.loads(base64.urlsafe_b64decode(p)).get("name", "")
    except Exception:
        return ""

async def _fs_get(c: httpx.AsyncClient, path: str, token: str) -> dict:
    r = await c.get(f"{config.FS}/{path}", headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json()

async def _fetch_workout(c, wid, token):
    try:
        wf = (await _fs_get(c, f"companies/{config.CID}/workouts/{wid}", token)).get("fields", {})
    except Exception:
        return None
    title = uv(wf.get("title", {"stringValue": wid}))
    detail = {
        "duration": uv(wf.get("duration", {"nullValue": None})),
        "target_area": uv(wf.get("target_area", {"nullValue": None})),
        "equipments": uv(wf.get("equipments", {"nullValue": None})),
        "desc": uv(wf.get("desc", {"nullValue": None})),
        "intensity": uv(wf.get("intensity", {"nullValue": None})),
    }
    media = uv(wf.get("media", {"nullValue": None})) or []
    for m in media:
        if isinstance(m, dict) and m.get("type") == "video" and m.get("url"):
            return {"id": wid, "title": title, "url": m["url"],
                    "thumb": m.get("thumbnailUrl"), "detail": detail, "exercises": []}
    return None  # v1: solo workouts con video a nivel workout; ejercicios -> iteracion futura

# rank de slot para ordenar programas (primary antes que secondary)
_SLOT_RANK = {"primary": 0, "a": 0, "secondary": 1, "b": 1}

async def build_content(id_token: str, uid: str) -> dict:
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": config.UA}) as c:
        prof = (await _fs_get(c, f"user_profiles/{config.CID}:{uid}", id_token)).get("fields", {})
        aplan = prof.get("aplan", {}).get("stringValue")
        name = (prof.get("displayName", {}).get("stringValue")
                or prof.get("name", {}).get("stringValue") or _name_from_token(id_token))
        if not aplan:
            return {"name": name, "startDate": None, "planId": None, "programs": [], "calendar": []}

        plan = (await _fs_get(c, f"plans/{aplan}", id_token)).get("fields", {})
        cal_data = uv(plan.get("data", {"nullValue": None})) or {}
        # wom2 ya viene DECODIFICADO por uv(); sus entries son dicts planos (no Firestore)
        wom2 = uv(plan.get("wom2", {"nullValue": None})) or {}
        start_ymd = uv(plan.get("startDate", {"nullValue": None}))
        plan_id = aplan.split(":")[-1] if aplan else None

        # cada programa (schedule) -> items (workoutId, week, day)
        progs = []
        for sid, entries in wom2.items():
            e = entries[0] if isinstance(entries, list) and entries else (entries if isinstance(entries, dict) else {})
            title = e.get("title", sid)
            slot = e.get("slot", "")
            try:
                sched = (await _fs_get(c, f"companies/{config.CID}/schedules/{sid}", id_token)).get("fields", {})
                sdata = uv(sched.get("data", {"nullValue": None})) or {}
            except Exception:
                sdata = {}
            progs.append((sid, title, slot, walk_calendar(sdata)))
        progs.sort(key=lambda p: _SLOT_RANK.get(p[2], 2))

        # workout ids: calendario + todos los programas
        ids = set(w for w, _, _ in walk_calendar(cal_data))
        for _, _, _, items in progs:
            ids.update(w for w, _, _ in items)
        ids = list(ids)

        # fetch concurrente acotado (asyncio.gather + semaforo)
        sem = asyncio.Semaphore(12)
        async def _one(wid):
            async with sem:
                return wid, await _fetch_workout(c, wid, id_token)
        cache = {}
        if ids:
            for wid, wk in await asyncio.gather(*[_one(w) for w in ids]):
                if wk:
                    cache[wid] = wk

        # programas con sus videos
        programs = []
        wid_to_prog = {}
        for sid, title, slot, items in progs:
            vids = []
            for wid, w, d in items:
                wid_to_prog.setdefault(wid, title)
                wk = cache.get(wid)
                if wk:
                    vids.append({**wk, "week": w, "day": d})
            if vids:
                programs.append({"title": title, "slot": slot, "count": len(vids), "videos": vids})

        # calendario (con _prog para distinguir videos del mismo dia)
        weeks = {}
        for wid, w, d in walk_calendar(cal_data):
            wk = cache.get(wid)
            if not wk:
                continue
            weeks.setdefault(w, {}).setdefault(d, []).append(
                {**wk, "week": w, "day": d, "_prog": wid_to_prog.get(wid)})
        calendar = [{"week": w, "days": [{"day": d, "videos": weeks[w][d]}
                                         for d in sorted(weeks[w], key=_dk)]}
                    for w in sorted(weeks, key=_wk)]

        start_d = None
        if start_ymd:
            try:
                from datetime import date
                start_d = date(int(start_ymd[0:4]), int(start_ymd[4:6]), int(start_ymd[6:8])).isoformat()
            except Exception:
                pass
        return {"name": name, "startDate": start_d, "planId": plan_id,
                "programs": programs, "calendar": calendar}
