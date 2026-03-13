with open("src/leagues/shl/league.py", "r") as f:
    text = f.read()
text = text.replace("return records", """for i, row in enumerate(records):
            row['standings_rank'] = i + 1
        return records""")
with open("src/leagues/shl/league.py", "w") as f:
    f.write(text)
