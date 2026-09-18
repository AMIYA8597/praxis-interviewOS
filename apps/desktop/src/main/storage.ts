import { safeStorage, app } from 'electron';
import path from 'path';
import fs from 'fs';

const STORAGE_FILE = path.join(app.getPath('userData'), 'storage.json');

export function saveCredential(key: string, value: string) {
  const encrypted = safeStorage.encryptString(value);
  let data: Record<string, string> = {};
  if (fs.existsSync(STORAGE_FILE)) {
    data = JSON.parse(fs.readFileSync(STORAGE_FILE, 'utf-8'));
  }
  data[key] = encrypted.toString('base64');
  fs.writeFileSync(STORAGE_FILE, JSON.stringify(data));
}

export function getCredential(key: string): string | null {
  if (!fs.existsSync(STORAGE_FILE)) return null;
  const data = JSON.parse(fs.readFileSync(STORAGE_FILE, 'utf-8'));
  if (!data[key]) return null;
  const encrypted = Buffer.from(data[key], 'base64');
  return safeStorage.decryptString(encrypted);
}
