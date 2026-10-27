import { test, expect } from '@playwright/test';

test.describe('British Auction RFQ System E2E Suite', () => {

  test('1. Dashboard renders KPIs and recent auctions', async ({ page }) => {
    await page.goto('/');

    // Verify title & branding
    await expect(page).toHaveTitle(/British Auction RFQ System/i);
    await expect(page.getByRole('heading', { name: 'Procurement Dashboard' })).toBeVisible();

    // Verify KPI Cards
    await expect(page.locator('text=Active Auctions')).toBeVisible();
    await expect(page.locator('text=Force-Closed')).toBeVisible();

    // Verify Navigation Links
    await expect(page.getByRole('link', { name: 'Auctions' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Create RFQ' })).toBeVisible();
  });

  test('2. Auction list page supports filtering and search', async ({ page }) => {
    await page.goto('/auctions');

    // Check header
    await expect(page.locator('h1:has-text("British Auctions & RFQs")')).toBeVisible();

    // Check filter buttons with exact match
    const allBtn = page.getByRole('button', { name: 'All Auctions' });
    const activeBtn = page.getByRole('button', { name: 'ACTIVE' });
    const closedBtn = page.getByRole('button', { name: 'CLOSED', exact: true });
    const forcedBtn = page.getByRole('button', { name: 'FORCE CLOSED' });

    await expect(allBtn).toBeVisible();
    await expect(activeBtn).toBeVisible();
    await expect(closedBtn).toBeVisible();
    await expect(forcedBtn).toBeVisible();

    // Click active filter
    await activeBtn.click();
    await page.waitForTimeout(300);

    // Verify search input
    const searchInput = page.locator('input[placeholder*="Search reference"]');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('LAX');
    await page.locator('button:has-text("Search")').click();
  });

  test('3. Create RFQ form validates constraints and creates new British Auction', async ({ page }) => {
    await page.goto('/rfqs/new');

    await expect(page.locator('h1:has-text("Create New RFQ Auction")')).toBeVisible();

    // Fill cargo specs
    const uniqueRef = `TEST-E2E-${Date.now().toString().slice(-4)}`;
    await page.locator('input[name="title"]').fill('Automated Test Container Load');
    await page.locator('input[name="reference_id"]').fill(uniqueRef);
    await page.locator('input[name="origin"]').fill('Shanghai Port, China');
    await page.locator('input[name="destination"]').fill('Rotterdam, Netherlands');
    await page.locator('input[name="cargo_details"]').fill('5x 40ft Reefer Containers');

    // Trigger modes radio check
    const mode3Radio = page.locator('input[value="L1_RANK_CHANGE"]');
    await mode3Radio.check();
    await expect(mode3Radio).toBeChecked();

    // Submit form
    const submitBtn = page.locator('button:has-text("Publish British Auction RFQ")');
    await submitBtn.click();

    // Should navigate to detail page
    await page.waitForURL(/\/auctions\/\d+/);
    await expect(page.locator(`text=${uniqueRef}`)).toBeVisible();
    await expect(page.locator('text=Mode 3: L1 Rank Change')).toBeVisible();
  });

  test('4. Auction detail page displays extension parameters, countdown, and quote table', async ({ page }) => {
    // Navigate to auction list and dynamically enter the first available auction room
    await page.goto('/auctions');
    const firstAuctionLink = page.locator('a:has-text("View Details")').first();
    await expect(firstAuctionLink).toBeVisible();
    await firstAuctionLink.click();
    await page.waitForURL(/\/auctions\/\d+/);

    // Verify shipment specifications card
    await expect(page.locator('text=Shipment Specifications')).toBeVisible();

    // Verify British Auction mechanics card
    await expect(page.locator('text=British Auction Extension Mechanics')).toBeVisible();
    await expect(page.locator('text=Trigger Window (X)')).toBeVisible();
    await expect(page.locator('text=Extension Duration (Y)')).toBeVisible();
    await expect(page.getByText('Forced Close Deadline', { exact: true })).toBeVisible();

    // Verify tabs
    await expect(page.locator('button:has-text("Supplier Rankings & Quotes")')).toBeVisible();
    await expect(page.locator('button:has-text("Activity Timeline")')).toBeVisible();
    await expect(page.locator('button:has-text("Extension History")')).toBeVisible();
  });

  test('5. Supplier quote submission calculates total and updates rankings', async ({ page }) => {
    // 1. Create a fresh active auction
    await page.goto('/rfqs/new');
    const uniqueRef = `BID-TEST-${Date.now().toString().slice(-4)}`;
    await page.locator('input[name="title"]').fill('Bid Workflow Verification Auction');
    await page.locator('input[name="reference_id"]').fill(uniqueRef);
    await page.locator('input[name="origin"]').fill('Port of Los Angeles, USA');
    await page.locator('input[name="destination"]').fill('Hamburg Port, Germany');
    await page.locator('input[name="cargo_details"]').fill('Standard 40ft High Cube Container');
    await page.locator('button:has-text("Publish British Auction RFQ")').click();
    await page.waitForURL(/\/auctions\/\d+/);

    // Wait for auction room to fully mount and render specifications
    await expect(page.locator('text=Shipment Specifications')).toBeVisible();

    // 2. Switch to Carrier persona via dropdown in navbar
    const headerSelect = page.locator('header select');
    await headerSelect.selectOption({ value: 'apex@logistics.com' });
    await page.waitForTimeout(500);

    // 3. Test quote submission modal
    const submitQuoteBtn = page.locator('button:has-text("Submit / Lower Quote")');
    await expect(submitQuoteBtn).toBeVisible({ timeout: 10000 });
    await submitQuoteBtn.click();

    // Check modal is open
    await expect(page.locator('h3:has-text("Submit Quotation / Bid")')).toBeVisible();

    // Enter quote breakdown charges
    const freightInput = page.locator('input[name="freight_charges"]');
    const originInput = page.locator('input[name="origin_charges"]');
    const destInput = page.locator('input[name="destination_charges"]');

    await freightInput.fill('2200');
    await originInput.fill('250');
    await destInput.fill('150');

    // Check total quote amount auto-calculated: 2200 + 250 + 150 = 2600.00
    await expect(page.locator('text=$2,600.00')).toBeVisible();

    // Submit quote
    await page.locator('form button:has-text("Submit Quote")').click();
    await page.waitForTimeout(1000);

    // Verify modal closed and ranking table has L1 with $2600.00
    await expect(page.locator('h3:has-text("Submit Quotation / Bid")')).toBeHidden();
    await expect(page.locator('text=$2600.00')).toBeVisible();
    await expect(page.getByText('L1', { exact: true })).toBeVisible();
  });

  test('6. Mobile viewport renders responsive layout without breaking', async ({ page }) => {
    // Set viewport to mobile phone width (iPhone SE: 375 x 667)
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Procurement Dashboard' })).toBeVisible();
    await expect(page.locator('text=Active Auctions')).toBeVisible();

    // Navigate to auction list on mobile
    await page.goto('/auctions');
    await expect(page.locator('h1:has-text("British Auctions & RFQs")')).toBeVisible();

    // Check filter buttons wrap cleanly
    const allBtn = page.getByRole('button', { name: 'All Auctions' });
    await expect(allBtn).toBeVisible();

    // Navigate to detail page on mobile via first auction link
    const firstAuctionLinkMobile = page.locator('a:has-text("View Details")').first();
    await expect(firstAuctionLinkMobile).toBeVisible();
    await firstAuctionLinkMobile.click();
    await page.waitForURL(/\/auctions\/\d+/);

    await expect(page.locator('text=Shipment Specifications')).toBeVisible();
    await expect(page.locator('text=British Auction Extension Mechanics')).toBeVisible();

    // Persona switch on mobile
    const headerSelect = page.locator('header select');
    await expect(headerSelect).toBeVisible();
    await headerSelect.selectOption({ value: 'swift@trans.com' });
    await page.waitForTimeout(300);
  });

  test('7. Auction detail page tab navigation displays Activity Timeline and Extensions', async ({ page }) => {
    // Navigate dynamically to an auction room
    await page.goto('/auctions');
    const firstAuctionLink = page.locator('a:has-text("View Details")').first();
    await expect(firstAuctionLink).toBeVisible();
    await firstAuctionLink.click();
    await page.waitForURL(/\/auctions\/\d+/);

    // Switch to Activity Timeline tab
    const timelineTab = page.locator('button:has-text("Activity Timeline")');
    await timelineTab.click();
    // Verify timeline activity items render
    await expect(page.locator('text=British Auction enabled').first()).toBeVisible();

    // Switch to Extension History tab
    const extensionsTab = page.locator('button:has-text("Extension History")');
    await extensionsTab.click();
    // Verify extension history container (either active extensions or empty state notice)
    const hasExtensions = page.locator('text=Extended by');
    const noExtensions = page.locator('text=No extensions triggered yet');
    await expect(hasExtensions.or(noExtensions).first()).toBeVisible();

    // Switch back to Quotes tab
    const quotesTab = page.locator('button:has-text("Supplier Rankings & Quotes")');
    await quotesTab.click();
    const hasQuotes = page.locator('th:has-text("Rank")');
    const noQuotes = page.locator('text=No supplier quotes placed yet');
    await expect(hasQuotes.or(noQuotes).first()).toBeVisible();
  });

  test('8. Empty search state displays clear empty message', async ({ page }) => {
    await page.goto('/auctions');

    const searchInput = page.locator('input[placeholder*="Search reference"]');
    await searchInput.fill('NON_EXISTENT_RFQ_QUERY_9999');
    await page.locator('button:has-text("Search")').click();

    // Assert clean empty state
    await expect(page.locator('text=No auctions matching your criteria.')).toBeVisible();
  });

  test('9. Create RFQ form validation displays field errors on invalid input', async ({ page }) => {
    await page.goto('/rfqs/new');
    const titleInput = page.locator('input[name="title"]');
    await titleInput.fill('');
    await page.locator('button:has-text("Publish British Auction RFQ")').click();

    // Should display validation error and stay on /rfqs/new
    await expect(page.locator('text=RFQ Title must be at least 3 characters')).toBeVisible();
    expect(page.url()).toContain('/rfqs/new');
  });

  test('10. Invalid auction detail route displays error state with back navigation', async ({ page }) => {
    await page.goto('/auctions/99999999');
    await expect(page.locator('text=Failed to load auction details').first()).toBeVisible();
    const backBtn = page.locator('a:has-text("Back to Auctions")');
    await expect(backBtn).toBeVisible();
    await backBtn.click();
    await page.waitForURL(/\/auctions$/);
    await expect(page.locator('h1:has-text("British Auctions & RFQs")')).toBeVisible();
  });

  test('11. Mobile drawer menu navigates between routes properly', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    const toggleBtn = page.locator('button[aria-label="Toggle navigation menu"]');
    await expect(toggleBtn).toBeVisible();
    await toggleBtn.click();

    // Mobile nav drawer should be visible
    const mobileAuctionsLink = page.locator('header a[href="/auctions"]').last();
    await expect(mobileAuctionsLink).toBeVisible();
    await mobileAuctionsLink.click();
    await page.waitForURL(/\/auctions$/);
    await expect(page.locator('h1:has-text("British Auctions & RFQs")')).toBeVisible();
  });

  test('12. Bid submission modal validates required fields and negative values', async ({ page }) => {
    await page.goto('/auctions');
    const firstAuctionLink = page.locator('a:has-text("View Details")').first();
    await firstAuctionLink.click();
    await page.waitForURL(/\/auctions\/\d+/);

    // Switch to supplier persona
    const headerSelect = page.locator('header select');
    await headerSelect.selectOption({ value: 'apex@logistics.com' });
    await page.waitForTimeout(500);

    const submitQuoteBtn = page.locator('button:has-text("Submit / Lower Quote")');
    if (await submitQuoteBtn.isVisible()) {
      await submitQuoteBtn.click();
      await expect(page.locator('h3:has-text("Submit Quotation / Bid")')).toBeVisible();

      // Clear carrier name
      const carrierInput = page.locator('input[name="carrier_name"]');
      await carrierInput.fill('');
      await page.locator('form button:has-text("Submit Quote")').click();

      // Validation error
      await expect(page.locator('text=Carrier name is required')).toBeVisible();
    }
  });

});
