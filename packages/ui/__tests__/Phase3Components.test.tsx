import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  EvidenceReference,
  ScoreDisplay,
  ReadinessCard,
  AudioControl,
} from '../src';
import type { ClaimGrounding, EvaluationScore, ReadinessResponse } from '@praxis/types';

describe('Phase 3 Shared UI Components', () => {
  describe('EvidenceReference', () => {
    it('renders supported claim with verified badge and confidence', () => {
      const claim: ClaimGrounding = {
        claim_text: 'Reduced p95 latency by 45% using Redis caching',
        classification: 'SUPPORTED',
        supported: true,
        confidence: 0.95,
        source_excerpt: 'deployed a Redis cluster that reduced 95th percentile latency by 45%',
      };

      render(<EvidenceReference claim={claim} />);

      expect(screen.getByText(/"Reduced p95 latency by 45% using Redis caching"/i)).toBeInTheDocument();
      expect(screen.getByTestId('classification-badge')).toHaveTextContent('Verified Fact');
      expect(screen.getByText('95%')).toBeInTheDocument();

      // Accordion toggle
      const toggleBtn = screen.getByRole('button', { name: /view grounded source excerpt/i });
      fireEvent.click(toggleBtn);

      expect(screen.getByTestId('evidence-excerpt')).toBeInTheDocument();
      expect(screen.getByText(/"deployed a Redis cluster that reduced 95th percentile latency by 45%"/i)).toBeInTheDocument();
    });

    it('renders contradicted claim with correct badge', () => {
      render(
        <EvidenceReference
          claimText="Scaled database to 10M QPS"
          classification="CONTRADICTED"
          confidence={0.88}
        />
      );

      expect(screen.getByTestId('classification-badge')).toHaveTextContent('Contradicted');
    });
  });

  describe('ScoreDisplay', () => {
    it('renders measured evaluation with 6 dimensions and STAR completeness', () => {
      const evaluation: EvaluationScore = {
        rubric_version: 'v1',
        measurement_status: 'MEASURED',
        overall: 0.85,
        relevance: 0.90,
        correctness: 0.88,
        structure: 0.82,
        specificity: 0.85,
        grounding: 0.92,
        conciseness: 0.75,
        rationale: 'Comprehensive explanation with solid architectural details.',
        star_completeness: {
          situation: true,
          task: true,
          action: true,
          result: false,
        },
      };

      render(<ScoreDisplay evaluation={evaluation} />);

      expect(screen.getByTestId('overall-score')).toHaveTextContent('85%');
      expect(screen.getByTestId('measurement-status-badge')).toHaveTextContent('MEASURED');
      expect(screen.getByTestId('dimension-relevance')).toHaveTextContent('90%');
      expect(screen.getByTestId('star-situation')).toHaveTextContent('Situation');
      expect(screen.getByTestId('star-result')).toHaveTextContent('Result');
      expect(screen.getByText(/"Comprehensive explanation with solid architectural details."/i)).toBeInTheDocument();
    });

    it('displays UNAVAILABLE when measurement failed without showing 0%', () => {
      render(
        <ScoreDisplay
          measurementStatus="UNAVAILABLE"
          overall={null}
          relevance={null}
        />
      );

      expect(screen.getByTestId('measurement-status-badge')).toHaveTextContent('UNAVAILABLE');
      expect(screen.getByTestId('overall-score')).toHaveTextContent('N/A');
      expect(screen.queryByText('0%')).not.toBeInTheDocument();
    });
  });

  describe('ReadinessCard', () => {
    it('renders insufficient evidence state when session count is 0', () => {
      const onStart = jest.fn();
      render(
        <ReadinessCard
          status="INSUFFICIENT_EVIDENCE"
          sessionCount={0}
          readinessScore={null}
          onStartSession={onStart}
        />
      );

      expect(screen.getByTestId('insufficient-evidence')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /start first practice session/i })).toBeInTheDocument();
      expect(screen.getByTestId('readiness-disclaimer')).toHaveTextContent(
        'PRAXIS Readiness Estimate is a calibrated preparatory indicator, not an employment guarantee.'
      );

      fireEvent.click(screen.getByRole('button', { name: /start first practice session/i }));
      expect(onStart).toHaveBeenCalledTimes(1);
    });

    it('renders calibrated readiness score and dimensions when measured', () => {
      const readiness: ReadinessResponse = {
        candidate_id: 'c123',
        status: 'MEASURED',
        session_count: 5,
        readiness_score: 0.82,
        disclaimer: 'PRAXIS Readiness Estimate is a calibrated preparatory indicator, not an employment guarantee.',
        dimensions: {
          system_design: { name: 'System Design', score: 0.85, confidence: 0.9 },
          communication: { name: 'Communication', score: 0.80, confidence: 0.88 },
        },
        recommended_actions: ['Improve conciseness in technical explanations'],
      };

      render(<ReadinessCard data={readiness} />);

      expect(screen.getByTestId('readiness-score-value')).toHaveTextContent('82%');
      expect(screen.getByTestId('readiness-dimension-system_design')).toHaveTextContent('85%');
      expect(screen.getByText('Improve conciseness in technical explanations')).toBeInTheDocument();
      expect(screen.getByTestId('readiness-disclaimer')).toBeInTheDocument();
    });
  });

  describe('AudioControl', () => {
    it('handles device selection, mute toggle, and volume meter', () => {
      const devices = [
        { deviceId: 'default', label: 'Default Microphone' },
        { deviceId: 'usb-mic', label: 'USB Condenser Mic' },
      ];
      const onDeviceChange = jest.fn();
      const onToggleMute = jest.fn();

      render(
        <AudioControl
          devices={devices}
          selectedDeviceId="default"
          onDeviceChange={onDeviceChange}
          isStreaming={true}
          isMuted={false}
          onToggleMute={onToggleMute}
          audioLevel={0.45}
        />
      );

      expect(screen.getByTestId('audio-state-badge')).toHaveTextContent('Streaming');
      expect(screen.getByTestId('audio-level-bar')).toHaveStyle('width: 45%');

      // Change device
      const select = screen.getByTestId('device-select');
      fireEvent.change(select, { target: { value: 'usb-mic' } });
      expect(onDeviceChange).toHaveBeenCalledWith('usb-mic');

      // Toggle mute
      const muteBtn = screen.getByTestId('toggle-mute-button');
      fireEvent.click(muteBtn);
      expect(onToggleMute).toHaveBeenCalledTimes(1);
    });

    it('displays error state and retry button when permission is denied', () => {
      const onRetry = jest.fn();
      render(
        <AudioControl
          error="Microphone permission was denied by the browser"
          onRetryPermission={onRetry}
        />
      );

      expect(screen.getByTestId('audio-error-banner')).toHaveTextContent(
        'Microphone permission was denied by the browser'
      );
      const retryBtn = screen.getByRole('button', { name: /grant microphone permission/i });
      fireEvent.click(retryBtn);
      expect(onRetry).toHaveBeenCalledTimes(1);
    });
  });
});
