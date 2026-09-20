import os

mappings = {
    'bg-white': 'bg-gray-900',
    'bg-gray-50': 'bg-gray-800',
    'bg-gray-100': 'bg-gray-800',
    'bg-gray-200': 'bg-gray-700',
    'text-gray-500': 'text-gray-400',
    'text-gray-600': 'text-gray-300',
    'text-gray-700': 'text-gray-300',
    'text-gray-800': 'text-gray-200',
    'text-gray-900': 'text-white',
    'border-gray-200': 'border-gray-800',
    ' border ': ' border border-gray-800 ',
    'border\"': 'border border-gray-800\"',
    'bg-indigo-50': 'bg-indigo-900/20',
    'bg-indigo-100': 'bg-indigo-900/30',
    'border-indigo-200': 'border-indigo-800',
    'text-indigo-600': 'text-indigo-400',
    'text-indigo-800': 'text-indigo-300',
    'text-indigo-900': 'text-indigo-200',
    'bg-blue-100': 'bg-blue-900/30',
    'text-blue-800': 'text-blue-300',
    'bg-yellow-50': 'bg-yellow-900/20',
    'border-yellow-400': 'border-yellow-600',
    'text-yellow-800': 'text-yellow-300',
    'bg-yellow-200': 'bg-yellow-800/50',
    'bg-red-50': 'bg-red-900/20',
    'bg-red-100': 'bg-red-900/30',
    'text-red-800': 'text-red-300',
    'border-red-200': 'border-red-800',
    'bg-green-100': 'bg-green-900/30',
    'text-green-800': 'text-green-300',
    'shadow-lg': 'shadow-xl shadow-black/50',
    'shadow': 'shadow-lg shadow-black/50',
    'border-b\"': 'border-b border-gray-800\"',
    'border-b ': 'border-b border-gray-800 ',
}

file_path = 'apps/web/src/app/(dashboard)/jobs/[id]/page.tsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

for old, new in mappings.items():
    content = content.replace(old, new)
    
# cleanup buggy mappings
content = content.replace('shadow-lg shadow-black/50-xl shadow-lg shadow-black/50-black/50', 'shadow-xl shadow-black/50')
content = content.replace('shadow-lg shadow-black/50-lg shadow-black/50-black/50', 'shadow-lg shadow-black/50')
content = content.replace('\"border p-4', '\"border border-gray-800 p-4')
content = content.replace(' bg-white\"', ' bg-gray-900\"')
content = content.replace('border-b border-gray-800 border-gray-800', 'border-b border-gray-800')
content = content.replace('border border-gray-800 border-indigo-800', 'border border-indigo-800')
content = content.replace('className=\"border p-2', 'className=\"border border-gray-800 bg-gray-900 p-2')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

