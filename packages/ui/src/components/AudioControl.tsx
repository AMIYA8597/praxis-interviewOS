import React from 'react';

export interface AudioDeviceOption {
  deviceId: string;
  label: string;
}

export interface AudioControlProps {
  devices?: AudioDeviceOption[];
  selectedDeviceId?: string;
  onDeviceChange?: (deviceId: string) => void;
  isStreaming?: boolean;
  isMuted?: boolean;
  onToggleMute?: () => void;
  audioLevel?: number; // 0.0 to 1.0
  error?: string | null;
  onRetryPermission?: () => void;
  className?: string;
}

export const AudioControl: React.FC<AudioControlProps> = ({
  devices = [],
  selectedDeviceId = '',
  onDeviceChange,
  isStreaming = false,
  isMuted = false,
  onToggleMute,
  audioLevel = 0,
  error = null,
  onRetryPermission,
  className = '',
}) => {
  const levelPercent = Math.min(100, Math.max(0, Math.round(audioLevel * 100)));

  return (
    <div
      data-testid="audio-control"
      className={`p-4 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg shadow-sm ${className}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span
            data-testid="audio-status-dot"
            className={`w-2.5 h-2.5 rounded-full ${
              error
                ? 'bg-rose-500 animate-pulse'
                : isStreaming
                ? isMuted
                  ? 'bg-amber-400'
                  : 'bg-emerald-500 animate-pulse'
                : 'bg-zinc-400'
            }`}
          />
          <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-700 dark:text-zinc-300">
            Audio Input Setup
          </h4>
        </div>

        <span
          data-testid="audio-state-badge"
          className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
            error
              ? 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800'
              : isStreaming
              ? isMuted
                ? 'bg-amber-50 text-amber-700 border-amber-200'
                : 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800'
              : 'bg-zinc-100 text-zinc-600 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400'
          }`}
        >
          {error ? 'Error' : isStreaming ? (isMuted ? 'Muted' : 'Streaming') : 'Idle'}
        </span>
      </div>

      {error ? (
        <div data-testid="audio-error-banner" className="my-2 p-3 bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 rounded text-xs text-rose-800 dark:text-rose-200">
          <p className="font-semibold">{error}</p>
          <p className="mt-1 text-[11px] text-rose-600 dark:text-rose-300">
            Check browser/system microphone permissions and ensure an audio device is connected.
          </p>
          {onRetryPermission && (
            <button
              type="button"
              onClick={onRetryPermission}
              className="mt-2 px-2.5 py-1 bg-rose-600 text-white rounded text-xs font-medium hover:bg-rose-700 focus:outline-none"
            >
              Grant Microphone Permission
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {/* Device Selector */}
          <div>
            <label
              htmlFor="audio-device-select"
              className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1"
            >
              Microphone Device:
            </label>
            <select
              id="audio-device-select"
              data-testid="device-select"
              value={selectedDeviceId}
              onChange={(e) => onDeviceChange && onDeviceChange(e.target.value)}
              className="w-full text-xs bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-md px-2.5 py-1.5 text-zinc-900 dark:text-zinc-100 focus:ring-1 focus:ring-blue-500 focus:outline-none"
            >
              {devices.length === 0 ? (
                <option value="">Default Microphone</option>
              ) : (
                devices.map((dev) => (
                  <option key={dev.deviceId} value={dev.deviceId}>
                    {dev.label || `Microphone (${dev.deviceId.slice(0, 6)}...)`}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Level Meter & Mute Control */}
          <div className="flex items-center gap-3 pt-1">
            <div className="flex-1">
              <div className="flex justify-between text-[11px] text-zinc-500 mb-1">
                <span>Input Level</span>
                <span className="font-mono">{levelPercent}%</span>
              </div>
              <div
                role="progressbar"
                aria-valuenow={levelPercent}
                aria-valuemin={0}
                aria-valuemax={100}
                className="w-full bg-zinc-200 dark:bg-zinc-700 h-2 rounded-full overflow-hidden"
              >
                <div
                  data-testid="audio-level-bar"
                  className={`h-full transition-all duration-75 ${
                    isMuted
                      ? 'bg-zinc-400 w-0'
                      : levelPercent > 85
                      ? 'bg-rose-500'
                      : levelPercent > 60
                      ? 'bg-amber-500'
                      : 'bg-emerald-500'
                  }`}
                  style={{ width: isMuted ? '0%' : `${levelPercent}%` }}
                />
              </div>
            </div>

            {onToggleMute && (
              <button
                type="button"
                data-testid="toggle-mute-button"
                onClick={onToggleMute}
                aria-label={isMuted ? 'Unmute microphone' : 'Mute microphone'}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md border transition-colors ${
                  isMuted
                    ? 'bg-rose-50 text-rose-700 border-rose-300 dark:bg-rose-950/40 dark:text-rose-300 hover:bg-rose-100'
                    : 'bg-zinc-100 text-zinc-700 border-zinc-300 dark:bg-zinc-800 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700'
                }`}
              >
                {isMuted ? 'Unmute' : 'Mute'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
