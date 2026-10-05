import glob, re

files = [
    'realtime-agent/realtime_agent/app/interview/debrief.py',
    'realtime-agent/realtime_agent/app/interview/policy.py',
    'realtime-agent/realtime_agent/app/interview/turn_detection.py',
    'realtime-agent/realtime_agent/app/scoring/claims.py',
    'realtime-agent/realtime_agent/app/scoring/service.py',
    'realtime-agent/realtime_agent/app/study/solver.py',
    'backend/app/services/solvers.py',
    'packages/ai-gateway/praxis_ai_gateway/classification.py'
]

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace("from praxis_config.settings import PROJECT_ROOT", "from packages.config.settings import PROJECT_ROOT")
    if 'PROJECT_ROOT' not in content:
        content = 'from packages.config.settings import PROJECT_ROOT\n' + content
        
    content = re.sub(r'"prompts/([^"]+)"', r'str(PROJECT_ROOT / "prompts/\1")', content)
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)

with open('packages/config/settings.py', 'r', encoding='utf-8') as f:
    settings_content = f.read()
settings_content = settings_content.replace('\x00', '')
if 'PROJECT_ROOT' not in settings_content:
    settings_content += '\nimport os\nimport pathlib\nPROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent\n'
with open('packages/config/settings.py', 'w', encoding='utf-8') as f:
    f.write(settings_content)

