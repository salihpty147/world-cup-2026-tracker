from flask import Flask, jsonify
from urllib.request import urlopen
import json
from html import escape
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

MATCHES_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
SQUADS_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.squads.json"
IST = timezone(timedelta(hours=5, minutes=30))

FLAGS = {
    "Argentina": "🇦🇷", "Australia": "🇦🇺", "Austria": "🇦🇹", "Belgium": "🇧🇪",
    "Bosnia & Herzegovina": "🇧🇦", "Bosnia and Herzegovina": "🇧🇦", "Brazil": "🇧🇷",
    "Canada": "🇨🇦", "Cabo Verde": "🇨🇻", "Cape Verde": "🇨🇻", "Colombia": "🇨🇴",
    "Congo DR": "🇨🇩", "DR Congo": "🇨🇩", "Croatia": "🇭🇷", "Curaçao": "🇨🇼",
    "Czech Republic": "🇨🇿", "Czechia": "🇨🇿", "Ecuador": "🇪🇨", "Egypt": "🇪🇬",
    "England": "🏴", "France": "🇫🇷", "Germany": "🇩🇪", "Ghana": "🇬🇭",
    "Haiti": "🇭🇹", "IR Iran": "🇮🇷", "Iran": "🇮🇷", "Iraq": "🇮🇶",
    "Ivory Coast": "🇨🇮", "Côte d'Ivoire": "🇨🇮", "Japan": "🇯🇵", "Jordan": "🇯🇴",
    "Mexico": "🇲🇽", "Morocco": "🇲🇦", "Netherlands": "🇳🇱", "New Zealand": "🇳🇿",
    "Norway": "🇳🇴", "Panama": "🇵🇦", "Paraguay": "🇵🇾", "Portugal": "🇵🇹",
    "Qatar": "🇶🇦", "Saudi Arabia": "🇸🇦", "Scotland": "🏴", "Senegal": "🇸🇳",
    "South Africa": "🇿🇦", "South Korea": "🇰🇷", "Korea Republic": "🇰🇷",
    "Spain": "🇪🇸", "Sweden": "🇸🇪", "Switzerland": "🇨🇭", "Tunisia": "🇹🇳",
    "Türkiye": "🇹🇷", "Turkiye": "🇹🇷", "USA": "🇺🇸", "United States": "🇺🇸",
    "Uruguay": "🇺🇾", "Uzbekistan": "🇺🇿"
}


def flag(team):
    return FLAGS.get(team, "🏳️")


def fetch_json(url):
    try:
        with urlopen(url, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:
        print("Data fetch error:", error)
        return {}


def get_matches():
    data = fetch_json(MATCHES_URL)
    return data.get("matches", []) if isinstance(data, dict) else []


def get_squads_raw():
    return fetch_json(SQUADS_URL)


def completed(match):
    return isinstance(match.get("score"), dict) and "ft" in match["score"]


def score_text(match):
    if completed(match):
        score = match["score"]["ft"]
        return f"{score[0]} - {score[1]}"
    return "Upcoming"


def team_label(team):
    return f"{flag(team)} {team}"


def match_ist_datetime(match):
    try:
        date_text = match.get("date", "")
        time_text = match.get("time", "")

        if not date_text or not time_text or "UTC" not in time_text:
            return None

        time_part, offset_part = time_text.split(" UTC")
        source_dt = datetime.strptime(f"{date_text} {time_part}", "%Y-%m-%d %H:%M")
        source_tz = timezone(timedelta(hours=int(offset_part)))

        return source_dt.replace(tzinfo=source_tz).astimezone(IST)
    except Exception:
        return None


def match_sort_key(match):
    return match_ist_datetime(match) or datetime.max.replace(tzinfo=timezone.utc)


def ist_text(match):
    dt = match_ist_datetime(match)
    if not dt:
        return match.get("time", "TBA") or "TBA"
    return dt.strftime("%d %b %Y, %I:%M %p IST")


def ist_date(match):
    dt = match_ist_datetime(match)
    return dt.date() if dt else None


def build_points_table(matches):
    table = {}

    for match in matches:
        group = match.get("group", "")
        team1 = match.get("team1", "")
        team2 = match.get("team2", "")

        if not group or "Group" not in group or not team1 or not team2:
            continue

        if group not in table:
            table[group] = {}

        for team in [team1, team2]:
            if team not in table[group]:
                table[group][team] = {
                    "team": team,
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                    "gf": 0,
                    "ga": 0,
                    "gd": 0,
                    "points": 0
                }

    for match in matches:
        if not completed(match):
            continue

        group = match.get("group", "")
        team1 = match.get("team1", "")
        team2 = match.get("team2", "")

        if group not in table or team1 not in table[group] or team2 not in table[group]:
            continue

        goals1, goals2 = match["score"]["ft"]
        goals1 = int(goals1)
        goals2 = int(goals2)

        table[group][team1]["played"] += 1
        table[group][team2]["played"] += 1

        table[group][team1]["gf"] += goals1
        table[group][team1]["ga"] += goals2

        table[group][team2]["gf"] += goals2
        table[group][team2]["ga"] += goals1

        if goals1 > goals2:
            table[group][team1]["won"] += 1
            table[group][team2]["lost"] += 1
            table[group][team1]["points"] += 3
        elif goals2 > goals1:
            table[group][team2]["won"] += 1
            table[group][team1]["lost"] += 1
            table[group][team2]["points"] += 3
        else:
            table[group][team1]["drawn"] += 1
            table[group][team2]["drawn"] += 1
            table[group][team1]["points"] += 1
            table[group][team2]["points"] += 1

        table[group][team1]["gd"] = table[group][team1]["gf"] - table[group][team1]["ga"]
        table[group][team2]["gd"] = table[group][team2]["gf"] - table[group][team2]["ga"]

    return {
        group: sorted(
            teams.values(),
            key=lambda x: (x["points"], x["gd"], x["gf"], x["team"]),
            reverse=True
        )
        for group, teams in table.items()
    }


def build_top_scorers(matches):
    scorers = {}

    for match in matches:
        for goals_key, team_key in [("goals1", "team1"), ("goals2", "team2")]:
            team = match.get(team_key, "")

            for goal in match.get(goals_key, []):
                player = goal.get("name", "Unknown")
                key = f"{player}|{team}"

                if key not in scorers:
                    scorers[key] = {
                        "player": player,
                        "team": team,
                        "goals": 0
                    }

                scorers[key]["goals"] += 1

    return sorted(
        scorers.values(),
        key=lambda x: (x["goals"], x["player"]),
        reverse=True
    )


def goal_scorer_text(match):
    parts = []

    for goals_key, team_key in [("goals1", "team1"), ("goals2", "team2")]:
        team = match.get(team_key, "")

        for goal in match.get(goals_key, []):
            name = goal.get("name", "Unknown")
            minute = goal.get("minute", "")
            penalty = " pen" if goal.get("penalty") else ""
            parts.append(f"{name} ({team}, {minute}'{penalty})")

    return "; ".join(parts) if parts else "Goal scorer details not available"


def normalize_squads(raw):
    squads = {}

    if isinstance(raw, dict):
        if isinstance(raw.get("squads"), list):
            items = raw["squads"]
        elif isinstance(raw.get("teams"), list):
            items = raw["teams"]
        else:
            items = [{"team": k, "players": v} for k, v in raw.items()]
    elif isinstance(raw, list):
        items = raw
    else:
        items = []

    for item in items:
        if not isinstance(item, dict):
            continue

        team = (
            item.get("team")
            or item.get("name")
            or item.get("title")
            or item.get("team_name")
