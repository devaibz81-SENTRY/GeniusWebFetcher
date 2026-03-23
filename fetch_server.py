@app.route('/debug/standings')
def debug_standings():
    html = fetch_html(URLS['standings'])
    standings = parse_standings(html)
    return jsonify({
        'html_length': len(html),
        'html_preview': html[:500] if html else '',
        'standings': standings,
        'count': len(standings)
    })