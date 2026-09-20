import { globalShortcut, desktopCapturer, BrowserWindow } from 'electron';

export function setupScreenshotCapture(mainWindow: BrowserWindow) {
  // Explicit, user-triggered single-shot capture. No continuous background recording.
  const registered = globalShortcut.register('CommandOrControl+Shift+S', async () => {
    try {
      console.log("User triggered explicit screen capture.");
      const sources = await desktopCapturer.getSources({ types: ['screen'], thumbnailSize: { width: 1920, height: 1080 } });
      
      if (sources.length > 0) {
        // Grab the primary screen thumbnail as a NativeImage data URL
        const dataUrl = sources[0].thumbnail.toDataURL();
        
        // Push buffer to the frontend to trigger the Study Workbench
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('screenshot.captureReady', dataUrl);
          console.log(`Captured image and sent to renderer.`);
        }
      }
    } catch (e) {
      console.error("Capture failed:", e);
    }
  });

  if (!registered) {
    console.error("Failed to register global shortcut for capture.");
  }
}

export function cleanupScreenshotCapture() {
  globalShortcut.unregister('CommandOrControl+Shift+S');
}
