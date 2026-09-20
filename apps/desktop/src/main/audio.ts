import { desktopCapturer, ipcMain } from 'electron';

export async function getAudioSources() {
  try {
    const sources = await desktopCapturer.getSources({ types: ['window', 'screen'] });
    const hasLoopback = sources.some(s => s.id.startsWith('loopback'));
    return { hasLoopback, sources: sources.map(s => ({ id: s.id, name: s.name })) };
  } catch (e) {
    console.error("Failed to enumerate desktop audio:", e);
    return { hasLoopback: false, sources: [] };
  }
}

export function setupAudioCapture() {
  // We'll leave the incoming event as 'audio-frame' or change it to match IPC if it's meant to be something else.
  // Wait, IPC doesn't specify renderer-to-main 'audio-frame', but let's keep it or rename it if needed.
  // Actually, 'audio.meterLevel' is what the Phase says to fix.
  ipcMain.on('audio-frame', (event, pcmData: Uint8Array, sequence: number, captureTimestamp: number) => {
    let sumSquares = 0;
    const view = new Int16Array(pcmData.buffer);
    for (let i = 0; i < view.length; i++) {
        sumSquares += view[i] * view[i];
    }
    const rms = Math.sqrt(sumSquares / view.length);
    event.sender.send('audio.meterLevel', rms);
  });
}
