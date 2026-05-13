#!/usr/bin/env python3
"""
日本生まれのMLB選手とそのIDを一覧表示するヘルパースクリプト。
ja_names.json に追加する選手IDを確認するのに使う。

使い方:
  pip install requests
  python discover_players.py
"""

import json
from datetime import date
from pathlib import Path

import requests

season = date.today().year
resp = requests.get(
    "https://statsapi.mlb.com/api/v1/sports/1/players",
    params={"season": season, "gameType": "R"},
    timeout=30,
)
resp.raise_for_status()

players = [p for p in resp.json()["people"] if p.get("birthCountry") == "Japan"]
players.sort(key=lambda p: p["fullName"])

print(f"\n{season}シーズン 日本生まれのMLB選手一覧：\n")
for p in players:
    print(f"  {p['id']:>7}  {p['fullName']}")

print(f"\n合計 {len(players)} 名\n")

# ja_names.json の現在の内容と照合
ja_file = Path(__file__).parent / "ja_names.json"
if ja_file.exists():
    ja_names = json.loads(ja_file.read_text(encoding="utf-8"))
    missing = [p for p in players if str(p["id"]) not in ja_names]
    if missing:
        print("ja_names.json に日本語名が未登録の選手：")
        for p in missing:
            print(f'  "{p["id"]}": "（日本語名）",  // {p["fullName"]}')
    else:
        print("全員の日本語名が登録済みです。")
