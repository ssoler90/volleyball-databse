# -*- coding: utf-8 -*-
"""
Created on Wed Aug 13 14:20:41 2025

@author: soler
"""

# scripts/scrape_plusliga_players.py

# scripts/scrape_plusliga_players.py

import re
import csv
import time
from urllib.parse import urljoin, urlparse
from pathlib import Path
import requests
from bs4 import BeautifulSoup, Tag

BASE = "https://www.plusliga.pl"
TEAMS_INDEX = f"{BASE}/teams.html"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36")
}
TIMEOUT = 25
SLEEP = 0.6
SEASON_TXT = re.compile(r"Sezon\s+\d{4}/\d{4}")

# Etiquetas (incluye sinónimos antiguos)
LABEL_MAP = {
    "data urodzenia": "birth_date",
    "drużyna": "team",
    "klub": "team",
    "zespół": "team",
    "pozycja": "position",
    "wzrost": "height_cm",
    "waga": "weight_kg",
    "zasięg ataku": "spike_reach_cm",
    "zasięg w ataku": "spike_reach_cm",
    "zasięg ataku w wyskoku": "spike_reach_cm",
    "zasięg z wyskoku do ataku": "spike_reach_cm",  # variante que viste
    "numer": "jersey_number",
}

def get_soup(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def season_text_to_slug(season_text: str) -> str:
    y1, y2 = re.search(r"(\d{4})/(\d{4})", season_text).groups()
    return f"{y1}-{y2}"

# -------- Descubrir temporadas desde /teams.html (más estable) --------
def extract_seasons_from_teams_index():
    soup = get_soup(TEAMS_INDEX)
    seasons = []
    for a in soup.select("a[href*='/teams/tour/']"):
        text = clean(a.get_text(" "))
        href = a.get("href", "")
        m = re.search(r"/teams/tour/(\d+)", href)
        if m and SEASON_TXT.fullmatch(text):
            seasons.append((text, m.group(1)))
    # únicos y ordenados
    seen=set(); out=[]
    for t, sid in seasons:
        if (t, sid) not in seen:
            seen.add((t, sid)); out.append((t, sid))
    out.sort(key=lambda x: int(re.search(r"(\d{4})/\d{4}", x[0]).group(1)))
    return out

# -------- Equipos oficiales por temporada (para verificar ‘team’) --------
def get_teams_for_season(season_id: str):
    url = f"{BASE}/teams/tour/{season_id}.html"
    soup = get_soup(url)
    names = []
    for a in soup.select("a[href*='/teams/id/']"):
        txt = clean(a.get_text(" "))
        if 2 <= len(txt) <= 100:
            names.append(txt)
    # únicos conservando orden
    seen=set(); out=[]
    for n in names:
        if n not in seen:
            seen.add(n); out.append(n)
    return out

# -------- Normalizadores --------
def normalize_team(s: str) -> str:
    return clean(s).lower()

def sanitize_player_name(name: str | None) -> str | None:
    if not name:
        return None
    n = clean(name)
    # cortar sufijos tipo " - Zawodnicy" o " | PlusLiga"
    n = re.split(r"\s[-|]\s", n)[0]
    n = re.sub(r"\b(zawodnicy|zawodnik)\b.*$", "", n, flags=re.IGNORECASE).strip()
    return n or name

# -------- URL canónica del jugador (arreglo principal) --------
def canonical_player_url(any_player_href: str, season_id: str) -> str:
    """
    Tome lo que tome (incluyendo .../section/playersByTeam/...), devuelve:
    https://www.plusliga.pl/players/id/<ID>/tour/<SEASON_ID>.html
    """
    href = any_player_href
    if not href.startswith("http"):
        href = urljoin(BASE, href)
    path = urlparse(href).path
    m = re.search(r"/players/id/(\d+)", path)
    if not m:
        # si no hay id, devolvemos tal cual
        return href
    pid = m.group(1)
    return urljoin(BASE, f"/players/id/{pid}/tour/{season_id}.html")

def parse_kv_from_profile(soup: BeautifulSoup) -> dict:
    data = {}
    # patrón "Etiqueta: Valor"
    for row in soup.select("div, li, p, tr"):
        text = clean(row.get_text(" "))
        m = re.match(r"([^:]+)\s*[:\-]\s*(.+)", text)
        if m:
            label = clean(m.group(1)).lower()
            val = clean(m.group(2))
            if label in LABEL_MAP and val:
                data[LABEL_MAP[label]] = val
    # tablas <th>/<td>
    for tr in soup.select("table tr"):
        th = tr.find(["th","td"])
        tds = tr.find_all("td")
        if th and tds:
            label = clean(th.get_text(" ")).lower()
            val = clean(tds[-1].get_text(" "))
            if label in LABEL_MAP and val:
                data[LABEL_MAP[label]] = val
    # limpieza numérica
    for k in ("height_cm","weight_kg","spike_reach_cm","jersey_number"):
        if k in data:
            m = re.search(r"(\d+)", str(data[k]))
            if m: data[k] = int(m.group(1))
    return data

# -------- Nombre robusto desde la ficha --------
def extract_player_name_from_profile(psoup: BeautifulSoup) -> str | None:
    # 1) h1/h2
    h = psoup.find(["h1","h2"])
    if h:
        name = sanitize_player_name(h.get_text(" "))
        if name and name.lower() not in ("zawodnicy","zawodnik"):
            return name
    # 2) meta og:title
    og = psoup.find("meta", property="og:title")
    if og and og.get("content"):
        name = sanitize_player_name(og["content"])
        if name and name.lower() not in ("zawodnicy","zawodnik"):
            return name
    # 3) clases frecuentes
    for sel in [".player__name", ".player-name", ".name", ".person__name", ".content h1", ".page-title"]:
        el = psoup.select_one(sel)
        if el:
            name = sanitize_player_name(el.get_text(" "))
            if name and name.lower() not in ("zawodnicy","zawodnik"):
                return name
    # 4) heurística: la línea anterior a "Data urodzenia"
    text = psoup.get_text("\n", strip=True)
    # buscar "Data urodzenia" y tomar la línea previa como nombre
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for i, l in enumerate(lines):
        if l.lower().startswith("data urodzenia"):
            if i > 0:
                candidate = sanitize_player_name(lines[i-1])
                if candidate and candidate.lower() not in ("zawodnicy","zawodnik"):
                    return candidate
    return None

# -------- 1) Lista por equipos: asignar equipo + nombre desde la lista --------
def extract_players_with_team_from_list(season_id: str, season_teams: list[str]):
    """
    Devuelve lista de tuplas (player_href, inferred_team, name_from_list)
    desde /players/section/playersByTeam/tour/<season_id>.html
    """
    url = f"{BASE}/players/section/playersByTeam/tour/{season_id}.html"
    soup = get_soup(url)

    team_norm = {t: normalize_team(t) for t in season_teams}
    results = []
    current_team = None

    def node_iter(container: Tag):
        for el in container.descendants:
            if isinstance(el, Tag):
                yield el

    for el in node_iter(soup.body or soup):
        # 1) Encabezados o bloques con texto que parece un equipo
        if el.name in ("h1","h2","h3","h4","strong","b","div","span"):
            text_l = normalize_team(el.get_text(" "))
            if text_l:
                for official, norm in team_norm.items():
                    if text_l == norm or norm in text_l:
                        current_team = official
                        break
        # 2) Enlace explícito a /teams/id/ define equipo
        if el.name == "a" and el.get("href", "").startswith("/teams/id/"):
            t = normalize_team(el.get_text(" "))
            for official, norm in team_norm.items():
                if t == norm or norm in t:
                    current_team = official
                    break
        # 3) Enlace a jugador: recogemos con el equipo vigente y nombre del enlace
        if el.name == "a" and "/players/id/" in (el.get("href") or ""):
            href = urljoin(BASE, el.get("href"))
            pname = clean(el.get_text(" "))  # a veces viene vacío, pero lo intentamos
            results.append((href, current_team, pname if pname else None))

    # únicos manteniendo el primer team/nombre asignado
    seen = {}
    uniq = []
    for href, team, pname in results:
        key = re.sub(r"#.*$", "", href)
        if key not in seen:
            seen[key] = True
            uniq.append((key, team, pname))
    return uniq

# -------- 2) Fallback en la ficha: buscar enlaces a /teams/id/ --------
def resolve_team_from_profile(psoup: BeautifulSoup, season_teams: list[str]) -> str | None:
    team_norm = {t: normalize_team(t) for t in season_teams}
    for a in psoup.select("a[href*='/teams/id/']"):
        t = normalize_team(a.get_text(" "))
        for official, norm in team_norm.items():
            if t == norm or norm in t:
                return official
    body_text = normalize_team(psoup.get_text(" "))
    for official, norm in team_norm.items():
        if norm in body_text:
            return official
    return None

def extract_player_records_from_season(season_text: str, season_id: str):
    season_slug = season_text_to_slug(season_text)
    season_teams = get_teams_for_season(season_id)
    links_with_info = extract_players_with_team_from_list(season_id, season_teams)

    records = []
    for i, (href, team_from_list, name_from_list) in enumerate(links_with_info, 1):
        # URL canónica SIEMPRE (evita /section/playersByTeam/…)
        url = canonical_player_url(href, season_id)

        try:
            psoup = get_soup(url)
        except Exception as e:
            print(f"  [WARN] {e} -> {url}")
            continue

        # Nombre: ficha (robusto) y/o fallback al de la lista
        name = extract_player_name_from_profile(psoup)
        if not name and name_from_list:
            name = name_from_list

        kv = parse_kv_from_profile(psoup)

        # team: prioriza el de la lista; si falta, intenta resolverlo en la ficha
        team = team_from_list or kv.get("team") or resolve_team_from_profile(psoup, season_teams)

        rec = {
            "season": season_slug,
            "player_name": name,
            "birth_date": kv.get("birth_date"),
            "team": team,
            "position": kv.get("position"),
            "height_cm": kv.get("height_cm"),
            "weight_kg": kv.get("weight_kg"),
            "spike_reach_cm": kv.get("spike_reach_cm"),
            "jersey_number": kv.get("jersey_number"),
            "player_url": url,
        }
        records.append(rec)

        if i % 20 == 0:
            print(f"    {i}/{len(links_with_info)} jugadores procesados...")
        time.sleep(SLEEP)

    return records

def save_csv(rows, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["season","player_name","birth_date","team","position",
            "height_cm","weight_kg","spike_reach_cm","jersey_number","player_url"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def main():
    seasons = extract_seasons_from_teams_index()
    if not seasons:
        raise RuntimeError("No se detectaron temporadas desde teams.html")

    all_rows = []
    for idx, (season_text, season_id) in enumerate(seasons, 1):
        print(f"[{idx}/{len(seasons)}] {season_text} (tour={season_id})")
        rows = extract_player_records_from_season(season_text, season_id)
        print(f"  -> {len(rows)} jugadores extraídos")
        save_csv(rows, Path(f"../data/raw/players_{season_text_to_slug(season_text)}.csv"))
        all_rows.extend(rows)

    save_csv(all_rows, Path("../data/raw/players_all_seasons.csv"))
    print("\n✅ Generados CSV por temporada y el global en data/raw/")

if __name__ == "__main__":
    main()
