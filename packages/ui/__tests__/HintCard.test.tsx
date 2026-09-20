import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { HintCard } from '../src/components/HintCard';

describe('HintCard', () => {
  it('renders without crashing', () => {
    const { getByText } = render(<HintCard hint="Test hint" level={1} />);
    expect(getByText('Test hint')).toBeInTheDocument();
  });
});
