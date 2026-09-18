import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Input } from '../src/components/Input';

describe('Input', () => {
  it('renders without crashing', () => {
    const { container } = render(<Input />);
    expect(container.firstChild).toBeInTheDocument();
  });
});
