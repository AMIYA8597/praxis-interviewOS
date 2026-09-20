import fs from 'fs';
import path from 'path';

describe('Next.js Directory Consolidation', () => {
  it('apps/web/app/ does not exist', () => {
    const oldAppDir = path.join(__dirname, '../../web/app');
    expect(fs.existsSync(oldAppDir)).toBe(false);
  });

  it('target structure exists in src/app', () => {
    const srcAppDir = path.join(__dirname, '../../web/src/app');
    expect(fs.existsSync(srcAppDir)).toBe(true);
    expect(fs.existsSync(path.join(srcAppDir, '(dashboard)/layout.tsx'))).toBe(true);
    expect(fs.existsSync(path.join(srcAppDir, '(dashboard)/analytics/page.tsx'))).toBe(true);
    expect(fs.existsSync(path.join(srcAppDir, 'auth/page.tsx'))).toBe(true);
  });
});
