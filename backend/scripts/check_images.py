import sqlite3

conn = sqlite3.connect("mafia42.db")
c = conn.cursor()

print("--- CARDS ---")
cards = c.execute("SELECT id, name, image, logo_image FROM catalogue_items WHERE category='cards' LIMIT 5").fetchall()
for card in cards:
    print(card)

print("\n--- SKINS ---")
skins = c.execute("SELECT id, name, image, logo_image FROM catalogue_items WHERE category='skins' LIMIT 5").fetchall()
for skin in skins:
    print(skin)

print("\n--- CARDS COUNT & LOGO STATUS ---")
total_cards = c.execute("SELECT count(*) FROM catalogue_items WHERE category='cards'").fetchone()[0]
cards_with_logo = c.execute("SELECT count(*) FROM catalogue_items WHERE category='cards' AND logo_image IS NOT NULL AND logo_image != ''").fetchone()[0]
print(f"Total cards: {total_cards}, with logo: {cards_with_logo}")

print("\n--- SKINS COUNT & LOGO STATUS ---")
total_skins = c.execute("SELECT count(*) FROM catalogue_items WHERE category='skins'").fetchone()[0]
skins_with_logo = c.execute("SELECT count(*) FROM catalogue_items WHERE category='skins' AND logo_image IS NOT NULL AND logo_image != ''").fetchone()[0]
print(f"Total skins: {total_skins}, with logo: {skins_with_logo}")

