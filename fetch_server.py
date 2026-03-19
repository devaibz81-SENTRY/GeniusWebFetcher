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

# Leaders cache
cached_leaders = {
    "categories": [],
    "fetched_at": None,
    "status": "empty"
}

# Global Leaders URL - from nebl.web.geniussports.com
TARGET_URL_LEADERS = f"{GENIUS_EMBED_BASE}/leaders?iurl=https%3A%2F%2Fnebl.web.geniussports.com%2F%3Fp%3D9&_cc=1&_lc=1&_nv=1&_mf=1"
TARGET_URL_GLOBAL_LEADERS = "https://hosted.dcd.shared.geniussports.com/embednf/BEBL/en/leaders?iurl=https%3A%2F%2Fnebl.web.geniussports.com%2Fcompetitions%2F%3Fcu%3DBEBL%2Fleaders&_cc=1&_lc=1&_nv=1&_mf=1"

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


def extract_leaders_data(html_content):
    """
    Extract leaders data from HTML
    Returns list of categories with top 10 players each
    """
    import re
    
    categories = [
        {"name": "Efficiency", "search": "EfficiencyCustom", "abbr": "EFF"},
        {"name": "Average Points", "search": "Average points", "abbr": "PPG"},
        {"name": "Average Assists", "search": "Average assists", "abbr": "APG"},
        {"name": "Average Rebounds", "search": "Average total rebounds", "abbr": "RPG"},
        {"name": "Field Goal %", "search": "Field goal percentage", "abbr": "FG%"},
        {"name": "3-Point %", "search": "3 Point percentage", "abbr": "3P%"},
        {"name": "Free Throw %", "search": "Free throw percentage", "abbr": "FT%"},
        {"name": "Average Minutes", "search": "Average minutes", "abbr": "MPG"},
    ]
    
    result = []
    
    for cat in categories:
        search_term = cat["search"]
        cat_index = html_content.find(search_term)
        
        if cat_index == -1:
            continue
        
        section_start = cat_index
        section_end = cat_index + 10000
        section = html_content[section_start:section_end]
        
        players = []
        
        # Find table rows with player data
        # Pattern: Player in <a href="/person/...">, Team in <td class="team"><a href="/team/...">, Value in <td>
        rows = re.findall(
            r'<a href="[^"]*person[^"]*">([^<]+)</a>\s*</td>\s*<td[^>]*class="team"[^>]*>\s*<a[^>]*>([^<]+)</a>\s*</td>\s*<td[^>]*>([\d.]+)</td>',
            section,
            re.IGNORECASE
        )
        
        for i, row in enumerate(rows[:10]):
            name = row[0].strip()
            team = row[1].strip()
            value = row[2].strip()
            
            players.append({
                "name": name,
                "team": team,
                "value": value
            })
        
        if players:
            result.append({
                "name": cat["name"],
                "abbr": cat["abbr"],
                "players": players
            })
    
    return result


def fetch_leaders_from_genius():
    """
    Fetch leaders data from Genius Sports
    """
    try:
        headers_req = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        response = requests.get(TARGET_URL_LEADERS, headers=headers_req, timeout=30)
        response.raise_for_status()
        
        html_content = parse_json_response(response.text)
        return html_content, None
        
    except requests.exceptions.RequestException as e:
        return None, str(e)


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


@app.route('/leaders')
def get_leaders():
    """Return leaders data as JSON - auto-refreshes if older than 60 seconds"""
    
    AUTO_REFRESH_SECONDS = 60
    
    fetched_at = cached_leaders.get('fetched_at')
    if fetched_at:
        try:
            last_fetch = datetime.fromisoformat(fetched_at)
            if datetime.now() - last_fetch > timedelta(seconds=AUTO_REFRESH_SECONDS):
                html_content, error = fetch_leaders_from_genius()
                if not error:
                    categories = extract_leaders_data(html_content)
                    cached_leaders['categories'] = categories
                    cached_leaders['fetched_at'] = datetime.now().isoformat()
                    cached_leaders['status'] = 'success'
        except:
            pass
    
    if not cached_leaders.get('categories'):
        html_content, error = fetch_leaders_from_genius()
        if not error:
            categories = extract_leaders_data(html_content)
            cached_leaders['categories'] = categories
            cached_leaders['fetched_at'] = datetime.now().isoformat()
            cached_leaders['status'] = 'success'
    
    return jsonify({
        'categories': cached_leaders.get('categories', []),
        'fetched_at': cached_leaders.get('fetched_at'),
        'category_count': len(cached_leaders.get('categories', []))
    })


@app.route('/fetch_leaders')
def fetch_leaders():
    """Trigger leaders data fetch"""
    html_content, error = fetch_leaders_from_genius()
    
    if error:
        cached_leaders['status'] = 'error'
        return jsonify({'success': False, 'error': error})
    
    categories = extract_leaders_data(html_content)
    
    cached_leaders['categories'] = categories
    cached_leaders['fetched_at'] = datetime.now().isoformat()
    cached_leaders['status'] = 'success'
    
    return jsonify({
        'success': True,
        'categories_found': len(categories),
        'fetched_at': cached_leaders['fetched_at']
    })


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
