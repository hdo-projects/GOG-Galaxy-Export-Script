#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Reads a CSV exported by galaxy_library_export.py and produces a lightweight
Markdown tracking table, ready to paste into a conversation:

    Titre | Plateforme | Statut | Verdict | Date

Statut is limited to what the GOG Galaxy database can actually tell us:
"Backlog" if the game was never launched, "Possede" otherwise. It does not
guess "Termine" / "Abandonne" or track in-progress state - those are manual,
human judgment calls and are left blank for the reader to fill in by hand.

Usage:
    python helper_scripts/export_markdown.py [-i gameDB.csv] [-o gameDB.md] [-d DELIM]
"""

import argparse
import csv
import re
import unicodedata


CORE_COLUMNS = ['Titre', 'Plateforme', 'Statut', 'Verdict', 'Date']
EXTRA_COLUMNS = ['Genres', 'Developpeurs', 'Score critique', 'Ma note', 'Temps de jeu (h)', 'Tags']

# Homebrew emulators/tools sideloaded onto Xbox under a "game" title (often with
# zero-width/invisible characters and random suffixes to dodge the store scanner).
# They are not games and are dropped from the export entirely.
KNOWN_EMULATOR_TOOLS = ['RetroArch', 'Dolphin', 'PPSSPP', 'Xenia', 'DevilutionX']

# GOG lists a game claimed both directly and via an Amazon Prime Gaming / Luna
# promo as two separate releases with a "- Amazon Prime"/"- Amazon Luna" suffix.
# These are the same game and are collapsed into a single row.
DUPLICATE_CLAIM_SUFFIX = re.compile(r'\s*(?:[-–]\s*)?Amazon (?:Prime|Luna)\s*$', re.IGNORECASE)

LEGEND = """<!--
Statut deduit automatiquement à partir du temps de jeu, à corriger à la main :
  - Backlog  : jamais lance (aucun temps de jeu enregistre)
  - Possede  : temps de jeu > 0 ; Termine/Abandonne sont des choix manuels
Verdict et Date sont toujours laisses vides : à completer à la main
(Verdict uniquement utile pour Termine/Abandonne, sans jugement de valeur).
Colonnes apres Date : contexte supplementaire tire du CSV, pas des colonnes
attendues par le format de suivi.
Nettoyage applique avant export : les entrees "- Amazon Prime"/"- Amazon Luna"
(meme jeu reclame deux fois) sont fusionnees avec le jeu de base, et les
emulateurs/outils sideloades sur Xbox (RetroArch, Dolphin, PPSSPP, Xenia,
DevilutionX) sont exclus car ce ne sont pas des jeux.
-->"""


def strip_invisible_chars(text):
    """ Removes zero-width/format Unicode characters (category Cf) used to
        disguise sideloaded Xbox emulator titles """
    return ''.join(ch for ch in text if unicodedata.category(ch) != 'Cf')


def is_emulator_tool(title, platform_list):
    if 'xbox live' not in (platform_list or '').lower():
        return False
    cleaned = strip_invisible_chars(title or '').strip().lower()
    return any(cleaned.startswith(name.lower()) for name in KNOWN_EMULATOR_TOOLS)


def strip_duplicate_claim_suffix(title):
    return DUPLICATE_CLAIM_SUFFIX.sub('', title or '').strip()


def split_platforms(platform_list, delimiter):
    return [p for p in (platform_list or '').split(delimiter) if p]


def merge_duplicate_claims(csv_rows, delimiter):
    """ Collapses "Title - Amazon Prime"/"Title - Amazon Luna" rows into the
        base "Title" row, merging platforms and taking the max playtime so a
        played copy isn't shadowed by an unplayed duplicate claim """
    groups = {}
    order = []
    for row in csv_rows:
        key = strip_duplicate_claim_suffix(row.get('title')).casefold()
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)

    merged_rows = []
    duplicates_collapsed = 0
    for key in order:
        members = groups[key]
        duplicates_collapsed += len(members) - 1

        # Prefer the un-suffixed row (if any) as the base for extra metadata
        base = next((m for m in members if not DUPLICATE_CLAIM_SUFFIX.search(m.get('title') or '')), members[0])
        merged = dict(base)
        merged['title'] = strip_duplicate_claim_suffix(base.get('title'))

        platforms = []
        for m in members:
            for p in split_platforms(m.get('platformList'), delimiter):
                if p not in platforms:
                    platforms.append(p)
        merged['platformList'] = delimiter.join(platforms)

        play_minutes = 0.0
        for m in members:
            try:
                play_minutes = max(play_minutes, float(m.get('gameMins') or 0))
            except ValueError:
                pass
        merged['gameMins'] = play_minutes if play_minutes else ''

        for field in ('genres', 'developers', 'criticsScore', 'myRating', 'tags'):
            if not (merged.get(field) or '').strip():
                for m in members:
                    if (m.get(field) or '').strip():
                        merged[field] = m[field]
                        break

        merged_rows.append(merged)

    return merged_rows, duplicates_collapsed


def escape_cell(value):
    return (value or '').replace('|', '\\|').replace('\t', ', ').strip()


def guess_status(game_mins):
    try:
        return 'Backlog' if float(game_mins) <= 0 else 'Possede'
    except (TypeError, ValueError):
        return 'Backlog'


def format_playtime_hours(game_mins):
    try:
        minutes = float(game_mins)
    except (TypeError, ValueError):
        return ''
    return '{:.1f}'.format(minutes / 60) if minutes else ''


def build_row(csv_row):
    return [
        escape_cell(csv_row.get('title')),
        escape_cell(csv_row.get('platformList')),
        guess_status(csv_row.get('gameMins')),
        '',  # Verdict: manual only
        '',  # Date: manual only
        escape_cell(csv_row.get('genres')),
        escape_cell(csv_row.get('developers')),
        escape_cell(csv_row.get('criticsScore')),
        escape_cell(csv_row.get('myRating')),
        format_playtime_hours(csv_row.get('gameMins')),
        escape_cell(csv_row.get('tags')),
    ]


def export_markdown(input_path, output_path, delimiter):
    with open(input_path, 'r', encoding='utf-8', newline='') as f:
        raw_rows = list(csv.DictReader(f, delimiter=delimiter))

    kept_rows = []
    excluded_tools = 0
    for row in raw_rows:
        if not (row.get('title') or '').strip():
            continue
        if is_emulator_tool(row.get('title'), row.get('platformList')):
            excluded_tools += 1
            continue
        kept_rows.append(row)

    merged_rows, duplicates_collapsed = merge_duplicate_claims(kept_rows, delimiter)
    merged_rows.sort(key=lambda r: (r.get('title') or '').casefold())

    header = CORE_COLUMNS + EXTRA_COLUMNS
    lines = [
        LEGEND, '',
        '| ' + ' | '.join(header) + ' |',
        '|' + '|'.join(['---'] * len(header)) + '|',
    ]
    for row in merged_rows:
        lines.append('| ' + ' | '.join(build_row(row)) + ' |')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    return {
        'raw': len(raw_rows),
        'excluded_tools': excluded_tools,
        'duplicates_collapsed': duplicates_collapsed,
        'written': len(merged_rows),
        'backlog': sum(1 for r in merged_rows if guess_status(r.get('gameMins')) == 'Backlog'),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Export a Markdown backlog-tracking table from a GOG Galaxy CSV export'
    )
    parser.add_argument('-i', '--input', default='gameDB.csv',
                         help='CSV file produced by galaxy_library_export.py (default: gameDB.csv)')
    parser.add_argument('-o', '--output', default='gameDB.md',
                         help='Markdown file to write (default: gameDB.md)')
    parser.add_argument('-d', '--delimiter', default='\t',
                         help="delimiter used in the input CSV, must match the export's -d option (default: tab)")
    args = parser.parse_args()

    stats = export_markdown(args.input, args.output, args.delimiter)
    print(
        '{written} entrees ecrites dans {output} '
        '(sur {raw} lignes du CSV : {excluded_tools} outils/emulateurs exclus, '
        '{duplicates_collapsed} doublons Amazon Prime/Luna fusionnes) - '
        'Backlog: {backlog}'.format(output=args.output, **stats)
    )
