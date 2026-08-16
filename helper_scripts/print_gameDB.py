
# PRINTS NUMBERED LIST OF GAMES FROM CSV FILE TO TEXT FILE

import csv
import os

# Resolve paths relative to this script so it works regardless of the
# directory it's run from, not just when run from inside helper_scripts/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CSV = os.path.join(SCRIPT_DIR, '..', 'gameDB.csv')
OUTPUT_TXT = os.path.join(SCRIPT_DIR, 'my_games.txt')

# String that contains all the games.
my_games = ""

# Index for the game.
i = 0

# Open csv file to reader (tab-delimited: galaxy_library_export.py's default)
with open(INPUT_CSV, 'r', encoding='utf-8') as csv_file:
    reader = csv.reader(csv_file, delimiter='\t')

    # The name of the game is on the first part of the row
    for row in reader:
        # Add the index to the game.
        if i > 0:
            my_games += str(i) + ". " + row[0] + "\n"
        print(row[0])
        i += 1

# Write the string to file.
with open(OUTPUT_TXT, 'w', encoding='utf-8') as games_file:
    games_file.write(my_games)

# Close the file.
games_file.close()
