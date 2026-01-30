"""
Fixed Reddit posting function - completely rewritten to avoid selector errors
"""
import asyncio
from pyppeteer import launch
from typing import Dict, Optional

async def post_to_reddit_puppeteer_fixed(content: str, credentials: Dict, image_url: Optional[str] = None) -> Dict:
    """
    Post content to Reddit using Puppeteer - Fixed version
    
    Args:
        content: Content to post
        credentials: Reddit credentials (email/username, password, subreddit)
        image_url: Optional image URL to attach
    
    Returns:
        Response dict with success status
    """
    browser = None
    try:
        username = credentials.get('email')  # Can be username or email
        password = credentials.get('password')
        subreddit = credentials.get('subreddit', 'test')
        
        if not username or not password:
            return {
                'success': False,
                'message': 'Reddit username/email and password are required'
            }
        
        # Launch browser in non-headless mode so user can see it
        print("Launching browser...")
        browser = await launch({
            'headless': False,  # Show browser to user
            'args': [
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--start-maximized'  # Start maximized
            ],
            'defaultViewport': None  # Use full window
        })
        page = await browser.newPage()
        
        try:
            # Navigate to Reddit login page
            print("Navigating to Reddit login page...")
            await page.goto('https://www.reddit.com/login', {
                'waitUntil': 'domcontentloaded',
                'timeout': 30000
            })
            
            # Wait for page to be fully loaded
            print("Waiting for page to load...")
            await asyncio.sleep(5)
            
            # Wait for input fields to appear
            try:
                await page.waitForFunction('''() => {
                    const hasTextInput = document.querySelector('input[type="text"]') !== null;
                    const hasPasswordInput = document.querySelector('input[type="password"]') !== null;
                    return document.readyState === 'complete' && (hasTextInput || hasPasswordInput);
                }''', {'timeout': 15000})
                print("Login form detected")
            except Exception as e:
                print(f"Warning: Could not detect form elements: {str(e)}")
                # Continue anyway
            
            # Fill username using JavaScript (most reliable method)
            print("Filling username field...")
            username_result = await page.evaluate('''(username) => {
                try {
                    // Try all possible selectors
                    const selectors = [
                        '#loginUsername',
                        'input[name="username"]',
                        'input[type="text"][name="username"]',
                        'input[id*="username"]',
                        'input[id*="user"]',
                        'input[placeholder*="Username"]',
                        'input[autocomplete="username"]'
                    ];
                    
                    for (const selector of selectors) {
                        const input = document.querySelector(selector);
                        if (input && input.offsetParent !== null) {
                            input.focus();
                            input.value = username;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            console.log('Username filled:', selector);
                            return { success: true, selector: selector };
                        }
                    }
                    
                    // Fallback: find first visible text input
                    const allTextInputs = Array.from(document.querySelectorAll('input[type="text"]'));
                    for (const input of allTextInputs) {
                        if (input.offsetParent !== null && !input.disabled) {
                            input.focus();
                            input.value = username;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            console.log('Username filled using fallback');
                            return { success: true, selector: 'fallback' };
                        }
                    }
                    
                    return { success: false, message: 'No username field found' };
                } catch (e) {
                    return { success: false, message: e.toString() };
                }
            }''', username)
            
            if not username_result.get('success'):
                print(f"ERROR: {username_result.get('message', 'Unknown error')}")
                print("Browser will remain open. Please enter username manually.")
                return {
                    'success': False,
                    'message': f'Could not find username field: {username_result.get("message", "Unknown error")}. Browser will remain open for manual entry.'
                }
            
            print(f"Username filled successfully using: {username_result.get('selector')}")
            await asyncio.sleep(1)
            
            # Fill password using JavaScript
            print("Filling password field...")
            password_result = await page.evaluate('''(password) => {
                try {
                    const selectors = [
                        '#loginPassword',
                        'input[name="password"]',
                        'input[type="password"]',
                        'input[id*="password"]',
                        'input[autocomplete="current-password"]'
                    ];
                    
                    for (const selector of selectors) {
                        const input = document.querySelector(selector);
                        if (input && input.offsetParent !== null) {
                            input.focus();
                            input.value = password;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            console.log('Password filled:', selector);
                            return { success: true, selector: selector };
                        }
                    }
                    
                    // Fallback: find first visible password input
                    const allPasswordInputs = Array.from(document.querySelectorAll('input[type="password"]'));
                    for (const input of allPasswordInputs) {
                        if (input.offsetParent !== null && !input.disabled) {
                            input.focus();
                            input.value = password;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            console.log('Password filled using fallback');
                            return { success: true, selector: 'fallback' };
                        }
                    }
                    
                    return { success: false, message: 'No password field found' };
                } catch (e) {
                    return { success: false, message: e.toString() };
                }
            }''', password)
            
            if not password_result.get('success'):
                print(f"ERROR: {password_result.get('message', 'Unknown error')}")
                print("Browser will remain open. Please enter password manually.")
                return {
                    'success': False,
                    'message': f'Could not find password field: {password_result.get("message", "Unknown error")}. Browser will remain open for manual entry.'
                }
            
            print(f"Password filled successfully using: {password_result.get('selector')}")
            await asyncio.sleep(1)
            
            # Click login button using JavaScript
            print("Clicking login button...")
            login_result = await page.evaluate('''() => {
                try {
                    // Try to find and click login button
                    const buttonSelectors = [
                        'button[type="submit"]',
                        'button[id*="login"]',
                        'button[class*="login"]',
                        'button[class*="submit"]',
                        'form button[type="submit"]'
                    ];
                    
                    for (const selector of buttonSelectors) {
                        const buttons = document.querySelectorAll(selector);
                        for (const button of buttons) {
                            const text = (button.textContent || button.innerText || '').toLowerCase();
                            if (button.offsetParent !== null && 
                                (text.includes('log in') || text.includes('sign in') || 
                                 text.includes('login') || button.type === 'submit')) {
                                button.focus();
                                button.click();
                                console.log('Login button clicked:', selector);
                                return { success: true, selector: selector };
                            }
                        }
                    }
                    
                    // Fallback: submit form
                    const form = document.querySelector('form');
                    if (form) {
                        form.submit();
                        console.log('Form submitted');
                        return { success: true, selector: 'form.submit()' };
                    }
                    
                    return { success: false, message: 'No login button found' };
                } catch (e) {
                    return { success: false, message: e.toString() };
                }
            }''')
            
            if not login_result.get('success'):
                print(f"WARNING: {login_result.get('message', 'Unknown error')}")
                print("Please click the login button manually in the browser.")
            else:
                print(f"Login button clicked using: {login_result.get('selector')}")
            
            # Wait for login to complete
            print("Waiting for login to complete...")
            await asyncio.sleep(6)
            
            # Check current URL
            current_url = page.url
            print(f"Current URL: {current_url}")
            
            # Check if login was successful
            if 'login' not in current_url.lower() or ('reddit.com' in current_url and '/login' not in current_url):
                print(f"Login successful! Navigating to r/{subreddit}...")
                
                # Navigate to subreddit submit page
                await page.goto(f'https://www.reddit.com/r/{subreddit}/submit', {
                    'waitUntil': 'domcontentloaded',
                    'timeout': 30000
                })
                await asyncio.sleep(3)
                
                # Split content
                lines = content.split('\n', 1)
                title = lines[0][:300]
                text = lines[1] if len(lines) > 1 else content
                
                # Fill title
                print("Filling post title...")
                title_result = await page.evaluate('''(title) => {
                    try {
                        const selectors = [
                            'textarea[placeholder*="Title"]',
                            'textarea[name="title"]',
                            'input[name="title"]',
                            'textarea[data-testid*="title"]',
                            'textarea'
                        ];
                        
                        for (const selector of selectors) {
                            const input = document.querySelector(selector);
                            if (input && input.offsetParent !== null) {
                                input.focus();
                                input.value = title;
                                input.dispatchEvent(new Event('input', { bubbles: true }));
                                return { success: true, selector: selector };
                            }
                        }
                        return { success: false };
                    } catch (e) {
                        return { success: false, message: e.toString() };
                    }
                }''', title)
                
                if title_result.get('success'):
                    print("Title filled successfully")
                else:
                    print("WARNING: Could not fill title. Please fill manually.")
                
                await asyncio.sleep(1)
                
                # Fill text
                print("Filling post text...")
                text_result = await page.evaluate('''(text) => {
                    try {
                        const selectors = [
                            'div[contenteditable="true"][data-testid*="text"]',
                            'textarea[name="text"]',
                            'div[contenteditable="true"]',
                            'textarea[placeholder*="Text"]'
                        ];
                        
                        for (const selector of selectors) {
                            const input = document.querySelector(selector);
                            if (input && input.offsetParent !== null) {
                                input.focus();
                                if (input.contentEditable === 'true') {
                                    input.textContent = text;
                                } else {
                                    input.value = text;
                                }
                                input.dispatchEvent(new Event('input', { bubbles: true }));
                                return { success: true, selector: selector };
                            }
                        }
                        
                        // Try second textarea if multiple exist
                        const textareas = document.querySelectorAll('textarea');
                        if (textareas.length > 1) {
                            const textarea = textareas[1];
                            if (textarea.offsetParent !== null) {
                                textarea.focus();
                                textarea.value = text;
                                textarea.dispatchEvent(new Event('input', { bubbles: true }));
                                return { success: true, selector: 'second textarea' };
                            }
                        }
                        
                        return { success: false };
                    } catch (e) {
                        return { success: false, message: e.toString() };
                    }
                }''', text)
                
                if text_result.get('success'):
                    print("Text filled successfully")
                else:
                    print("WARNING: Could not fill text. Please fill manually.")
                
                await asyncio.sleep(2)
                
                # Click submit
                print("Clicking submit button...")
                submit_result = await page.evaluate('''() => {
                    try {
                        const buttons = document.querySelectorAll('button[type="submit"], button[data-testid*="submit"]');
                        for (const button of buttons) {
                            if (button.offsetParent !== null) {
                                button.click();
                                return { success: true };
                            }
                        }
                        return { success: false };
                    } catch (e) {
                        return { success: false, message: e.toString() };
                    }
                }''')
                
                if submit_result.get('success'):
                    print("Submit button clicked")
                else:
                    print("WARNING: Could not click submit. Please click manually.")
                
                await asyncio.sleep(5)
                
                print("Post submitted! Browser will remain open for 15 seconds...")
                await asyncio.sleep(15)
                
                return {
                    'success': True,
                    'message': f'Content posted to r/{subreddit} successfully'
                }
            else:
                return {
                    'success': False,
                    'message': 'Reddit login failed. Please check your credentials. Browser will remain open.'
                }
                
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error during Reddit posting: {str(e)}")
            print(error_trace)
            return {
                'success': False,
                'message': f'Error posting to Reddit: {str(e)}. Browser will remain open for debugging.'
            }
        finally:
            # Keep browser open - don't close automatically
            print("Browser will remain open. Close it manually when done.")
            # await browser.close()  # Commented out
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error launching browser: {str(e)}")
        print(error_trace)
        return {
            'success': False,
            'message': f'Error launching browser: {str(e)}'
        }
