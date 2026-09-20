with open('realtime-agent/realtime_agent/app/session/orchestrator.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "import uuid" in line and "turn_id = str(uuid.uuid4())" in lines[i+1]:
        # Fix indentation
        lines[i] = "        import uuid\n"
        lines[i+1] = "        turn_id = str(uuid.uuid4())\n"

with open('realtime-agent/realtime_agent/app/session/orchestrator.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
