"""Minimalny klient Fabric REST API oparty na tokenach z Azure CLI (az login).

Obsługuje operacje długotrwałe (202 + Location), definicje elementów (base64)
oraz zapis plików do OneLake przez API zgodne z ADLS Gen2.
"""
from __future__ import annotations

import base64
import json
import subprocess
import time
from pathlib import Path
from typing import Any

import requests

FABRIC_API = "https://api.fabric.microsoft.com/v1"
FABRIC_RESOURCE = "https://api.fabric.microsoft.com"
STORAGE_RESOURCE = "https://storage.azure.com"
ONELAKE_DFS = "https://onelake.dfs.fabric.microsoft.com"

_tokens: dict[str, tuple[str, float]] = {}


def get_token(resource: str = FABRIC_RESOURCE) -> str:
    cached = _tokens.get(resource)
    if cached and cached[1] - time.time() > 300:
        return cached[0]
    proc = subprocess.run(
        f'az account get-access-token --resource "{resource}" -o json',
        capture_output=True, text=True, shell=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"az get-access-token nie powiodło się: {proc.stderr.strip()}")
    data = json.loads(proc.stdout)
    expires = data.get("expires_on") or time.time() + 3000
    _tokens[resource] = (data["accessToken"], float(expires))
    return data["accessToken"]


def _headers(resource: str = FABRIC_RESOURCE) -> dict[str, str]:
    return {"Authorization": f"Bearer {get_token(resource)}", "Content-Type": "application/json"}


def _wait_lro(resp: requests.Response, timeout: int = 900) -> Any:
    """Czeka na zakończenie operacji długotrwałej i zwraca jej wynik (jeśli jest)."""
    location = resp.headers.get("Location")
    op_id = resp.headers.get("x-ms-operation-id")
    if not location and op_id:
        location = f"{FABRIC_API}/operations/{op_id}"
    if not location:
        return resp.json() if resp.content else None
    deadline = time.time() + timeout
    while time.time() < deadline:
        delay = int(resp.headers.get("Retry-After", "3") or 3)
        time.sleep(max(2, min(delay, 15)))
        resp = requests.get(location, headers=_headers(), timeout=120)
        if resp.status_code == 200:
            body = resp.json() if resp.content else {}
            status = body.get("status")
            if status in (None, "Succeeded"):
                if status == "Succeeded":
                    res = requests.get(location.rstrip("/") + "/result", headers=_headers(), timeout=120)
                    if res.status_code == 200 and res.content:
                        return res.json()
                    return body
                return body
            if status in ("Failed", "Cancelled"):
                raise RuntimeError(f"Operacja {location} zakończona statusem {status}: {json.dumps(body, ensure_ascii=False)}")
        elif resp.status_code not in (202,):
            raise RuntimeError(f"Błąd odpytywania LRO {resp.status_code}: {resp.text}")
    raise TimeoutError(f"Przekroczono czas oczekiwania na {location}")


def call(method: str, path: str, body: Any | None = None, ok=(200, 201, 202), wait: bool = True,
         timeout: int = 900) -> Any:
    url = path if path.startswith("http") else f"{FABRIC_API}{path}"
    for attempt in range(6):
        resp = requests.request(method, url, headers=_headers(), json=body, timeout=180)
        if resp.status_code == 429:
            time.sleep(int(resp.headers.get("Retry-After", "20") or 20))
            continue
        break
    if resp.status_code not in ok:
        raise RuntimeError(f"{method} {url} -> {resp.status_code}: {resp.text[:2000]}")
    if resp.status_code == 202 and wait:
        return _wait_lro(resp, timeout=timeout)
    if resp.content:
        try:
            return resp.json()
        except ValueError:
            return resp.text
    return None


def list_items(workspace_id: str, item_type: str | None = None) -> list[dict]:
    path = f"/workspaces/{workspace_id}/items" + (f"?type={item_type}" if item_type else "")
    out: list[dict] = []
    while path:
        data = call("GET", path)
        out.extend(data.get("value", []))
        token = data.get("continuationToken")
        path = (f"/workspaces/{workspace_id}/items?continuationToken={token}"
                + (f"&type={item_type}" if item_type else "")) if token else None
    return out


def find_item(workspace_id: str, name: str, item_type: str) -> dict | None:
    for it in list_items(workspace_id, item_type):
        if it["displayName"] == name:
            return it
    return None


def find_workspace(name: str) -> dict | None:
    path: str | None = "/workspaces"
    while path:
        data = call("GET", path)
        for ws in data.get("value", []):
            if ws["displayName"] == name:
                return ws
        token = data.get("continuationToken")
        path = f"/workspaces?continuationToken={token}" if token else None
    return None


# ---------- Power BI REST (odświeżanie i zapytania DAX) ----------

PBI_API = "https://api.powerbi.com/v1.0/myorg"
PBI_RESOURCE = "https://analysis.windows.net/powerbi/api"


def pbi_call(method: str, path: str, body: Any | None = None, ok=(200, 201, 202)) -> Any:
    url = path if path.startswith("http") else f"{PBI_API}{path}"
    h = {"Authorization": " ".join(("Bearer", get_token(PBI_RESOURCE))), "Content-Type": "application/json"}
    for _ in range(6):
        resp = requests.request(method, url, headers=h, json=body, timeout=300)
        if resp.status_code == 429:
            time.sleep(int(resp.headers.get("Retry-After", "20") or 20))
            continue
        break
    if resp.status_code not in ok:
        raise RuntimeError(f"{method} {url} -> {resp.status_code}: {resp.text[:2000]}")
    if resp.content:
        try:
            return resp.json()
        except ValueError:
            return resp.text
    return None


def dax(workspace_id: str, dataset_id: str, query: str) -> list[dict]:
    """Wykonuje zapytanie DAX przez executeQueries i zwraca wiersze pierwszej tabeli wyniku."""
    res = pbi_call("POST", f"/groups/{workspace_id}/datasets/{dataset_id}/executeQueries",
                   {"queries": [{"query": query}], "serializerSettings": {"includeNulls": True}}, ok=(200,))
    first = res["results"][0]
    if "error" in first:
        raise RuntimeError(json.dumps(first["error"], ensure_ascii=False)[:2000])
    return first["tables"][0].get("rows", [])


def get_definition(workspace_id: str, item_id: str, fmt: str | None = None) -> dict:
    path = f"/workspaces/{workspace_id}/items/{item_id}/getDefinition" + (f"?format={fmt}" if fmt else "")
    return call("POST", path)


def decode_parts(definition: dict) -> dict[str, str]:
    parts = definition.get("definition", definition).get("parts", [])
    out = {}
    for p in parts:
        raw = base64.b64decode(p["payload"])
        try:
            out[p["path"]] = raw.decode("utf-8")
        except UnicodeDecodeError:
            out[p["path"]] = f"<binary {len(raw)} bytes>"
    return out


def encode_part(path: str, content: str | bytes) -> dict:
    data = content.encode("utf-8") if isinstance(content, str) else content
    return {"path": path, "payload": base64.b64encode(data).decode("ascii"), "payloadType": "InlineBase64"}


def parts_from_folder(folder: Path) -> list[dict]:
    parts = []
    for f in sorted(folder.rglob("*")):
        if f.is_file():
            parts.append(encode_part(f.relative_to(folder).as_posix(), f.read_bytes()))
    return parts


# ---------- OneLake (ADLS Gen2 DFS) ----------

def onelake_upload(workspace_id: str, item_id: str, rel_path: str, data: bytes) -> None:
    """Zapisuje plik w OneLake: rel_path względem elementu, np. 'Files/raw/plik.csv'."""
    base = f"{ONELAKE_DFS}/{workspace_id}/{item_id}/{rel_path}"
    h = {"Authorization": f"Bearer {get_token(STORAGE_RESOURCE)}", "x-ms-version": "2023-11-03"}
    r = requests.put(base + "?resource=file", headers=h, timeout=120)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"OneLake create {rel_path}: {r.status_code} {r.text[:500]}")
    chunk = 32 * 1024 * 1024
    for pos in range(0, len(data), chunk):
        r = requests.patch(base + f"?action=append&position={pos}",
                           headers={**h, "Content-Type": "application/octet-stream"},
                           data=data[pos:pos + chunk], timeout=600)
        if r.status_code not in (200, 202):
            raise RuntimeError(f"OneLake append {rel_path}: {r.status_code} {r.text[:500]}")
    r = requests.patch(base + f"?action=flush&position={len(data)}", headers=h, timeout=120)
    if r.status_code not in (200,):
        raise RuntimeError(f"OneLake flush {rel_path}: {r.status_code} {r.text[:500]}")


def onelake_list(workspace_id: str, item_id: str, directory: str) -> list[str]:
    url = f"{ONELAKE_DFS}/{workspace_id}?resource=filesystem&recursive=true&directory={item_id}/{directory}"
    h = {"Authorization": f"Bearer {get_token(STORAGE_RESOURCE)}", "x-ms-version": "2023-11-03"}
    r = requests.get(url, headers=h, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"OneLake list: {r.status_code} {r.text[:500]}")
    return [p["name"] for p in r.json().get("paths", [])]
