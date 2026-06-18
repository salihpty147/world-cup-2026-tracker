from flask import Flask, jsonify
from urllib.request import urlopen
import json
from html import escape

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


@app.route("/")
def home():
    return world_cup_tracker()


@app.route("/world-cup-2026")
def world_cup_tracker():
    matches = get_matches_from_api()

    completed_matches = [match for match in matches if is_completed(match)]
    upcoming_matches = [match for match in matches if not is_completed(match)]

    completed_rows = ""
    for match in completed_matches:
        completed_rows += f"""
        <tr>
            <td>{escape(match.get("date", ""))}</td>
            <td>{escape(match.get("time", ""))}</td>
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
            <td>{escape(match.get("time", ""))}</td>
            <td><span class="group-badge">{escape(match.get("group", ""))}</span></td>
            <td>{escape(match.get("team1", ""))} vs {escape(match.get("team2", ""))}</td>
            <td>{escape(match.get("ground", ""))}</td>
        </tr>
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
            }}

            .card {{
                flex: 1;
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

            .section-title {{
                margin-top: 30px;
                padding-left: 10px;
                border-left: 5px solid #0077b6;
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
            </div>

            <h2 class="section-title">Completed Matches</h2>
            <table>
                <tr>
                    <th>Date</th>
                    <th>Time</th>
                    <th>Group</th>
                    <th>Match</th>
                    <th>Score</th>
                    <th>Venue</th>
                </tr>
                {completed_rows}
            </table>

            <h2 class="section-title">Upcoming Matches</h2>
            <table>
                <tr>
                    <th>Date</th>
                    <th>Time</th>
                    <th>Group</th>
                    <th>Match</th>
                    <th>Venue</th>
                </tr>
                {upcoming_rows}
            </table>

            <div class="footer">
                Data source: OpenFootball World Cup 2026 JSON.
            </div>

        </div>
    </body>
    </html>
    """


@app.route("/api/matches")
def api_matches():
    matches = get_matches_from_api()
    return jsonify(matches)


if __name__ == "__main__":
    app.run(debug=True)
