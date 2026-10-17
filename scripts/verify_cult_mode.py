import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000/api"

print("--- Testing GET /api/gems ---")
req = urllib.request.Request(f"{BASE_URL}/gems")
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))
teams = data.get("teams", {})
print("Teams present in API response:", list(teams.keys()))

mafia_list = teams.get("Mafia Team", [])
citizen_list = teams.get("Citizen Team", [])
cult_list = teams.get("Cult Mode", [])

print(f"Mafia Team count: {len(mafia_list)}")
print(f"Citizen Team count: {len(citizen_list)}")
print(f"Cult Mode count: {len(cult_list)}")

# Check Cult Leader is in Cult Mode and not in Citizen Team
cult_chars = [g["character"] for g in cult_list]
citizen_chars = [g["character"] for g in citizen_list]

print("Cult Mode characters:", cult_chars)
assert "Cult Leader" in cult_chars, "Cult Leader MUST be in Cult Mode!"
assert "Cult Leader" not in citizen_chars, "Cult Leader MUST NOT be in Citizen Team!"
assert len(data.get("all_gems", [])) == 38, f"Expected 38 gems, got {len(data.get('all_gems', []))}"

cult_gem = cult_list[0]
print("Cult Leader gem details:")
print(f"  ID: {cult_gem['id']}")
print(f"  Name: {cult_gem['name']}")
print(f"  Character: {cult_gem['character']}")
print(f"  Team: {cult_gem['team']}")
print(f"  Levels count: {len(cult_gem['levels'])}")
print(f"  L1: {cult_gem['levels'][0]['name']} ({cult_gem['levels'][0]['cp']} CP)")
print(f"  L16: {cult_gem['levels'][15]['name']} ({cult_gem['levels'][15]['cp']} CP, {cult_gem['levels'][15]['gem_points']} Gem Points)")
print(f"  Linked card: {cult_gem.get('linked_card')}")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
