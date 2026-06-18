from flask import Flask, jsonify
from urllib.request import urlopen
import json
from html import escape
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

DATA_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"


def get_matches_from_api():
    try:
        with urlopen(DATA_URL, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("matches", [])
    except Exception as error:
        print("API error:", error)
        return []


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


def build_points_table(matches):
    standings = {}

    for match in matches:
        if not is_completed(match):
            continue

        group = match.get("group", "Other")
        team1 = match.get("team1", "")
        team2 = match.get("team2", "")

        if not team1 or not team2:
            continue

        score = match["score"]["ft"]
        team1_goals = score[0]
        team2_goals = score[1]

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


@app.route("/")
def home():
    return world_cup_tracker()


@app.route("/world-cup-2026")
def world_cup_tracker():
    matches = get_matches_from_api()

    completed_matches = [match for match in matches if is_completed(match)]
    upcoming_matches = [match for match in matches if not is_completed(match)]
    standings = build_points_table(matches)

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
                }}

                th, td {{
                    padding: 8px;
                }}

                .header h1 {{
                    font-size: 26px;
                }}
            }}
        </style>

        <script>
            function showSection(sectionId, buttonId) {{
                document.getElementById("completed-section").classList.remove("active");
                document.getElementById("upcoming-section").classList.remove("active");
                document.getElementById("points-section").classList.remove("active");

                document.getElementById("completed-btn").classList.remove("active");
                document.getElementById("upcoming-btn").classList.remove("active");
                document.getElementById("points-btn").classList.remove("active");

                document.getElementById(sectionId).classList.add("active");
                document.getElementById(buttonId).classList.add("active");
            }}
        </script>
    </head>

    <body>
        <div class="header">
            <h1>FIFA World Cup 2026 Tracker</h1>
            <p>Match data loaded from online JSON API/source</p>
        </div>

        <div class="container">

            <div class="summary">
                <div class="card">
                    <h2>{len(matches)}</h2>
                    <p>Total Matches</p>
                </div>

                <div class="card">
                    <h2>{len(completed_matches)}</h2>
                    <p>Completed Matches</p>
                </div>

                <div class="card">
                    <h2>{len(upcoming_matches)}</h2>
                    <p>Upcoming Matches</p>
                </div>

                <div class="card">
                    <h2>{len(standings)}</h2>
                    <p>Groups With Points</p>
                </div>
            </div>

            <div class="button-area">
                <button id="completed-btn" class="tab-button active" onclick="showSection('completed-section', 'completed-btn')">
                    Completed Matches
                </button>

                <button id="upcoming-btn" class="tab-button" onclick="showSection('upcoming-section', 'upcoming-btn')">
                    Upcoming Matches
                </button>

                <button id="points-btn" class="tab-button" onclick="showSection('points-section', 'points-btn')">
                    Group Points Table
                </button>
            </div>

            <div id="completed-section" class="section active">
                <h2 class="section-title">Completed Matches</h2>
                <table>
                    <tr>
                        <th>Date</th>
                        <th>Indian Time</th>
                        <th>Group</th>
                        <th>Match</th>
                        <th>Score</th>
                        <th>Venue</th>
                    </tr>
                    {completed_rows}
                </table>
            </div>

            <div id="upcoming-section" class="section">
                <h2 class="section-title">Upcoming Matches</h2>
                <table>
                    <tr>
                        <th>Date</th>
                        <th>Indian Time</th>
                        <th>Group</th>
                        <th>Match</th>
                        <th>Venue</th>
                    </tr>
                    {upcoming_rows}
                </table>
            </div>

            <div id="points-section" class="section">
                <h2 class="section-title">Group Stage Points Table</h2>
                {points_html}
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


if __name__ == "__main__":
    app.run(debug=True)
