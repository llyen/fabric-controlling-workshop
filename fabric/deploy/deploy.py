"""Wdrożenie środowiska warsztatowego na Microsoft Fabric. Każdy krok można powtarzać.

Kroki (w tej kolejności):
  obszar     obszar roboczy na wskazanej pojemności
  lakehouse  lakehouse LH_Kontroling i oczekiwanie na punkt końcowy SQL
  pliki      parquet z dane/parquet do Files/dane, Excel z dane/excel do Files/wejscia
  tabele     ładowanie plików parquet do tabel Delta (Load Table API)
  sql        wymuszenie synchronizacji metadanych punktu końcowego SQL
  modele     trzy modele semantyczne Direct Lake z fabric/semantic_model (z folderem Copilot, jeśli jest);
             na końcu sprawdza, czy SM_Planowanie korzysta z połączenia chmurowego bez SSO
  odswiez    odświeżenie (reframing) modeli i kontrolne zapytanie DAX
  sqldb      baza Fabric SQL SQLDB_Planowanie, cel writebacku planu i aplikacji PowerTable
  agenci     dwa agenty danych z fabric/data_agent

Elementu Plan skrypt nie tworzy. Plan buduje się w interfejsie według scenariusza warsztatu (rozdział o Planning).
Nie tworzy też połączenia chmurowego OAuth 2.0 bez SSO, bez którego Plan nie łączy się z modelem Direct Lake.
API połączeń nie przyjmuje poświadczeń OAuth 2.0, więc to połączenie ustawia się ręcznie (krok P0 scenariusza).

Przykłady:
  python fabric/deploy/deploy.py                      (wszystkie kroki)
  python fabric/deploy/deploy.py --kroki modele,odswiez
  python fabric/deploy/deploy.py --tryb-direct-lake onelake

Konfiguracja przez zmienne środowiskowe:
  FABRIC_WORKSPACE    nazwa obszaru (domyślnie "Fabrikam Kontroling Warsztat")
  FABRIC_CAPACITY_ID  identyfikator pojemności Fabric (wymagany przy tworzeniu obszaru)
Uwierzytelnienie: az login na koncie z prawem tworzenia obszarów w docelowej dzierżawie.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fabric_api as fa  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
STAN = Path(__file__).with_name(".stan_wdrozenia.json")
WS_NAME = os.environ.get("FABRIC_WORKSPACE", "Fabrikam Kontroling Warsztat")
CAPACITY_ID = os.environ.get("FABRIC_CAPACITY_ID", "")
LH_NAME = "LH_Kontroling"
SQLDB_NAME = "SQLDB_Planowanie"

MODELE = {
    "SM_Kontroling": "Model przygotowany dla AI: polskie nazwy, opisy, miary P&L, odchylenia, LFL. Dane syntetyczne.",
    "SM_Kontroling_surowy": "Te same tabele bez przygotowania: nazwy techniczne, bez miar i opisów. Do porównania.",
    "SM_Planowanie": "Model dla Planning w Fabric IQ: miesiące, marki, kraje, kanały, sprzedaż ACT, BUD i FC. "
                     "Nazwy ASCII. Dane syntetyczne.",
}
TABELA_KONTROLNA = {"SM_Kontroling": "Rachunek wyników", "SM_Kontroling_surowy": "fakt_pnl",
                    "SM_Planowanie": "Sprzedaz"}
AGENCI = {
    "Agent_Kontroling": {
        "model": "SM_Kontroling",
        "opis": "Agent danych kontrolingu: wyniki, budżet, prognoza, odchylenia i sprzedaż. Dane syntetyczne.",
        "instrukcje": "instrukcje_agenta_en.md",
    },
    "Agent_Kontroling_bez_przygotowania": {
        "model": "SM_Kontroling_surowy",
        "opis": "Ten sam zakres danych bez instrukcji i bez przygotowania modelu. Do porównania na warsztacie.",
        "instrukcje": None,
    },
}
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition"


def wczytaj_stan() -> dict:
    return json.loads(STAN.read_text(encoding="utf-8")) if STAN.exists() else {}


def zapisz_stan(st: dict) -> None:
    STAN.write_text(json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")


def pliki_parquet() -> list[Path]:
    files = sorted((REPO / "dane" / "parquet").glob("*.parquet"))
    if not files:
        sys.exit("Brak plików w dane/parquet. Najpierw uruchom generator: python generator/generate_data.py")
    return files


# ---------------------------------------------------------------- kroki

def krok_obszar(st: dict) -> None:
    ws = fa.find_workspace(WS_NAME)
    if not ws:
        if not CAPACITY_ID:
            sys.exit("Ustaw FABRIC_CAPACITY_ID, aby utworzyć obszar roboczy.")
        ws = fa.call("POST", "/workspaces", {
            "displayName": WS_NAME, "capacityId": CAPACITY_ID,
            "description": "Warsztat Microsoft Fabric dla kontrolingu i finansów. Dane syntetyczne."})
        print(f"  utworzono obszar {ws['id']}")
    elif CAPACITY_ID and ws.get("capacityId", "").lower() != CAPACITY_ID.lower():
        fa.call("POST", f"/workspaces/{ws['id']}/assignToCapacity", {"capacityId": CAPACITY_ID})
        print("  przypisano obszar do pojemności")
    else:
        print(f"  obszar istnieje {ws['id']}")
    st["workspaceId"] = ws["id"]


def krok_lakehouse(st: dict) -> None:
    ws = st["workspaceId"]
    lh = fa.find_item(ws, LH_NAME, "Lakehouse")
    if not lh:
        lh = fa.call("POST", f"/workspaces/{ws}/lakehouses", {
            "displayName": LH_NAME, "description": "Dane syntetyczne kontrolingu (parquet i tabele Delta)."})
        lh = lh or fa.find_item(ws, LH_NAME, "Lakehouse")
        print(f"  utworzono lakehouse {lh['id']}")
    st["lakehouseId"] = lh["id"]
    for _ in range(60):
        d = fa.call("GET", f"/workspaces/{ws}/lakehouses/{lh['id']}")
        sql = (d.get("properties") or {}).get("sqlEndpointProperties") or {}
        if sql.get("provisioningStatus") == "Success" and sql.get("connectionString") and sql.get("id"):
            st["sqlEndpoint"] = sql["connectionString"]
            st["sqlEndpointId"] = sql["id"]
            print(f"  punkt końcowy SQL gotowy {sql['id']}")
            return
        time.sleep(10)
    sys.exit("Punkt końcowy SQL lakehouse nie jest gotowy po 10 minutach.")


def krok_pliki(st: dict) -> None:
    ws, lh = st["workspaceId"], st["lakehouseId"]
    for f in pliki_parquet():
        fa.onelake_upload(ws, lh, f"Files/dane/{f.name}", f.read_bytes())
        print(f"  Files/dane/{f.name} ({f.stat().st_size / 1e6:.1f} MB)")
    for f in sorted((REPO / "dane" / "excel").glob("*.xlsx")):
        fa.onelake_upload(ws, lh, f"Files/wejscia/{f.name}", f.read_bytes())
        print(f"  Files/wejscia/{f.name}")


def krok_tabele(st: dict) -> None:
    ws, lh = st["workspaceId"], st["lakehouseId"]
    for f in pliki_parquet():
        t0 = time.time()
        fa.call("POST", f"/workspaces/{ws}/lakehouses/{lh}/tables/{f.stem}/load", {
            "relativePath": f"Files/dane/{f.name}", "pathType": "File", "mode": "Overwrite",
            "recursive": False, "formatOptions": {"format": "Parquet"}}, timeout=1800)
        print(f"  tabela {f.stem} załadowana ({time.time() - t0:.0f} s)")
    # Lista tabel w API odświeża się z opóźnieniem względem zakończonych operacji load.
    for _ in range(18):
        tabele = {t["name"] for t in fa.call("GET", f"/workspaces/{ws}/lakehouses/{lh}/tables").get("data", [])}
        brak = [f.stem for f in pliki_parquet() if f.stem not in tabele]
        if not brak:
            break
        time.sleep(10)
    if brak:
        sys.exit(f"Brak tabel w lakehouse: {brak}")
    print(f"  w lakehouse jest {len(tabele)} tabel")


def krok_sql(st: dict) -> None:
    ws, sid = st["workspaceId"], st["sqlEndpointId"]
    for suffix in ("", "?preview=true"):
        try:
            fa.call("POST", f"/workspaces/{ws}/sqlEndpoints/{sid}/refreshMetadata{suffix}", {}, timeout=900)
            print("  metadane punktu końcowego SQL zsynchronizowane")
            return
        except RuntimeError as e:
            last = e
    print(f"  ostrzeżenie: synchronizacja metadanych nie powiodła się ({str(last)[:300]})")


def model_parts(name: str, st: dict, tryb: str) -> list[dict]:
    folder = REPO / "fabric" / "semantic_model" / name
    if not folder.exists():
        sys.exit(f"Brak definicji {folder}. Uruchom: python fabric/semantic_model/build_tmdl.py")
    parts = []
    for f in sorted(folder.rglob("*")):
        if not f.is_file():
            continue
        txt = f.read_text(encoding="utf-8")
        if f.name == "expressions.tmdl":
            if tryb == "onelake":
                url = f"https://onelake.dfs.fabric.microsoft.com/{st['workspaceId']}/{st['lakehouseId']}"
                txt = re.sub(r"Sql\.Database\([^)]*\)", f'AzureStorage.DataLake("{url}")', txt)
            else:
                txt = txt.replace("{{SQL_ENDPOINT}}", st["sqlEndpoint"]).replace("{{SQL_ENDPOINT_ID}}", st["sqlEndpointId"])
        if tryb == "onelake" and f.suffix == ".tmdl":
            txt = re.sub(r"^\t\t\tschemaName: dbo\n", "", txt, flags=re.M)
        parts.append(fa.encode_part(f.relative_to(folder).as_posix(), txt))
    return parts


def krok_modele(st: dict, tryb: str) -> None:
    ws = st["workspaceId"]
    st.setdefault("modele", {})
    for name, desc in MODELE.items():
        parts = model_parts(name, st, tryb)
        it = fa.find_item(ws, name, "SemanticModel")
        if it:
            fa.call("POST", f"/workspaces/{ws}/semanticModels/{it['id']}/updateDefinition",
                    {"definition": {"parts": parts}})
            print(f"  zaktualizowano {name} {it['id']}")
        else:
            res = fa.call("POST", f"/workspaces/{ws}/semanticModels",
                          {"displayName": name, "description": desc, "definition": {"parts": parts}})
            it = res if isinstance(res, dict) and res.get("id") else fa.find_item(ws, name, "SemanticModel")
            print(f"  utworzono {name} {it['id']}")
        st["modele"][name] = it["id"]
        if (REPO / "fabric" / "semantic_model" / name / "Copilot").exists():
            got = fa.decode_parts(fa.get_definition(ws, it["id"]))
            cop = sorted(p for p in got if p.startswith("Copilot/"))
            print(f"  {name}: Fabric zwraca {len(cop)} plików folderu Copilot {cop}")
            if not cop:
                print("  ostrzeżenie: Fabric nie zachował folderu Copilot (sprawdź wersję 6.0 w definition.pbism "
                      "i pliki version.json); instrukcje trzeba wtedy wkleić ręcznie w Prep data for AI")
    st["trybDirectLake"] = tryb
    sprawdz_polaczenie_planu(st)


MODEL_PLANU = "SM_Planowanie"


def polaczenie_modelu(ws: str, mid: str) -> dict | None:
    """Połączenie chmurowe, do którego przypisano model, albo None, gdy model działa na domyślnym SSO."""
    zrodla = fa.pbi_call("GET", f"/groups/{ws}/datasets/{mid}/datasources").get("value") or []
    for z in zrodla:
        if z.get("gatewayId") and z.get("datasourceId"):
            try:
                c = fa.call("GET", f"/connections/{z['datasourceId']}", ok=(200,))
            except RuntimeError:
                c = {}
            cred = c.get("credentialDetails") or {}
            return {"id": z["datasourceId"], "nazwa": c.get("displayName", z["datasourceId"]),
                    "poswiadczenia": cred.get("credentialType", "?"), "sso": cred.get("singleSignOnType", "?")}
    return None


def sprawdz_polaczenie_planu(st: dict) -> None:
    mid = st.get("modele", {}).get(MODEL_PLANU)
    if not mid:
        return
    try:
        pol = polaczenie_modelu(st["workspaceId"], mid)
    except RuntimeError as e:
        print(f"  nie udało się sprawdzić połączenia {MODEL_PLANU}: {str(e)[:300]}")
        return
    if pol is None:
        print(f"  ostrzeżenie: {MODEL_PLANU} korzysta z domyślnego SSO i Plan nie połączy się z nim. Ustaw ręcznie "
              "połączenie chmurowe OAuth 2.0 bez SSO (Settings > Gateway and cloud connections > Maps to), "
              "jak w kroku P0 scenariusza")
    elif pol["sso"] == "None":
        print(f"  {MODEL_PLANU}: połączenie {pol['nazwa']}, poświadczenia {pol['poswiadczenia']}, bez SSO")
    elif pol["sso"] == "?":
        print(f"  {MODEL_PLANU}: przypisany do połączenia {pol['id']}, ale jego ustawień nie udało się odczytać")
    else:
        print(f"  ostrzeżenie: połączenie {pol['nazwa']} modelu {MODEL_PLANU} ma włączone SSO ({pol['sso']}); "
              "dla modelu Direct Lake Plan wymaga stałej tożsamości, czyli SSO wyłączonego")


def krok_odswiez(st: dict) -> None:
    ws = st["workspaceId"]
    for name, mid in st["modele"].items():
        fa.pbi_call("POST", f"/groups/{ws}/datasets/{mid}/refreshes",
                    {"type": "full", "commitMode": "transactional", "retryCount": 1}, ok=(200, 202))
        for _ in range(90):
            time.sleep(10)
            hist = fa.pbi_call("GET", f"/groups/{ws}/datasets/{mid}/refreshes?$top=1", ok=(200,))
            stat = (hist.get("value") or [{}])[0].get("status")
            if stat in ("Completed", "Failed", "Disabled", "Cancelled"):
                break
        if stat != "Completed":
            det = (hist.get("value") or [{}])[0].get("serviceExceptionJson", "")
            sys.exit(f"Odświeżenie {name}: {stat} {det}")
        tabela = TABELA_KONTROLNA.get(name, "Rachunek wyników")
        rows = fa.dax(ws, mid, f"EVALUATE ROW(\"wiersze\", COUNTROWS('{tabela}'))")
        print(f"  {name}: odświeżony, {tabela} ma {rows[0]['[wiersze]']:,} wierszy")


def krok_sqldb(st: dict) -> None:
    ws = st["workspaceId"]
    db = fa.find_item(ws, SQLDB_NAME, "SQLDatabase")
    if db:
        print(f"  baza istnieje {db['id']}")
    else:
        res = fa.call("POST", f"/workspaces/{ws}/sqlDatabases", {
            "displayName": SQLDB_NAME,
            "description": "Cel writebacku planu i aplikacji PowerTable (Planning w Fabric IQ). Dane syntetyczne."},
            timeout=1200)
        db = res if isinstance(res, dict) and res.get("id") else fa.find_item(ws, SQLDB_NAME, "SQLDatabase")
        print(f"  utworzono bazę {db['id']}")
    st["sqlDatabaseId"] = db["id"]


def agent_parts(st: dict, cfg: dict) -> list[dict]:
    ws = st["workspaceId"]
    model = cfg["model"]
    mid = st["modele"][model]
    tabele = sorted(f.stem for f in (REPO / "fabric" / "semantic_model" / model / "definition" / "tables").glob("*.tmdl"))

    def tekst(nazwa: str | None) -> str | None:
        if not nazwa:
            return None
        return (REPO / "fabric" / "data_agent" / nazwa).read_text(encoding="utf-8").strip()

    stage = {"$schema": f"{SCHEMA}/stageConfiguration/1.0.0/schema.json", "aiInstructions": tekst(cfg["instrukcje"])}
    # Przy źródle typu model semantyczny agent pomija instrukcje i opis źródła. Reguły biznesowe są w
    # instrukcjach AI modelu (Prep data for AI, folder Copilot), dlatego te pola zostają puste.
    ds = {
        "$schema": f"{SCHEMA}/dataSource/1.0.0/schema.json",
        "artifactId": mid,
        "workspaceId": ws,
        "dataSourceInstructions": None,
        "displayName": model,
        "type": "semantic_model",
        "userDescription": None,
        "metadata": None,
        "elements": [{"id": None, "is_selected": True, "display_name": t, "type": "semantic_model.table",
                      "description": None, "children": []} for t in tabele],
    }
    folder = f"semantic-model-{model}"
    pliki = [
        ("Files/Config/data_agent.json", {"$schema": f"{SCHEMA}/dataAgent/2.1.0/schema.json"}),
        ("Files/Config/draft/stage_config.json", stage),
        (f"Files/Config/draft/{folder}/datasource.json", ds),
        ("Files/Config/publish_info.json", {"$schema": f"{SCHEMA}/publishInfo/1.0.0/schema.json",
                                            "description": cfg["opis"]}),
        ("Files/Config/published/stage_config.json", stage),
        (f"Files/Config/published/{folder}/datasource.json", ds),
    ]
    return [fa.encode_part(p, json.dumps(o, ensure_ascii=False, indent=2)) for p, o in pliki]


def krok_agenci(st: dict) -> None:
    ws = st["workspaceId"]
    st.setdefault("agenci", {})
    for name, cfg in AGENCI.items():
        parts = agent_parts(st, cfg)
        it = fa.find_item(ws, name, "DataAgent")
        if not it:
            res = fa.call("POST", f"/workspaces/{ws}/items",
                          {"displayName": name, "description": cfg["opis"], "type": "DataAgent"})
            it = res if isinstance(res, dict) and res.get("id") else fa.find_item(ws, name, "DataAgent")
            print(f"  utworzono {name} {it['id']}")
        fa.call("POST", f"/workspaces/{ws}/items/{it['id']}/updateDefinition", {"definition": {"parts": parts}})
        time.sleep(3)
        got = fa.decode_parts(fa.get_definition(ws, it["id"]))
        zrodla = [p for p in got if p.endswith("datasource.json")]
        opublikowane = [p for p in zrodla if "/published/" in p]
        stage = json.loads(got.get("Files/Config/draft/stage_config.json", "{}"))
        print(f"  {name}: {len(zrodla)} plików źródeł (opublikowane {len(opublikowane)}), "
              f"instrukcje {len(stage.get('aiInstructions') or '')} znaków")
        if not zrodla:
            sys.exit(f"Fabric nie przyjął źródła danych agenta {name}.")
        st["agenci"][name] = it["id"]


KROKI = ["obszar", "lakehouse", "pliki", "tabele", "sql", "modele", "odswiez", "sqldb", "agenci"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kroki", default=",".join(KROKI), help="lista kroków oddzielona przecinkami")
    ap.add_argument("--tryb-direct-lake", choices=["sql", "onelake"], default="sql",
                    help="Direct Lake przez punkt końcowy SQL (domyślnie) albo bezpośrednio z OneLake")
    args = ap.parse_args()
    kroki = [k.strip() for k in args.kroki.split(",") if k.strip()]
    nieznane = [k for k in kroki if k not in KROKI]
    if nieznane:
        sys.exit(f"Nieznane kroki: {nieznane}. Dostępne: {KROKI}")

    st = wczytaj_stan()
    if "obszar" not in kroki and "workspaceId" not in st:
        krok_obszar(st)
    for k in KROKI:
        if k not in kroki:
            continue
        print(f"== {k}")
        if k == "modele":
            krok_modele(st, args.tryb_direct_lake)
        else:
            globals()[f"krok_{k}"](st)
        zapisz_stan(st)
    print("Gotowe. Stan zapisano w", STAN.relative_to(REPO))


if __name__ == "__main__":
    main()
