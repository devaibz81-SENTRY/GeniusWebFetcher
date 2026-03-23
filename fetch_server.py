"""
NEBL Fetch Server
Flask app to fetch player statistics from Genius Sports
"""
from flask import Flask, jsonify, request, render_template_string
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# Default target URLs - Using JSON API endpoint for player statistics
GENIUS_EMBED_BASE = "https://hosted.dcd.shared.geniussports.com/embednf/BEBL/en"
TARGET_URL_PLAYER = f"{GENIUS_EMBED_BASE}/statistics/player?iurl=https%3A%2F%2Fnebl.web.geniussports.com%2F%3Fp%3D9&_cc=1&_lc=1&_nv=1&_mf=1"
TARGET_URL_TEAM = f"{GENIUS_EMBED_BASE}/statistics/team?iurl=https%3A%2F%2Fnebl.web.geniussports.com%2F%3Fp%3D9&_cc=1&_lc=1&_nv=1&_mf=1"
TARGET_URL_STANDINGS = f"{GENIUS_EMBED_BASE}/standings?iurl=https%3A%2F%2Fnebl.web.geniussports.com%2F%3Fp%3D9&_cc=1&_lc=1&_nv=1&_mf=1"

# Default target URL for compatibility
TARGET_URL = TARGET_URL_PLAYER

# Cache for fetched data
cached_data = {
    "headers": [],
    "data": [],
    "fetched_at": None,
    "status": "empty"
}

# HTML Template for the interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEBL Fetch Server</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #043f8f 0%, #1a1a2e 100%);
            min-height: 100vh;
            padding: 20px;
            color: #fff;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .subtitle {
            text-align: center;
            color: #90caf9;
            margin-bottom: 30px;
        }
        .card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }
        .card h2 {
            margin-bottom: 15px;
            color: #90caf9;
            border-bottom: 2px solid #90caf9;
            padding-bottom: 10px;
        }
        .status-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .status-item {
            background: rgba(0,0,0,0.3);
            padding: 10px 20px;
            border-radius: 25px;
        }
        .status-online { color: #4caf50; }
        .status-error { color: #f44336; }
        .status-pending { color: #ff9800; }
        .btn {
            background: #043f8f;
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s ease;
            display: inline-block;
            text-decoration: none;
        }
        .btn:hover {
            background: #0656b0;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        .btn-fetch {
            background: #4caf50;
        }
        .btn-fetch:hover {
            background: #5cbf60;
        }
        .btn-clear {
            background: #f44336;
        }
        .btn-clear:hover {
            background: #e53935;
        }
        .btn-group {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 15px;
        }
        .url-display {
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 10px;
            word-break: break-all;
            font-family: monospace;
            font-size: 12px;
            margin-top: 10px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .stat-box {
            background: rgba(0,0,0,0.3);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #90caf9;
        }
        .stat-label {
            color: #ccc;
            font-size: 12px;
            text-transform: uppercase;
        }
        .endpoint-list {
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 10px;
            font-family: monospace;
        }
        .endpoint-list a {
            color: #90caf9;
            display: block;
            padding: 5px 0;
        }
        .error-msg {
            background: rgba(244, 67, 54, 0.2);
            border: 1px solid #f44336;
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
        }
        .success-msg {
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid #4caf50;
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏀 NEBL Fetch Server</h1>
        <p class="subtitle">Player Statistics Extractor</p>
        
        <div class="card">
            <div class="status-bar">
                <div class="status-item">
                    <strong>Status:</strong> 
                    <span class="status-{{ 'online' if has_data else 'pending' }}">
                        {{ 'Data Loaded' if has_data else 'No Data' }}
                    </span>
                </div>
                <div class="status-item">
                    <strong>Last Fetch:</strong> {{ last_fetch or 'Never' }}
                </div>
            </div>
            
            <h2>Target URL</h2>
            <div class="url-display">{{ target_url }}</div>
            
            <div class="btn-group">
                <button class="btn btn-fetch" onclick="fetchData()">🔄 Fetch Data</button>
                <button class="btn btn-clear" onclick="clearData()">🗑️ Clear</button>
            </div>
            
            {% if message %}
                <div class="{{ 'success-msg' if 'success' in message else 'error-msg' }}">
                    {{ message }}
                </div>
            {% endif %}
        </div>
        
        {% if has_data %}
        <div class="card">
            <h2>📊 Statistics</h2>
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-number">{{ player_count }}</div>
                    <div class="stat-label">Players</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{{ column_count }}</div>
                    <div class="stat-label">Columns</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{{ data_size }}</div>
                    <div class="stat-label">KB</div>
                </div>
            </div>
        </div>
        {% endif %}
        
        <div class="card">
            <h2>🔗 API Endpoints</h2>
            <div class="endpoint-list">
                <a href="/data" target="_blank">GET /data - JSON Data</a>
                <a href="/fetch" target="_blank">GET /fetch - Trigger Fetch</a>
                <a href="/health" target="_blank">GET /health - Health Check</a>
                <a href="/" target="_blank">GET / - This Page</a>
            </div>
        </div>
        
        <div class="card">
            <h2>📝 Instructions</h2>
            <ol style="line-height: 1.8; padding-left: 20px;">
                <li>Click <strong>Fetch Data</strong> to retrieve player statistics</li>
                <li>View JSON data at <strong>/data</strong> endpoint</li>
                <li>Use <strong>/data</strong> URL in Google Sheets Apps Script</li>
                <li>For external access, deploy to Render.com</li>
            </ol>
        </div>
        
        <div class="footer">
            NEBL Fetch Server | Genius Sports Data Extractor
        </div>
    </div>
    
    <script>
        function fetchData() {
            fetch('/fetch')
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        location.reload();
                    } else {
                        alert('Error: ' + (d.error || 'Unknown error'));
                    }
                })
                .catch(e => alert('Fetch failed: ' + e));
        }
        
        function clearData() {
            if (confirm('Clear cached data?')) {
                fetch('/clear', {method: 'POST'})
                    .then(r => r.json())
                    .then(d => location.reload());
            }
        }
    </script>
</body>
</html>
"""

def extract_player_stats(html_content):
    """
    Extract player statistics table from HTML
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    players_data = []
    headers = []
    
    tables = soup.find_all('table')
    
    for table in tables:
        rows = table.find_all('tr')
        for i, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            if cells:
                row_data = []
                for cell in cells:
                    text = cell.get_text(strip=True)
                    row_data.append(text)
                
                if i == 0:
                    headers = row_data
                else:
                    if row_data:
                        players_data.append(row_data)
    
    return headers, players_data


def parse_json_response(response_text):
    """
    Parse the JSON response from Genius Sports embed endpoint
    The response is JSON with an 'html' field containing escaped HTML
    """
    try:
        data = json.loads(response_text)
        return data.get('html', '')
    except json.JSONDecodeError:
        return response_text


def fetch_from_genius():
    """
    Fetch data from Genius Sports
    """
    try:
        headers_req = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        response = requests.get(TARGET_URL, headers=headers_req, timeout=30)
        response.raise_for_status()
        
        html_content = parse_json_response(response.text)
        return html_content, None
        
    except requests.exceptions.RequestException as e:
        return None, str(e)


@app.route('/')
def index():
    """Main page"""
    has_data = bool(cached_data.get('data'))
    last_fetch = cached_data.get('fetched_at', 'Never')
    
    player_count = len(cached_data.get('data', []))
    column_count = len(cached_data.get('headers', []))
    data_size = 0
    if cached_data.get('data'):
        data_size = len(json.dumps(cached_data)) // 1024
    
    return render_template_string(
        HTML_TEMPLATE,
        target_url=TARGET_URL,
        has_data=has_data,
        last_fetch=last_fetch,
        player_count=player_count,
        column_count=column_count,
        data_size=data_size,
        message=request.args.get('message', '')
    )


@app.route('/fetch')
def fetch():
    """Trigger data fetch"""
    html_content, error = fetch_from_genius()
    
    if error:
        cached_data['status'] = 'error'
        return jsonify({'success': False, 'error': error})
    
    headers, data = extract_player_stats(html_content)
    
    cached_data['headers'] = headers
    cached_data['data'] = data
    cached_data['fetched_at'] = datetime.now().isoformat()
    cached_data['status'] = 'success'
    
    return jsonify({
        'success': True,
        'players_found': len(data),
        'columns': len(headers),
        'fetched_at': cached_data['fetched_at']
    })


@app.route('/data')
def get_data():
    """Return cached data as JSON - auto-refreshes if older than 60 seconds"""
    
    AUTO_REFRESH_SECONDS = 60
    
    fetched_at = cached_data.get('fetched_at')
    if fetched_at:
        try:
            last_fetch = datetime.fromisoformat(fetched_at)
            if datetime.now() - last_fetch > timedelta(seconds=AUTO_REFRESH_SECONDS):
                html_content, error = fetch_from_genius()
                if not error:
                    headers, data = extract_player_stats(html_content)
                    cached_data['headers'] = headers
                    cached_data['data'] = data
                    cached_data['fetched_at'] = datetime.now().isoformat()
                    cached_data['status'] = 'success'
        except:
            pass
    
    if not cached_data.get('data'):
        return jsonify({
            'error': 'No data available. Call /fetch first.',
            'headers': [],
            'data': []
        }), 404
    
    return jsonify({
        'headers': cached_data['headers'],
        'data': cached_data['data'],
        'fetched_at': cached_data['fetched_at'],
        'player_count': len(cached_data['data'])
    })


@app.route('/clear', methods=['POST'])
def clear():
    """Clear cached data"""
    cached_data['headers'] = []
    cached_data['data'] = []
    cached_data['fetched_at'] = None
    cached_data['status'] = 'empty'
    return jsonify({'success': True})


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'has_data': bool(cached_data.get('data')),
        'player_count': len(cached_data.get('data', [])),
        'fetched_at': cached_data.get('fetched_at')
    })


@app.route('/url', methods=['GET', 'POST'])
def set_url():
    """Get or set target URL"""
    global TARGET_URL
    
    if request.method == 'POST':
        new_url = request.form.get('url', '')
        if new_url:
            TARGET_URL = new_url
            return jsonify({'success': True, 'url': TARGET_URL})
        return jsonify({'success': False, 'error': 'No URL provided'})
    
    return jsonify({'url': TARGET_URL})


# ==================== ADDITIONAL ENDPOINTS ====================

TEAM_MAP = {
    "Orange Walk Running Rebels": "OWR",
    "San Pedro Tiger Sharks": "SPT",
    "Cayo Western Ballaz": "CWB",
    "Belize City Defenders": "DEF",
    "Belmopan Trojans": "BMP",
    "Griga Dream Ballers": "DDB",
    "EZ Investment Griga Dream Ballers": "DDB",
    "Corozal Spartans": "COR"
}


@app.route('/standings')
def get_standings():
    """Return standings data"""
    url = f"https://hosted.dcd.shared.geniussports.com/embednf/BEBL/en/standings?iurl=https%3A%2F%2Fnebl.web.geniussports.com%2F%3Fp%3D9&_cc=1&_lc=1&_nv=1&_mf=1"
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        data = resp.json()
        html = data.get('html', '')
        soup = BeautifulSoup(html, 'html.parser')
        standings = []
        
        # Find all rows with team data (11 columns: pos, logo, team, pts, w, l, gp, streak, for, against, diff)
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) == 10:
                team_link = row.find('a', href=lambda h: h and '/team/' in h)
                if team_link:
                    span = team_link.find('span', class_='team-name-full')
                    team_name = span.get_text(strip=True) if span else team_link.get_text(strip=True)
                    standings.append({
                        'rank': cells[0].get_text(strip=True),
                        'team': team_name,
                        'abbr': TEAM_MAP.get(team_name, ''),
                        'gp': cells[6].get_text(strip=True),
                        'w': cells[4].get_text(strip=True),
                        'l': cells[5].get_text(strip=True),
                        'pts': cells[3].get_text(strip=True),
                        'diff': cells[9].get_text(strip=True)
                    })
        
        return jsonify({'standings': standings, 'count': len(standings)})
    except Exception as e:
        return jsonify({'error': str(e), 'standings': []})


@app.route('/leaders')
def get_leaders():
    """Return leaders data"""
    url = f"https://hosted.dcd.shared.geniussports.com/embednf/BEBL/en/leaders?iurl=https%3A%2F%2Fnebl.web.geniussports.com%2Fcompetitions%2F%3Fcu%3DBEBL%2Fleaders&_cc=1&_lc=1&_nv=1&_mf=1"
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        data = resp.json()
        html = data.get('html', '')
        soup = BeautifulSoup(html, 'html.parser')
        
        categories = []
        cat_names = [
            ('Efficiency', 'EFF', 'EfficiencyCustom'),
            ('Average Points', 'PPG', 'Average points'),
            ('Average Assists', 'APG', 'Average assists'),
            ('Average Rebounds', 'RPG', 'Average total rebounds'),
            ('Field Goal %', 'FG%', 'Field goal percentage'),
            ('3-Point %', '3P%', '3 Point percentage'),
            ('Free Throw %', 'FT%', 'Free throw percentage'),
            ('Average Minutes', 'MPG', 'Average minutes')
        ]
        
        for name, abbr, search in cat_names:
            cat_div = soup.find('div', id=lambda x: x and search in x if x else False)
            if cat_div:
                players = []
                rows = cat_div.find_all('tr')[:10]
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        player_link = row.find('a', href=lambda h: h and '/person/' in h if h else False)
                        team_link = row.find('a', href=lambda h: h and '/team/' in h if h else False)
                        player_name = player_link.get_text(strip=True) if player_link else ''
                        team_name = team_link.get_text(strip=True) if team_link else ''
                        value = cells[-1].get_text(strip=True)
                        if player_name:
                            players.append({
                                'name': player_name,
                                'team': team_name,
                                'abbr': TEAM_MAP.get(team_name, ''),
                                'value': value
                            })
                if players:
                    categories.append({'name': name, 'abbr': abbr, 'players': players})
        
        return jsonify({'categories': categories, 'count': len(categories)})
    except Exception as e:
        return jsonify({'error': str(e), 'categories': []})


@app.route('/schedule')
def get_schedule():
    """Return schedule data"""
    url = f"https://hosted.dcd.shared.geniussports.com/embednf/BEBL/en/schedule?iurl=https%3A%2F%2Fnebl.web.geniussports.com%2Fcompetitions%2F%3Fcu%3DBEBL%2Fschedule&_cc=1&_lc=1&_nv=1&_mf=1"
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        data = resp.json()
        html = data.get('html', '')
        soup = BeautifulSoup(html, 'html.parser')
        games = []
        
        for row in soup.find_all('tr'):
            teams = row.find_all('a', href=lambda h: h and '/team/' in h if h else False)
            if len(teams) >= 2:
                home = teams[0].get_text(strip=True)
                away = teams[1].get_text(strip=True)
                date_cell = row.find('td', class_=lambda x: 'date' in x if x else False)
                date = date_cell.get_text(strip=True) if date_cell else ''
                games.append({
                    'date': date,
                    'home': home,
                    'away': away,
                    'home_abbr': TEAM_MAP.get(home, ''),
                    'away_abbr': TEAM_MAP.get(away, '')
                })
        
        return jsonify({'schedule': games, 'count': len(games)})
    except Exception as e:
        return jsonify({'error': str(e), 'schedule': []})


@app.route('/team-stats')
def get_team_stats():
    """Return team stats data"""
    url = f"https://hosted.dcd.shared.geniussports.com/embednf/BEBL/en/statistics/team?iurl=https%3A%2F%2Fnebl.web.geniussports.com%2F%3Fp%3D9&_cc=1&_lc=1&_nv=1&_mf=1"
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        data = resp.json()
        html = data.get('html', '')
        soup = BeautifulSoup(html, 'html.parser')
        teams = []
        
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 12:
                team_link = row.find('a', href=lambda h: h and '/team/' in h if h else False)
                if team_link:
                    team_name = team_link.get_text(strip=True)
                    teams.append({
                        'name': team_name,
                        'abbr': TEAM_MAP.get(team_name, ''),
                        'gp': cells[0].get_text(strip=True),
                        'pts': cells[1].get_text(strip=True),
                        'fgm': cells[2].get_text(strip=True),
                        'fga': cells[3].get_text(strip=True),
                        'fgp': cells[4].get_text(strip=True),
                        'tpm': cells[5].get_text(strip=True),
                        'tpa': cells[6].get_text(strip=True),
                        'tpp': cells[7].get_text(strip=True),
                        'ftm': cells[8].get_text(strip=True),
                        'fta': cells[9].get_text(strip=True),
                        'ftp': cells[10].get_text(strip=True),
                        'reb': cells[11].get_text(strip=True),
                        'ast': cells[12].get_text(strip=True) if len(cells) > 12 else ''
                    })
        
        return jsonify({'teams': teams, 'count': len(teams)})
    except Exception as e:
        return jsonify({'error': str(e), 'teams': []})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print("  NEBL Fetch Server")
    print("=" * 50)
    print(f"  Local URL: http://localhost:{port}")
    print(f"  Target: {TARGET_URL}")
    print("=" * 50)
    print("  Press CTRL+C to stop")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=True)
