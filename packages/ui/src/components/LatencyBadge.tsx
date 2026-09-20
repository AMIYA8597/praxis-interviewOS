import React from 'react';
export const LatencyBadge = ({ ms }: { ms: number }) => {
  const color = ms < 200 ? 'text-green-400' : ms < 500 ? 'text-yellow-400' : 'text-red-400';
  return <span className={`text-xs px-2 py-1 bg-gray-800 rounded ${color}`}>{ms}ms</span>;
};
