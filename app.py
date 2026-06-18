from flask import Flask, jsonifyfrom flask importimport json
from html import escape
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
MATCHES_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
SQUADS_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.squads.json"
IST = timezone(timedelta(hours=5, minutes=30))

FLAGS = {
    "Argentina": "🇦🇷", "Australia": "🇦🇺", "Austria": "🇦🇹", "Belgium": "🇧🇪", "Brazil": "🇧🇷", "Canada": "🇨🇦",
    "Colombia": "🇨🇴", "Croatia": "🇭🇷", "Czech Republic": "🇨🇿", "Czechia": "🇨🇿", "Ecuador": "🇪🇨", "Egypt": "🇪🇬",
    "England": "🏴", "France": "🇫🇷", "Germany": "🇩🇪", "Ghana": "🇬🇭", "Haiti": "🇭🇹", "Iraq": "🇮🇶",
    "IR Iran": "🇮🇷", "Iran": "🇮🇷", "Japan": "🇯🇵", "Mexico": "🇲🇽", "Morocco": "🇲🇦", "Netherlands": "🇳🇱",
    "New Zealand": "🇳🇿", "Norway": "🇳🇴", "Panama": "🇵🇦", "Paraguay": "🇵🇾", "Portugal": "🇵🇹", "Qatar": "🇶🇦",
    "Saudi Arabia": "🇸🇦", "Scotland": "🏴", "Senegal": "🇸🇳", "South Africa": "🇿🇦", "South Korea": "🇰🇷", "Korea Republic": "🇰🇷",
    "Spain": "🇪🇸", "Sweden": "🇸🇪", "Switzerland": "🇨🇭", "Tunisia": "🇹🇳", "Türkiye": "🇹🇷", "Turkiye": "🇹🇷",
    "USA": "🇺🇸", "United States": "🇺🇸", "Uruguay": "🇺🇾", "Uzbekistan": "🇺🇿", "Bosnia & Herzegovina": "🇧🇦",
    "Bosnia and Herzegovina": "🇧🇦", "Cabo Verde": "🇨🇻", "Cape Verde": "🇨🇻", "Congo DR": "🇨🇩", "DR Congo": "🇨🇩",
    "Curaçao": "🇨🇼", "Ivory Coast": "🇨🇮", "Côte d'Ivoire": "🇨🇮", "Jordan": "🇯🇴"
}

def flag(team):
    return FLAGS.get(team, "🏳️")

def team_label(team):
    return f"{flag(team)} {team}"

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
        goals1, goals2 = int(goals1), int(goals2)

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

def rows_for_matches(matches, score=False, round_col=False, status=False, scorers=False):
    rows = ""

    for match in matches:
        team1 = match.get("team1", "")
        team2 = match.get("team2", "")
        scorer_details = goal_scorer_text(match) if scorers else ""
        search_text = f"{team1} {team2} {match.get('group', '')} {match.get('round', '')} {scorer_details}".lower()

        rows += f"""
        <tr data-search="{escape(search_text)}">
            {f"<td>{escape(match.get('round', ''))}</td>" if round_col else ""}
            <td>{escape(match.get('date', ''))}</td>
            <td>{escape(ist_text(match))}</td>
            <td><span class="badge blue">{escape(match.get('group', ''))}</span></td>
            <td class="match-name">{escape(team_label(team1))} vs {escape(team_label(team2))}</td>
            {f"<td><span class='badge green'>{escape(score_text(match))}</span></td>" if score else ""}
            {f"<td>{'Completed' if completed(match) else 'Upcoming'}</td>" if status else ""}
            <td>{escape(match.get('ground', ''))}</td>
            {f"<td>{escape(scorer_details)}</td>" if scorers else ""}
        </tr>
        """

    return rows

@app.route("/")
def home():
    return world_cup_2026()

@app.route("/world-cup-2026")
def world_cup_2026():
    matches = get_matches()

    all_matches = sorted(matches, key=match_sort_key)
    done_matches = sorted([m for m in matches if completed(m)], key=match_sort_key)
    recent_matches = list(reversed(done_matches[-8:]))
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

    today_rows = rows_for_matches(today_matches, score=True, scorers=True)
    tomorrow_rows = rows_for_matches(tomorrow_matches, score=True)
    completed_rows = rows_for_matches(done_matches, score=True, scorers=True)
    recent_rows = rows_for_matches(recent_matches, score=True, scorers=True)
    upcoming_rows = rows_for_matches(upcoming_matches)
    fixtures_rows = rows_for_matches(all_matches, score=True, round_col=True, status=True)

    next_text = "No upcoming match"
    if next_match:
        next_text = f"{team_label(next_match.get('team1', ''))} vs {team_label(next_match.get('team2', ''))}<br><span>{ist_text(next_match)}</span>"

    latest_text = "No completed result"
    if latest_result:
        latest_text = f"{team_label(latest_result.get('team1', ''))} {score_text(latest_result)} {team_label(latest_result.get('team2', ''))}<br><span>{ist_text(latest_result)}</span>"

    points_html = ""

    for group in sorted(standings.keys()):
        points_html += f"""
        <h3 class="group-title">{escape(group)}</h3>
        <div class="table-wrap">
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

        for pos, team in enumerate(standings[group], start=1):
            team_name = team["team"]
            search_text = f"{team_name} {group}".lower()

            points_html += f"""
            <tr data-search="{escape(search_text)}">
                <td>{pos}</td>
                <td>{escape(team_label(team_name))}</td>
                <td>{team['played']}</td>
                <td>{team['won']}</td>
                <td>{team['drawn']}</td>
                <td>{team['lost']}</td>
                <td>{team['gf']}</td>
                <td>{team['ga']}</td>
                <td>{team['gd']}</td>
                <td><span class="badge gold">{team['points']}</span></td>
            </tr>
            """

        points_html += """
            </table>
        </div>
        """

    scorers_rows = ""

    for rank, scorer in enumerate(scorers, start=1):
        search_text = f"{scorer['player']} {scorer['team']}".lower()

        scorers_rows += f"""
        <tr data-search="{escape(search_text)}">
            <td>{rank}</td>
            <td>{escape(scorer['player'])}</td>
            <td>{escape(team_label(scorer['team']))}</td>
            <td><span class="badge green">{scorer['goals']}</span></td>
        </tr>
        """

    if not scorers_rows:
        scorers_rows = """
        <tr>
            <td colspan="4">No goal scorer data available yet.</td>
        </tr>
        """

    players_html = ""

    if squads:
        for team in sorted(squads.keys()):
            players_html += f"""
            <h3 class="group-title">{escape(team_label(team))}</h3>
            <div class="table-wrap">
                <table>
                    <tr>
                        <th>No</th>
                        <th>Player</th>
                        <th>Position</th>
                    </tr>
            """

            for player in squads[team]:
                search_text = f"{player.get('name', '')} {player.get('position', '')} {team}".lower()

                players_html += f"""
                <tr data-search="{escape(search_text)}">
                    <td>{escape(str(player.get('number', '')))}</td>
                    <td>{escape(player.get('name', ''))}</td>
                    <td>{escape(player.get('position', ''))}</td>
                </tr>
                """

            players_html += """
                </table>
            </div>
            """
    else:
        players_html = """
        <div class="empty">
            Player squad data is not available from the free source currently.
        </div>
        """

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
                padding: 34px 22px 58px;
            }}

            .hero-inner {{
                max-width: 1180px;
                margin: auto;
                display: grid;
                grid-template-columns: 1.5fr .8fr;
                gap: 24px;
                align-items: center;
            }}

            .hero h1 {{
                margin: 0;
                font-size: 42px;
            }}

            .hero p {{
                margin: 10px 0 0;
                opacity: .92;
                font-size: 17px;
            }}

            .hero-icons {{
                display: flex;
                gap: 10px;
                margin-top: 18px;
                flex-wrap: wrap;
            }}

            .hero-icon {{
                background: rgba(255,255,255,.14);
                border: 1px solid rgba(255,255,255,.26);
                padding: 9px 13px;
                border-radius: 999px;
                font-weight: 800;
            }}

            .side-panel {{
                background: rgba(255,255,255,.15);
                border: 1px solid rgba(255,255,255,.28);
                border-radius: 22px;
                padding: 18px;
                backdrop-filter: blur(8px);
            }}

            .side-panel h3 {{
                margin: 0 0 12px;
            }}

            .side-item {{
                background: rgba(255,255,255,.12);
                border-radius: 16px;
                padding: 12px;
                margin-top: 10px;
                font-weight: 800;
            }}

            .side-item span {{
                display: inline-block;
                margin-top: 5px;
                opacity: .82;
                font-weight: 600;
            }}

            .container {{
                max-width: 1180px;
                margin: -42px auto 30px;
                padding: 0 18px;
            }}

            .cards {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 16px;
            }}

            .card {{
                background: white;
                border-radius: 22px;
                padding: 20px;
                box-shadow: 0 12px 28px rgba(15,23,42,.09);
                display: flex;
                gap: 14px;
                align-items: center;
            }}

            .card-icon {{
                width: 46px;
                height: 46px;
                display: grid;
                place-items: center;
                border-radius: 16px;
                background: #e0f2fe;
                font-size: 24px;
            }}

            .num {{
                font-size: 34px;
                font-weight: 900;
                color: #0057a8;
            }}

            .label {{
                color: #64748b;
                margin-top: 3px;
            }}

            .toolbar {{
                margin: 18px 0;
                background: white;
                border-radius: 22px;
                padding: 16px;
                box-shadow: 0 12px 28px rgba(15,23,42,.07);
            }}

            .tabs {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }}

            button {{
                border: 0;
                cursor: pointer;
            }}

            .tab {{
                background: #e6eef8;
                color: #0f3764;
                padding: 12px 16px;
                border-radius: 999px;
                font-weight: 900;
            }}

            .tab.active {{
                background: #00a86b;
                color: white;
            }}

            .search {{
                margin-top: 14px;
                width: 100%;
                padding: 14px 16px;
                border-radius: 14px;
                border: 1px solid #d8e2ee;
                font-size: 15px;
            }}

            .section {{
                display: none;
                background: white;
                border-radius: 22px;
                padding: 18px;
                box-shadow: 0 12px 28px rgba(15,23,42,.07);
                margin-bottom: 22px;
            }}

            .section.active {{
                display: block;
            }}

            .section h2 {{
                margin: 0 0 14px;
                color: #082f5f;
                font-size: 28px;
            }}

            .table-wrap {{
                overflow-x: auto;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                min-width: 850px;
            }}

            th {{
                background: #082f5f;
                color: white;
                text-align: left;
                padding: 13px;
            }}

            td {{
                padding: 13px;
                border-bottom: 1px solid #e8eef5;
                vertical-align: top;
            }}

            tr:hover {{
                background: #f6fbff;
            }}

            .badge {{
                display: inline-block;
                padding: 6px 10px;
                border-radius: 999px;
                font-weight: 900;
                font-size: 12px;
            }}

            .blue {{
                background: #dff1ff;
                color: #075985;
            }}

            .green {{
                background: #dcfce7;
                color: #166534;
            }}

            .gold {{
                background: #fef3c7;
                color: #92400e;
            }}

            .match-name {{
                font-weight: 850;
            }}

            .group-title {{
                color: #075985;
                margin: 20px 0 10px;
            }}

            .empty {{
                padding: 20px;
                background: #f8fafc;
                border-radius: 14px;
                color: #64748b;
            }}

            .footer {{
                text-align: center;
                color: #64748b;
                padding: 25px;
            }}

            @media (max-width: 900px) {{
                .hero-inner {{
                    grid-template-columns: 1fr;
                }}

                .cards {{
                    grid-template-columns: repeat(2, 1fr);
                }}

                .hero h1 {{
                    font-size: 32px;
                }}
            }}

            @media (max-width: 560px) {{
                .cards {{
                    grid-template-columns: 1fr;
                }}

                .tab {{
                    width: 100%;
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
                const value = document.getElementById('teamSearch').value.toLowerCase();

                document.querySelectorAll('tr[data-search]').forEach(row => {{
                    row.style.display = row.getAttribute('data-search').includes(value) ? '' : 'none';
                }});
            }}
        </script>
    </head>

    <body>
        <div class="hero">
            <div class="hero-inner">
                <div>
                    <h1>⚽ FIFA World Cup 2026 Tracker</h1>
                    <p>Fixtures, results, Indian time, points table, top scorers, squads and goal details</p>

                    <div class="hero-icons">
                        <div class="hero-icon">🏆 104 Fixtures</div>
                        <div class="hero-icon">🇮🇳 IST Time</div>
                        <div class="hero-icon">📊 Live Dashboard</div>
                        <div class="hero-icon">🥅 Goal Scorers</div>
                    </div>
                </div>

                <div class="side-panel">
                    <h3>📌 Quick Details</h3>
                    <div class="side-item">⏭️ Next Match<br><span>{next_text}</span></div>
                    <div class="side-item">✅ Latest Result<br><span>{latest_text}</span></div>
                    <div class="side-item">🔎 Search works for teams, groups, players and goal scorers</div>
                </div>
            </div>
        </div>

        <main class="container">
            <div class="cards">
                <div class="card">
                    <div class="card-icon">🏟️</div>
                    <div>
                        <div class="num">{len(matches)}</div>
                        <div class="label">Total Fixtures</div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-icon">✅</div>
                    <div>
                        <div class="num">{len(done_matches)}</div>
                        <div class="label">Completed</div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-icon">⏳</div>
                    <div>
                        <div class="num">{len(upcoming_matches)}</div>
                        <div class="label">Upcoming</div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-icon">📅</div>
                    <div>
                        <div class="num">{len(today_matches)}</div>
                        <div class="label">Today in IST</div>
                    </div>
                </div>
            </div>

            <div class="toolbar">
                <div class="tabs">
                    <button id="today-btn" class="tab active" onclick="showSection('today-section','today-btn')">📅 Today</button>
                    <button id="tomorrow-btn" class="tab" onclick="showSection('tomorrow-section','tomorrow-btn')">🗓️ Tomorrow</button>
                    <button id="recent-btn" class="tab" onclick="showSection('recent-section','recent-btn')">⚡ Recent</button>
                    <button id="completed-btn" class="tab" onclick="showSection('completed-section','completed-btn')">✅ Completed</button>
                    <button id="upcoming-btn" class="tab" onclick="showSection('upcoming-section','upcoming-btn')">⏳ Upcoming</button>
                    <button id="fixtures-btn" class="tab" onclick="showSection('fixtures-section','fixtures-btn')">🏟️ All Fixtures</button>
                    <button id="points-btn" class="tab" onclick="showSection('points-section','points-btn')">📊 Points</button>
                    <button id="scorers-btn" class="tab" onclick="showSection('scorers-section','scorers-btn')">🥅 Top Scorers</button>
                    <button id="goals-btn" class="tab" onclick="showSection('goals-section','goals-btn')">⚽ Match Goals</button>
                    <button id="players-btn" class="tab" onclick="showSection('players-section','players-btn')">👥 Players</button>
                </div>

                <input id="teamSearch" onkeyup="filterRows()" class="search" placeholder="Search team, group, player, scorer, e.g. Messi, Brazil, Group A">
            </div>

            <section id="today-section" class="section active">
                <h2>📅 Today’s Matches</h2>
                <div class="table-wrap">
                    <table>
                        <tr>
                            <th>Date</th>
                            <th>Indian Time</th>
                            <th>Group/Round</th>
                            <th>Match</th>
                            <th>Score/Status</th>
                            <th>Venue</th>
                            <th>Goal Scorers</th>
                        </tr>
                        {today_rows}
                    </table>
                </div>
            </section>

            <section id="tomorrow-section" class="section">
                <h2>🗓️ Tomorrow’s Matches</h2>
                <div class="table-wrap">
                    <table>
                        <tr>
                            <th>Date</th>
                            <th>Indian Time</th>
                            <th>Group/Round</th>
                            <th>Match</th>
                            <th>Score/Status</th>
                            <th>Venue</th>
                        </tr>
                        {tomorrow_rows}
                    </table>
                </div>
            </section>

            <section id="recent-section" class="section">
                <h2>⚡ Recent Matches</h2>
                <div class="table-wrap">
                    <table>
                        <tr>
                            <th>Date</th>
                            <th>Indian Time</th>
                            <th>Group/Round</th>
                            <th>Match</th>
                            <th>Score</th>
                            <th>Venue</th>
                            <th>Goal Scorers</th>
                        </tr>
                        {recent_rows}
                    </table>
                </div>
            </section>

            <section id="completed-section" class="section">
                <h2>✅ Completed Matches</h2>
                <div class="table-wrap">
                    <table>
                        <tr>
                            <th>Date</th>
                            <th>Indian Time</th>
                            <th>Group/Round</th>
                            <th>Match</th>
                            <th>Score</th>
                            <th>Venue</th>
                            <th>Goal Scorers</th>
                        </tr>
                        {completed_rows}
                    </table>
                </div>
            </section>

            <section id="upcoming-section" class="section">
                <h2>⏳ Upcoming Matches</h2>
                <div class="table-wrap">
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
            </section>

            <section id="fixtures-section" class="section">
                <h2>🏟️ All Fixtures Till Final</h2>
                <div class="table-wrap">
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
                        {fixtures_rows}
                    </table>
                </div>
            </section>

            <section id="points-section" class="section">
                <h2>📊 Points Table</h2>
                {points_html}
            </section>

            <section id="scorers-section" class="section">
                <h2>🥅 Top Scorers</h2>
                <div class="table-wrap">
                    <table>
                        <tr>
                            <th>Rank</th>
                            <th>Player</th>
                            <th>Team</th>
                            <th>Goals</th>
                        </tr>
                        {scorers_rows}
                    </table>
                </div>
            </section>

            <section id="goals-section" class="section">
                <h2>⚽ Goal Scorers by Match</h2>
                <div class="table-wrap">
                    <table>
                        <tr>
                            <th>Date</th>
                            <th>Indian Time</th>
                            <th>Group/Round</th>
                            <th>Match</th>
                            <th>Score</th>
                            <th>Venue</th>
                            <th>Goal Scorers</th>
                        </tr>
                        {completed_rows}
                    </table>
                </div>
            </section>

            <section id="players-section" class="section">
                <h2>👥 Players List</h2>
                {players_html}
            </section>

            <div class="footer">
                Data source: OpenFootball World Cup 2026 JSON. Time converted to Indian Standard Time.
            </div>
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
from urllib.request import urlopen
