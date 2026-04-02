const { test, expect } = require('@playwright/test');

test.describe('Authentication Tests', () => {
    test('should render the login page correctly', async ({ page }) => {
        await page.goto('/login.html');

        // Check if main elements are visible
        await expect(page.locator('h1')).toHaveText('Login');
        await expect(page.locator('#username')).toBeVisible();
        await expect(page.locator('#password')).toBeVisible();
        await expect(page.locator('#submitBtn')).toBeVisible();
    });

    test('should show error message on invalid credentials', async ({ page }) => {
        // Mock the API response for failed login
        await page.route('**/api/login', async route => {
            const json = { status: 'error', message: 'Invalid username or password' };
            await route.fulfill({ json });
        });

        await page.goto('/login.html');

        await page.fill('#username', 'wronguser');
        await page.fill('#password', 'wrongpass');
        await page.click('#submitBtn');

        // System message should display the error
        const sysMsg = page.locator('#systemMessage');
        await expect(sysMsg).toBeVisible();
        await expect(sysMsg).toContainText('Invalid username or password');
    });

    test('should redirect to index on successful login', async ({ page }) => {
        // Mock the API response for successful login
        await page.route('**/api/login', async route => {
            const json = { status: 'success', token: 'mock-token-123', username: 'testuser' };
            await route.fulfill({ json });
        });

        await page.goto('/login.html');

        await page.fill('#username', 'testuser');
        await page.fill('#password', 'password123');
        await page.click('#submitBtn');

        // Should redirect to index.html
        await expect(page).toHaveURL(/.*index\.html/);

        // Verify localStorage was set
        const token = await page.evaluate(() => localStorage.getItem('token'));
        const username = await page.evaluate(() => localStorage.getItem('username'));
        expect(token).toBe('mock-token-123');
        expect(username).toBe('testuser');
    });
});
