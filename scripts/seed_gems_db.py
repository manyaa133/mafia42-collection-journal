import sqlite3
import json

def seed_gems_to_db():
    conn = sqlite3.connect('mafia42.db')
    cur = conn.cursor()

    with open('database/seed_gems.json', 'r', encoding='utf-8') as f:
        gems = json.load(f)

    for g in gems:
        extra_data = {
            'team': g['team'],
            'role_id': g['role_id'],
            'card_name': g['card_name'],
            'badge_image': g['badge_image'],
            'levels': g['levels']
        }
        cur.execute('''
            INSERT OR REPLACE INTO catalogue_items (
                id, category, name, character, card_id, rarity, level, cp, description, condition, how_to, extra, image, logo_image, wallet_images, display_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            g['id'],
            'gems',
            g['name'],
            g['character'],
            g['card_id'],
            '',
            16,
            1099,
            f"{g['team']} gem for {g['character']}",
            '',
            '',
            json.dumps(extra_data, ensure_ascii=False),
            g['image'],
            g['badge_image'],
            '[]',
            g['display_order']
        ))

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM catalogue_items WHERE category='gems'")
    count = cur.fetchone()[0]
    print(f"Successfully seeded {count} gems into catalogue_items table.")
    conn.close()

if __name__ == '__main__':
    seed_gems_to_db()

