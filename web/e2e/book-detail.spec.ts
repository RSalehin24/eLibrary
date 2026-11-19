import { expect, test, type Page } from '@playwright/test';

const AXE_SOURCE = require.resolve('axe-core/axe.min.js');
const BLOCKING_IMPACTS = ['serious', 'critical'];

interface AxeViolation {
  id: string;
  impact: string | null;
}
interface AxeResult {
  violations: AxeViolation[];
}
interface AxeWindow {
  axe: { run: () => Promise<AxeResult> };
}

async function blockingViolations(page: Page): Promise<string[]> {
  await page.addScriptTag({ path: AXE_SOURCE });
  const result = await page.evaluate(() => (globalThis as unknown as AxeWindow).axe.run());
  return result.violations
    .filter((violation) => BLOCKING_IMPACTS.includes(violation.impact ?? ''))
    .map((violation) => `${violation.id} (${violation.impact})`);
}

const configurations = [
  { name: 'light desktop', colorScheme: 'light', viewport: { width: 1280, height: 800 } },
  { name: 'dark desktop', colorScheme: 'dark', viewport: { width: 1280, height: 800 } },
  { name: 'mobile', colorScheme: 'light', viewport: { width: 375, height: 667 } },
] as const;

for (const configuration of configurations) {
  test.describe(configuration.name, () => {
    test.use({ colorScheme: configuration.colorScheme, viewport: configuration.viewport });

    test('book page has no serious or critical accessibility violations', async ({ page }) => {
      await page.goto('/books/bangla-bhasha');
      await expect(page.getByRole('heading', { name: 'বাংলা ভাষা' }).or(page.getByText('বাংলা ভাষা').first())).toBeVisible();
      expect(await blockingViolations(page)).toEqual([]);
    });
  });
}

test('page title and description come from the server and hydration logs no errors', async ({ page }) => {
  const problems: string[] = [];
  page.on('console', (message) => {
    if (['error', 'warning'].includes(message.type())) {
      problems.push(message.text());
    }
  });
  const response = await page.request.get('/books/bangla-bhasha');
  const html = await response.text();
  expect(html).toContain('<title>বাংলা ভাষা — নমুনা লেখক</title>');
  expect(html).toContain('<meta name="description"');
  await page.goto('/books/bangla-bhasha');
  await page.waitForLoadState('networkidle');
  expect(problems).toEqual([]);
});
