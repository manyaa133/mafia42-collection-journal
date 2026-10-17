import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('frontend/src/App.tsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines in App.tsx: {len(lines)}")

button_instances = []
current_btn = []
in_button = False
btn_start_line = 0

for idx, line in enumerate(lines, 1):
    if '<button' in line:
        in_button = True
        btn_start_line = idx
        current_btn = [line]
        if '</button>' in line or '/>' in line:
            button_instances.append((btn_start_line, "".join(current_btn)))
            in_button = False
    elif in_button:
        current_btn.append(line)
        if '</button>' in line or '/>' in line:
            button_instances.append((btn_start_line, "".join(current_btn)))
            in_button = False

print(f"Found {len(button_instances)} button instances in App.tsx.")

print("\n--- Summary of button elements ---")
for line_no, btn_code in button_instances:
    # extract className
    m = re.search(r'className=["`\']([^"`\']+)["`\']', btn_code)
    cls = m.group(1) if m else "NO_CLASS"
    # extract button text/snippet
    clean_snippet = " ".join(btn_code.split())[:120]
    print(f"Line {line_no:4d} | Class: {cls:35s} | Snippet: {clean_snippet}")

