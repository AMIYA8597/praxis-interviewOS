import os
import re

files = [
    'apps/web/src/app/(dashboard)/analytics/page.tsx',
    'apps/web/src/app/(dashboard)/candidates/page.tsx',
    'apps/web/src/app/(dashboard)/study/page.tsx',
    'apps/web/src/app/(dashboard)/platform/tracker/page.tsx',
    'apps/web/src/app/(dashboard)/settings/providers/page.tsx',
]

for file_path in files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # fix the shadow bug
    content = content.replace('shadow-lg shadow-black/50-xl shadow-lg shadow-black/50-black/50', 'shadow-xl shadow-black/50')
    content = content.replace('shadow-lg shadow-black/50-lg shadow-black/50-black/50', 'shadow-lg shadow-black/50')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
