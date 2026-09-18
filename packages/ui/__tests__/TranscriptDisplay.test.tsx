import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TranscriptDisplay } from '../src/components/TranscriptDisplay';

describe('TranscriptDisplay', () => {
  it('renders without crashing', () => {
    const { getByTestId } = render(<TranscriptDisplay />);
    expect(getByTestId('transcriptdisplay')).toBeInTheDocument();
  });
});
