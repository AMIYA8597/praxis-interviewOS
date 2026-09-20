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
    
    content = content.replace('border-b border-gray-800 border-gray-800', 'border-b border-gray-800')
    content = content.replace('border border-gray-800 border-indigo-800', 'border border-indigo-800')
    content = content.replace('className=\"border p-2', 'className=\"border border-gray-800 bg-gray-900 p-2')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
