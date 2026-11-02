import { test, expect } from '@playwright/test';

const NOW = Math.floor(Date.now() / 1000);
const EXP = NOW + 7200;

// Valid JWT structure
const VALID_JWT = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJlbWFpbCI6ImNhbmRpZGF0ZUBwcmF4aXMtaW50ZXJ2aWV3LmNvbSIsImlhdCI6MTcwMDAwMDAwMCwiZXhwIjoyNTAwMDAwMDAwfQ.dummy_signature';

const MOCK_AUTH_STORAGE_KEY = 'sb-rqbbfegkqmsvthdgoyqk-auth-token';
const MOCK_SESSION_DATA = JSON.stringify({
  access_token: VALID_JWT,
  refresh_token: 'refresh-token-12345',
  expires_in: 7200,
  expires_at: 2500000000,
  token_type: 'bearer',
  user: {
    id: '00000000-0000-0000-0000-000000000001',
    aud: 'authenticated',
    role: 'authenticated',
    email: 'candidate@praxis-interview.com',
    created_at: '2026-01-01T00:00:00.000Z',
  },
});

test.describe('PRAXIS Candidate Journey & Frontend Verification', () => {

  test('1. Landing page renders branding, hero section, and get started CTA', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/PRAXIS InterviewOS/i);
    await expect(page.getByText('Master Technical Interviews Through Real-Time Speech Intelligence')).toBeVisible();
    await expect(page.getByRole('link', { name: /Get Started/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Sign In/i })).toBeVisible();
  });

  test('2. Auth page renders login and signup views', async ({ page }) => {
    await page.goto('/auth');
    await expect(page.getByRole('heading', { name: /Sign In/i })).toBeVisible();
    await expect(page.getByPlaceholder(/Email/i)).toBeVisible();
    await expect(page.getByPlaceholder(/Password/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /Sign In/i })).toBeVisible();
  });

  test('3. Onboarding page renders profile form and resume upload', async ({ page }) => {
    await page.goto('/onboarding');
    await expect(page.getByRole('heading', { name: /Complete Profile/i })).toBeVisible();
    await expect(page.getByLabel(/Full Name/i)).toBeVisible();
    await expect(page.getByText(/Upload Resume \(PDF\)/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /Save & Continue/i })).toBeVisible();
  });

  test('4. Unauthenticated dashboard access redirects securely to /auth', async ({ page }) => {
    await page.goto('/sessions');
    await expect(page).toHaveURL(/\/auth/);
    await expect(page.getByRole('heading', { name: /Sign In/i })).toBeVisible();
  });

  test.describe('Authenticated Dashboard Routes', () => {
    test.beforeEach(async ({ page }) => {
      page.on('console', (msg) => console.log('[BROWSER CONSOLE]', msg.type(), msg.text()));
      page.on('requestfailed', (req) => console.log('[REQ FAILED]', req.method(), req.url(), req.failure()?.errorText));

      // Intercept Supabase Auth
      await page.route('**/auth/v1/**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: '00000000-0000-0000-0000-000000000001',
            email: 'candidate@praxis-interview.com',
            role: 'authenticated',
            aud: 'authenticated',
          }),
        });
      });

      // Intercept all API v1 endpoints across any origin (including localhost:8000)
      await page.route((url) => url.href.includes('/api/v1/'), async (route) => {
        console.log('[ROUTE INTERCEPT]', route.request().method(), route.request().url());

        const corsHeaders = {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': '*',
        };

        if (route.request().method() === 'OPTIONS') {
          await route.fulfill({
            status: 204,
            headers: corsHeaders,
          });
          return;
        }

        const urlStr = route.request().url();
        const jsonHeaders = {
          'Content-Type': 'application/json',
          ...corsHeaders,
        };

        if (urlStr.includes('/api/v1/health/providers')) {
          await route.fulfill({
            status: 200,
            headers: jsonHeaders,
            body: JSON.stringify({
              status: 'ok',
              providers: {
                groq: {
                  capabilities: {
                    streaming: true,
                    structured_output: true,
                    vision: false,
                    embeddings: false,
                    is_local: false,
                    is_free_tier: true,
                  },
                  circuit_breaker_state: 'closed',
                },
                gemini: {
                  capabilities: {
                    streaming: true,
                    structured_output: true,
                    vision: true,
                    embeddings: true,
                    is_local: false,
                    is_free_tier: true,
                  },
                  circuit_breaker_state: 'closed',
                },
              },
            }),
          });
        } else if (urlStr.includes('/study/items')) {
          await route.fulfill({
            status: 200,
            headers: jsonHeaders,
            body: JSON.stringify({
              items: [],
              total: 0,
            }),
          });
        } else if (urlStr.includes('/debrief')) {
          await route.fulfill({
            status: 200,
            headers: jsonHeaders,
            body: JSON.stringify({
              id: '00000000-0000-0000-0000-000000000001',
              session_id: '00000000-0000-0000-0000-000000000001',
              headline_metrics: {
                average_score: 0.85,
                average_wpm: 140,
                filler_rate: 0.02,
                total_duration_s: 1200,
              },
              strengths: ['Clear systems architecture explanations', 'Structured problem solving'],
              weaknesses: ['Could quantify throughput and latency tradeoffs with concrete numbers'],
              recommendations: ['Practice calculating queries per second under peak load'],
              flagged_claims: [],
            }),
          });
        } else if (urlStr.includes('/turns')) {
          await route.fulfill({
            status: 200,
            headers: jsonHeaders,
            body: JSON.stringify([
              {
                id: '00000000-0000-0000-0000-000000000001',
                session_id: '00000000-0000-0000-0000-000000000001',
                turn_index: 0,
                speaker: 'interviewer',
                content: 'Welcome! How would you design a distributed key-value cache?',
                created_at: '2026-11-01T12:00:00Z',
              },
              {
                id: '00000000-0000-0000-0000-000000000002',
                session_id: '00000000-0000-0000-0000-000000000001',
                turn_index: 1,
                speaker: 'candidate',
                content: 'I would start by choosing consistent hashing for horizontal partitioning across nodes.',
                created_at: '2026-11-01T12:01:00Z',
              },
            ]),
          });
        } else if (urlStr.match(/\/api\/v1\/sessions\/[0-9a-f-]+/)) {
          // Single session details
          await route.fulfill({
            status: 200,
            headers: jsonHeaders,
            body: JSON.stringify({
              id: '00000000-0000-0000-0000-000000000001',
              candidate_id: '00000000-0000-0000-0000-000000000001',
              interview_type: 'technical',
              difficulty: 'senior',
              status: 'active',
              mode: 'practice',
              started_at: '2026-11-01T12:00:00Z',
              ended_at: null,
            }),
          });
        } else if (urlStr.includes('/api/v1/sessions')) {
          await route.fulfill({
            status: 200,
            headers: jsonHeaders,
            body: JSON.stringify({
              items: [
                {
                  id: '00000000-0000-0000-0000-000000000001',
                  candidate_id: '00000000-0000-0000-0000-000000000001',
                  interview_type: 'technical',
                  difficulty: 'senior',
                  status: 'completed',
                  mode: 'practice',
                  started_at: '2026-11-01T12:00:00Z',
                  ended_at: '2026-11-01T12:30:00Z',
                },
              ],
              total: 1,
            }),
          });
        } else {
          await route.fulfill({
            status: 200,
            headers: jsonHeaders,
            body: JSON.stringify({ ok: true }),
          });
        }
      });

      await page.addInitScript(({ key, val }) => {
        window.localStorage.setItem(key, val);
      }, { key: MOCK_AUTH_STORAGE_KEY, val: MOCK_SESSION_DATA });
    });

    test('5. Sessions dashboard renders creation controls and session list', async ({ page }) => {
      await page.goto('/sessions');
      await expect(page.getByRole('heading', { name: /Practice Sessions/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /Start.*Practice Session/i })).toBeVisible();
    });

    test('6. AI Providers settings page displays routing status and capabilities', async ({ page }) => {
      await page.goto('/settings/providers');
      await expect(page.getByRole('heading', { name: /AI Providers/i })).toBeVisible();
      await expect(page.getByText(/Provider routing and health status/i)).toBeVisible();
    });

    test('7. Study & revision page renders preparation view', async ({ page }) => {
      await page.goto('/study');
      await expect(page.getByRole('heading', { name: /Study/i })).toBeVisible();
    });

    test('8. Readiness dashboard renders metrics breakdown', async ({ page }) => {
      await page.goto('/readiness');
      await expect(page.getByRole('heading', { name: /Interview Readiness/i })).toBeVisible();
    });

    test('9. Live session room renders audio controls and prompt container', async ({ page }) => {
      const testSessionId = '00000000-0000-0000-0000-000000000001';
      await page.goto(`/sessions/${testSessionId}`);
      await expect(page.getByRole('heading', { name: /Live Practice Interview Arena/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /Conclude Session/i })).toBeVisible();
    });

    test('10. Session debrief page renders metrics container', async ({ page }) => {
      const testSessionId = '00000000-0000-0000-0000-000000000001';
      await page.goto(`/sessions/${testSessionId}/debrief`);
      await expect(page.getByRole('heading', { name: /Interview Debrief/i })).toBeVisible();
    });
  });

});
