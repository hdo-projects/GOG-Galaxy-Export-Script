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


CORE_COLUMNS = ['Titre', 'Plateforme', 'Statut', 'Verdict', 'Date']
EXTRA_COLUMNS = ['Genres', 'Developpeurs', 'Score critique', 'Ma note', 'Temps de jeu (h)', 'Tags']

LEGEND = """<!--
Statut deduit automatiquement à partir du temps de jeu, à corriger à la main :
  - Backlog  : jamais lance (aucun temps de jeu enregistre)
  - Possede  : temps de jeu > 0 ; Termine/Abandonne sont des choix manuels
Verdict et Date sont toujours laisses vides : à completer à la main
(Verdict uniquement utile pour Termine/Abandonne, sans jugement de valeur).
Colonnes apres Date : contexte supplementaire tire du CSV, pas des colonnes
attendues par le format de suivi.
-->"""


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
        rows = list(csv.DictReader(f, delimiter=delimiter))

    rows.sort(key=lambda r: (r.get('title') or '').casefold())

    header = CORE_COLUMNS + EXTRA_COLUMNS
    lines = [
        LEGEND, '',
        '| ' + ' | '.join(header) + ' |',
        '|' + '|'.join(['---'] * len(header)) + '|',
    ]

    written = 0
    for csv_row in rows:
        if not (csv_row.get('title') or '').strip():
            continue
        lines.append('| ' + ' | '.join(build_row(csv_row)) + ' |')
        written += 1

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    return written


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

    count = export_markdown(args.input, args.output, args.delimiter)
    print('{} entrees ecrites dans {}'.format(count, args.output))
