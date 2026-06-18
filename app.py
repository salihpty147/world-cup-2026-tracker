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


def flag_img(team):
    code = COUNTRY_CODES.get(team)
    if not code:
        return ""
    return f'<img class="team-flag" src="https://flagcdn.com/24x18/{code}.png" alt="{escape(team)} flag" loading="lazy">'


def team_label(team):
    return f'{flag_img(team)}<span>{escape(team)}</span>'


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


def match_datetime_ist(match):
    try:
        date_text = match.get("date", "")
        time_text = match.get("time", "")

        if not date_text or not time_text or "UTC" not in time_text:
            return None

        time_part, offset_part = time_text.split(" UTC")
        local_dt = datetime.strptime(f"{date_text} {time_part}", "%Y-%m-%d %H:%M")
        local_tz = timezone(timedelta(hours=int(offset_part)))

        return local_dt.replace(tzinfo=local_tz).astimezone(IST)

    except Exception:
        return None


def sort_key(match):
    return match_datetime_ist(match) or datetime.max.replace(tzinfo=timezone.utc)


def ist_text(match):
    dt = match_datetime_ist(match)
    return dt.strftime("%d %b %Y, %I:%M %p IST") if dt else "TBA"


def ist_date(match):
    dt = match_datetime_ist(match)
    return dt.date() if dt else None


def goal_scorer_text(match):
    items = []

    for goals_key, team_key in [("goals1", "team1"), ("goals2", "team2")]:
        team = match.get(team_key, "")

        for goal in match.get(goals_key, []):
            name = goal.get("name", "Unknown")
            minute = goal.get("minute", "")
            penalty = " pen" if goal.get("penalty") else ""
            items.append(f"{name} ({team}, {minute}'{penalty})")

    return "; ".join(items) if items else "Goal scorer details not available"


def build_top_scorers(matches):
    scorers = {}

    for match in matches:
        for goals_key, team_key in [("goals1", "team1"), ("goals2", "team2")]:
            team = match.get(team_key, "")

            for goal in match.get(goals_key, []):
                player = goal.get("name", "Unknown")
                key = f"{player}|{team}"

                scorers.setdefault(key, {
                    "player": player,
                    "team": team,
                    "goals": 0
                })

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


def normalize_squads(raw):
    squads = {}

    if isinstance(raw, dict):
        if isinstance(raw.get("squads"), list):
            items = raw["squads"]
        elif isinstance(raw.get("teams"), list):
            items = raw["teams"]
        else:
            items = [{"team": team_name, "players": players} for team_name, players in raw.items()]
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

        score_html = f"<span class='score-pill'>{escape(score_text(match))}</span>" if show_score else ""

        round_html = ""
        if show_round:
            round_html = f"<div class='match-info'><span>Round</span><b>{escape(match.get('round', ''))}</b></div>"

        status_html = ""
        if show_status:
            status_html = f"<div class='match-info'><span>Status</span><b>{'Completed' if completed(match) else 'Upcoming'}</b></div>"

        scorers_html = ""
        if show_scorers:
            scorers_html = f"<div class='match-info full'><span>Goal Scorers</span><b>{escape(scorer_details)}</b></div>"

        cards += f"""
        <div class="match-card" data-search="{escape(search_text)}">
            <div class="match-main-row">
                <div class="team-name">{team_label(team1)}</div>
                <div class="vs-text">vs</div>
                <div class="team-name">{team_label(team2)}</div>
                <div class="match-score">{score_html}</div>
            </div>

            <div class="match-details-grid">
                {round_html}
                <div class="match-info"><span>Date</span><b>{escape(match.get('date', ''))}</b></div>
                <div class="match-info"><span>Indian Time</span><b>{escape(ist_text(match))}</b></div>
                <div class="match-info"><span>Group</span><b>{escape(match.get('group', ''))}</b></div>
                {status_html}
                <div class="match-info full"><span>Venue</span><b>{escape(match.get('ground', ''))}</b></div>
                {scorers_html}
            </div>
        </div>
        """

    return cards


def scorer_cards(scorers):
    if not scorers:
        return "<div class='empty-card'>No goal scorer data available yet.</div>"

    html = ""

    for rank, scorer in enumerate(scorers[:10], start=1):
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


def points_tables(standings):
    html = ""

    for group in sorted(standings.keys()):
        html += f"""
        <h3 class="group-title">{escape(group)}</h3>
        <div class="table-wrap">
            <table class="points-table">
                <tr>
                    <th>Pos</th>
                    <th>Team</th>
                    <th>P</th>
                    <th>W</th>
                    <th>D</th>
                    <th>L</th>
                    <th>GF</th>
                    <th>GA</th>
                    <th>GD</th>
                    <th>Pts</th>
                </tr>
        """

        for pos, team in enumerate(standings[group], start=1):
            team_name = team["team"]
            search_text = f"{team_name} {group}".lower()

            html += f"""
            <tr data-search="{escape(search_text)}">
                <td>{pos}</td>
                <td>{team_label(team_name)}</td>
                <td>{team['played']}</td>
                <td>{team['won']}</td>
                <td>{team['drawn']}</td>
                <td>{team['lost']}</td>
                <td>{team['gf']}</td>
                <td>{team['ga']}</td>
                <td>{team['gd']}</td>
                <td><b>{team['points']}</b></td>
            </tr>
            """

        html += """
            </table>
        </div>
        """

    return html or "<div class='empty-card'>Points table not available.</div>"


def player_dropdown_html(squads):
    if not squads:
        return "<div class='empty-card'>Player squad data is not available from the free source currently.</div>"

    options = '<option value="">Select country</option>'
    cards = ""

    for team in sorted(squads.keys()):
        safe_team = escape(team)
        options += f'<option value="{safe_team}">{safe_team}</option>'
        cards += f'<div class="player-team-block" data-team="{safe_team}" style="display:none;">'
        cards += f'<h3 class="group-title">{team_label(team)}</h3>'

        for player in squads[team]:
            search_text = f"{player.get('name', '')} {player.get('position', '')} {team}".lower()
            number = player.get("number", "")
            position = player.get("position", "") or "Position not available"

            cards += f"""
            <div class="mini-card" data-search="{escape(search_text)}">
                <div class="rank">{escape(str(number))}</div>
                <div>
                    <b>{escape(player.get('name', ''))}</b>
                    <span>{escape(position)}</span>
                </div>
                <div>{flag_img(team)}</div>
            </div>
            """

        cards += "</div>"

    return f"""
    <select id="teamSelect" class="team-select" onchange="showPlayersByTeam()">
        {options}
    </select>

    <div id="playerHint" class="empty-card">Select a country to view players.</div>

    {cards}
    """


@app.route("/")
def home():
    return world_cup_2026()


@app.route("/world-cup-2026")
def world_cup_2026():
    matches = get_matches()

    all_matches = sorted(matches, key=sort_key)
    completed_matches = sorted([m for m in matches if completed(m)], key=sort_key)
    upcoming_matches = sorted([m for m in matches if not completed(m)], key=sort_key)

    today = datetime.now(IST).date()
    tomorrow = today + timedelta(days=1)

    today_matches = [m for m in all_matches if ist_date(m) == today]
    tomorrow_matches = [m for m in all_matches if ist_date(m) == tomorrow]

    standings = build_points_table(matches)
    top_scorers = build_top_scorers(matches)
    squads = normalize_squads(get_squads_raw())

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>FIFA World Cup 2026 Tracker</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-VMBRKJMJNM"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-VMBRKJMJNM');
</script>
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
                padding: 14px 12px;
            }}

            .hero h1 {{
                margin: 0;
                font-size: 23px;
                line-height: 1.2;
            }}

            .container {{
                max-width: 1100px;
                margin: 0 auto;
                padding: 10px;
            }}

            .toolbar {{
                background: white;
                border-radius: 16px;
                padding: 11px;
                box-shadow: 0 8px 20px rgba(15,23,42,.08);
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
                padding: 11px 8px;
                border-radius: 13px;
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
                margin-top: 10px;
                padding: 12px;
                border-radius: 13px;
                border: 1px solid #d8e2ee;
                font-size: 14px;
            }}

            .stats-line {{
                display: flex;
                align-items: center;
                gap: 8px;
                overflow-x: auto;
                white-space: nowrap;
                background: white;
                border-radius: 15px;
                padding: 10px;
                margin: 10px 0;
                box-shadow: 0 8px 20px rgba(15,23,42,.08);
            }}

            .stat-pill {{
                display: inline-flex;
                align-items: center;
                gap: 5px;
                font-size: 13px;
                font-weight: 900;
                color: #0f3764;
                background: #f1f7fd;
                padding: 7px 10px;
                border-radius: 999px;
            }}

            .section {{
                display: none;
            }}

            .section.active {{
                display: block;
            }}

            .section-title {{
                font-size: 21px;
                color: #082f5f;
                margin: 14px 0 10px;
            }}

            .match-card,
            .mini-card,
            .empty-card {{
                background: white;
                border-radius: 16px;
                padding: 13px;
                margin-bottom: 11px;
                box-shadow: 0 8px 20px rgba(15,23,42,.08);
            }}

            .match-main-row {{
                display: grid;
                grid-template-columns: 1fr auto 1fr;
                gap: 8px;
                align-items: center;
            }}

            .team-name {{
                font-size: 16px;
                font-weight: 900;
                line-height: 1.3;
            }}

            .vs-text {{
                color: #64748b;
                font-size: 12px;
                font-weight: 900;
                text-align: center;
            }}

            .match-score {{
                grid-column: 1 / 4;
                margin-top: 8px;
            }}

            .score-pill {{
                display: inline-block;
                background: #dcfce7;
                color: #166534;
                padding: 6px 10px;
                border-radius: 999px;
                font-weight: 900;
                white-space: nowrap;
                font-size: 13px;
            }}

            .gold-pill {{
                background: #fef3c7;
                color: #92400e;
            }}

            .match-details-grid {{
                margin-top: 10px;
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 8px;
            }}

            .match-info {{
                background: #f8fafc;
                border-radius: 12px;
                padding: 8px;
            }}

            .match-info span {{
                display: block;
                color: #64748b;
                font-size: 11px;
                font-weight: 800;
                margin-bottom: 3px;
            }}

            .match-info b {{
                font-size: 12px;
            }}

            .match-info.full {{
                grid-column: 1 / 3;
            }}

            .mini-card {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12px;
            }}

            .mini-card b {{
                display: block;
            }}

            .mini-card span {{
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

            .table-wrap {{
                overflow-x: auto;
                background: white;
                border-radius: 14px;
                box-shadow: 0 8px 20px rgba(15,23,42,.08);
                margin-bottom: 12px;
            }}

            .points-table {{
                width: 100%;
                border-collapse: collapse;
                min-width: 640px;
            }}

            .points-table th {{
                background: #082f5f;
                color: white;
                padding: 10px;
                text-align: left;
                font-size: 12px;
            }}

            .points-table td {{
                padding: 10px;
                border-bottom: 1px solid #e8eef5;
                font-size: 12px;
            }}

            .team-select {{
                width: 100%;
                padding: 13px;
                border-radius: 13px;
                border: 1px solid #d8e2ee;
                background: white;
                font-size: 14px;
                font-weight: 800;
                margin-bottom: 12px;
            }}

            @media (min-width: 800px) {{
                .hero {{
                    padding: 20px 22px;
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

                .match-score {{
                    grid-column: auto;
                    margin-top: 0;
                    text-align: right;
                }}

                .match-main-row {{
                    grid-template-columns: 1fr auto 1fr auto;
                }}

                .stats-line {{
                    justify-content: flex-start;
                }}
            }}
        </style>

        <script>
            function showSection(sectionId, buttonId) {{
                document.querySelectorAll('.section').forEach(section => section.classList.remove('active'));
                document.querySelectorAll('.tab').forEach(button => button.classList.remove('active'));

                document.getElementById(sectionId).classList.add('active');
                document.getElementById(buttonId).classList.add('active');
            }}

            function filterRows() {{
                const value = document.getElementById('searchBox').value.toLowerCase();

                document.querySelectorAll('[data-search]').forEach(card => {{
                    card.style.display = card.getAttribute('data-search').includes(value) ? '' : 'none';
                }});
            }}

            function showPlayersByTeam() {{
                const selected = document.getElementById('teamSelect').value;

                document.querySelectorAll('.player-team-block').forEach(block => {{
                    block.style.display = block.getAttribute('data-team') === selected ? 'block' : 'none';
                }});

                document.getElementById('playerHint').style.display = selected ? 'none' : 'block';
            }}
        </script>
    </head>

    <body>
        <div class="hero">
            <h1>⚽ FIFA World Cup 2026 Tracker</h1>
        </div>

        <main class="container">
            <div class="toolbar">
                <div class="tabs">
                    <button id="today-btn" class="tab active" onclick="showSection('today','today-btn')">📅 Matches Today</button>
                    <button id="tomorrow-btn" class="tab" onclick="showSection('tomorrow','tomorrow-btn')">🗓️ Matches Tomorrow</button>
                    <button id="completed-btn" class="tab" onclick="showSection('completed','completed-btn')">✅ Completed</button>
                    <button id="upcoming-btn" class="tab" onclick="showSection('upcoming','upcoming-btn')">⏳ Upcoming</button>
                    <button id="fixtures-btn" class="tab" onclick="showSection('fixtures','fixtures-btn')">🏟️ Fixtures</button>
                    <button id="points-btn" class="tab" onclick="showSection('points','points-btn')">📊 Points Table</button>
                    <button id="scorers-btn" class="tab" onclick="showSection('scorers','scorers-btn')">🥅 Top Scorers</button>
                    <button id="players-btn" class="tab" onclick="showSection('players','players-btn')">👥 Players List</button>
                </div>

                <input id="searchBox" onkeyup="filterRows()" class="search" placeholder="Search team, group, player or goal scorer">
            </div>

            <div class="stats-line">
                <span class="stat-pill">🏟️ Total Fixtures {len(matches)}</span>
                <span class="stat-pill">✅ {len(completed_matches)} Completed</span>
                <span class="stat-pill">⏳ {len(upcoming_matches)} Upcoming</span>
                <span class="stat-pill">📅 {len(today_matches)} Today in IST</span>
            </div>

            <section id="today" class="section active">
                <h2 class="section-title">📅 Matches Today</h2>
                {match_cards(today_matches, True, False, False, True)}
            </section>

            <section id="tomorrow" class="section">
                <h2 class="section-title">🗓️ Matches Tomorrow</h2>
                {match_cards(tomorrow_matches, True)}
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
                <h2 class="section-title">🏟️ Fixtures</h2>
                {match_cards(all_matches, True, True, True)}
            </section>

            <section id="points" class="section">
                <h2 class="section-title">📊 Points Table</h2>
                {points_tables(standings)}
            </section>

            <section id="scorers" class="section">
                <h2 class="section-title">🥅 Top Scorers</h2>
                {scorer_cards(top_scorers)}
            </section>

            <section id="players" class="section">
                <h2 class="section-title">👥 Players List</h2>
                {player_dropdown_html(squads)}
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
    return jsonify(build_top_scorers(get_matches())[:10])


@app.route("/api/squads")
def api_squads():
    return jsonify(normalize_squads(get_squads_raw()))


if __name__ == "__main__":
    app.run(debug=True)
