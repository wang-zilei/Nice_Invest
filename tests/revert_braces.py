"""Step 1: Revert all doubled braces to single."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('src/agents/template.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Revert: {{ → {, }} → }
content = content.replace('{{', '{').replace('}}', '}')

# But don't touch { and } inside the build_system_prompt f-string
# which uses {var_name} for Python interpolation
# Let's just revert and then apply the JSON-block-only fix

with open('src/agents/template.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Step 1 done: reverted all braces to single')
