import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MetricsDisplay } from '../src/components/MetricsDisplay';

describe('MetricsDisplay', () => {
  it('renders without crashing', () => {
    const { container } = render(<MetricsDisplay metrics={{}} />);
    expect(container).toBeInTheDocument();
  });
});
