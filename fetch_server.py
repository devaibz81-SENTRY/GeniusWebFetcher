def parse_standings(html):
    """Parse standings table"""
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')
    standings = []

    for row in rows:
        cells = row.find_all(['td', 'th'])
        if len(cells) == 11:
            # Skip header row by checking if the first cell is a number
            rank_text = cells[0].get_text(strip=True)
            if not rank_text.isdigit():
                continue

            # Extract team name and abbr from the team cell (index 2)
            team_cell = cells[2]
            team_text = team_cell.get_text(strip=True)
            team_name = None
            abbr = None
            for name, code in TEAM_MAP.items():
                if team_text.startswith(name):
                    team_name = name
                    abbr = code
                    break
            if team_name is None:
                # If we can't find a match, skip this row.
                continue

            # Extract the stats:
            #   W: index 4
            #   L: index 5
            #   GP: index 6
            #   GD: index 10
            try:
                w = int(cells[4].get_text(strip=True)) if cells[4].get_text(strip=True).isdigit() else 0
                l = int(cells[5].get_text(strip=True)) if cells[5].get_text(strip=True).isdigit() else 0
                gp = int(cells[6].get_text(strip=True)) if cells[6].get_text(strip=True).isdigit() else 0
            except:
                w = l = gp = 0

            # Compute pct: if gp > 0, then (w / gp) * 100, else 0
            if gp > 0:
                pct = round(w / gp * 100, 1)
            else:
                pct = 0.0

            standings.append({
                'rank': rank_text,
                'team': team_name,
                'abbr': abbr,
                'gp': str(gp),
                'w': str(w),
                'l': str(l),
                'pct': str(pct),
                'diff': cells[10].get_text(strip=True),   # GD
            })

    return standings