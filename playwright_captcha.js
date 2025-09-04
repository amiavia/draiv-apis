const { chromium } = require('playwright');

async function generateBMWCaptchaToken() {
    console.log('🎭 Playwright: Starting browser automation...');
    
    const browser = await chromium.launch({ 
        headless: false, // Show browser for debugging
        slowMo: 1000,    // Slow down operations for visibility
        args: ['--disable-blink-features=AutomationControlled']
    });
    
    try {
        const page = await browser.newPage({
            userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        });
        
        console.log('🌐 Navigating to BMW captcha page...');
        await page.goto('https://bimmer-connected.readthedocs.io/en/stable/captcha/rest_of_world.html');
        
        // Wait for hCaptcha to load
        console.log('⏳ Waiting for hCaptcha to load...');
        await page.waitForSelector('.h-captcha', { timeout: 30000 });
        
        // Wait a bit for full initialization
        await page.waitForTimeout(3000);
        
        // Check if hCaptcha iframe is present
        const hCaptchaFrame = page.frameLocator('iframe[src*="hcaptcha.com"]').first();
        
        console.log('🤖 Looking for hCaptcha checkbox...');
        try {
            // Try to click the hCaptcha checkbox
            await hCaptchaFrame.locator('#checkbox').click({ timeout: 10000 });
            console.log('✅ Clicked hCaptcha checkbox');
            
            // Wait a moment to see if challenge appears
            await page.waitForTimeout(2000);
            
        } catch (error) {
            console.log('⚠️  Direct checkbox click failed, trying alternative selectors...');
            
            // Try alternative selectors
            const selectors = [
                '.h-captcha iframe',
                '[data-hcaptcha-widget-id]',
                '.h-captcha-checkbox'
            ];
            
            for (const selector of selectors) {
                try {
                    await page.locator(selector).click({ timeout: 5000 });
                    console.log(`✅ Clicked using selector: ${selector}`);
                    break;
                } catch (e) {
                    console.log(`❌ Failed selector: ${selector}`);
                }
            }
        }
        
        console.log('🎯 Manual intervention required...');
        console.log('👆 Please solve the hCaptcha challenge manually in the browser');
        console.log('⏳ Waiting for token to appear...');
        
        // Wait for the token to appear (user solves captcha manually)
        let token = null;
        let attempts = 0;
        const maxAttempts = 60; // Wait up to 60 seconds
        
        while (!token && attempts < maxAttempts) {
            try {
                // Check for token in various possible locations
                token = await page.evaluate(() => {
                    // Look for token in DOM
                    const tokenElements = [
                        document.querySelector('[name="h-captcha-response"]'),
                        document.querySelector('[name="g-recaptcha-response"]'),
                        document.querySelector('.hcaptcha-token'),
                        document.querySelector('#hcaptcha-token')
                    ];
                    
                    for (const element of tokenElements) {
                        if (element && element.value && element.value.length > 10) {
                            return element.value;
                        }
                    }
                    
                    // Check for token in global variables
                    if (window.hcaptchaToken) return window.hcaptchaToken;
                    if (window.captchaToken) return window.captchaToken;
                    
                    return null;
                });
                
                if (token) {
                    console.log('🎉 Token found!');
                    console.log(`🔑 Token (first 50 chars): ${token.substring(0, 50)}...`);
                    break;
                }
                
                await page.waitForTimeout(1000);
                attempts++;
                
                if (attempts % 10 === 0) {
                    console.log(`⏳ Still waiting... ${attempts}/${maxAttempts} seconds`);
                }
                
            } catch (error) {
                // Continue waiting
                attempts++;
                await page.waitForTimeout(1000);
            }
        }
        
        if (!token) {
            throw new Error('❌ Timeout: Could not retrieve hCaptcha token');
        }
        
        return token;
        
    } finally {
        await browser.close();
    }
}

// Export for use in other scripts
module.exports = { generateBMWCaptchaToken };

// Run directly if called as script
if (require.main === module) {
    generateBMWCaptchaToken()
        .then(token => {
            console.log('✅ SUCCESS!');
            console.log('🔑 hCaptcha Token:');
            console.log(token);
        })
        .catch(error => {
            console.error('❌ ERROR:', error.message);
            process.exit(1);
        });
}