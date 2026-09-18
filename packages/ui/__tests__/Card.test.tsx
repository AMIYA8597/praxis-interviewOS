import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Card } from '../src/components/Card';

describe('Card', () => {
  it('renders without crashing', () => {
    const { container } = render(<Card />);
    expect(container.firstChild).toBeInTheDocument();
  });
});
