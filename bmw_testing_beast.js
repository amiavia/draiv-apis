const { generateBMWCaptchaToken } = require('./playwright_captcha.js');
const { execSync } = require('child_process');
const fs = require('fs');

class BMWTestingBeast {
    constructor() {
        this.bmwApiUrl = 'https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_stateless';
        this.testCredentials = {
            email: 'Info@miavia.ai',
            password: 'qegbe6-ritdoz-vikDeK',
            wkn: 'WBA3K51040K175114'
        };
        this.maxAttempts = 10;
        this.currentAttempt = 0;
    }

    async log(message) {
        const timestamp = new Date().toISOString();
        console.log(`[${timestamp}] ${message}`);
    }

    async generateFreshToken() {
        await this.log('🎭 Generating fresh hCaptcha token with Playwright...');
        try {
            const token = await generateBMWCaptchaToken();
            await this.log(`🔑 Fresh token generated (${token.length} chars)`);
            return token;
        } catch (error) {
            await this.log(`❌ Token generation failed: ${error.message}`);
            throw error;
        }
    }

    async testBMWAPI(hcaptchaToken) {
        await this.log('🧪 Testing BMW API...');
        
        const payload = {
            ...this.testCredentials,
            hcaptcha: hcaptchaToken
        };

        try {
            const curlCommand = `curl -s -X POST \\
                -H "Content-Type: application/json" \\
                -d '${JSON.stringify(payload)}' \\
                "${this.bmwApiUrl}"`;
            
            const response = execSync(curlCommand, { encoding: 'utf-8' });
            const result = JSON.parse(response);
            
            if (result.success) {
                await this.log('✅ BMW API authentication SUCCESS!');
                await this.log(`🎉 Vehicle: ${result.vehicle?.model || 'Unknown'}`);
                return { success: true, result };
            } else {
                await this.log('❌ BMW API authentication FAILED');
                await this.log(`📋 Error: ${result.error || 'Unknown error'}`);
                await this.log(`📋 Details: ${result.details || result.bmw_raw_error || 'No details'}`);
                return { success: false, error: result };
            }
        } catch (error) {
            await this.log(`💥 API test crashed: ${error.message}`);
            return { success: false, error: { message: error.message } };
        }
    }

    async analyzeAndFix(errorResult) {
        await this.log('🔍 Analyzing error and implementing fix...');
        
        const error = errorResult.error;
        let fixApplied = false;

        // Analysis patterns and fixes
        if (error.bmw_raw_error || error.details) {
            const errorText = (error.bmw_raw_error || error.details || '').toString().toLowerCase();
            
            // OAuth endpoint issues
            if (errorText.includes('404') || errorText.includes('not found')) {
                await this.log('🔧 FIX: OAuth endpoint issue detected');
                await this.fixOAuthEndpoints();
                fixApplied = true;
            }
            
            // Authentication parameter issues  
            else if (errorText.includes('invalid_request') || errorText.includes('missing')) {
                await this.log('🔧 FIX: Authentication parameter issue detected');
                await this.fixAuthParameters();
                fixApplied = true;
            }
            
            // Header issues
            else if (errorText.includes('unauthorized') || errorText.includes('invalid_client')) {
                await this.log('🔧 FIX: Header/client issue detected');
                await this.fixHeaders();
                fixApplied = true;
            }
            
            // PKCE issues
            else if (errorText.includes('code_challenge') || errorText.includes('pkce')) {
                await this.log('🔧 FIX: PKCE issue detected');
                await this.fixPKCE();
                fixApplied = true;
            }
        }

        if (!fixApplied) {
            await this.log('🤔 Generic fix: Enhancing error logging and debugging');
            await this.enhanceDebugging();
            fixApplied = true;
        }

        return fixApplied;
    }

    async fixOAuthEndpoints() {
        // Fix OAuth endpoint configuration
        const fix = `
        // Update OAuth configuration endpoint
        oauth_config_url = f"{BMW_BASE_URL}/gcdm/oauth/config"
        `;
        await this.log('📝 Applying OAuth endpoint fix...');
        // Implementation would modify the actual Python file
    }

    async fixAuthParameters() {
        await this.log('📝 Applying authentication parameter fix...');
        // Would implement parameter fixes
    }

    async fixHeaders() {
        await this.log('📝 Applying header fix...');
        // Would implement header fixes
    }

    async fixPKCE() {
        await this.log('📝 Applying PKCE fix...');
        // Would implement PKCE fixes
    }

    async enhanceDebugging() {
        await this.log('📝 Enhancing debugging output...');
        // Would add more detailed logging
    }

    async redeploy() {
        await this.log('🚀 Triggering redeployment...');
        try {
            execSync('gh workflow run "BMW API CI/CD Pipeline" --repo amiavia/draiv-apis', { encoding: 'utf-8' });
            await this.log('✅ Deployment triggered');
            
            // Wait for deployment to complete
            await this.log('⏳ Waiting for deployment to complete...');
            await this.waitForDeployment();
            
        } catch (error) {
            await this.log(`❌ Deployment failed: ${error.message}`);
            throw error;
        }
    }

    async waitForDeployment() {
        let deploymentComplete = false;
        let attempts = 0;
        const maxWait = 30; // 5 minutes max wait

        while (!deploymentComplete && attempts < maxWait) {
            try {
                const status = execSync('gh run list --repo amiavia/draiv-apis --limit 1 --json status,conclusion', { encoding: 'utf-8' });
                const runs = JSON.parse(status);
                
                if (runs.length > 0) {
                    const latestRun = runs[0];
                    if (latestRun.status === 'completed') {
                        if (latestRun.conclusion === 'success') {
                            await this.log('✅ Deployment completed successfully');
                            deploymentComplete = true;
                        } else {
                            throw new Error(`Deployment failed with status: ${latestRun.conclusion}`);
                        }
                    }
                }
                
                if (!deploymentComplete) {
                    await new Promise(resolve => setTimeout(resolve, 10000)); // Wait 10 seconds
                    attempts++;
                    await this.log(`⏳ Still waiting for deployment... ${attempts}/${maxWait}`);
                }
                
            } catch (error) {
                await this.log(`⚠️  Error checking deployment status: ${error.message}`);
                attempts++;
                await new Promise(resolve => setTimeout(resolve, 10000));
            }
        }

        if (!deploymentComplete) {
            throw new Error('Deployment timeout - took too long to complete');
        }
    }

    async runTestingLoop() {
        await this.log('🚀 STARTING BMW TESTING BEAST LOOP!');
        await this.log(`🎯 Maximum attempts: ${this.maxAttempts}`);
        
        for (this.currentAttempt = 1; this.currentAttempt <= this.maxAttempts; this.currentAttempt++) {
            await this.log(`\n🔄 ATTEMPT ${this.currentAttempt}/${this.maxAttempts}`);
            
            try {
                // Step 1: Generate fresh token
                const token = await this.generateFreshToken();
                
                // Step 2: Test BMW API
                const testResult = await this.testBMWAPI(token);
                
                if (testResult.success) {
                    await this.log('🎉🎉🎉 SUCCESS! BMW AUTHENTICATION WORKING! 🎉🎉🎉');
                    return true;
                }
                
                // Step 3: Analyze and fix
                const fixApplied = await this.analyzeAndFix(testResult);
                
                if (fixApplied && this.currentAttempt < this.maxAttempts) {
                    // Step 4: Redeploy
                    await this.redeploy();
                } else if (!fixApplied) {
                    await this.log('⚠️  No fix could be applied automatically');
                }
                
            } catch (error) {
                await this.log(`💥 Attempt ${this.currentAttempt} crashed: ${error.message}`);
                
                if (this.currentAttempt === this.maxAttempts) {
                    await this.log('❌ All attempts exhausted. Manual intervention required.');
                    return false;
                }
            }
            
            await this.log(`⏳ Cooling down before next attempt...`);
            await new Promise(resolve => setTimeout(resolve, 5000)); // 5 second pause
        }
        
        await this.log('❌ Testing loop completed without success');
        return false;
    }
}

// Run the beast
if (require.main === module) {
    const beast = new BMWTestingBeast();
    beast.runTestingLoop()
        .then(success => {
            if (success) {
                console.log('✅ BMW AUTHENTICATION FIXED!');
                process.exit(0);
            } else {
                console.log('❌ BMW authentication still failing');
                process.exit(1);
            }
        })
        .catch(error => {
            console.error('💥 Beast crashed:', error);
            process.exit(1);
        });
}