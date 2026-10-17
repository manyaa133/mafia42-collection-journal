import json
import sqlite3

def polish_citizen_gems():
    with open('database/seed_gems.json', 'r', encoding='utf-8') as f:
        gems = json.load(f)

    # Dictionary of exact overrides per role and level
    exact_names = {
        'hacker': {
            1: ('Tourmaline Gemstone', 'A tourmaline gemstone freshly mined from the mine. When equipped, it increases the probability of being assigned to a hacker.'),
            2: ('Brilliant Tourmaline Gemstone', 'A tourmaline gemstone polished to shine brightly. When equipped, it increases the probability of being assigned to a hacker.'),
            3: ('Lesser Tourmaline', 'A low-grade tourmaline gem refined into a rough shape. When equipped, it increases the probability of being assigned to a hacker.'),
            4: ('Brilliant Lesser Tourmaline', 'A low-grade tourmaline gem polished to shine brightly. When equipped, it increases the probability of being assigned to a hacker.'),
            5: ('Intermediate Tourmaline', "A mid-grade gemstone of tourmaline smelted into a simple shape. When equipped, it increases the hacker's assignment probability and acquisition rubles."),
            6: ('Luminous Intermediate Tourmaline', "A mid-grade tourmaline gem polished to shine brilliantly. When equipped, it increases the hacker's assignment probability and acquisition rubles."),
            7: ('Advanced Tourmaline', "A high-quality tourmaline gem refined into an elaborate shape. When equipped, it increases the hacker's assignment probability and acquisition rubles."),
            8: ('Brilliant Premium Tourmaline', "A high-grade tourmaline gem polished to shine brightly. When equipped, it increases the hacker's assignment probability and acquisition rubles."),
            9: ('Top Quality Tourmaline', "A top-quality tourmaline gem refined into an enchanting shape. When equipped, it increases the hacker's assignment probability, acquisition rubles, and RP increase rate."),
            10: ('Luminous Top-notch Tourmaline', "A top-quality tourmaline gem polished to shine brilliantly. When equipped, it increases the hacker's assignment probability, acquisition rubles, and RP increase rate."),
            11: ("Artisan's Tourmaline", "A tourmaline gem refined by legendary craftsmen. When equipped, it increases the hacker's assignment probability, acquisition rubles, and RP increase rate."),
            12: ('Tourmaline by a Brilliant Artisan', "An artisan gem of tourmaline that has been smelted by a craftsman and polished to a brilliant shine. When equipped, it increases the hacker's assignment probability, acquisition rubles, and RP increase rate."),
            13: ('Miracle Tourmaline', "A gem of tourmaline that was miraculously refined through an incredible coincidence. When equipped, it increases the hacker's assignment probability, acquisition rubles, and RP increase rate."),
            14: ('Brilliant Miracle Tourmaline', "A tourmaline gem that has been miraculously refined and polished to a brilliant shine. When equipped, it increases the hacker's assignment probability, acquisition rubles, and RP increase rate."),
            15: ('System', 'A system in virtual reality organized to move within a predictable range for one ideal.'),
            16: ('Singularity', 'The complete turning point of the system that will be faced in the irreversible flow.'),
        },
        'mentalist': {
            7: ('Greater Coral', "A high-quality coral gem refined into an elaborate shape. When equipped, it increases the psychologist's assignment probability and acquisition rubles."),
            8: ('Luminous Superior Coral', "A high-grade coral gem polished to shine brightly. When equipped, it increases the psychologist's assignment probability and acquisition rubles."),
            11: ('Artisan Coral', "A coral gem smelted by a legendary craftsman. When equipped, it increases the psychologist's assignment probability, rubles earned, and RP increase rate."),
        },
        'mercenary': {
            6: ('Brilliant Intermediate Bloodstone', 'A mid-level bloodstone gem polished to shine brightly. When equipped, it increases the assignment probability and acquisition rubles of mercenaries.'),
            9: ('Supreme Bloodstone', "A top-quality bloodstone gem refined into an enchanting shape. When equipped, it increases the mercenary's assignment probability, rubles earned, and RP increase rate."),
            10: ('Brilliant Supreme Bloodstone', "A top-quality bloodstone gem polished to shine brilliantly. When equipped, it increases the mercenary's assignment probability, rubles earned, and RP increase rate."),
            13: ('Miraculous Bloodstone', "A bloodstone gem that was miraculously refined through a great coincidence. When equipped, it increases the mercenary's assignment probability, rubles earned, and RP increase rate."),
        },
        'official': {
            3: ('Lower Citrine', 'A low-grade citrine gem refined into a rough shape. When installed, it increases the probability of being assigned to a civil servant.'),
            6: ('Brilliant Intermediate Citrine', 'A mid-grade citrine gem polished to shine brightly. When equipped, it increases the assignment probability and acquisition rubles of civil servants.'),
            10: ('Brilliant, Top-notch Citrine', 'A top-quality citrine gem polished to shine brilliantly. When equipped, it increases the assignment probability of civil servants, the rubles earned, and the RP increase rate.'),
        },
        'cabal': {
            7: ('Greater Obsidian', 'A high-grade obsidian gem refined into an elaborate shape. When equipped, it increases the secret society assignment probability and acquisition rubles.'),
            8: ('Resplendent Greater Obsidian', 'A high-grade obsidian gem polished to shine brilliantly. When equipped, it increases the secret society assignment probability and acquisition rubles.'),
            9: ('Superlative Obsidian', 'A top-quality obsidian gem refined into an enchanting shape. When equipped, it increases the chance of assigning a secret society, earning Rubles, and increasing RP.'),
            10: ('Resplendent Superlative Obsidian', 'A top-quality obsidian gem polished to shine brilliantly. When equipped, it increases the chance of assigning a secret society, earning Rubles, and increasing RP.'),
            12: ("Resplendent Artisan's Obsidian", 'An obsidian artisan gem that has been smelted by a craftsman and polished to a brilliant shine. When equipped, it increases the chance of assigning a secret society, earning Rubles, and increasing RP.'),
        },
        'paparazzi': {
            7: ('Greater Rhodonite', 'A high-grade rhodonite gem refined into an elaborate shape. When equipped, it increases the assignment probability and acquisition rubles of paparazzi.'),
            8: ('Brilliant Advanced Rhodonite', 'A high-grade rhodonite gem polished to shine brightly. When equipped, it increases the assignment probability and acquisition rubles of paparazzi.'),
            9: ('Top Grade Rhodonite', "A top-quality rhodonite gem refined into an enchanting shape. When equipped, it increases Paparazzi's assignment probability, earned rubles, and RP increase rate."),
            10: ('Brilliant Top Grade Rhodonite', "A top-quality rhodonite gem polished to shine brilliantly. When equipped, it increases Paparazzi's assignment probability, earned rubles, and RP increase rate."),
        },
        'hypnotist': {
            7: ('Greater Alexandrite', "A high-grade alexandrite gem refined into an elaborate shape. When equipped, it increases the hypnotist's assignment probability and acquisition rubles."),
            8: ('Brilliant Advanced Alexandrite', "A high-grade alexandrite gem polished to shine brightly. When equipped, it increases the hypnotist's assignment probability and acquisition rubles."),
            12: ("Bright Artisan's Alexandrite", "An alexandrite artisan gem that has been smelted by a craftsman and polished to a brilliant shine. When equipped, it increases the hypnotist's assignment probability, rubles earned, and RP increase rate."),
            14: ('Bright Miraculous Alexandrite', "An alexandrite gem that has been miraculously refined and polished to a brilliant shine. When equipped, it increases the hypnotist's assignment probability, rubles earned, and RP increase rate."),
        },
        'fortuneteller': {
            1: ('Meteorite', 'Gemstones of the meteorite just digging from the mine. Installation increases the probability of the fortune-teller.'),
            2: ('Brilliant Meteorite', 'The gemstone of the meteorite polished to give a brilliant light. Installation increases the probability of the fortune-teller.'),
            3: ('Low-class Meteorite', 'Lower jewelry of meteorites in a clunky shape. Installation increases the probability of the fortune-teller.'),
            4: ('Lower Meteorite', 'Lower jewelry of meteorites polished to produce brilliant light. Installation increases the probability of the fortune-teller.'),
            5: ('Intermediate Meteorite', 'Intermediate jewelry of meteorites in a simple shape. When installed, it increases the stomach accumulation and acquisition of the fort.'),
            6: ('Brilliant Intermediate Meteorite', 'Intermediate jewelry of meteorites polished to light light. When installed, the fort is the stomach accumulation and acquisition ruble.'),
            7: ('Advanced Meteorite', 'Advanced jewelry of meteorites in elaborate shapes. When installed, the fort is the stomach accumulation and acquisition ruble.'),
            8: ('Brilliant Advanced Meteorite', 'Advanced jewelry of meteorites polished to produce brilliant light. When installed, the fort is the stomach accumulation and acquisition ruble.'),
            9: ('Top-class Meteorite', 'The best jewel of meteorite smelting in an ecstasy. When mounted, the rate of stomach fortune, acquisition and RP increase, increase the rate of increase.'),
            10: ('The Best Meteorite', 'The best jewel of meteorites polished to light light. When mounted, the rate of stomach fortune, acquisition and RP increase, increase the rate of increase.'),
            11: ('Craftsman Meteorite', 'Jewelry of the meteorite smoked by legendary craftsmen. When mounted, the rate of stomach fortune, acquisition and RP increase, increase the rate of increase.'),
            12: ('Resplendent Craftsman Meteorite', 'The craftsmen of the meteorites polished by craftsmen and glow light. When mounted, the rate of stomach fortune, acquisition and RP increase, increase the rate of increase.'),
            13: ('Miracle Meteorite', 'The jewel of the meteorite miraculously smoked through a tremendous coincidence. When mounted, the rate of stomach fortune, acquisition and RP increase, increase the rate of increase.'),
            14: ('Brilliant Miracle Meteorite', 'The jewel of the meteorite polished to miraculously smelting and bright light. When mounted, the rate of stomach fortune, acquisition and RP increase, increase the rate of increase.'),
            15: ('Trust', 'A revelation delivered in a language hidden in the starlight.'),
            16: ('Oracle', 'A fate revealed by the gathering of starlight scattered between dimensions.'),
        },
        'gangster': {
            15: ('Ambrosia', 'A herb that, if eaten, is said to make you immortal and give you tremendous power.'),
            16: ('Terra', 'The origin and source of all power and life.'),
        },
        'reporter': {
            15: ('Torch', 'A holy flame that does not go out in any darkness.'),
            16: ('Libertas', "A transcendent existence created by the people's longing for freedom."),
        },
        'inspector': {
            15: ('Principle', 'A book that contains all the knowledge and logic of the world.'),
            16: ('Epic', 'A majestic story written by a blind poet, containing all the joys and sorrows of mankind, all the stories of heroes and beggars, kings and slaves and common people.'),
        },
        'ghoul': {
            15: ("Philosopher's Stone", 'A stone said to contain the power to transcend death.'),
            16: ('Orichalcum', 'A legendary mineral that cannot be created by human power.'),
        },
        'terrorist': {
            15: ('Tsar Bomba', 'A bomb with the strongest and worst power in human history.'),
            16: ('Armageddon', 'A crystal containing the power to end everything.'),
        },
        'priest': {
            15: ('Memento', 'A gift left to posterity by someone who died not in vain.'),
            16: ('Avalon', 'An ancient relic said to have been made in heaven.'),
        },
        'prophet': {
            15: ('The Ball of Correction', 'A crystal ball of prophecy that allows you to foresee future events.'),
            16: ('Ragnarok', 'The final end that not even God can avoid.'),
        },
        'judge': {
            15: ('Balance', 'A scale that symbolizes fairness that does not lean towards either side.'),
            16: ('Justitia', 'A crystal containing the power of a fair goddess.'),
        },
        'nurse': {
            15: ('Heavenly Trumpet', 'An angelic instrument resounding in heaven.'),
            16: ('Raphael', 'An archangel of healing who can heal any disease.'),
        },
        'magician': {
            15: ('Rune Inscription Stone', 'An ore imprinted with powerful magical runes.'),
            16: ('Holy Grail', 'A holy grail made by carving a rune imprint stone enchanted with powerful magic.'),
        },
        'police': {
            15: ('Valkyrie', 'Wings of a righteous and courageous angel.'),
            16: ('Freya', "The most powerful angel's wing piece that guides the Valkyries."),
        },
        'vigilante': {
            15: ('Iokeira', 'An arrowhead used by the goddess Artemis.'),
            16: ('Fail Note', 'A bow and arrow that never misses its target.'),
        },
        'agent': {
            15: ('Qubit', 'An arithmetic algorithm that decrypts all passwords by exceeding the information limit.'),
            16: ('Omega', 'The final form of a program completed after infinite calculations.'),
        },
        'detective': {
            15: ('Test Tube Mouth', 'The roar of a wild beast that pierces the darkness and pursues evil.'),
            16: ('Sphinx', "A judge's question that only the righteous are qualified to answer."),
        },
        'doctor': {
            15: ('Yggdrasil', 'The tree is said to be the source of all life.'),
            16: ('Entropy', 'The source of energy that operates all order in the world.'),
        },
        'soldier': {
            15: ('Aegis', 'A mythical shield that can block anything.'),
            16: ('Iron Curtain', 'A device designed to overcome the limitations of physical defenses.'),
        },
        'politician': {
            15: ('Obelisk', 'A monument erected to honor the achievements of a great leader.'),
            16: ('Babel', 'The end of the powerful who challenged the power of God.'),
        },
        'shaman': {
            15: ('Magic Lamp', 'A magical lamp that is said to have sealed the soul of a fairy.'),
            16: ('Tartarus', 'The worst space where all the ghosts in the world are sealed.'),
        },
        'couple': {
            15: ('Agape', 'The crystallization of the purest and noblest love.'),
            16: ('Idea', 'An object of eternal admiration that exists beyond time and space.'),
        },
    }

    updated_count = 0
    for g in gems:
        r_id = g['role_id']
        if r_id in exact_names:
            for lvl in g['levels']:
                l_num = lvl['level']
                if l_num in exact_names[r_id]:
                    new_n, new_d = exact_names[r_id][l_num]
                    lvl['name'] = new_n
                    if new_d:
                        lvl['description'] = new_d
                    updated_count += 1

    with open('database/seed_gems.json', 'w', encoding='utf-8') as f:
        json.dump(gems, f, indent=2, ensure_ascii=False)
    print(f'Polished {updated_count} citizen levels in database/seed_gems.json')

    # Update database
    conn = sqlite3.connect('mafia42.db')
    cur = conn.cursor()
    for g in gems:
        extra_data = {
            'team': g['team'],
            'role_id': g['role_id'],
            'card_name': g['card_name'],
            'badge_image': g['badge_image'],
            'levels': g['levels']
        }
        cur.execute('''
            UPDATE catalogue_items
            SET extra = ?, name = ?, character = ?, card_id = ?, image = ?, logo_image = ?
            WHERE id = ?
        ''', (
            json.dumps(extra_data, ensure_ascii=False),
            g['name'],
            g['character'],
            g['card_id'],
            g['image'],
            g['badge_image'],
            g['id']
        ))
    conn.commit()
    conn.close()
    print('Updated mafia42.db catalogue_items with polished metadata!')

if __name__ == '__main__':
    polish_citizen_gems()

