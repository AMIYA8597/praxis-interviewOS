import React from 'react';
import { render } from '@testing-library/react';
import { ErrorState } from '../src/components/ErrorState';
import { EmptyState } from '../src/components/EmptyState';
import { Skeleton } from '../src/components/Skeleton';
import { StatusIndicator } from '../src/components/StatusIndicator';
import { LatencyBadge } from '../src/components/LatencyBadge';
import { ProviderBadge } from '../src/components/ProviderBadge';
import '@testing-library/jest-dom';

describe('New UI Components', () => {
  it('renders ErrorState', () => {
    const { getByText } = render(<ErrorState message="Test error" />);
    expect(getByText('Test error')).toBeInTheDocument();
  });
  it('renders EmptyState', () => {
    const { getByText } = render(<EmptyState message="Nothing here" />);
    expect(getByText('Nothing here')).toBeInTheDocument();
  });
  it('renders Skeleton', () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveClass('animate-pulse');
  });
  it('renders StatusIndicator', () => {
    const { container } = render(<StatusIndicator status="online" />);
    expect(container.firstChild).toHaveClass('bg-green-500');
  });
  it('renders LatencyBadge', () => {
    const { getByText } = render(<LatencyBadge ms={150} />);
    expect(getByText('150ms')).toBeInTheDocument();
  });
  it('renders ProviderBadge', () => {
    const { getByText } = render(<ProviderBadge provider="openai" />);
    expect(getByText('openai')).toBeInTheDocument();
  });
});
