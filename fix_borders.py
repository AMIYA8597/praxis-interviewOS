import os

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
    
    content = content.replace('\"border p-4', '\"border border-gray-800 p-4')
    content = content.replace(' bg-white\"', ' bg-gray-900\"')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
