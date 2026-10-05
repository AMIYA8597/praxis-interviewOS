import React, { useCallback, useRef, useState } from 'react';

interface CodingSandboxProps {
  language?: string;
  initialCode?: string;
  onCodeChange?: (code: string) => void;
  readOnly?: boolean;
}

const SUPPORTED_LANGUAGES = ['python', 'javascript', 'typescript', 'java', 'cpp', 'go', 'rust', 'sql'] as const;
type Language = typeof SUPPORTED_LANGUAGES[number];

export function CodingSandbox({
  language: initialLanguage = 'python',
  initialCode = '',
  onCodeChange,
  readOnly = false,
}: CodingSandboxProps) {
  const [code, setCode] = useState(initialCode);
  const [language, setLanguage] = useState<Language>(initialLanguage as Language);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const v = e.target.value;
      setCode(v);
      onCodeChange?.(v);
    },
    [onCodeChange],
  );

  // Tab key inserts 2 spaces instead of moving focus
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const el = e.currentTarget;
      const start = el.selectionStart;
      const end = el.selectionEnd;
      const next = code.substring(0, start) + '  ' + code.substring(end);
      setCode(next);
      onCodeChange?.(next);
      requestAnimationFrame(() => {
        el.selectionStart = start + 2;
        el.selectionEnd = start + 2;
      });
    }
  }, [code, onCodeChange]);

  return (
    <div className="coding-sandbox" style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#0d1117', border: '1px solid #30363d', borderRadius: 8 }}>
      {/* Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', borderBottom: '1px solid #21262d', background: '#161b22' }}>
        <select
          value={language}
          onChange={e => setLanguage(e.target.value as Language)}
          disabled={readOnly}
          style={{ background: '#0d1117', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: 4, padding: '2px 6px', fontSize: 12 }}
        >
          {SUPPORTED_LANGUAGES.map(l => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
        <span style={{ flex: 1 }} />
        <span style={{ color: '#8b949e', fontSize: 11 }}>
          {code.split('\n').length} lines
        </span>
      </div>

      {/* Editor area */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        {/* Line numbers */}
        <div
          aria-hidden
          style={{
            position: 'absolute', left: 0, top: 0, bottom: 0, width: 40,
            background: '#161b22', color: '#484f58', fontSize: 12, lineHeight: '20px',
            paddingTop: 8, paddingRight: 8, textAlign: 'right', userSelect: 'none', overflow: 'hidden',
            fontFamily: 'ui-monospace, monospace',
          }}
        >
          {code.split('\n').map((_, i) => (
            <div key={i}>{i + 1}</div>
          ))}
        </div>

        <textarea
          ref={textareaRef}
          value={code}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          readOnly={readOnly}
          spellCheck={false}
          data-testid="coding-sandbox-editor"
          style={{
            position: 'absolute', left: 40, right: 0, top: 0, bottom: 0,
            background: 'transparent', color: '#c9d1d9', border: 'none', outline: 'none',
            resize: 'none', fontFamily: 'ui-monospace, monospace', fontSize: 13, lineHeight: '20px',
            padding: '8px 12px', tabSize: 2,
          }}
        />
      </div>
    </div>
  );
}
