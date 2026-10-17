import os
import re
import json

def clean_name(raw_name):
    raw_name = raw_name.strip()
    raw_name = re.sub(r'\[\d+\]', '', raw_name).strip()
    l = len(raw_name)
    if l % 2 == 0 and raw_name[:l//2].strip() == raw_name[l//2:].strip():
        raw_name = raw_name[:l//2].strip()
    return raw_name.strip()

def get_img_path(role, lvl):
    base = r'C:\Users\Manya\Desktop\mafia42 details\frontend\public\assets\gems'
    webp = f'item_gem_lv{lvl}_{role}.webp'
    png = f'item_gem_lv{lvl}_{role}.png'
    if os.path.exists(os.path.join(base, role, webp)):
        return f'/assets/gems/{role}/{webp}'
    elif os.path.exists(os.path.join(base, role, png)):
        return f'/assets/gems/{role}/{png}'
    return ''

def extract_items_from_section(sec_text):
    # Find GEM header inside section to isolate item entries
    gem_pos = sec_text.find('GEM')
    if gem_pos != -1:
        sec_text = sec_text[gem_pos + 3:]

    blocks = re.split(r'Increased collection points:\s*([0-9,]+)\s*CP', sec_text)
    items = []
    for i in range(1, len(blocks), 2):
        cp_val = int(blocks[i].replace(',', ''))
        pre_text = blocks[i-1].strip()
        lines = [l.strip() for l in pre_text.split('\n') if l.strip() and not l.strip().startswith('=== PAGE') and l.strip() != 'GEM']
        
        filtered_lines = []
        for line in lines:
            if re.match(r'^\d+\.\d+(?:\.\d+)?\.?', line):
                continue
            if 'A gem that slightly increases' in line or 'A jewel that slightly increases' in line or 'It is a gem that slightly' in line or 'It is a jewel that' in line:
                continue
            if 'The symbol' in line or 'The symbolic' in line or 'symbolic gem' in line or 'symbol jewel' in line or 'symbol gem' in line or 'The motif' in line:
                continue
            filtered_lines.append(line)
        
        name = ''
        desc = ''
        if len(filtered_lines) >= 2:
            name = clean_name(filtered_lines[0])
            desc = ' '.join(filtered_lines[1:])
        elif len(filtered_lines) == 1:
            name = clean_name(filtered_lines[0])
            desc = ''
        else:
            name = f'Level {(i+1)//2}'
            desc = ''

        items.append({
            'level': (i+1)//2,
            'name': name,
            'description': desc,
            'cp': cp_val,
            'gem_points': 1 if ((i+1)//2) == 15 else (2 if ((i+1)//2) == 16 else 0)
        })
    return items

def build_catalogue():
    with open('scratch_mafia_pdf.txt', encoding='utf-8') as f:
        m_txt = f.read()

    with open('scratch_citizen_pdf.txt', encoding='utf-8') as f:
        c_txt = f.read()

    mafia_roles_defs = [
        ('mafia', 'Mafia', 'onyx', 476, '1.2. mafia assistant job', 'iouygpwh', 'Mafia'),
        ('spy', 'Spy', 'ruby', 4110, '1.2.2. beast man', 'e0ry458b', 'Spy'),
        ('beastman', 'Beastman', 'catseye', 7537, '1.2.3. madam', '5207y874', 'Beastman'),
        ('madam', 'Madam', 'garnet', 11425, '1.2.4. thief', 'pfqk1pwr', 'Hostess'),
        ('thief', 'Thief', 'tanzanite', 14995, '1.2.5. witch', 'q27cibgz', 'Theif'),
        ('witch', 'Witch', 'fluorite', 18711, '1.2.6. Scientist', '7k7fp35h', 'Witch'),
        ('scientist', 'Scientist', 'luminous', 22395, '1.2.7. fraud', 'xxjwfv5m', 'Mad Scientist'),
        ('pretender', 'Swindler', 'sardonyx', 26528, '1.2.8. contractor', 'yx4huoi7', 'Swindler'),
        ('hitman', 'Hit Man', 'marble', 30298, '1.2.9. godfather', 'mx1qwlmg', 'Hit-Man'),
        ('godfather', 'Godfather', 'jasper', 33945, None, '1o78bybc', 'Godfather'),
    ]

    citizen_roles_defs = [
        ('police', 'Cop', 'sapphire', 1047, '9ahwn42r', 'Cop'),
        ('vigilante', 'Vigilante', 'lapislazuli', 4646, '64vuwue5', 'Vigilante'),
        ('agent', 'Agent', 'aquamarine_or_similar', 8496, 'nks95xam', 'Agent'),
        ('detective', 'Detective', 'jade', 12233, 'wpgg9tj2', 'Detective'),
        ('doctor', 'Doctor', 'diamond', 15759, 'aemgwk05', 'Doctor'),
        ('soldier', 'Soldier', 'emerald', 19518, '2r5leefr', 'Soldier'),
        ('politician', 'Politician', 'turquoise', 23212, 'k8ns7hg9', 'Politician'),
        ('shaman', 'Psychic', 'topaz', 26975, 'avu23jrp', 'Psychic'),
        ('couple', 'Lover', 'opal', 30488, '9moc515d', 'Lover'),
        ('gangster', 'Gangster', 'peridot', 33878, 'ixkz4u0t', 'Gangster'),
        ('reporter', 'Reporter', 'aquamarine', 37545, 'r4nv56bg', 'Reporter'),
        ('inspector', 'Inspector', 'amber', 41270, 'sgabjzcp', 'Inspector'),
        ('ghoul', 'Ghoul', 'moonstone', 45125, '3biud0co', 'Ghoul'),
        ('terrorist', 'Martyr', 'amethyst', 49046, 'ld44g5ge', 'Martyr'),
        ('priest', 'Priest', 'mithril', 52782, '30d1hqok', 'Priest'),
        ('prophet', 'Prophet', 'softcrystal', 56574, '84ny3xom', 'Prophet'),
        ('judge', 'Judge', 'goldstone', 60631, 'uw6eljes', 'Judge'),
        ('nurse', 'Nurse', 'rosequartz', 64328, '00zax2kt', 'Nurse'),
        ('magician', 'Magician', 'iolite', 68077, 'lmvs86cn', 'Magician'),
        ('hacker', 'Hacker', 'tourmaline', 71751, 'dyrvzrh3', 'Hacker'),
        ('mentalist', 'Mentalist', 'coral', 75591, 'ptmzctfg', 'Mentalist'),
        ('mercenary', 'Mercenary', 'bloodstone', 79244, 'u2g4v8l8', 'Mercenary'),
        ('official', 'Administrator', 'citrine', 82996, 'r9ckip5o', 'Administrartor'),
        ('cabal', 'Cabal', 'obsidian', 86809, 'w872wv9y', 'Cabal'),
        ('paparazzi', 'Paparazzi', 'rhodonite', 90543, 'e6hcmnui', 'Paparazzi'),
        ('hypnotist', 'Hypnotist', 'alexandrite', 94348, 'la6don9i', 'Hypnotist'),
        ('fortuneteller', 'Fortuneteller', 'meteorite', 98206, 'wzdv38wy', 'Fortuneteller'),
    ]

    all_gems = []
    display_order = 1

    # 1. Mafia Team
    for role_id, role_name, gem_sym, pos, next_title, card_id, card_name in mafia_roles_defs:
        end_pos = m_txt.find(next_title, pos) if next_title else len(m_txt)
        sec = m_txt[pos:end_pos]
        items = extract_items_from_section(sec)
        for item in items:
            item['image'] = get_img_path(role_id, item['level'])

        gem_record = {
            'id': f'gem_{role_id}',
            'category': 'gems',
            'team': 'Mafia Team',
            'role_id': role_id,
            'name': f'{role_name} Gem',
            'character': role_name,
            'card_id': card_id,
            'card_name': card_name,
            'image': get_img_path(role_id, 16),
            'badge_image': f'/assets/gems/{role_id}/jobcard_gem_{role_id}.webp',
            'display_order': display_order,
            'levels': items
        }
        all_gems.append(gem_record)
        display_order += 1

    # 2. Citizen Team
    for i, (role_id, role_name, gem_sym, start_pos, card_id, card_name) in enumerate(citizen_roles_defs):
        end_pos = citizen_roles_defs[i+1][3] if i+1 < len(citizen_roles_defs) else len(c_txt)
        sec = c_txt[start_pos:end_pos]
        items = extract_items_from_section(sec)
        for item in items:
            item['image'] = get_img_path(role_id, item['level'])

        gem_record = {
            'id': f'gem_{role_id}',
            'category': 'gems',
            'team': 'Citizen Team',
            'role_id': role_id,
            'name': f'{role_name} Gem',
            'character': role_name,
            'card_id': card_id,
            'card_name': card_name,
            'image': get_img_path(role_id, 16),
            'badge_image': f'/assets/gems/{role_id}/jobcard_gem_{role_id}.webp',
            'display_order': display_order,
            'levels': items
        }
        all_gems.append(gem_record)
        display_order += 1

    # 3. Cult Leader
    cultleader_levels = [
        {'level': 1, 'name': 'Pyrite Ore', 'description': 'Pyrite ore freshly mined from the mine. Increases Cult Leader appearance probability.', 'cp': 75, 'gem_points': 0, 'image': get_img_path('cultleader', 1)},
        {'level': 2, 'name': 'Brilliant Pyrite Ore', 'description': 'A pyrite gemstone polished to shine brightly.', 'cp': 91, 'gem_points': 0, 'image': get_img_path('cultleader', 2)},
        {'level': 3, 'name': 'Lesser Pyrite', 'description': 'A low-grade pyrite gem refined into a rough shape.', 'cp': 111, 'gem_points': 0, 'image': get_img_path('cultleader', 3)},
        {'level': 4, 'name': 'Brilliant Lesser Pyrite', 'description': 'A low-grade pyrite gem polished to shine brightly.', 'cp': 139, 'gem_points': 0, 'image': get_img_path('cultleader', 4)},
        {'level': 5, 'name': 'Intermediate Pyrite', 'description': 'A mid-level pyrite gem refined into a simple shape.', 'cp': 175, 'gem_points': 0, 'image': get_img_path('cultleader', 5)},
        {'level': 6, 'name': 'Brilliant Intermediate Pyrite', 'description': 'A mid-grade pyrite gem polished to shine brilliantly.', 'cp': 219, 'gem_points': 0, 'image': get_img_path('cultleader', 6)},
        {'level': 7, 'name': 'Advanced Pyrite', 'description': 'A high-quality pyrite gem refined into an elaborate shape.', 'cp': 271, 'gem_points': 0, 'image': get_img_path('cultleader', 7)},
        {'level': 8, 'name': 'Brilliant Advanced Pyrite', 'description': 'A high-grade pyrite gem polished to shine brightly.', 'cp': 331, 'gem_points': 0, 'image': get_img_path('cultleader', 8)},
        {'level': 9, 'name': 'Top quality pyrite', 'description': 'A top-quality pyrite gem refined into an enchanting shape.', 'cp': 399, 'gem_points': 0, 'image': get_img_path('cultleader', 9)},
        {'level': 10, 'name': 'Luminous top-notch pyrite', 'description': 'A top-quality pyrite gem polished to shine brilliantly.', 'cp': 475, 'gem_points': 0, 'image': get_img_path('cultleader', 10)},
        {'level': 11, 'name': "Artisan's pyrite", 'description': 'A pyrite gem refined by a legendary craftsman.', 'cp': 559, 'gem_points': 0, 'image': get_img_path('cultleader', 11)},
        {'level': 12, 'name': "Brilliant artisan's pyrite", 'description': 'A pyrite artisan gem refined by a craftsman and polished to a brilliant shine.', 'cp': 651, 'gem_points': 0, 'image': get_img_path('cultleader', 12)},
        {'level': 13, 'name': 'Miracle pyrite', 'description': 'A gem of pyrite that was miraculously refined through an incredible coincidence.', 'cp': 751, 'gem_points': 0, 'image': get_img_path('cultleader', 13)},
        {'level': 14, 'name': 'Brilliant miracle pyrite', 'description': 'A gem of pyrite that has been miraculously refined and polished to a brilliant shine.', 'cp': 859, 'gem_points': 0, 'image': get_img_path('cultleader', 14)},
        {'level': 15, 'name': 'Idol', 'description': 'An ancient idol symbolizing dark devotion and cult influence.', 'cp': 975, 'gem_points': 1, 'image': get_img_path('cultleader', 15)},
        {'level': 16, 'name': 'Baphomet', 'description': 'The supreme horns and sigil of the forbidden entity.', 'cp': 1099, 'gem_points': 2, 'image': get_img_path('cultleader', 16)},
    ]
    cultleader_gem = {
        'id': 'gem_cultleader',
        'category': 'gems',
        'team': 'Citizen Team',
        'role_id': 'cultleader',
        'name': 'Cult Leader Gem',
        'character': 'Cult Leader',
        'card_id': 'wtsw3x9h',
        'card_name': 'Cult Leader',
        'image': get_img_path('cultleader', 16),
        'badge_image': '/assets/gems/cultleader/jobcard_gem_cultleader.webp',
        'display_order': display_order,
        'levels': cultleader_levels
    }
    all_gems.append(cultleader_gem)

    out_file = r'C:\Users\Manya\Desktop\mafia42 details\database\seed_gems.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(all_gems, f, indent=2, ensure_ascii=False)
    print(f'Successfully built {len(all_gems)} gems in {out_file}')

if __name__ == '__main__':
    build_catalogue()

