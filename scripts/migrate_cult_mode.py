import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("=== MIGRATING CULT LEADER TO CULT MODE ===")

# 1. Update SQLite mafia42.db
conn = sqlite3.connect("mafia42.db")
c = conn.cursor()

c.execute("SELECT id, name, character, extra FROM catalogue_items WHERE id = 'gem_cultleader'")
row = c.fetchone()
if not row:
    print("ERROR: gem_cultleader not found in catalogue_items!")
    sys.exit(1)

extra = json.loads(row[3]) if row[3] else {}
print(f"Current DB team: {extra.get('team')}")

extra['team'] = "Cult Mode"
new_extra_json = json.dumps(extra, ensure_ascii=False)
new_desc = "Cult Mode gem for Cult Leader"

c.execute("""
    UPDATE catalogue_items
    SET description = ?, extra = ?
    WHERE id = 'gem_cultleader'
""", (new_desc, new_extra_json))
conn.commit()

c.execute("SELECT id, name, description, extra FROM catalogue_items WHERE id = 'gem_cultleader'")
updated_row = c.fetchone()
updated_extra = json.loads(updated_row[3])
print(f"Updated DB team: {updated_extra.get('team')}")
print(f"Updated DB description: {updated_row[2]}")

# Check user_gems
c.execute("SELECT count(*) FROM user_gems WHERE item_id = 'gem_cultleader'")
ug_count = c.fetchone()[0]
print(f"Existing user_gems selections for gem_cultleader preserved: {ug_count}")

conn.close()

# 2. Update database/seed_gems.json
with open("database/seed_gems.json", "r", encoding="utf-8") as f:
    seed_gems = json.load(f)

updated_seed_gems = False
for g in seed_gems:
    if g.get("id") == "gem_cultleader":
        g["team"] = "Cult Mode"
        updated_seed_gems = True
        break

if updated_seed_gems:
    with open("database/seed_gems.json", "w", encoding="utf-8") as f:
        json.dump(seed_gems, f, indent=2, ensure_ascii=False)
    print("Updated database/seed_gems.json successfully.")

# 3. Update database/seed_catalogue.json
with open("database/seed_catalogue.json", "r", encoding="utf-8") as f:
    seed_cat = json.load(f)

updated_seed_cat = False
gems_list = seed_cat.get("gems", [])
for g in gems_list:
    if g.get("id") == "gem_cultleader":
        g["description"] = "Cult Mode gem for Cult Leader"
        if "extra" in g and g["extra"]:
            try:
                cat_extra = json.loads(g["extra"])
                cat_extra["team"] = "Cult Mode"
                g["extra"] = json.dumps(cat_extra, ensure_ascii=False)
            except Exception:
                pass
        updated_seed_cat = True
        break

if updated_seed_cat:
    with open("database/seed_catalogue.json", "w", encoding="utf-8") as f:
        json.dump(seed_cat, f, indent=2, ensure_ascii=False)
    print("Updated database/seed_catalogue.json successfully.")

print("=== MIGRATION COMPLETE ===")

