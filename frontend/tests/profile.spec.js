const { test, expect } = require('@playwright/test');

test.describe('Profile Tests', () => {

    test.beforeEach(async ({ page }) => {
        // Set Auth State
        await page.addInitScript(() => {
            localStorage.setItem('token', 'mock-token-profile');
            localStorage.setItem('username', 'adventurer99');
        });

        // Mock Profile API
        await page.route('**/api/profile/adventurer99', async route => {
            if (route.request().method() === 'GET') {
                const json = {
                    status: 'success',
                    data: {
                        username: 'adventurer99',
                        email: 'hero@guild.com',
                        score: 15300,
                        rank: 'Gold Rank ✦'
                    }
                };
                await route.fulfill({ json });
            } else if (route.request().method() === 'DELETE') {
                const json = { status: 'success', message: 'Account deleted' };
                await route.fulfill({ json });
            }
        });
    });

    test('should render profile data correctly', async ({ page }) => {
        await page.goto('/profile.html');

        // Check specific DOM elements that get updated by fetch API
        await expect(page.locator('#displayUsername')).toHaveText('adventurer99');
        await expect(page.locator('#displayEmail')).toHaveText('hero@guild.com');
        await expect(page.locator('#displayScore')).toHaveText('15300');
        await expect(page.locator('#displayRank')).toHaveText('Gold Rank ✦');

        // Check if the rank icon was dynamically updated to point to the clean rank name (goldrank)
        await expect(page.locator('#rankIcon')).toHaveAttribute('src', 'images/rank_goldrank.png');
        await expect(page.locator('#rankIcon')).toBeVisible();
    });

    test('should allow user to delete account', async ({ page }) => {
        await page.goto('/profile.html');

        // Handle window.confirm and window.alert dialogs
        page.on('dialog', async dialog => {
            // Check if it's the confirm dialog or the success alert
            const msg = dialog.message();
            if (msg.includes('คุณแน่ใจหรือไม่ว่าต้องการลบบัญชีนี้')) {
                await dialog.accept();
            } else if (msg.includes('ลบบัญชีเรียบร้อยแล้ว')) {
                await dialog.accept();
            } else {
                await dialog.accept(); // dismiss or accept other unexpected dialogs
            }
        });

        // Click the delete button
        const deleteBtn = page.locator('#deleteAccountBtn');
        await deleteBtn.click();

        // System should redirect to login.html
        await expect(page).toHaveURL(/.*login\.html/);
    });
});
