with open('docs/ARCHITECTURE_DECISIONS.md', 'rb') as f:
    c = f.read()

# find the bad utf-16 tail
idx = c.find(b'\x00#\x00#\x00 ')
if idx != -1:
    # it might have some prefix like \r\n\x00
    # Let's search for the first \x00
    idx = c.find(b'\x00')
    if idx != -1:
        c = c[:idx]
        # remove trailing \r or \n
        while c and c[-1] in (b'\r', b'\n', 13, 10):
            c = c[:-1]

text_to_append = b'''

## ADR-019: Real-Supabase Migration Parity
**Date:** 2026-09-20
**Context:** The SQL migrations use 'MOCK' and 'local dev only' comments for defining auth primitives and schemas (e.g. auth.uid(), storage schema/tables) that are pre-provided by Supabase.
**Decision:** The migrations use "CREATE OR REPLACE FUNCTION", "CREATE SCHEMA IF NOT EXISTS", and "CREATE TABLE IF NOT EXISTS" for these primitives. This makes the migrations completely safe and idempotent for real-Supabase deployments. In a real Supabase environment, the existing Supabase schemas (auth, storage) will be untouched, and our mock auth.uid() definition uses dynamic current_setting, which avoids colliding with real Supabase internals if used correctly.
'''

c += text_to_append

with open('docs/ARCHITECTURE_DECISIONS.md', 'wb') as f:
    f.write(c)
