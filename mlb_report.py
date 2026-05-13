#!/usr/bin/env python3
"""MLB日本人選手 日次成績レポーター"""

import json
import os
from datetime import date, timedelta
from pathlib import Path

import requests

MLB_API_BASE = "https://statsapi.mlb.com/api/v1"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
JA_NAMES_FILE = Path(__file__).parent / "ja_names.json"
SEPARATOR = "─" * 20


def load_ja_names() -> dict[str, str]:
    if JA_NAMES_FILE.exists():
        return json.loads(JA_NAMES_FILE.read_text(encoding="utf-8"))
    return {}


def get_japan_born_players(season: int) -> dict[int, str]:
    resp = requests.get(
        f"{MLB_API_BASE}/sports/1/players",
        params={"season": season, "gameType": "R"},
        timeout=30,
    )
    resp.raise_for_status()
    return {
        p["id"]: p["fullName"]
        for p in resp.json().get("people", [])
        if p.get("birthCountry") == "Japan"
    }


def get_schedule(game_date: date) -> list[dict]:
    resp = requests.get(
        f"{MLB_API_BASE}/schedule",
        params={"sportId": 1, "date": game_date.isoformat(), "gameType": "R", "hydrate": "team"},
        timeout=30,
    )
    resp.raise_for_status()
    dates = resp.json().get("dates", [])
    return dates[0]["games"] if dates else []


def get_boxscore(game_pk: int) -> dict:
    resp = requests.get(f"{MLB_API_BASE}/game/{game_pk}/boxscore", timeout=30)
    resp.raise_for_status()
    return resp.json()


def fmt_batting_game(b: dict) -> str | None:
    ab = b.get("atBats", 0)
    bb = b.get("baseOnBalls", 0)
    if ab == 0 and bb == 0:
        return None
    hits = b.get("hits", 0)
    parts = [f"{hits}/{ab}"]
    extras = []
    if b.get("homeRuns"):
        extras.append(f"{b['homeRuns']}本")
    if b.get("rbi"):
        extras.append(f"{b['rbi']}打点")
    if bb:
        extras.append(f"{bb}四球")
    if b.get("strikeOuts"):
        extras.append(f"{b['strikeOuts']}三振")
    if b.get("stolenBases"):
        extras.append(f"{b['stolenBases']}盗塁")
    line = "打：" + " ".join(parts)
    if extras:
        line += "  " + " ".join(extras)
    return line


def fmt_batting_season(b: dict) -> str | None:
    avg = b.get("avg", ".---")
    hr = b.get("homeRuns", 0)
    rbi = b.get("rbi", 0)
    ops = b.get("ops", ".---")
    if avg in (".---", None) and hr == 0:
        return None
    return f"今季：打率{avg}  {hr}本  {rbi}打点  OPS{ops}"


def fmt_pitching_game(p: dict) -> str | None:
    ip = p.get("inningsPitched", "0.0")
    if not ip or ip == "0.0":
        return None
    parts = [
        f"{ip}回",
        f"{p.get('hits', 0)}安",
        f"{p.get('earnedRuns', 0)}失",
        f"{p.get('baseOnBalls', 0)}四球",
        f"{p.get('strikeOuts', 0)}奪三振",
    ]
    note = ""
    if p.get("wins"):
        note = "  ◎勝"
    elif p.get("losses"):
        note = "  ●敗"
    elif p.get("saves"):
        note = "  Ｓ"
    elif p.get("holds"):
        note = "  Ｈ"
    elif p.get("blownSaves"):
        note = "  ＢＳ"
    return "投：" + " ".join(parts) + note


def fmt_pitching_season(p: dict) -> str | None:
    era = p.get("era", "-.--")
    wins = p.get("wins", 0)
    losses = p.get("losses", 0)
    so = p.get("strikeOuts", 0)
    ip = p.get("inningsPitched", "0.0")
    if era in ("-.--", None) and ip == "0.0":
        return None
    return f"今季：防御率{era}  {wins}勝{losses}敗  {so}奪三振"


def collect_stats(games: list[dict], jp_ids: set[int]) -> list[dict]:
    results = []
    seen: set[int] = set()

    for game in games:
        if game.get("status", {}).get("abstractGameState") != "Final":
            continue

        game_pk = game["gamePk"]
        t = game["teams"]
        away_abbr = t["away"]["team"].get("abbreviation") or t["away"]["team"].get("name", "???")
        home_abbr = t["home"]["team"].get("abbreviation") or t["home"]["team"].get("name", "???")

        away_score = t["away"].get("score", 0)
        home_score = t["home"].get("score", 0)
        score_line = f"{away_abbr} {away_score}-{home_score} {home_abbr}"

        try:
            box = get_boxscore(game_pk)
        except Exception as e:
            print(f"Warning: boxscore取得失敗 game {game_pk}: {e}")
            continue

        for side in ("home", "away"):
            team_box = box.get("teams", {}).get(side, {})
            team_abbr = team_box.get("team", {}).get("abbreviation", "")

            for _, pdata in team_box.get("players", {}).items():
                pid = pdata.get("person", {}).get("id")
                if pid not in jp_ids or pid in seen:
                    continue
                seen.add(pid)

                stats = pdata.get("stats", {})
                season = pdata.get("seasonStats", {})

                batting_game = fmt_batting_game(stats.get("batting", {}))
                batting_season = fmt_batting_season(season.get("batting", {}))
                pitching_game = fmt_pitching_game(stats.get("pitching", {}))
                pitching_season = fmt_pitching_season(season.get("pitching", {}))

                if batting_game or pitching_game:
                    results.append({
                        "id": pid,
                        "name_en": pdata["person"]["fullName"],
                        "team": team_abbr,
                        "score_line": score_line,
                        "batting_game": batting_game,
                        "batting_season": batting_season,
                        "pitching_game": pitching_game,
                        "pitching_season": pitching_season,
                    })

    return results


def build_message(game_date: date, stats: list[dict], ja_names: dict[str, str]) -> str:
    header = f"⚾ MLB日本人選手成績\n{game_date.year}/{game_date.month}/{game_date.day} (現地時間)\n{SEPARATOR}"

    if not stats:
        return header + "\nこの日は日本人選手の出場試合がありませんでした。"

    lines = [header]
    for p in stats:
        ja = ja_names.get(str(p["id"]), p["name_en"])
        lines.append(f"\n【{ja}】 {p['team']}")
        lines.append(f"  {p['score_line']}")
        if p["pitching_game"]:
            lines.append(f"  {p['pitching_game']}")
            if p["pitching_season"]:
                lines.append(f"  {p['pitching_season']}")
        if p["batting_game"]:
            lines.append(f"  {p['batting_game']}")
            if p["batting_season"]:
                lines.append(f"  {p['batting_season']}")

    return "\n".join(lines)


def send_line(token: str, user_id: str, message: str) -> None:
    resp = requests.post(
        LINE_PUSH_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"to": user_id, "messages": [{"type": "text", "text": message}]},
        timeout=30,
    )
    resp.raise_for_status()


def main() -> None:
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    user_id = os.environ["LINE_USER_ID"]

    game_date = date.today() - timedelta(days=1)
    season = game_date.year

    print(f"対象日：{game_date}")

    jp_players = get_japan_born_players(season)
    print(f"日本生まれの選手：{list(jp_players.values())}")

    games = get_schedule(game_date)
    print(f"試合数：{len(games)}")

    stats = collect_stats(games, set(jp_players.keys()))
    print(f"出場した日本人選手：{len(stats)}名")

    ja_names = load_ja_names()
    message = build_message(game_date, stats, ja_names)

    print("\n--- 送信内容プレビュー ---")
    print(message)
    print("---")

    send_line(token, user_id, message)
    print("LINE送信完了！")


if __name__ == "__main__":
    main()
