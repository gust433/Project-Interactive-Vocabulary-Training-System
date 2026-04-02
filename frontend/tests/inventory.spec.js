const { test, expect } = require('@playwright/test');

test.describe('Inventory / Dictionary Tests', () => {

    test.beforeEach(async ({ page }) => {
        // Set Auth State
        await page.addInitScript(() => {
            localStorage.setItem('token', 'mock-token-inventory');
            localStorage.setItem('username', 'hero123');
        });

        // Mock the API response to get the user's dictionary/inventory
        await page.route('**/api/mydict/hero123', async route => {
            const json = {
                status: 'success',
                data: [
                    { id: 1, vocab: 'Sword', meaning: 'ดาบ', note: 'อาวุธเริ่มต้น' },
                    { id: 2, vocab: 'Shield', meaning: 'โล่', note: '' },
                    { id: 3, vocab: 'Potion', meaning: 'ยาฟื้นพลัง', note: 'ห้ามกินเกินวันละ 2 ขวด' }
                ]
            };
            await route.fulfill({ json });
        });
    });

    test('should render inventory items correctly', async ({ page }) => {
        await page.goto('/mydict.html');

        // Title should be correctly set
        await expect(page.locator('h1')).toHaveText('Inventory');

        // Table should contain 3 rows representing our items
        await expect(page.locator('#dict-body tr')).toHaveCount(3);

        // Check specific content in the DOM
        await expect(page.locator('#dict-body')).toContainText('Sword');
        await expect(page.locator('#dict-body')).toContainText('ยาฟื้นพลัง');

        // Verify if note is correctly pre-populated
        const swordNote = page.locator('.note-box').first();
        await expect(swordNote).toHaveValue('อาวุธเริ่มต้น');
    });

    test('should filter items using the search box', async ({ page }) => {
        await page.goto('/mydict.html');

        const searchInput = page.locator('#searchInput');

        // Search for "Sword"
        await searchInput.fill('Sword');
        await searchInput.press('Enter'); // Trigger keyup event
        await expect(page.locator('#dict-body tr')).toHaveCount(1);
        await expect(page.locator('#dict-body')).toContainText('Sword');

        // Search for "ยา"
        await searchInput.fill('ยา');
        await searchInput.press('Enter');
        await expect(page.locator('#dict-body tr')).toHaveCount(1);
        await expect(page.locator('#dict-body')).toContainText('Potion');

        // Search for non-existent item
        await searchInput.fill('Bow');
        await searchInput.press('Enter');
        await expect(page.locator('#dict-body')).toContainText('( Inventory is Empty )');
    });

    test('should open delete modal and remove item', async ({ page }) => {
        // Mock the DELETE API
        await page.route('**/api/mydict/1', async route => {
            if (route.request().method() === 'DELETE') {
                const json = { status: 'success', message: 'Deleted' };
                await route.fulfill({ json });
            }
        });

        await page.goto('/mydict.html');

        const firstDeleteBtn = page.locator('.btn-toss').first();

        // Click delete on Sword
        await firstDeleteBtn.click();

        // Modal should appear
        const modal = page.locator('#tossModal');
        await expect(modal).toHaveClass(/active/);
        await expect(page.locator('#tossDesc')).toContainText('Sword');

        // Confirm deletion
        const confirmBtn = page.locator('.btn-modal.confirm');
        await confirmBtn.click();

        // Modal should disappear and row count should be 2
        await expect(modal).not.toHaveClass(/active/);
        await expect(page.locator('#dict-body tr')).toHaveCount(2);
        await expect(page.locator('#dict-body')).not.toContainText('Sword');
    });

    test('should trigger save note API on blur', async ({ page }) => {
        let noteSaved = false;
        let savedNoteText = '';

        // Mock the POST API for saving note
        await page.route('**/api/save_note/2', async route => {
            const payload = JSON.parse(route.request().postData());
            noteSaved = true;
            savedNoteText = payload.note;

            const json = { status: 'success' };
            await route.fulfill({ json });
        });

        await page.goto('/mydict.html');

        // Find the note box for the second item ( Shield )
        const shieldNoteBox = page.locator('.note-box').nth(1);

        // Fill the note and trigger blur (lose focus)
        await shieldNoteBox.fill('โล่ป้องกันเวทย์');
        // Blur can be triggered by pressing Tab or dispatching event
        await shieldNoteBox.press('Tab');

        // Assert that the API was called with the correct note
        await page.waitForTimeout(500); // small delay to allow fetch promise to resolve
        expect(noteSaved).toBe(true);
        expect(savedNoteText).toBe('โล่ป้องกันเวทย์');
    });
});
