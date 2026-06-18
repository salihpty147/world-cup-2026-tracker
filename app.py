from flask import Flask

app = Flask(__name__)

completed_matches = [
    {"date": "11 Jun 2026", "group": "Group A", "match": "Mexico vs South Africa", "score": "2-0", "venue": "Mexico City Stadium"},
    {"date": "11 Jun 2026", "group": "Group A", "match": "Korea Republic vs Czechia", "score": "2-1", "venue": "Guadalajara Stadium"},

    {"date": "12 Jun 2026", "group": "Group B", "match": "Canada vs Bosnia and Herzegovina", "score": "1-1", "venue": "Toronto Stadium"},
    {"date": "12 Jun 2026", "group": "Group D", "match": "USA vs Paraguay", "score": "4-1", "venue": "Los Angeles Stadium"},

    {"date": "13 Jun 2026", "group": "Group B", "match": "Qatar vs Switzerland", "score": "1-1", "venue": "San Francisco Bay Area Stadium"},
    {"date": "13 Jun 2026", "group": "Group C", "match": "Brazil vs Morocco", "score": "1-1", "venue": "New York New Jersey Stadium"},
    {"date": "13 Jun 2026", "group": "Group C", "match": "Haiti vs Scotland", "score": "0-1", "venue": "Boston Stadium"},
    {"date": "13 Jun 2026", "group": "Group D", "match": "Australia vs Türkiye", "score": "2-0", "venue": "BC Place Vancouver"},

    {"date": "14 Jun 2026", "group": "Group E", "match": "Germany vs Curaçao", "score": "7-1", "venue": "Houston Stadium"},
    {"date": "14 Jun 2026", "group": "Group F", "match": "Netherlands vs Japan", "score": "2-2", "venue": "Dallas Stadium"},
    {"date": "14 Jun 2026", "group": "Group E", "match": "Côte d'Ivoire vs Ecuador", "score": "1-0", "venue": "Philadelphia Stadium"},
    {"date": "14 Jun 2026", "group": "Group F", "match": "Sweden vs Tunisia", "score": "5-1", "venue": "Monterrey Stadium"},

    {"date": "15 Jun 2026", "group": "Group H", "match": "Spain vs Cabo Verde", "score": "0-0", "venue": "Atlanta Stadium"},
    {"date": "15 Jun 2026", "group": "Group G", "match": "Belgium vs Egypt", "score": "1-1", "venue": "Seattle Stadium"},
    {"date": "15 Jun 2026", "group": "Group H", "match": "Saudi Arabia vs Uruguay", "score": "1-1", "venue": "Miami Stadium"},
    {"date": "15 Jun 2026", "group": "Group G", "match": "IR Iran vs New Zealand", "score": "2-2", "venue": "Los Angeles Stadium"},

    {"date": "16 Jun 2026", "group": "Group I", "match": "France vs Senegal", "score": "3-1", "venue": "New York New Jersey Stadium"},
    {"date": "16 Jun 2026", "group": "Group I", "match": "Norway vs Iraq", "score": "4-1", "venue": "Boston Stadium"},
    {"date": "16 Jun 2026", "group": "Group J", "match": "Argentina vs Algeria", "score": "3-0", "venue": "Kansas City Stadium"},
    {"date": "16 Jun 2026", "group": "Group J", "match": "Austria vs Jordan", "score": "3-1", "venue": "San Francisco Bay Area Stadium"},

    {"date": "17 Jun 2026", "group": "Group K", "match": "Portugal vs DR Congo", "score": "1-1", "venue": "Houston Stadium"},
    {"date": "17 Jun 2026", "group": "Group L", "match": "England vs Croatia", "score": "4-2", "venue": "Dallas Stadium"},
    {"date": "17 Jun 2026", "group": "Group L", "match": "Ghana vs Panama", "score": "1-0", "venue": "Toronto Stadium"},
    {"date": "18 Jun 2026", "group": "Group K", "match": "Uzbekistan vs Colombia", "score": "1-3", "venue": "Mexico City Stadium"}
]

upcoming_matches = [
    {"date": "18 Jun 2026", "time": "9:30 PM IST", "group": "Group A", "match": "Czechia vs South Africa", "venue": "Atlanta Stadium"},
    {"date": "19 Jun 2026", "time": "12:30 AM IST", "group": "Group B", "match": "Switzerland vs Bosnia and Herzegovina", "venue": "Los Angeles Stadium"},
    {"date": "19 Jun 2026", "time": "3:30 AM IST", "group": "Group B", "match": "Canada vs Qatar", "venue": "BC Place Vancouver"},
    {"date": "19 Jun 2026", "time": "6:30 AM IST", "group": "Group A", "match": "Mexico vs Korea Republic", "venue": "Guadalajara Stadium"},

    {"date": "20 Jun 2026", "time": "12:30 AM IST", "group": "Group D", "match": "USA vs Australia", "venue": "Seattle Stadium"},
    {"date": "20 Jun 2026", "time": "3:30 AM IST", "group": "Group C", "match": "Scotland vs Morocco", "venue": "Boston Stadium"},
    {"date": "20 Jun 2026", "time": "6:30 AM IST", "group": "Group C", "match": "Brazil vs Haiti", "venue": "Philadelphia Stadium"}
]

@app.route("/")
def home():
    completed_rows = ""
    for match in completed_matches:
        completed_rows += f"""
        <tr>
            <td>{match['date']}</td>
            <td>{match['group']}</td>
            <td>{match['match']}</td>
            <td>{match['score']}</td>
            <td>{match['venue']}</td>
        </tr>
        """

    upcoming_rows = ""
    for match in upcoming_matches:
        upcoming_rows += f"""
        <tr>
            <td>{match['date']}</td>
            <td>{match['time']}</td>
            <td>{match['group']}</td>
            <td>{match['match']}</td>
            <td>{match['venue']}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>World Cup 2026 Tracker</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f6f8;
                margin: 0;
                padding: 20px;
            }}

            h1 {{
                text-align: center;
                color: #12355b;
            }}

            h2 {{
                color: #1f4e79;
                margin-top: 35px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background-color: white;
                margin-top: 10px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}

            th {{
                background-color: #1f4e79;
                color: white;
                padding: 12px;
                text-align: left;
            }}

            td {{
                padding: 10px;
                border-bottom: 1px solid #ddd;
            }}

            tr:hover {{
                background-color: #f1f1f1;
            }}

            .completed {{
                color: green;
                font-weight: bold;
            }}

            .upcoming {{
                color: orange;
                font-weight: bold;
            }}

            .summary {{
                background-color: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
        </style>
    </head>
    <body>

        <h1>FIFA World Cup 2026 Match Tracker</h1>

        <div class="summary">
            <p><b>Total Completed Matches Shown:</b> {len(completed_matches)}</p>
            <p><b>Total Upcoming Matches Shown:</b> {len(upcoming_matches)}</p>
        </div>

        <h2 class="completed">Completed Matches</h2>
        <table>
            <tr>
                <th>Date</th>
                <th>Group</th>
                <th>Match</th>
                <th>Score</th>
                <th>Venue</th>
            </tr>
            {completed_rows}
        </table>

        <h2 class="upcoming">Upcoming Matches</h2>
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

    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(debug=True)