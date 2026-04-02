const { test, expect } = require('@playwright/test');

test.describe('Battle Game Tests', () => {
    test.beforeEach(async ({ page }) => {
        // Set up mock auth state
        await page.addInitScript(() => {
            localStorage.setItem('token', 'mock-token');
            localStorage.setItem('username', 'testhero');
        });

        // Mock the enemy question API
        await page.route('**/api/get_word', async route => {
            const json = {
                word: 'Apple',
                answer: 'แอปเปิ้ล',
                options: ['กล้วย', 'แอปเปิ้ล', 'ส้ม', 'แตงโม']
            };
            await route.fulfill({ json });
        });
    });

    test('should render battle scene correctly', async ({ page }) => {
        await page.goto('/test.html');

        // Ensure boss details are visible
        await expect(page.locator('.target-name')).toHaveText('Shadow Demon Lord');
        await expect(page.locator('#word-display')).toHaveText('Apple');

        // Ensure 4 options are rendered
        await expect(page.locator('.action-btn')).toHaveCount(4);
    });

    test('should deal damage to boss on correct answer', async ({ page }) => {
        await page.goto('/test.html');

        // Read initial boss HP
        const bossHpText = page.locator('#boss-hp-text');
        await expect(bossHpText).toHaveText('100');

        // Wait for the options to be rendered
        const correctBtn = page.locator('.action-btn', { hasText: 'แอปเปิ้ล' });
        await expect(correctBtn).toBeVisible();

        // Click correct answer
        await correctBtn.click();

        // Boss HP should decrease (base dmg is 25, multiplied by speed bonus which could be 1.5, making it 100 - 37 = 63, or 100 - 30 = 70)
        // The HP should be literally anything less than 100
        await expect(bossHpText).not.toHaveText('100');

        // Combo counter should appear after multiple correct answers, let's just make sure damage text popped up
        await expect(page.locator('#dmg-boss')).not.toBeEmpty();
    });

    test('should lose HP on incorrect answer', async ({ page }) => {
        await page.goto('/test.html');

        // Player starts with 9999 HP
        const playerHpText = page.locator('.hp-text').filter({ hasText: '9999 / 9999' });
        await expect(playerHpText).toBeVisible();

        const wrongBtn = page.locator('.action-btn', { hasText: 'กล้วย' });
        await expect(wrongBtn).toBeVisible();

        // Click wrong answer
        await wrongBtn.click();

        // Player takes damage and modal shows up, HP should be subtracted by 1500 -> 8499
        const newPlayerHp = page.locator('.hp-text').filter({ hasText: '8499 / 9999' });
        await expect(newPlayerHp).toBeVisible();

        // Wrong modal appears
        await expect(page.locator('#wrongModal')).toHaveClass(/active/);
        await expect(page.locator('#correct-answer-display')).toHaveText('แอปเปิ้ล');
    });
});
