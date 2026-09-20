import React from 'react';
export const ProviderBadge = ({ provider }: { provider: string }) => (
  <span className="text-xs px-2 py-1 bg-blue-900 text-blue-100 rounded border border-blue-800 uppercase tracking-wide">
    {provider}
  </span>
);
