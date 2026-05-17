"""Fix template.py — double all braces inside JSON code blocks."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('src/agents/template.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
in_json_block = False
fixed_lines = []

for line in lines:
    if '```json' in line:
        in_json_block = True
        fixed_lines.append(line)
        continue
    if in_json_block and '```' in line:
        in_json_block = False
        fixed_lines.append(line)
        continue

    if in_json_block:
        fixed = line.replace('{', '{{').replace('}', '}}')
        fixed_lines.append(fixed)
    else:
        fixed_lines.append(line)

result = '\n'.join(fixed_lines)

with open('src/agents/template.py', 'w', encoding='utf-8') as f:
    f.write(result)

print('Done. Fixed JSON block braces in template.py')
