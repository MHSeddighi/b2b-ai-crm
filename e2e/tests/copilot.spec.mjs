import { test, expect } from '@playwright/test';

async function openCopilot(page) {
  await page.goto('/');
  await page.waitForTimeout(1200);
  const fab = page.locator('div.fixed.z-40.select-none').first();
  await fab.click();
  await page.waitForTimeout(800);
}

async function ask(page, question) {
  const input = page.getByPlaceholder(/بپرسید/i);
  await input.fill(question);
  await page.getByRole('button', { name: /ارسال/i }).click();
  // wait for the typing indicator to appear then disappear
  await page.waitForTimeout(500);
  await page.waitForSelector('aside .animate-bounce', { state: 'detached', timeout: 100000 }).catch(() => {});
  await page.waitForTimeout(500);
}

test.describe('Customer360 Copilot (live backend)', () => {
  test('opens and greets', async ({ page }) => {
    await openCopilot(page);
    const aside = page.locator('aside').last();
    await expect(aside).toContainText(/دستیار/i);
  });

  test('conversational greeting returns markdown block', async ({ page }) => {
    await openCopilot(page);
    await ask(page, 'hi');
    const aside = page.locator('aside').last();
    await expect(aside).toContainText(/سلام/i);
  });

  test('data question returns a chart block', async ({ page }) => {
    test.slow();
    await openCopilot(page);
    await ask(page, 'monthly sales trend');
    const aside = page.locator('aside').last();
    // a chart renders as an svg (recharts) inside the panel
    const svgCount = await aside.locator('svg').count();
    expect(svgCount).toBeGreaterThan(0);
    // and the panel has some analytical text
    await expect(aside).toContainText(/فروش|sales|revenue|month/i);
  });

  test('does not show the generic error on a chart request', async ({ page }) => {
    test.slow();
    await openCopilot(page);
    await ask(page, 'top customers by revenue');
    const aside = page.locator('aside').last();
    await expect(aside).not.toContainText('با عرض پوزش');
  });
});

test.describe('Multi-step chat', () => {
  test('follow-up keeps context and shows a customer card', async ({ page }) => {
    test.slow();
    await openCopilot(page);
    await ask(page, 'show me the top customers');
    const aside = page.locator('aside').last();
    // first answer renders (has some text)
    await expect(aside).toContainText(/مشتری|customer|فروش|revenue/i);

    // follow-up asking for a customer detail
    await ask(page, 'show me the top customer detail');
    await expect(aside).not.toContainText('با عرض پوزش');
    // a customer card block renders a Card with an id (C_...)
    await expect(aside.locator('text=/C_\\d+/').first()).toBeVisible({ timeout: 10000 });
  });
});
