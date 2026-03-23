"""
NEBL GLOBAL STATS SERVER
Flask server - serves all data with proper parsing
Endpoints: /leaders, /standings, /rankings, /schedule, /team-stats, /players
"""

from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
import re
import os
from datetime import datetime, timedelta

app = Flask(__name__)

GENIUS_EMBED_BASE = "https://hosted.dcd.shared.geniussports.com/embednf/BEBL/en"
GENIUS_WEB_BASE = "https://nebl.web.geniussports.com"

URLS = {
    'leaders': f"{GENIUS_EMBED_BASE}/leaders?iurl=https%3A%2F%2Fnebl.web.geniussports.com%2Fcompetitions%2F%3Fcu%3DBEBL%2Fleaders&_cc=1&_lc=1&_nv=1&_mf=1",
    'player': f"{GENIUS_EMBED_BASE}/statistics/player?iurl=https%3A%2F%2Fnebl.web.geniussports.com%2F%3Fp%3D9&_cc=1&_lc=1&_nv=1&_mf=1",
    'standings': f"{GENIUS_EMBED_BASE}/standings?iurl=https%3A%2F%2Fnebl.web.geniussports.com%2F%3Fp%3D9&_cc=1&_lc=1&_nv=1&_mf=1",
    'team': f"{GENIUS_EMBED_BASE}/statistics/team?iurl=https%3A%2F%2Fnebl.web.geniussports.com%2F%3Fp%3D9&_cc=1&_lc=1&_nv=1&_mf=1",
    'schedule': f"{GENIUS_EMBED_BASE}/schedule?iurl=https%3A%2F%2Fnebl.web.geniussports.com%2Fcompetitions%2F%3Fcu%3DBEBL%2Fschedule&_cc=1&_lc=1&_nv=1&_mf=1",
}

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

CATEGORIES = [
    {"name": "Efficiency", "abbr": "EFF"},
    {"name": "Average points", "abbr": "PPG"},
    {"name": "Average assists", "abbr": "APG"},
    {"name": "Average total rebounds", "abbr": "RPG"},
    {"name": "Average defensive rebounds", "abbr": "DRPG"},
    {"name": "Average offensive rebounds", "abbr": "ORPG"},
    {"name": "Average blocks", "abbr": "BLKPG"},
    {"name": "Average steals", "abbr": "STPG"},
    {"name": "Average fouls on", "abbr": "FOPG"},
    {"name": "Field goal percentage", "abbr": "FG%"},
    {"name": "3 Points made", "abbr": "3PM"},
    {"name": "3 Point percentage", "abbr": "3P%"},
    {"name": "2 Points percentage", "abbr": "2P%"},
    {"name": "Free throw percentage", "abbr": "FT%"},
    {"name": "Average minutes", "abbr": "MPG"},
]

cache = {k: {'data': None, 'fetched_at': None} for k in URLS}
game_cache = {}
FIBALIVE = "https://fibalivestats.dcd.shared.geniussports.com/data"


def fetch_html(url):
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"Fetch error: {e}")
        return ""


def parse_leaders(html):
    """Parse all 15 leader categories"""
    categories = []
    
    for cat in CATEGORIES:
        idx = html.find(cat['name'])
        if idx == -1:
            idx = html.find(cat['abbr'])
        if idx == -1:
            continue
        
        section = html[idx:idx+25000]
        players = []
        
        lines = section.split('\n')
        current = {'name': '', 'team': '', 'value': ''}
        
        for line in lines:
            clean = re.sub(r'<[^>]+>', '', line).strip()
            
            for team_name, abbr in TEAM_MAP.items():
                if team_name in line:
                    if current.get('name') and current.get('value'):
                        players.append(current)
                    current = {'name': '', 'team': team_name, 'abbr': abbr, 'value': ''}
                    break
            
            val_match = re.match(r'^(\d+\.?\d*)\s*$', clean)
            if val_match and current.get('name') and not current.get('value'):
                current['value'] = val_match.group(1)
                players.append(current)
                current = {'name': '', 'team': '', 'value': ''}
            elif len(clean) > 2 and len(clean) < 40 and clean[0].isupper():
                if not val_match and not clean.startswith('ld-') and not clean.startswith('class='):
                    current['name'] = clean
        
        if players and len(categories) < 16:
            categories.append({'name': cat['name'], 'abbr': cat['abbr'], 'players': players[:10]})
    
    return categories


def parse_standings(html):
    """Parse standings table"""
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')
    standings = []
    
    for row in rows:
        cells = row.find_all(['td', 'th'])
        if len(cells) >= 6:
            team_link = row.find('a', href=lambda h: h and '/team/' in h)
            if team_link:
                team_name = team_link.get_text(strip=True)
                standings.append({
                    'rank': cells[0].get_text(strip=True) if cells else '',
                    'team': team_name,
                    'abbr': TEAM_MAP.get(team_name, ''),
                    'gp': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                    'w': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                    'l': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                    'pct': cells[4].get_text(strip=True) if len(cells) > 4 else '',
                    'diff': cells[5].get_text(strip=True) if len(cells) > 5 else '',
                })
    
    return standings


def parse_rankings(html):
    """Parse player rankings"""
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')
    rankings = []
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 6:
            team = cells[2].get_text(strip=True) if len(cells) > 2 else ''
            rankings.append({
                'rank': cells[0].get_text(strip=True),
                'player': cells[1].get_text(strip=True),
                'team': team,
                'abbr': next((v for k, v in TEAM_MAP.items() if k in team), ''),
                'gp': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                'min': cells[4].get_text(strip=True) if len(cells) > 4 else '',
                'pts': cells[5].get_text(strip=True) if len(cells) > 5 else '',
                'reb': cells[6].get_text(strip=True) if len(cells) > 6 else '',
                'ast': cells[7].get_text(strip=True) if len(cells) > 7 else '',
            })
    
    return rankings


def parse_schedule(html):
    """Parse schedule - games with date, teams, scores"""
    soup = BeautifulSoup(html, 'html.parser')
    games = []
    
    items = soup.find_all(['tr', 'div'], class_=re.compile(r'game|match|schedule|event'))
    
    for item in items:
        teams = item.find_all('a', href=lambda h: h and '/team/' in h)
        if len(teams) >= 2:
            home = teams[0].get_text(strip=True)
            away = teams[1].get_text(strip=True)
            
            scores = re.findall(r'\d+\s*-\s*\d+', item.get_text())
            
            game = {
                'date': item.find(class_=re.compile(r'date|time')).get_text(strip=True) if item.find(class_=re.compile(r'date|time')) else '',
                'home': home,
                'away': away,
                'home_abbr': TEAM_MAP.get(home, ''),
                'away_abbr': TEAM_MAP.get(away, ''),
            }
            
            if scores:
                parts = re.split(r'\s*-\s*', scores[0])
                if len(parts) == 2:
                    game['home_score'] = parts[0].strip()
                    game['away_score'] = parts[1].strip()
                    game['status'] = 'COMPLETED'
                else:
                    game['status'] = 'SCHEDULED'
            else:
                game['status'] = 'SCHEDULED'
            
            games.append(game)
    
    return games


def parse_team_stats(html):
    """Parse team statistics"""
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')
    teams = []
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 12:
            team_link = row.find('a', href=lambda h: h and '/team/' in h)
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
                    'ast': cells[12].get_text(strip=True) if len(cells) > 12 else '',
                })
    
    return teams


# ==================== ROUTES ====================

@app.route('/')
def index():
    return jsonify({
        'name': 'NEBL Global Server',
        'status': 'online',
        'endpoints': [
            '/leaders - All 15 categories',
            '/standings - League standings',
            '/rankings - Player rankings',
            '/schedule - Game schedule',
            '/team-stats - Team statistics',
            '/live/<game_id> - Live game',
            '/health - Status',
            '/refresh - Force refresh'
        ]
    })


@app.route('/leaders')
def get_leaders():
    if not cache['leaders']['data']:
        html = fetch_html(URLS['leaders'])
        cache['leaders']['data'] = parse_leaders(html)
        cache['leaders']['fetched_at'] = datetime.now().isoformat()
    return jsonify({
        'categories': cache['leaders']['data'],
        'count': len(cache['leaders']['data']),
        'fetched_at': cache['leaders']['fetched_at']
    })


@app.route('/standings')
def get_standings():
    if not cache['standings']['data']:
        html = fetch_html(URLS['standings'])
        cache['standings']['data'] = parse_standings(html)
        cache['standings']['fetched_at'] = datetime.now().isoformat()
    return jsonify({
        'standings': cache['standings']['data'],
        'count': len(cache['standings']['data']),
        'fetched_at': cache['standings']['fetched_at']
    })


@app.route('/rankings')
def get_rankings():
    if not cache['rankings']['data']:
        html = fetch_html(URLS['player'])
        cache['rankings']['data'] = parse_rankings(html)
        cache['rankings']['fetched_at'] = datetime.now().isoformat()
    return jsonify({
        'rankings': cache['rankings']['data'],
        'count': len(cache['rankings']['data']),
        'fetched_at': cache['rankings']['fetched_at']
    })


@app.route('/schedule')
def get_schedule():
    if not cache['schedule']['data']:
        html = fetch_html(URLS['schedule'])
        cache['schedule']['data'] = parse_schedule(html)
        cache['schedule']['fetched_at'] = datetime.now().isoformat()
    return jsonify({
        'schedule': cache['schedule']['data'],
        'count': len(cache['schedule']['data']),
        'fetched_at': cache['schedule']['fetched_at']
    })


@app.route('/team-stats')
def get_team_stats():
    if not cache['team_stats']['data']:
        html = fetch_html(URLS['team'])
        cache['team_stats']['data'] = parse_team_stats(html)
        cache['team_stats']['fetched_at'] = datetime.now().isoformat()
    return jsonify({
        'teams': cache['team_stats']['data'],
        'count': len(cache['team_stats']['data']),
        'fetched_at': cache['team_stats']['fetched_at']
    })


@app.route('/refresh')
def refresh():
    for k in cache:
        cache[k] = {'data': None, 'fetched_at': None}
    return jsonify({'status': 'refreshed'})


@app.route('/health')
def health():
    return jsonify({
        'status': 'online',
        'cache': {k: bool(v['data']) for k, v in cache.items()},
        'games': len(game_cache),
        'time': datetime.now().isoformat()
    })


# ==================== LIVE GAME ====================

def fetch_game(game_id):
    try:
        resp = requests.get(f"{FIBALIVE}/{game_id}/data.json", timeout=30)
        return resp.json()
    except:
        return None


@app.route('/live/<game_id>')
def live_game(game_id):
    data = fetch_game(game_id)
    if not data:
        return jsonify({'error': 'Game not found'}), 404
    return jsonify({'game_id': game_id, 'data': data})


@app.route('/live/<game_id>/team')
def live_team(game_id):
    data = fetch_game(game_id)
    if not data:
        return jsonify({'error': 'Game not found'}), 404
    
    teams = []
    for tid, t in data.get('tm', {}).items():
        teams.append({
            'id': tid,
            'name': t.get('name', ''),
            'code': t.get('code', ''),
            'score': t.get('score', 0),
            'fgm': t.get('tot_sFieldGoalsMade', 0),
            'fga': t.get('tot_sFieldGoalsAttempted', 0),
            'fgp': t.get('tot_sFieldGoalsPercentage', 0),
            'tpm': t.get('tot_sThreePointersMade', 0),
            'tpa': t.get('tot_sThreePointersAttempted', 0),
            'tpp': t.get('tot_sThreePointersPercentage', 0),
            'ftm': t.get('tot_sFreeThrowsMade', 0),
            'fta': t.get('tot_sFreeThrowsAttempted', 0),
            'reb': t.get('tot_sReboundsTotal', 0),
            'oreb': t.get('tot_sReboundsOffensive', 0),
            'dreb': t.get('tot_sReboundsDefensive', 0),
            'ast': t.get('tot_sAssists', 0),
            'stl': t.get('tot_sSteals', 0),
            'blk': t.get('tot_sBlocks', 0),
            'to': t.get('tot_sTurnovers', 0),
            'pf': t.get('tot_sFoulsPersonal', 0),
        })
    
    return jsonify({
        'game_id': game_id,
        'clock': data.get('clock', ''),
        'period': data.get('period', 0),
        'teams': teams
    })


@app.route('/live/<game_id>/home')
def live_home(game_id):
    return live_players(game_id, 0)


@app.route('/live/<game_id>/away')
def live_away(game_id):
    return live_players(game_id, 1)


def live_players(game_id, pos):
    data = fetch_game(game_id)
    if not data:
        return jsonify({'error': 'Game not found'}), 404
    
    team_ids = list(data.get('tm', {}).keys())
    if len(team_ids) < 2:
        return jsonify({'error': 'Invalid game'}), 400
    
    target_id = team_ids[pos]
    team_info = data['tm'][target_id]
    
    players = []
    for pid, p in data.get('pl', {}).items():
        if p.get('ti') == target_id:
            players.append({
                'id': pid,
                'firstName': p.get('firstName', '') or p.get('fn', ''),
                'lastName': p.get('familyName', '') or p.get('ln', ''),
                'name': f"{p.get('firstName', '') or p.get('fn', '')} {p.get('familyName', '') or p.get('ln', '')}".strip(),
                'no': p.get('pno', '') or p.get('no', ''),
                'pos': p.get('pos', ''),
                'min': p.get('min', '0:00'),
                'pts': p.get('pts', 0),
                'reb': p.get('reb', 0),
                'ass': p.get('ass', 0),
                'stl': p.get('stl', 0),
                'blk': p.get('blk', 0),
                'fgm': p.get('fgm', 0),
                'fga': p.get('fga', 0),
                'tpm': p.get('tpm', 0),
                'tpa': p.get('tpa', 0),
                'ftm': p.get('ftm', 0),
                'fta': p.get('fta', 0),
                'oreb': p.get('oreb', 0),
                'dreb': p.get('dreb', 0),
                'to': p.get('to', 0),
                'f': p.get('f', 0),
                'starter': p.get('E', 'N')
            })
    
    players.sort(key=lambda x: int(x['pts']) if x['pts'] else 0, reverse=True)
    
    return jsonify({
        'game_id': game_id,
        'team': {'id': target_id, 'name': team_info.get('name', ''), 'code': team_info.get('code', ''), 'score': team_info.get('score', 0)},
        'players': players
    })


@app.route('/live/<game_id>/leaders')
def live_leaders(game_id):
    data = fetch_game(game_id)
    if not data:
        return jsonify({'error': 'Game not found'}), 404
    
    players = []
    for pid, p in data.get('pl', {}).items():
        tinfo = data['tm'].get(p.get('ti', ''), {})
        players.append({
            'id': pid,
            'name': f"{p.get('firstName', '') or p.get('fn', '')} {p.get('familyName', '') or p.get('ln', '')}".strip(),
            'team': tinfo.get('shortName', ''),
            'code': tinfo.get('code', ''),
            'pts': p.get('pts', 0),
            'reb': p.get('reb', 0),
            'ass': p.get('ass', 0),
            'stl': p.get('stl', 0),
            'blk': p.get('blk', 0)
        })
    
    return jsonify({
        'game_id': game_id,
        'clock': data.get('clock', ''),
        'period': data.get('period', 0),
        'leaders': {
            'pts': sorted(players, key=lambda x: int(x['pts']) if x['pts'] else 0, reverse=True)[:5],
            'reb': sorted(players, key=lambda x: int(x['reb']) if x['reb'] else 0, reverse=True)[:5],
            'ass': sorted(players, key=lambda x: int(x['ass']) if x['ass'] else 0, reverse=True)[:5],
            'stl': sorted(players, key=lambda x: int(x['stl']) if x['stl'] else 0, reverse=True)[:5],
            'blk': sorted(players, key=lambda x: int(x['blk']) if x['blk'] else 0, reverse=True)[:5],
        }
    })


if __name__ == '__main__':
    print("NEBL Stats Server starting...")
    print("Endpoints: /leaders, /standings, /rankings, /schedule, /team-stats")
    print("Live: /live/<game_id>/team|home|away|leaders")
    app.run(host='0.0.0.0', port=5001, debug=True)
# Rebuilt at Mon Mar 23 14:36:41 CAST 2026
