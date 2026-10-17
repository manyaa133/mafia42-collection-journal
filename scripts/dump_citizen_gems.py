import json

def dump():
    gems = json.load(open('database/seed_gems.json', encoding='utf-8'))
    with open('scratch_current_citizen_levels.txt', 'w', encoding='utf-8') as out:
        for g in gems:
            if g['team'] == 'Citizen Team':
                out.write(f"=== {g['role_id']} ({g['character']}) ===\n")
                for lvl in g['levels']:
                    out.write(f"Lv{lvl['level']}: {lvl['name']} | {lvl['cp']} CP | {lvl['image']} | {lvl['description']}\n")
                out.write('\n')
    print('Dumped successfully!')

if __name__ == '__main__':
    dump()

