from flask import Flask, jsonify
from urllib.request import urlopen
import json
from html import escape
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

MATCHES_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
SQUADS_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.squads.json"


def fetch_json(url):
    try:
        with urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:
        print("API error:", error)
        return {}


def get_matches_from_api():
    data = fetch_json(MATCHES_URL)
    return data.get("matches", [])


def get_squads_from_api():
    data = fetch_json(SQUADS_URL)
    return data


def is_completed(match):
    return "score" in match and "ft" in match["score"]


def get_score(match):
    if is_completed(match):
        score = match["score"]["ft"]
        return f"{score[0]} - {score[1]}"
    return "Upcoming"


def convert_to_ist(date_text, time_text):
    try:
        if not time_text or "UTC" not in time_text:
            return time_text

        time_part, utc_part = time_text.split(" UTC")
        match_datetime = datetime.strptime(f"{date_text} {time_part}", "%Y-%m-%d %H:%M")

        offset_hours = int(utc_part)

        source_timezone = timezone(timedelta(hours=offset_hours))
        match_datetime = match_datetime.replace(tzinfo=source_timezone)

        ist_timezone = timezone(timedelta(hours=5, minutes=30))
        ist_datetime = match_datetime.astimezone(ist_timezone)

        return ist_datetime.strftime("%d %b %Y, %I:%M %p IST")

    except Exception:
        return time_text


def get_match_datetime_for_sorting(match):
    try:
        date_text = match.get("date", "")
        time_text = match.get("time", "")

        if not date_text or not time_text or "UTC" not in time_text:
            return datetime.max.replace(tzinfo=timezone.utc)

        time_part, utc_part = time_text.split(" UTC")
        match_datetime = datetime.strptime(f"{date_text} {time_part}", "%Y-%m-%d %H:%M")

        offset_hours = int(utc_part)

        source_timezone = timezone(timedelta(hours=offset_hours))
        match_datetime = match_datetime.replace(tzinfo=source_timezone)

        ist_timezone = timezone(timedelta(hours=5, minutes=30))
        ist_datetime = match_datetime.astimezone(ist_timezone)

        return ist_datetime

    except Exception:
        return datetime.max.replace(tzinfo=timezone.utc)


def build_points_table(matches):
    standings = {}

    for match in matches:
        group = match.get("group", "")
        team1 = match.get("team1", "")
        team2 = match.get("team2", "")

        if not group or not team1 or not team2:
            continue

        if "Group" not in group:
            continue

        if group not in standings:
            standings[group] = {}

        for team in [team1, team2]:
            if team not in standings[group]:
                standings[group][team] = {
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
        if not is_completed(match):
            continue

        group = match.get("group", "")
        team1 = match.get("team1", "")
        team2 = match.get("team2", "")

        if not group or not team1 or not team2:
            continue

        if "Group" not in group:
            continue

        score = match["score"]["ft"]
        team1_goals = score[0]
        team2_goals = score[1]

        standings[group][team1]["played"] += 1
        standings[group][team2]["played"] += 1

        standings[group][team1]["gf"] += team1_goals
        standings[group][team1]["ga"] += team2_goals

        standings[group][team2]["gf"] += team2_goals
        standings[group][team2]["ga"] += team1_goals

        if team1_goals > team2_goals:
            standings[group][team1]["won"] += 1
            standings[group][team2]["lost"] += 1
            standings[group][team1]["points"] += 3
        elif team2_goals > team1_goals:
            standings[group][team2]["won"] += 1
            standings[group][team1]["lost"] += 1
            standings[group][team2]["points"] += 3
        else:
            standings[group][team1]["drawn"] += 1
            standings[group][team2]["drawn"] += 1
            standings[group][team1]["points"] += 1
            standings[group][team2]["points"] += 1

        standings[group][team1]["gd"] = standings[group][team1]["gf"] - standings[group][team1]["ga"]
        standings[group][team2]["gd"] = standings[group][team2]["gf"] - standings[group][team2]["ga"]

    sorted_standings = {}

    for group, teams in standings.items():
        sorted_teams = sorted(
            teams.values(),
            key=lambda x: (x["points"], x["gd"], x["gf"]),
            reverse=True
        )
        sorted_standings[group] = sorted_teams

    return sorted_standings


def build_top_scorers(matches):
    scorers = {}

    for match in matches:
        team1 = match.get("team1", "")
        team2 = match.get("team2", "")

        goals1 = match.get("goals1", [])
        goals2 = match.get("goals2", [])

        for goal in goals1:
            player_name = goal.get("name", "Unknown")
            key = f"{player_name}__{team1}"

            if key not in scorers:
                scorers[key] = {
                    "player": player_name,
                    "team": team1,
                    "goals": 0
                }

            scorers[key]["goals"] += 1

        for goal in goals2:
            player_name = goal.get("name", "Unknown")
            key = f"{player_name}__{team2}"

            if key not in scorers:
                scorers[key] = {
                    "player": player_name,
                    "team": team2,
                    "goals": 0
                }

            scorers[key]["goals"] += 1

    return sorted(
        scorers.values(),
        key=lambda x: (x["goals"], x["player"]),
        reverse=True
    )


def normalize_squads(raw_data):
    squads = {}

    if isinstance(raw_data, dict):
        if "squads" in raw_data:
            squad_items = raw_data.get("squads", [])
        elif "teams" in raw_data:
            squad_items = raw_data.get("teams", [])
        else:
            squad_items = []
            for team_name, players in raw_data.items():
                squad_items.append({
                    "team": team_name,
                    "players": players
                })
    elif isinstance(raw_data, list):
        squad_items = raw_data
    else:
        squad_items = []

    for item in squad_items:
        if not isinstance(item, dict):
            continue

        team_name = (
            item.get("team")
            or item.get("name")
            or item.get("title")
            or item.get("team_name")
            or "Unknown Team"
        )

        players = (
            item.get("players")
            or item.get("squad")
            or item.get("roster")
            or []
        )

        normalized_players = []

        if isinstance(players, list):
            for player in players:
                if isinstance(player, str):
                    normalized_players.append({
                        "name": player,
                        "position": "",
                        "number": ""
                    })
                elif isinstance(player, dict):
                    normalized_players.append({
                        "name": player.get("name", player.get("player", "Unknown")),
                        "position": player.get("position", player.get("pos", "")),
                        "number": player.get("number", player.get("no", ""))
                    })

        squads[team_name] = normalized_players

    return squads


@app.route("/")
def home():
    return world_cup_tracker()


@app.route("/world-cup-2026")
def world_cup_tracker():
    matches = get_matches_from_api()

    sorted_matches = sorted(matches, key=get_match_datetime_for_sorting)

    completed_matches = sorted(
        [match for match in matches if is_completed(match)],
        key=get_match_datetime_for_sorting
    )

    upcoming_matches = sorted(
        [match for match in matches if not is_completed(match)],
        key=get_match_datetime_for_sorting
    )

    standings = build_points_table(matches)
    top_scorers = build_top_scorers(matches)
    squads = normalize_squads(get_squads_from_api())

    completed_rows = ""
    for match in completed_matches:
        completed_rows += f"""
        <tr>
            <td>{escape(match.get("date", ""))}</td>
            <td>{escape(convert_to_ist(match.get("date", ""), match.get("time", "")))}</td>
            <td><span class="group-badge">{escape(match.get("group", ""))}</span></td>
            <td>{escape(match.get("team1", ""))} vs {escape(match.get("team2", ""))}</td>
            <td><span class="score-badge">{get_score(match)}</span></td>
            <td>{escape(match.get("ground", ""))}</td>
        </tr>
        """

    upcoming_rows = ""
    for match in upcoming_matches:
        upcoming_rows += f"""
        <tr>
            <td>{escape(match.get("date", ""))}</td>
            <td>{escape(convert_to_ist(match.get("date", ""), match.get("time", "")))}</td>
            <td><span class="group-badge">{escape(match.get("group", ""))}</span></td>
            <td>{escape(match.get("team1", ""))} vs {escape(match.get("team2", ""))}</td>
            <td>{escape(match.get("ground", ""))}</td>
        </tr>
        """

    all_fixtures_rows = ""
    for match in sorted_matches:
        status = "Completed" if is_completed(match) else "Upcoming"

        score_or_status = get_score(match)

        all_fixtures_rows += f"""
        <tr>
            <td>{escape(match.get("round", ""))}</td>
            <td>{escape(match.get("date", ""))}</td>
            <td>{escape(convert_to_ist(match.get("date", ""), match.get("time", "")))}</td>
            <td><span class="group-badge">{escape(match.get("group", ""))}</span></td>
            <td>{escape(match.get("team1", ""))} vs {escape(match.get("team2", ""))}</td>
            <td>{escape(score_or_status)}</td>
            <td>{escape(status)}</td>
            <td>{escape(match.get("ground", ""))}</td>
        </tr>
        """

    points_html = ""

    for group in sorted(standings.keys()):
        points_html += f"""
        <h3 class="group-title">{escape(group)}</h3>
        <table>
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

        position = 1
        for team in standings[group]:
            points_html += f"""
            <tr>
                <td>{position}</td>
                <td>{escape(team["team"])}</td>
                <td>{team["played"]}</td>
                <td>{team["won"]}</td>
                <td>{team["drawn"]}</td>
                <td>{team["lost"]}</td>
                <td>{team["gf"]}</td>
                <td>{team["ga"]}</td>
                <td>{team["gd"]}</td>
                <td><span class="points-badge">{team["points"]}</span></td>
            </tr>
            """
            position += 1

        points_html += "</table>"

    top_scorers_rows = ""

    rank = 1
    for scorer in top_scorers:
        top_scorers_rows += f"""
        <tr>
            <td>{rank}</td>
            <td>{escape(scorer["player"])}</td>
            <td>{escape(scorer["team"])}</td>
            <td><span class="score-badge">{scorer["goals"]}</span></td>
        </tr>
        """
        rank += 1

    if not top_scorers_rows:
        top_scorers_rows = """
        <tr>
            <td colspan="4">No goal data available yet.</td>
        </tr>
        """

    players_html = ""

    if squads:
        for team_name in sorted(squads.keys()):
            players_html += f"""
            <h3 class="group-title">{escape(team_name)}</h3>
            <table>
                <tr>
                    <th>No</th>
                    <th>Player</th>
                    <th>Position</th>
                </tr>
            """

            for player in squads[team_name]:
                players_html += f"""
                <tr>
                    <td>{escape(str(player.get("number", "")))}</td>
                    <td>{escape(player.get("name", ""))}</td>
                    <td>{escape(player.get("position", ""))}</td>
                </tr>
                """

            players_html += "</table>"
    else:
        players_html = """
        <div class="info-box">
            Player squad data is not available from the current free source at this moment.
        </div>
        """

    lineup_html = ""

    next_matches_for_lineup = upcoming_matches[:8]

    for match in next_matches_for_lineup:
        lineup_html += f"""
        <div class="lineup-card">
            <h3>{escape(match.get("team1", ""))} vs {escape(match.get("team2", ""))}</h3>
            <p><b>Kickoff:</b> {escape(convert_to_ist(match.get("date", ""), match.get("time", "")))}</p>
            <p><b>Venue:</b> {escape(match.get("ground", ""))}</p>

            <div class="pitch">
                <div class="pitch-line">Goalkeeper</div>
                <div class="pitch-line">Defenders</div>
                <div class="pitch-line">Midfielders</div>
                <div class="pitch-line">Forwards</div>
            </div>

            <p class="lineup-note">
                Official starting XI is not available from the current free JSON source.
                Official lineups usually need a lineup API and are generally available before kickoff.
            </p>
        </div>
        """

    if not lineup_html:
        lineup_html = """
        <div class="info-box">
            No upcoming matches available for lineup preview.
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>FIFA World Cup 2026 Tracker</title>
        <style>
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #eef2f7;
                color: #1f2937;
            }}

            .header {{
                background: linear-gradient(135deg, #003b5c, #0077b6);
                color: white;
                padding: 30px;
                text-align: center;
            }}

            .header h1 {{
                margin: 0;
                font-size: 36px;
            }}

            .header p {{
                margin-top: 8px;
                font-size: 16px;
            }}

            .container {{
                width: 95%;
                margin: 25px auto;
            }}

            .summary {{
                display: flex;
                gap: 20px;
                margin-bottom: 25px;
                flex-wrap: wrap;
            }}

            .card {{
                flex: 1;
                min-width: 180px;
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 3px 12px rgba(0,0,0,0.08);
                text-align: center;
            }}

            .card h2 {{
                margin: 0;
                color: #0077b6;
                font-size: 32px;
            }}

            .card p {{
                margin: 5px 0 0;
                color: #555;
            }}

            .button-area {{
                display: flex;
                gap: 15px;
                justify-content: center;
                margin: 25px 0;
                flex-wrap: wrap;
            }}

            .tab-button {{
                background: #003b5c;
                color: white;
                border: none;
                padding: 14px 22px;
                border-radius: 25px;
                font-size: 15px;
                font-weight: bold;
                cursor: pointer;
            }}

            .tab-button:hover {{
                background: #0077b6;
            }}

            .tab-button.active {{
                background: #16a34a;
            }}

            .section {{
                display: none;
            }}

            .section.active {{
                display: block;
            }}

            .section-title {{
                margin-top: 30px;
                padding-left: 10px;
                border-left: 5px solid #0077b6;
                color: #003b5c;
            }}

            .group-title {{
                margin-top: 25px;
                color: #003b5c;
            }}

            .table-wrapper {{
                overflow-x: auto;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 3px 12px rgba(0,0,0,0.08);
                margin-top: 12px;
                margin-bottom: 25px;
            }}

            th {{
                background: #003b5c;
                color: white;
                padding: 14px;
                text-align: left;
                font-size: 14px;
            }}

            td {{
                padding: 13px;
                border-bottom: 1px solid #e5e7eb;
                font-size: 14px;
            }}

            tr:hover {{
                background: #f3f8ff;
            }}

            .score-badge {{
                background: #16a34a;
                color: white;
                padding: 6px 12px;
                border-radius: 20px;
                font-weight: bold;
            }}

            .points-badge {{
                background: #f59e0b;
                color: white;
                padding: 6px 12px;
                border-radius: 20px;
                font-weight: bold;
            }}

            .group-badge {{
                background: #e0f2fe;
                color: #0369a1;
                padding: 6px 10px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 12px;
            }}

            .info-box {{
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 3px 12px rgba(0,0,0,0.08);
                margin-top: 15px;
            }}

            .lineup-card {{
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 3px 12px rgba(0,0,0,0.08);
                margin-bottom: 25px;
            }}

            .pitch {{
                background: linear-gradient(135deg, #15803d, #22c55e);
                color: white;
                border-radius: 18px;
                padding: 20px;
                margin-top: 15px;
                min-height: 250px;
                display: flex;
                flex-direction: column;
                justify-content: space-around;
                text-align: center;
                border: 4px solid white;
            }}

            .pitch-line {{
                background: rgba(255,255,255,0.18);
                padding: 12px;
                border-radius: 20px;
                font-weight: bold;
            }}

            .lineup-note {{
                color: #555;
                font-size: 14px;
            }}

            .footer {{
                text-align: center;
                margin: 30px;
                color: #666;
                font-size: 13px;
            }}

            @media (max-width: 768px) {{
                .summary {{
                    flex-direction: column;
                }}

                table {{
                    font-size: 12px;
                    min-width: 750px;
                }}

                th, td {{
                    padding: 8px;
                }}

                .header h1 {{
                    font-size: 26px;
                }}

                .tab-button {{
                    width: 100%;
                }}
            }}
        </style>

        <script>
            function showSection(sectionId, buttonId) {{
                const sections = document.querySelectorAll(".section");
                const buttons = document.querySelectorAll(".tab-button");

                sections.forEach(section => section.classList.remove("active"));
                buttons.forEach(button => button.classList.remove("active"));

                document.getElementById(sectionId).classList.add("active");
                document.getElementById(buttonId).classList.add("active");
            }}
        </script>
    </head>

    <body>
        <div class="header">
            <h1>FIFA World Cup 2026 Tracker</h1>
            <p>Fixtures, results, points table, top scorers and squad list</p>
        </div>

        <div class="container">

            <div class="summary">
                <div class="card">
                    <h2>{len(matches)}</h2>
                    <p>Total Fixtures</p>
                </div>

                <div class="card">
                    <h2>{len(completed_matches)}</h2>
                    <p>Completed</p>
                </div>

                <div class="card">
                    <h2>{len(upcoming_matches)}</h2>
                    <p>Upcoming</p>
                </div>

                <div class="card">
                    <h2>{len(top_scorers)}</h2>
                    <p>Goal Scorers</p>
                </div>
            </div>

            <div class="button-area">
                <button id="completed-btn" class="tab-button active" onclick="showSection('completed-section', 'completed-btn')">
                    Completed Matches
                </button>

                <button id="upcoming-btn" class="tab-button" onclick="showSection('upcoming-section', 'upcoming-btn')">
                    Upcoming Matches
                </button>

                <button id="fixtures-btn" class="tab-button" onclick="showSection('fixtures-section', 'fixtures-btn')">
                    All Fixtures
                </button>

                <button id="points-btn" class="tab-button" onclick="showSection('points-section', 'points-btn')">
                    Points Table
                </button>

                <button id="scorers-btn" class="tab-button" onclick="showSection('scorers-section', 'scorers-btn')">
                    Top Scorers
                </button>

                <button id="players-btn" class="tab-button" onclick="showSection('players-section', 'players-btn')">
                    Players List
                </button>

                <button id="lineup-btn" class="tab-button" onclick="showSection('lineup-section', 'lineup-btn')">
                    Lineup
                </button>
            </div>

            <div id="completed-section" class="section active">
                <h2 class="section-title">Completed Matches</h2>
                <div class="table-wrapper">
                    <table>
                        <tr>
                            <th>Date</th>
                            <th>Indian Time</th>
                            <th>Group/Round</th>
                            <th>Match</th>
                            <th>Score</th>
                            <th>Venue</th>
                        </tr>
                        {completed_rows}
                    </table>
                </div>
            </div>

            <div id="upcoming-section" class="section">
                <h2 class="section-title">Upcoming Matches</h2>
                <div class="table-wrapper">
                    <table>
                        <tr>
                            <th>Date</th>
                            <th>Indian Time</th>
                            <th>Group/Round</th>
                            <th>Match</th>
                            <th>Venue</th>
                        </tr>
                        {upcoming_rows}
                    </table>
                </div>
            </div>

            <div id="fixtures-section" class="section">
                <h2 class="section-title">All Fixtures Till Final</h2>
                <div class="table-wrapper">
                    <table>
                        <tr>
                            <th>Round</th>
                            <th>Date</th>
                            <th>Indian Time</th>
                            <th>Group/Round</th>
                            <th>Match</th>
                            <th>Score/Status</th>
                            <th>Status</th>
                            <th>Venue</th>
                        </tr>
                        {all_fixtures_rows}
                    </table>
                </div>
            </div>

            <div id="points-section" class="section">
                <h2 class="section-title">Points Table</h2>
                <div class="table-wrapper">
                    {points_html}
                </div>
            </div>

            <div id="scorers-section" class="section">
                <h2 class="section-title">Top Scorers</h2>
                <div class="table-wrapper">
                    <table>
                        <tr>
                            <th>Rank</th>
                            <th>Player</th>
                            <th>Team</th>
                            <th>Goals</th>
                        </tr>
                        {top_scorers_rows}
                    </table>
                </div>
            </div>

            <div id="players-section" class="section">
                <h2 class="section-title">Players List</h2>
                <div class="table-wrapper">
                    {players_html}
                </div>
            </div>

            <div id="lineup-section" class="section">
                <h2 class="section-title">Lineup</h2>
                <div class="info-box">
                    Official lineup data is not available in the current free JSON source.
                    This section shows upcoming matches in a pitch-style layout.
                    Official starting XI needs a lineup API.
                </div>
                {lineup_html}
            </div>

            <div class="footer">
                Data source: OpenFootball World Cup 2026 JSON. Time converted to Indian Standard Time.
            </div>

        </div>
    </body>
    </html>
    """


@app.route("/api/matches")
def api_matches():
    matches = get_matches_from_api()
    return jsonify(matches)


@app.route("/api/standings")
def api_standings():
    matches = get_matches_from_api()
    standings = build_points_table(matches)
    return jsonify(standings)


@app.route("/api/top-scorers")
def api_top_scorers():
    matches = get_matches_from_api()
    top_scorers = build_top_scorers(matches)
    return jsonify(top_scorers)


@app.route("/api/squads")
def api_squads():
    squads = normalize_squads(get_squads_from_api())
    return jsonify(squads)


if __name__ == "__main__":
    app.run(debug=True)
``
