from flask import Flask, jsonify
from urllib.request import urlopen
import json
from html import escape
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

MATCHES_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
SQUADS_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.squads.json"
IST = timezone(timedelta(hours=5, minutes=30))

COUNTRY_CODES = {
    "Argentina": "ar", "Australia": "au", "Austria": "at", "Belgium": "be", "Brazil": "br", "Canada": "ca",
    "Colombia": "co", "Croatia": "hr", "Czech Republic": "cz", "Czechia": "cz", "Ecuador": "ec", "Egypt": "eg",
    "England": "gb-eng", "France": "fr", "Germany": "de", "Ghana": "gh", "Haiti": "ht", "Iraq": "iq",
    "IR Iran": "ir", "Iran": "ir", "Japan": "jp", "Mexico": "mx", "Morocco": "ma", "Netherlands": "nl",
    "New Zealand": "nz", "Norway": "no", "Panama": "pa", "Paraguay": "py", "Portugal": "pt", "Qatar": "qa",
    "Saudi Arabia": "sa", "Scotland": "gb-sct", "Senegal": "sn", "South Africa": "za", "South Korea": "kr",
    "Korea Republic": "kr", "Spain": "es", "Sweden": "se", "Switzerland": "ch", "Tunisia": "tn",
    "Türkiye": "tr", "Turkiye": "tr", "USA": "us", "United States": "us", "Uruguay": "uy", "Uzbekistan": "uz",
    "Bosnia & Herzegovina": "ba", "Bosnia and Herzegovina": "ba", "Cabo Verde": "cv", "Cape Verde": "cv",
    "Congo DR": "cd", "DR Congo": "cd", "Curaçao": "cw", "Curacao": "cw", "Ivory Coast": "ci",
    "Côte d'Ivoire": "ci", "Jordan": "jo", "Algeria": "dz"
}


def flag_image(team):
    code = COUNTRY_CODES.get(team)
    if not code:
        return ""
    return f'https://flagcdn.com/24x18/{code}.png flag" loading="lazy">'


def team_label(team):
    return f'{flag_image(team)}<span>{escape(team)}</span>'


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
    return dt.strftime("%d %b %Y, %I:%M %p IST") if dt else "TBA"


def ist_date(match):
    dt = match_ist_datetime(match)
    return dt.date() if dt else None


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


def build_points_table(matches):
    table = {}

    for match in matches:
        group = match.get("group", "")
        team1 = match.get("team1", "")
        team2 = match.get("team2", "")

        if not group or "Group" not in group or not team1 or not team2:
            continue

        table.setdefault(group, {})

        for team in [team1, team2]:
            table[group].setdefault(team, {
                "team": team,
                "played": 0,
                "won": 0,
                "drawn": 0,
                "lost": 0,
                "gf": 0,
                "ga": 0,
                "gd": 0,
                "points": 0
            })

    for match in matches:
        if not completed(match):
            continue

        group = match.get("group", "")
        team1 = match.get("team1", "")
        team2 = match.get("team2", "")

        if group not in table or team1 not in table[group] or team2 not in tablecontinue

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

        team = item.get("team") or item.get("name") or item.get("title") or item.get("team_name") or "Unknown Team"
        players = item.get("players") or item.get("squad") or item.get("roster") or []

        normalized = []

        if isinstance(players, list):
            for player in players:
                if isinstance(player, str):
                    normalized.append({
                        "name": player,
                        "number": "",
                        "position": ""
                    })
                elif isinstance(player, dict):
                    normalized.append({
                        "name": player.get("name") or player.get("player") or "Unknown",
                        "number": player.get("number") or player.get("no") or "",
                        "position": player.get("position") or player.get("pos") or ""
                    })

        squads[team] = normalized

    return squads


def match_cards(matches, show_score=False, show_round=False, show_status=False, show_scorers=False):
    if not matches:
        return "<div class='empty-card'>No matches available.</div>"

    cards = ""

    for match in matches:
        team1 = match.get("team1", "")
        team2 = match.get("team2", "")
        scorer_details = goal_scorer_text(match) if show_scorers else ""

        search_text = f"{team1} {team2} {match.get('group', '')} {match.get('round', '')} {scorer_details}".lower()

        score_html = ""
        if show_score:
            score_html = f"<div class='score-pill'>{escape(score_text(match))}</div>"

        round_html = ""
        if show_round:
            round_html = f"<div class='meta-line'><span>Round</span><b>{escape(match.get('round', ''))}</b></div>"

        status_html = ""
        if show_status:
            status_html = f"<div class='meta-line'><span>Status</span><b>{'Completed' if completed(match) else 'Upcoming'}</b></div>"

        scorers_html = ""
        if show_scorers:
            scorers_html = f"<div class='meta-line full'><span>Goal Scorers</span><b>{escape(scorer_details)}</b></div>"

        cards += f"""
        <div class="match-card" data-search="{escape(search_text)}">
            <div class="match-top">
                <div class="match-teams">
                    {team_label(team1)}
                    <br><small>vs</small><br>
                    {team_label(team2)}
                </div>
                {score_html}
            </div>

            <div class="match-meta">
                {round_html}
                <div class="meta-line"><span>Date</span><b>{escape(match.get('date', ''))}</b></div>
                <div class="meta-line"><span>Indian Time</span><b>{escape(ist_text(match))}</b></div>
                <div class="meta-line"><span>Group</span><b>{escape(match.get('group', ''))}</b></div>
                {status_html}
                <div class="meta-line full"><span>Venue</span><b>{escape(match.get('ground', ''))}</b></div>
                {scorers_html}
            </div>
        </div>
        """

    return cards


def scorer_cards(scorers):
    if not scorers:
        return "<div class='empty-card'>No goal scorer data available yet.</div>"

    html = ""

    for rank, scorer in enumerate(scorers, start=1):
        search_text = f"{scorer['player']} {scorer['team']}".lower()

        html += f"""
        <div class="mini-card" data-search="{escape(search_text)}">
            <div class="rank">#{rank}</div>
            <div>
                <b>{escape(scorer['player'])}</b>
                <span>{team_label(scorer['team'])}</span>
            </div>
            <div class="score-pill">{scorer['goals']}</div>
        </div>
        """

    return html


def points_cards(standings):
    html = ""

    for group in sorted(standings.keys()):
        html += f"<h3 class='group-title'>{escape(group)}</h3>"

        for pos, team in enumerate(standings[group], start=1):
            team_name = team["team"]
            search_text = f"{team_name} {group}".lower()

            html += f"""
            <div class="points-card" data-search="{escape(search_text)}">
                <div>
                    <b>{pos}. {team_label(team_name)}</b>
                    <span>P {team['played']} | W {team['won']} | D {team['drawn']} | L {team['lost']}</span>
                </div>
                <div>
                    <span>GD {team['gd']}</span>
                    <b class="score-pill gold-pill">{team['points']} pts</b>
                </div>
            </div>
            """

    return html or "<div class='empty-card'>Points table not available.</div>"


def player_cards(squads):
    if not squads:
        return "<div class='empty-card'>Player squad data is not available from the free source currently.</div>"

    html = ""

    for team in sorted(squads.keys()):
        html += f"<h3 class='group-title'>{team_label(team)}</h3>"

        for player in squadssearch_text = f"{player.get('name', '')} {player.get('position', '')} {team}".lower()
            number = player.get("number", "")
            position = player.get("position", "") or "Position not available"

            html += f"""
            <div class="mini-card" data-search="{escape(search_text)}">
                <div class="rank">{escape(str(number))}</div>
                <div>
                    <b>{escape(player.get('name', ''))}</b>
                    <span>{escape(position)}</span>
                </div>
                <div>{flag_image(team)}</div>
            </div>
            """

    return html


@app.route("/")
def home():
    return world_cup_2026()


@app.route("/world-cup-2026")
def world_cup_2026():
    matches = get_matches()

    all_matches = sorted(matches, key=match_sort_key)
    completed_matches = sorted([m for m in matches if completed(m)], key=match_sort_key)
    recent_matches = list(reversed(completed_matches[-8:]))
    upcoming_matches = sorted([m for m in matches if not completed(m)], key=match_sort_key)

    today = datetime.now(IST).date()
    tomorrow = today + timedelta(days=1)

    today_matches = [m for m in all_matches if ist_date(m) == today]
    tomorrow_matches = [m for m in all_matches if ist_date(m) == tomorrow]

    next_match = upcoming_matches[0] if upcoming_matches else None
    latest_result = recent_matches[0] if recent_matches else None

    standings = build_points_table(matches)
    scorers = build_top_scorers(matches)
    squads = normalize_squads(get_squads_raw())

    next_text = "No upcoming match"
    if next_match:
        next_text = f"{next_match.get('team1', '')} vs {next_match.get('team2', '')} • {ist_text(next_match)}"

    latest_text = "No completed result"
    if latest_result:
        latest_text = f"{latest_result.get('team1', '')} {score_text(latest_result)} {latest_result.get('team2', '')}"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>FIFA World Cup 2026 Tracker</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <style>
            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #eef4fb;
                color: #0f172a;
            }}

            .hero {{
                background: linear-gradient(135deg, #071b3a, #0057a8, #00a86b);
                color: white;
                padding: 16px 14px 16px;
            }}

            .hero h1 {{
                margin: 0;
                font-size: 24px;
                line-height: 1.2;
            }}

            .hero p {{
                margin: 6px 0 0;
                font-size: 13px;
                opacity: .9;
            }}

            .container {{
                max-width: 1100px;
                margin: 0 auto;
                padding: 10px;
            }}

            .toolbar {{
                background: white;
                border-radius: 18px;
                padding: 12px;
                box-shadow: 0 8px 24px rgba(15,23,42,.08);
                margin-top: 0;
            }}

            .tabs {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 8px;
            }}

            .tab {{
                border: 0;
                background: #e6eef8;
                color: #0f3764;
                padding: 12px 8px;
                border-radius: 14px;
                font-weight: 900;
                font-size: 13px;
                cursor: pointer;
            }}

            .tab.active {{
                background: #00a86b;
                color: white;
            }}

            .search {{
                width: 100%;
                margin-top: 12px;
                padding: 13px;
                border-radius: 14px;
                border: 1px solid #d8e2ee;
                font-size: 14px;
            }}

            .cards {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
                margin: 12px 0;
            }}

            .summary-card {{
                background: white;
                border-radius: 18px;
                padding: 14px;
                box-shadow: 0 8px 24px rgba(15,23,42,.08);
                display: flex;
                gap: 10px;
                align-items: center;
            }}

            .summary-icon {{
                width: 38px;
                height: 38px;
                border-radius: 13px;
                background: #e0f2fe;
                display: grid;
                place-items: center;
            }}

            .summary-num {{
                font-size: 26px;
                color: #0057a8;
                font-weight: 900;
            }}

            .summary-label {{
                font-size: 12px;
                color: #64748b;
            }}

            .quick {{
                background: white;
                padding: 14px;
                border-radius: 18px;
                box-shadow: 0 8px 24px rgba(15,23,42,.08);
                margin-bottom: 12px;
            }}

            .quick div {{
                background: #f1f7fd;
                border-radius: 14px;
                padding: 10px;
                margin-top: 8px;
                font-weight: 700;
                font-size: 13px;
            }}

            .section {{
                display: none;
            }}

            .section.active {{
                display: block;
            }}

            .section-title {{
                font-size: 22px;
                color: #082f5f;
                margin: 14px 0 10px;
            }}

            .match-card,
            .mini-card,
            .points-card,
            .empty-card {{
                background: white;
                border-radius: 18px;
                padding: 14px;
                margin-bottom: 12px;
                box-shadow: 0 8px 24px rgba(15,23,42,.08);
            }}

            .match-top {{
                display: flex;
                justify-content: space-between;
                gap: 10px;
                align-items: flex-start;
            }}

            .match-teams {{
                font-size: 18px;
                line-height: 1.35;
                font-weight: 900;
            }}

            .match-teams small {{
                color: #64748b;
                font-size: 12px;
                font-weight: 700;
            }}

            .score-pill {{
                display: inline-block;
                background: #dcfce7;
                color: #166534;
                padding: 7px 11px;
                border-radius: 999px;
                font-weight: 900;
                white-space: nowrap;
            }}

            .gold-pill {{
                background: #fef3c7;
                color: #92400e;
            }}

            .match-meta {{
                margin-top: 10px;
                display: grid;
                gap: 8px;
            }}

            .meta-line {{
                display: flex;
                justify-content: space-between;
                gap: 12px;
                border-top: 1px solid #eef2f7;
                padding-top: 8px;
            }}

            .meta-line span {{
                color: #64748b;
                font-size: 12px;
                font-weight: 800;
            }}

            .meta-line b {{
                text-align: right;
                font-size: 13px;
            }}

            .meta-line.full {{
                display: block;
            }}

            .meta-line.full b {{
                display: block;
                text-align: left;
                margin-top: 3px;
            }}

            .mini-card,
            .points-card {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12px;
            }}

            .mini-card b,
            .points-card b {{
                display: block;
            }}

            .mini-card span,
            .points-card span {{
                display: block;
                color: #64748b;
                font-size: 12px;
                margin-top: 3px;
            }}

            .rank {{
                min-width: 38px;
                height: 38px;
                border-radius: 13px;
                background: #e0f2fe;
                display: grid;
                place-items: center;
                font-weight: 900;
                color: #075985;
            }}

            .group-title {{
                color: #075985;
                margin: 18px 0 10px;
            }}

            .team-flag {{
                width: 24px;
                height: 18px;
                object-fit: cover;
                border-radius: 3px;
                margin-right: 7px;
                vertical-align: middle;
                box-shadow: 0 1px 3px rgba(0,0,0,.18);
            }}

            @media (min-width: 800px) {{
                .hero {{
                    padding: 20px 22px 22px;
                }}

                .hero h1 {{
                    font-size: 34px;
                }}

                .container {{
                    padding: 18px;
                }}

                .tabs {{
                    display: flex;
                    flex-wrap: wrap;
                }}

                .tab {{
                    font-size: 15px;
                    padding: 12px 16px;
                }}

                .cards {{
                    grid-template-columns: repeat(4, 1fr);
                }}
            }}
        </style>

        <script>
            function showSection(sectionId, buttonId) {{
                document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
                document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));

                document.getElementById(sectionId).classList.add('active');
                document.getElementById(buttonId).classList.add('active');
            }}

            function filterRows() {{
                const value = document.getElementById('searchBox').value.toLowerCase();

                document.querySelectorAll('[data-search]').forEach(card => {{
                    card.style.display = card.getAttribute('data-search').includes(value) ? '' : 'none';
                }});
            }}
        </script>
    </head>

    <body>
        <div class="hero">
            <h1>⚽ FIFA World Cup 2026 Tracker</h1>
            <p>Fixtures, results, IST time, points table, top scorers and squads</p>
        </div>

        <main class="container">
            <div class="toolbar">
                <div class="tabs">
                    <button id="today-btn" class="tab active" onclick="showSection('today','today-btn')">📅 Today</button>
                    <button id="tomorrow-btn" class="tab" onclick="showSection('tomorrow','tomorrow-btn')">🗓️ Tomorrow</button>
                    <button id="recent-btn" class="tab" onclick="showSection('recent','recent-btn')">⚡ Recent</button>
                    <button id="completed-btn" class="tab" onclick="showSection('completed','completed-btn')">✅ Completed</button>
                    <button id="upcoming-btn" class="tab" onclick="showSection('upcoming','upcoming-btn')">⏳ Upcoming</button>
                    <button id="fixtures-btn" class="tab" onclick="showSection('fixtures','fixtures-btn')">🏟️ Fixtures</button>
                    <button id="points-btn" class="tab" onclick="showSection('points','points-btn')">📊 Points</button>
                    <button id="scorers-btn" class="tab" onclick="showSection('scorers','scorers-btn')">🥅 Scorers</button>
                    <button id="goals-btn" class="tab" onclick="showSection('goals','goals-btn')">⚽ Goals</button>
                    <button id="players-btn" class="tab" onclick="showSection('players','players-btn')">👥 Players</button>
                </div>

                <input id="searchBox" onkeyup="filterRows()" class="search" placeholder="Search team, group, player or goal scorer">
            </div>

            <div class="cards">
                <div class="summary-card">
                    <div class="summary-icon">🏟️</div>
                    <div>
                        <div class="summary-num">{len(matches)}</div>
                        <div class="summary-label">Total Fixtures</div>
                    </div>
                </div>

                <div class="summary-card">
                    <div class="summary-icon">✅</div>
                    <div>
                        <div class="summary-num">{len(completed_matches)}</div>
                        <div class="summary-label">Completed</div>
                    </div>
                </div>

                <div class="summary-card">
                    <div class="summary-icon">⏳</div>
                    <div>
                        <div class="summary-num">{len(upcoming_matches)}</div>
                        <div class="summary-label">Upcoming</div>
                    </div>
                </div>

                <div class="summary-card">
                    <div class="summary-icon">📅</div>
                    <div>
                        <div class="summary-num">{len(today_matches)}</div>
                        <div class="summary-label">Today in IST</div>
                    </div>
                </div>
            </div>

            <div class="quick">
                <b>📌 Quick Details</b>
                <div>⏭️ Next Match: {escape(next_text)}</div>
                <div>✅ Latest Result: {escape(latest_text)}</div>
            </div>

            <section id="today" class="section active">
                <h2 class="section-title">📅 Today’s Matches</h2>
                {match_cards(today_matches, True, False, False, True)}
            </section>

            <section id="tomorrow" class="section">
                <h2 class="section-title">🗓️ Tomorrow’s Matches</h2>
                {match_cards(tomorrow_matches, True)}
            </section>

            <section id="recent" class="section">
                <h2 class="section-title">⚡ Recent Matches</h2>
                {match_cards(recent_matches, True, False, False, True)}
            </section>

            <section id="completed" class="section">
                <h2 class="section-title">✅ Completed Matches</h2>
                {match_cards(completed_matches, True, False, False, True)}
            </section>

            <section id="upcoming" class="section">
                <h2 class="section-title">⏳ Upcoming Matches</h2>
                {match_cards(upcoming_matches)}
            </section>

            <section id="fixtures" class="section">
                <h2 class="section-title">🏟️ All Fixtures Till Final</h2>
                {match_cards(all_matches, True, True, True)}
            </section>

            <section id="points" class="section">
                <h2 class="section-title">📊 Points Table</h2>
                {points_cards(standings)}
            </section>

            <section id="scorers" class="section">
                <h2 class="section-title">🥅 Top Scorers</h2>
                {scorer_cards(scorers)}
            </section>

            <section id="goals" class="section">
                <h2 class="section-title">⚽ Goal Scorers by Match</h2>
                {match_cards(completed_matches, True, False, False, True)}
            </section>

            <section id="players" class="section">
                <h2 class="section-title">👥 Players List</h2>
                {player_cards(squads)}
            </section>
        </main>
    </body>
    </html>
    """


@app.route("/api/matches")
def api_matches():
    return jsonify(get_matches())


@app.route("/api/standings")
def api_standings():
    return jsonify(build_points_table(get_matches()))


@app.route("/api/top-scorers")
def api_top_scorers():
    return jsonify(build_top_scorers(get_matches()))


@app.route("/api/squads")
def api_squads():
    return jsonify(normalize_squads(get_squads_raw()))


if __name__ == "__main__":
    app.run(debug=True)
