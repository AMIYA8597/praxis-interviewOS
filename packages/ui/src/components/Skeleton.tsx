import React from 'react';
export const Skeleton = ({ className = '' }: { className?: string }) => (
  <div className={`animate-pulse bg-gray-800 rounded ${className}`}></div>
);
