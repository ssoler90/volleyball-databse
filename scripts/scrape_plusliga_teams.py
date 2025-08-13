# -*- coding: utf-8 -*-
"""
Created on Wed Aug 13 12:20:13 2025

@author: soler
"""


import re
import csv
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE = "https://www.plusliga.pl"
INDEX = f"{BASE}/teams.html"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36")
}
TIMEOUT = 25
season_pat = re.compile(r"Sezon\s+\d{4}/\d{4}")

def get_soup(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def get_season_links(index_url: str):
    soup = get_soup(index_url)
    seasons = []
    for a in soup.select("a[href]"):
        text = clean_text(a.get_text(" "))
        href = a.get("href", "")
        if season_pat.fullmatch(text) and "/teams/tour/" in href:
            seasons.append(urljoin(BASE, href))
    seen = set(); out = []
    for u in seasons:
        if u not in seen:
            seen.add(u); out.append(u)
    return out

def normalize_key(name: str) -> str:
    return clean_text(name).lower()

def extract_teams_from_season(season_url: str):
    soup = get_soup(season_url)
    names = []
    for a in soup.select("a[href*='/teams/id/']"):
        txt = clean_text(a.get_text(" "))
        if 2 <= len(txt) <= 100:
            names.append(txt)
    seen = set(); out = []
    for n in names:
        if n not in seen:
            seen.add(n); out.append(n)
    return out

def main():
    seasons = get_season_links(INDEX)
    if not seasons:
        raise RuntimeError("No se encontraron enlaces de temporada.")

    uniq = {}
    for i, season_url in enumerate(seasons, 1):
        print(f"[{i}/{len(seasons)}] {season_url}")
        for name in extract_teams_from_season(season_url):
            key = normalize_key(name)
            if key not in uniq:
                uniq[key] = name

    final_names = sorted(uniq.values(), key=lambda x: x.lower())
    print(f"\nTotal equipos únicos: {len(final_names)}")
    for n in final_names:
        print("-", n)

    # Guardar CSV en data/raw/
    output_path = "../data/raw/plusliga_teams_unique.csv"
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["team"])
        for n in final_names:
            w.writerow([n])
    print(f"\nArchivo CSV guardado en: {output_path}")

if __name__ == "__main__":
    main()
