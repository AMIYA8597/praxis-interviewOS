import { test, expect } from '@playwright/test';

test('has title', async ({ page }) => {
  await page.goto('/');

  // Expect a title to contain PRAXIS
  await expect(page).toHaveTitle(/PRAXIS/i);
});

test('get started link navigates to auth', async ({ page }) => {
  await page.goto('/');

  // Click the get started link.
  await page.getByRole('link', { name: /Get Started/i }).click();

  // Expect navigation to auth with Sign In heading
  await expect(page).toHaveURL(/\/auth/);
  await expect(page.getByRole('heading', { name: /Sign In/i })).toBeVisible();
});

test('onboarding page renders complete profile heading', async ({ page }) => {
  await page.goto('/onboarding');
  await expect(page.getByRole('heading', { name: /Complete Profile/i })).toBeVisible();
});
