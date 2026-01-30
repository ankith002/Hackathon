"""
Puppeteer-based posting functions for LinkedIn, Reddit, and Email
Using pyppeteer (Python port of Puppeteer)
"""
import asyncio
from pyppeteer import launch
from typing import Dict, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import requests
import time

async def post_to_linkedin_puppeteer(content: str, credentials: Dict, image_url: Optional[str] = None) -> Dict:
    """
    Post content to LinkedIn using Puppeteer
    
    Args:
        content: Content to post
        credentials: LinkedIn credentials (email, password)
        image_url: Optional image URL to attach
    
    Returns:
        Response dict with success status
    """
    browser = None
    try:
        email = credentials.get('email')
        password = credentials.get('password')
        
        if not email or not password:
            return {
                'success': False,
                'message': 'LinkedIn email and password are required'
            }
        
        # Launch browser in non-headless mode so user can see it
        print("Launching browser for LinkedIn...")
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
            # Navigate to LinkedIn login
            print("Navigating to LinkedIn login page...")
            await page.goto('https://www.linkedin.com/login', {
                'waitUntil': 'domcontentloaded',
                'timeout': 30000
            })
            await asyncio.sleep(3)
            
            # Fill in login credentials using JavaScript (improved method)
            print("Filling login credentials...")
            await asyncio.sleep(2)  # Wait for page to load
            
            # Fill email using page.$ (more reliable)
            email_input = await page.querySelector('#username, [name=session_key]')
            if email_input:
                await email_input.type(email, {'delay': 50})
                await asyncio.sleep(0.5)
            
            # Fill password
            pass_input = await page.querySelector('#password, [name=session_password]')
            if pass_input:
                await pass_input.type(password, {'delay': 50})
                await asyncio.sleep(1)
            
            # Click login button using improved text-based search
            print("Clicking login button...")
            login_clicked = await page.evaluate('''() => {
                const btns = document.querySelectorAll("button, [type=submit], [role=button]");
                for (const b of btns) {
                    const text = (b.textContent || "").trim();
                    // Skip social login buttons
                    if (/with apple|with google|with microsoft/i.test(text)) continue;
                    // Find sign in button
                    if (/^sign\\s*in$|^log\\s*in$/i.test(text) || (b.type === "submit" && /sign\\s*in/i.test(text))) {
                        b.click();
                        return true;
                    }
                }
                return false;
            }''')
            
            if not login_clicked:
                print("WARNING: Could not click login button automatically. Please click it manually.")
            
            # Wait for login to complete
            print("Waiting for login to complete...")
            await asyncio.sleep(4)
            
            # Check current URL
            current_url = page.url
            print(f"Current URL: {current_url}")
            
            # Check if login was successful
            if 'feed' in current_url or 'linkedin.com/feed' in current_url or 'linkedin.com/in/' in current_url or 'login' not in current_url:
                print("Login successful! Navigating to feed...")
                
                # Navigate to feed page
                await page.goto('https://www.linkedin.com/feed/', {
                    'waitUntil': 'networkidle0',  # Wait for network to be idle
                    'timeout': 60000
                })
                await asyncio.sleep(5)  # Wait for page to fully load
                
                print("🔍 Finding post input field with multiple strategies...")
                
                # COMPREHENSIVE INPUT FIELD DETECTION - Multiple strategies
                input_focused = False
                
                # Strategy 1: Direct contenteditable search with many selectors
                print("Strategy 1: Searching for contenteditable elements...")
                for attempt in range(15):  # More attempts
                    input_focused = await page.evaluate('''() => {
                        // Comprehensive selector list
                        const allSelectors = [
                            'div[contenteditable="true"][role="textbox"]',
                            'div[contenteditable="plaintext-only"][role="textbox"]',
                            'div[contenteditable="true"]',
                            'div[contenteditable="plaintext-only"]',
                            '[contenteditable="true"]',
                            '[contenteditable="plaintext-only"]',
                            '[role="textbox"]',
                            'div[role="textbox"]',
                            'div[class*="share-box"]',
                            'div[class*="shareBox"]',
                            'div[class*="feed"]',
                            'div[class*="compose"]',
                            'div[class*="editor"]',
                            'div[class*="text"]',
                            'div[class*="input"]',
                            'div[data-placeholder]',
                            'div[aria-label]',
                            'div[id*="share"]',
                            'div[id*="post"]',
                            'div[id*="compose"]',
                            'div[data-control-name*="share"]',
                            'div[data-control-name*="create"]'
                        ];
                        
                        const candidates = [];
                        
                        // Search all selectors
                        for (const selector of allSelectors) {
                            try {
                                const els = document.querySelectorAll(selector);
                                for (const el of els) {
                                    const rect = el.getBoundingClientRect();
                                    if (rect.width > 20 && rect.height > 10 && rect.top >= 0 && rect.left >= 0) {
                                        const isContentEditable = el.contentEditable === 'true' || el.contentEditable === 'plaintext-only';
                                        const hasRole = el.getAttribute('role') === 'textbox';
                                        const placeholder = (el.getAttribute('data-placeholder') || el.getAttribute('aria-label') || '').toLowerCase();
                                        const className = (el.className || '').toLowerCase();
                                        const area = rect.width * rect.height;
                                        
                                        // Calculate priority score
                                        let priority = area;
                                        if (isContentEditable) priority += 5000;
                                        if (hasRole) priority += 3000;
                                        if (placeholder.includes('what') || placeholder.includes('talk')) priority += 2000;
                                        if (className.includes('share') || className.includes('compose') || className.includes('feed')) priority += 1000;
                                        if (rect.width > 300 && rect.height > 100) priority += 500;
                                        
                                        candidates.push({ el: el, priority: priority, rect: rect });
                                    }
                                }
                            } catch (e) {
                                continue;
                            }
                        }
                        
                        // Sort by priority
                        candidates.sort((a, b) => b.priority - a.priority);
                        
                        // Try top 5 candidates
                        for (let i = 0; i < Math.min(5, candidates.length); i++) {
                            const candidate = candidates[i];
                            try {
                                candidate.el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                candidate.el.focus();
                                candidate.el.click();
                                
                                // Verify it's focused
                                if (document.activeElement === candidate.el || candidate.el === document.querySelector(':focus')) {
                                    return true;
                                }
                            } catch (e) {
                                continue;
                            }
                        }
                        return false;
                    }''')
                    
                    if input_focused:
                        print("✅ Input field found using Strategy 1!")
                        break
                    await asyncio.sleep(0.5)
                
                # Strategy 2: Click on share box container first, then find input
                if not input_focused:
                    print("Strategy 2: Clicking share box container first...")
                    share_box_clicked = await page.evaluate('''() => {
                        const containers = document.querySelectorAll('div[class*="share"], div[class*="compose"], div[class*="feed"]');
                        for (const container of containers) {
                            const rect = container.getBoundingClientRect();
                            if (rect.width > 400 && rect.height > 100) {
                                container.click();
                                return true;
                            }
                        }
                        return false;
                    }''')
                    if share_box_clicked:
                        await asyncio.sleep(2)
                        # Now try to find input again
                        input_focused = await page.evaluate('''() => {
                            const inputs = document.querySelectorAll('[contenteditable="true"], [contenteditable="plaintext-only"]');
                            for (const input of inputs) {
                                const rect = input.getBoundingClientRect();
                                if (rect.width > 200 && rect.height > 50) {
                                    input.focus();
                                    input.click();
                                    return true;
                                }
                            }
                            return false;
                        }''')
                        if input_focused:
                            print("✅ Input field found using Strategy 2!")
                
                # Strategy 3: Find by text content "What do you want to talk about"
                if not input_focused:
                    print("Strategy 3: Searching by placeholder text...")
                    for attempt in range(5):
                        input_focused = await page.evaluate('''() => {
                            function findByText(root) {
                                const all = root.querySelectorAll('*');
                                for (const el of all) {
                                    const text = (el.textContent || el.innerText || '').toLowerCase();
                                    const placeholder = (el.getAttribute('data-placeholder') || el.getAttribute('aria-label') || '').toLowerCase();
                                    
                                    if ((text.includes('what do you want to talk about') || 
                                         placeholder.includes('what do you want to talk about') ||
                                         text.includes('start a post')) && 
                                        (el.contentEditable === 'true' || el.getAttribute('role') === 'textbox')) {
                                        el.focus();
                                        el.click();
                                        return true;
                                    }
                                }
                                return false;
                            }
                            return findByText(document);
                        }''')
                        if input_focused:
                            print("✅ Input field found using Strategy 3!")
                            break
                        await asyncio.sleep(1)
                
                # Strategy 4: Click center of page where input usually is
                if not input_focused:
                    print("Strategy 4: Clicking center area of feed...")
                    await page.evaluate('''() => {
                        const centerX = window.innerWidth / 2;
                        const centerY = window.innerHeight / 3; // Upper third where input usually is
                        const clickEvent = new MouseEvent('click', {
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            clientX: centerX,
                            clientY: centerY
                        });
                        document.elementFromPoint(centerX, centerY).dispatchEvent(clickEvent);
                    }''')
                    await asyncio.sleep(2)
                    # Try finding input again
                    input_focused = await page.evaluate('''() => {
                        const inputs = document.querySelectorAll('[contenteditable="true"]');
                        if (inputs.length > 0) {
                            inputs[0].focus();
                            inputs[0].click();
                            return true;
                        }
                        return false;
                    }''')
                    if input_focused:
                        print("✅ Input field found using Strategy 4!")
                
                # Strategy 5: Use Tab key to navigate to input
                if not input_focused:
                    print("Strategy 5: Using keyboard navigation...")
                    try:
                        await page.keyboard.press('Tab')
                        await asyncio.sleep(0.5)
                        await page.keyboard.press('Tab')
                        await asyncio.sleep(0.5)
                        # Check if focused element is contenteditable
                        focused = await page.evaluate('''() => {
                            const active = document.activeElement;
                            return active && (active.contentEditable === 'true' || active.getAttribute('role') === 'textbox');
                        }''')
                        if focused:
                            input_focused = True
                            print("✅ Input field found using Strategy 5!")
                    except:
                        pass
                
                if not input_focused:
                    raise Exception("Could not find input field using any strategy")
                
                print("📝 Inserting content with multiple methods...")
                await asyncio.sleep(1)
                
                # COMPREHENSIVE CONTENT INSERTION - Multiple methods
                content_inserted = False
                
                # Method 1: document.execCommand (most reliable)
                if not content_inserted:
                    try:
                        await page.evaluate('''(text) => {
                            document.execCommand("insertText", false, text);
                        }''', content)
                        # Verify content was inserted
                        inserted = await page.evaluate('''(text) => {
                            const active = document.activeElement;
                            if (active && (active.contentEditable === 'true' || active.getAttribute('role') === 'textbox')) {
                                return active.textContent.includes(text.substring(0, 20));
                            }
                            return false;
                        }''', content)
                        if inserted:
                            content_inserted = True
                            print("✅ Content inserted using execCommand")
                    except Exception as e:
                        print(f"execCommand failed: {str(e)}")
                
                # Method 2: Direct textContent with full event simulation
                if not content_inserted:
                    try:
                        await page.evaluate('''(text) => {
                            const inputs = document.querySelectorAll('[contenteditable="true"], [contenteditable="plaintext-only"], [role="textbox"]');
                            for (const input of inputs) {
                                const r = input.getBoundingClientRect();
                                if (r.width > 30 && r.height > 15) {
                                    input.focus();
                                    // Clear first
                                    input.innerHTML = '';
                                    input.textContent = '';
                                    input.innerText = '';
                                    // Set content
                                    input.textContent = text;
                                    input.innerText = text;
                                    // Trigger all events
                                    input.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                                    input.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                                    input.dispatchEvent(new Event('keyup', { bubbles: true, cancelable: true }));
                                    input.dispatchEvent(new Event('keydown', { bubbles: true, cancelable: true }));
                                    input.dispatchEvent(new Event('paste', { bubbles: true, cancelable: true }));
                                    return true;
                                }
                            }
                            return false;
                        }''', content)
                        content_inserted = True
                        print("✅ Content inserted using textContent")
                    except Exception as e:
                        print(f"textContent method failed: {str(e)}")
                
                # Method 3: Use innerHTML for rich text
                if not content_inserted:
                    try:
                        await page.evaluate('''(text) => {
                            const inputs = document.querySelectorAll('[contenteditable="true"]');
                            for (const input of inputs) {
                                if (document.activeElement === input || input === document.querySelector(':focus')) {
                                    input.innerHTML = text.replace(/\\n/g, '<br>');
                                    input.dispatchEvent(new Event('input', { bubbles: true }));
                                    return true;
                                }
                            }
                            return false;
                        }''', content)
                        content_inserted = True
                        print("✅ Content inserted using innerHTML")
                    except Exception as e:
                        print(f"innerHTML method failed: {str(e)}")
                
                # Method 4: Paste simulation
                if not content_inserted:
                    try:
                        await page.evaluate('''(text) => {
                            const active = document.activeElement;
                            if (active && active.contentEditable === 'true') {
                                const dataTransfer = new DataTransfer();
                                dataTransfer.setData('text/plain', text);
                                const pasteEvent = new ClipboardEvent('paste', {
                                    clipboardData: dataTransfer,
                                    bubbles: true,
                                    cancelable: true
                                });
                                active.dispatchEvent(pasteEvent);
                                active.textContent = text;
                                return true;
                            }
                            return false;
                        }''', content)
                        content_inserted = True
                        print("✅ Content inserted using paste simulation")
                    except Exception as e:
                        print(f"Paste simulation failed: {str(e)}")
                
                # Method 5: Character-by-character typing
                if not content_inserted:
                    try:
                        print("Trying character-by-character typing...")
                        # Clear first
                        await page.keyboard.down('Control')
                        await page.keyboard.press('KeyA')
                        await page.keyboard.up('Control')
                        await asyncio.sleep(0.2)
                        # Type content
                        for char in content[:2000]:  # Increased limit
                            await page.keyboard.type(char)
                            await asyncio.sleep(0.02)
                        content_inserted = True
                        print("✅ Content inserted using keyboard typing")
                    except Exception as e:
                        print(f"Keyboard typing failed: {str(e)}")
                
                if not content_inserted:
                    raise Exception("Could not insert content using any method")
                
                # Verify content was inserted
                await asyncio.sleep(0.5)
                content_verified = await page.evaluate('''(text) => {
                    const active = document.activeElement;
                    if (active && (active.contentEditable === 'true' || active.getAttribute('role') === 'textbox')) {
                        const content = active.textContent || active.innerText || '';
                        return content.length > 10; // At least some content
                    }
                    // Check all contenteditables
                    const all = document.querySelectorAll('[contenteditable="true"]');
                    for (const el of all) {
                        const content = el.textContent || el.innerText || '';
                        if (content.length > 10) return true;
                    }
                    return false;
                }''', content)
                
                if not content_verified:
                    print("⚠️ Warning: Content insertion may have failed, but continuing...")
                else:
                    print("✅ Content verified in input field")
                
                await asyncio.sleep(1)
                
                # COMPREHENSIVE POST BUTTON DETECTION - Multiple strategies
                print("🚀 Finding and clicking Post button...")
                post_clicked = False
                
                # Strategy 0: Direct ember ID (highest priority - LinkedIn specific)
                print("Strategy 0: Trying ember244 (LinkedIn Post button ID)...")
                ember_button = await page.querySelector('#ember244')
                if ember_button:
                    try:
                        await ember_button.click()
                        post_clicked = True
                        print("✅ Post button clicked using ember244 ID!")
                    except Exception as e:
                        print(f"ember244 click failed: {str(e)}")
                
                # Strategy 1: Comprehensive button search
                if not post_clicked:
                    for attempt in range(12):  # More attempts
                        post_clicked = await page.evaluate('''() => {
                            // First try ember244 directly
                            const ember244 = document.getElementById('ember244');
                            if (ember244 && ember244.offsetParent !== null) {
                                ember244.click();
                                return true;
                            }
                            
                            const allButtons = document.querySelectorAll('button, [type=submit], [role=button], a, span, div');
                            const candidates = [];
                            
                            for (const button of allButtons) {
                                if (button.offsetParent === null) continue;
                                
                                const text = (button.textContent || button.innerText || button.getAttribute('aria-label') || '').toLowerCase().trim();
                                const dataControlName = button.getAttribute('data-control-name') || '';
                                const className = (button.className || '').toLowerCase();
                                const id = (button.id || '').toLowerCase();
                                const rect = button.getBoundingClientRect();
                                
                                // Check for ember244
                                if (id === 'ember244') {
                                    button.click();
                                    return true;
                                }
                                
                                // Comprehensive matching
                                const isPostButton = (
                                    text === 'post' ||
                                    text === 'share' ||
                                    (text.includes('post') && !text.includes('start') && !text.includes('view')) ||
                                    text.includes('share') ||
                                    button.type === 'submit' ||
                                    dataControlName.includes('share') ||
                                    dataControlName.includes('post') ||
                                    className.includes('share') ||
                                    className.includes('post') ||
                                    id.includes('post') ||
                                    id.includes('share')
                                );
                                
                                if (isPostButton && rect.width > 25 && rect.height > 8) {
                                    let priority = rect.width * rect.height;
                                    if (id === 'ember244') priority += 10000;  // Highest priority for ember244
                                    if (text === 'post') priority += 5000;
                                    if (text === 'share') priority += 4000;
                                    if (text.includes('post')) priority += 3000;
                                    if (button.type === 'submit') priority += 2000;
                                    if (dataControlName.includes('share')) priority += 1500;
                                    if (className.includes('share') || className.includes('post')) priority += 1000;
                                    
                                    candidates.push({ button: button, priority: priority });
                                }
                            }
                            
                            candidates.sort((a, b) => b.priority - a.priority);
                            
                            // Try top 10 candidates
                            for (let i = 0; i < Math.min(10, candidates.length); i++) {
                                const candidate = candidates[i];
                                try {
                                    candidate.button.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                    candidate.button.focus();
                                    candidate.button.click();
                                    return true;
                                } catch (e) {
                                    try {
                                        candidate.button.click();
                                        return true;
                                    } catch (e2) {
                                        continue;
                                    }
                                }
                            }
                            return false;
                        }''')
                        
                        if post_clicked:
                            print("✅ Post button clicked using Strategy 1!")
                            break
                        await asyncio.sleep(0.5)
                
                # Strategy 2: Find by data attributes
                if not post_clicked:
                    print("Strategy 2: Searching by data attributes...")
                    post_clicked = await page.evaluate('''() => {
                        const buttons = document.querySelectorAll('[data-control-name*="share"], [data-control-name*="post"], [data-testid*="post"], [data-testid*="share"]');
                        for (const btn of buttons) {
                            if (btn.offsetParent !== null) {
                                btn.click();
                                return true;
                            }
                        }
                        return false;
                    }''')
                    if post_clicked:
                        print("✅ Post button clicked using Strategy 2!")
                
                # Strategy 3: Find submit button in form
                if not post_clicked:
                    print("Strategy 3: Searching for form submit button...")
                    post_clicked = await page.evaluate('''() => {
                        const forms = document.querySelectorAll('form');
                        for (const form of forms) {
                            const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                            if (submitBtn && submitBtn.offsetParent !== null) {
                                submitBtn.click();
                                return true;
                            }
                        }
                        return false;
                    }''')
                    if post_clicked:
                        print("✅ Post button clicked using Strategy 3!")
                
                # Strategy 4: Enter key (multiple times)
                if not post_clicked:
                    print("Strategy 4: Using Enter key...")
                    try:
                        # Try Enter key 3 times
                        await page.keyboard.press('Enter')
                        await asyncio.sleep(0.3)
                        await page.keyboard.press('Enter')
                        await asyncio.sleep(0.3)
                        await page.keyboard.press('Enter')
                        post_clicked = True
                        print("✅ Submitted using Enter key!")
                    except Exception as e:
                        print(f"Enter key failed: {str(e)}")
                
                # Strategy 5: Ctrl+Enter (common shortcut)
                if not post_clicked:
                    print("Strategy 5: Trying Ctrl+Enter...")
                    try:
                        await page.keyboard.down('Control')
                        await page.keyboard.press('Enter')
                        await page.keyboard.up('Control')
                        post_clicked = True
                        print("✅ Submitted using Ctrl+Enter!")
                    except Exception as e:
                        print(f"Ctrl+Enter failed: {str(e)}")
                
                if not post_clicked:
                    raise Exception("Could not click Post button using any method. Browser will remain open.")
                
                # Wait and verify post was ACTUALLY submitted (not just button clicked)
                print("⏳ Waiting for post to be submitted and verifying...")
                await asyncio.sleep(8)  # Wait longer for LinkedIn to process
                
                # COMPREHENSIVE VERIFICATION - Must pass ALL checks
                post_verified = False
                verification_attempts = 0
                max_verification_attempts = 15  # More attempts
                
                while not post_verified and verification_attempts < max_verification_attempts:
                    verification_attempts += 1
                    print(f"🔍 Verification attempt {verification_attempts}/{max_verification_attempts}...")
                    
                    verification_result = await page.evaluate('''() => {
                        const checks = {
                            onFeed: false,
                            inputCleared: false,
                            postButtonGone: false,
                            contentNotInInput: false
                        };
                        
                        // Check 1: Still on feed page
                        const url = window.location.href;
                        checks.onFeed = url.includes('/feed');
                        
                        // Check 2: Input fields are cleared (MOST IMPORTANT)
                        const inputs = document.querySelectorAll('[contenteditable="true"], [contenteditable="plaintext-only"]');
                        let allCleared = true;
                        let hasLargeInput = false;
                        for (const input of inputs) {
                            const rect = input.getBoundingClientRect();
                            if (rect.width > 200 && rect.height > 50) {
                                hasLargeInput = true;
                                const text = (input.textContent || input.innerText || '').trim();
                                if (text.length > 5) {
                                    allCleared = false; // Input still has content
                                }
                            }
                        }
                        checks.inputCleared = hasLargeInput && allCleared;
                        
                        // Check 3: Post button (ember244) is GONE or disabled
                        const ember244 = document.getElementById('ember244');
                        const buttonStillVisible = ember244 && ember244.offsetParent !== null;
                        
                        // Also check for any "Post" button
                        const postButtons = document.querySelectorAll('button');
                        let anyPostButtonVisible = false;
                        for (const btn of postButtons) {
                            const text = (btn.textContent || '').toLowerCase().trim();
                            if ((text === 'post' || text === 'share') && btn.offsetParent !== null) {
                                anyPostButtonVisible = true;
                                break;
                            }
                        }
                        checks.postButtonGone = !buttonStillVisible && !anyPostButtonVisible;
                        
                        // Check 4: Content is NOT in input field anymore
                        let contentInInput = false;
                        for (const input of inputs) {
                            const rect = input.getBoundingClientRect();
                            if (rect.width > 200) {
                                const text = (input.textContent || input.innerText || '').trim();
                                // Check if our content is still there (first 50 chars)
                                if (text.length > 50) {
                                    contentInInput = true;
                                }
                            }
                        }
                        checks.contentNotInInput = !contentInInput;
                        
                        // ALL checks must pass for verification
                        const allPassed = checks.onFeed && checks.inputCleared && checks.postButtonGone && checks.contentNotInInput;
                        
                        return {
                            verified: allPassed,
                            checks: checks,
                            details: {
                                onFeed: checks.onFeed,
                                inputCleared: checks.inputCleared,
                                postButtonGone: checks.postButtonGone,
                                contentNotInInput: checks.contentNotInInput
                            }
                        };
                    }''')
                    
                    if verification_result.get('verified'):
                        post_verified = True
                        print(f"✅ Post VERIFIED! All checks passed:")
                        print(f"   - On feed page: {verification_result.get('details', {}).get('onFeed')}")
                        print(f"   - Input cleared: {verification_result.get('details', {}).get('inputCleared')}")
                        print(f"   - Post button gone: {verification_result.get('details', {}).get('postButtonGone')}")
                        print(f"   - Content not in input: {verification_result.get('details', {}).get('contentNotInInput')}")
                        break
                    else:
                        details = verification_result.get('details', {})
                        print(f"⚠️ Verification failed. Checks:")
                        print(f"   - On feed: {details.get('onFeed', False)}")
                        print(f"   - Input cleared: {details.get('inputCleared', False)}")
                        print(f"   - Post button gone: {details.get('postButtonGone', False)}")
                        print(f"   - Content not in input: {details.get('contentNotInInput', False)}")
                        
                        # If post button is still visible, try clicking again
                        if not details.get('postButtonGone', True):
                            print("🔄 Post button still visible - trying to click again...")
                            await page.evaluate('''() => {
                                const ember244 = document.getElementById('ember244');
                                if (ember244 && ember244.offsetParent !== null) {
                                    ember244.click();
                                    return true;
                                }
                                return false;
                            }''')
                            await asyncio.sleep(3)
                        
                        await asyncio.sleep(2)  # Wait before next verification attempt
                
                # Final verification check
                if not post_verified:
                    print("❌ CRITICAL: Post submission could NOT be verified!")
                    print("⚠️ Browser will remain OPEN for manual verification.")
                    print("⚠️ Please check the LinkedIn feed to see if your post appears.")
                    print("⚠️ If post button is still visible, please click it manually.")
                    # Keep browser open - don't close
                    raise Exception("Post submission verification failed. Browser remains open - please verify manually and click Post if needed.")
                
                # Only close browser if post was verified
                if post_verified:
                    print("✅ Post submitted and verified successfully!")
                    try:
                        await asyncio.sleep(2)
                        await browser.close()
                        print("✅ Browser closed - post completed successfully")
                    except:
                        pass
                    
                    return {
                        'success': True,
                    'message': 'Content posted to LinkedIn successfully'
                }
            else:
                return {
                    'success': False,
                    'message': 'LinkedIn login failed. Please check your credentials. Browser will remain open for you to verify.'
                }
                
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error during LinkedIn posting: {str(e)}")
            print(error_trace)
            return {
                'success': False,
                'message': f'Error posting to LinkedIn: {str(e)}. Browser will remain open for debugging.'
            }
        finally:
            # Only close browser if post was verified successfully
            # Otherwise keep it open for manual verification
            pass  # Browser closing is handled in the main flow
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error launching browser: {str(e)}")
        print(error_trace)
        return {
            'success': False,
            'message': f'Error launching browser: {str(e)}'
        }


async def post_to_reddit_puppeteer(content: str, credentials: Dict, image_url: Optional[str] = None) -> Dict:
    """
    Post content to Reddit using Puppeteer
    
    Args:
        content: Content to post
        credentials: Reddit credentials (email/username, password, subreddit)
        image_url: Optional image URL to attach
    
    Returns:
        Response dict with success status
    """
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
            print(f"Navigating to Reddit login page...")
            await page.goto('https://www.reddit.com/login', {
                'waitUntil': 'domcontentloaded',  # Changed to be faster
                'timeout': 30000
            })
            await asyncio.sleep(5)  # Give page more time to fully load and render
            
            # Wait for page to be interactive and have input fields
            try:
                await page.waitForFunction('''() => {
                    return document.readyState === 'complete' && 
                           (document.querySelector('input[type="text"]') || 
                            document.querySelector('input[type="password"]') ||
                            document.querySelector('input[name*="user"]') ||
                            document.querySelector('input[id*="user"]'));
                }''', {'timeout': 15000})
                print("Page elements detected")
            except Exception as e:
                print(f"Warning: Page elements may not be fully loaded: {str(e)}")
                # Continue anyway - we'll try to find fields
            
            print(f"Page loaded. Checking for login fields...")
            
            # Use JavaScript to find and fill username field (more reliable)
            username_filled = await page.evaluate('''(username) => {
                // Try multiple selectors
                const selectors = [
                    '#loginUsername',
                    'input[name="username"]',
                    'input[type="text"][name="username"]',
                    'input[id*="username"]',
                    'input[id*="user"]',
                    'input[placeholder*="Username"]',
                    'input[autocomplete="username"]',
                    'input[type="text"]'
                ];
                
                for (const selector of selectors) {
                    try {
                        const input = document.querySelector(selector);
                        if (input && input.offsetParent !== null) {  // Check if visible
                            input.focus();
                            input.value = username;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            console.log('Username filled using selector:', selector);
                            return true;
                        }
                    } catch (e) {
                        continue;
                    }
                }
                
                // Fallback: find first visible text input
                const allInputs = document.querySelectorAll('input[type="text"]');
                for (const input of allInputs) {
                    if (input.offsetParent !== null) {
                        input.focus();
                        input.value = username;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                        console.log('Username filled using fallback');
                        return true;
                    }
                }
                
                return false;
            }''', username)
            
            if not username_filled:
                # Wait a bit more and try again
                await asyncio.sleep(2)
                username_filled = await page.evaluate('''(username) => {
                    const input = document.querySelector('input[type="text"], input[name*="user"], input[id*="user"]');
                    if (input) {
                        input.focus();
                        input.value = username;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        return true;
                    }
                    return false;
                }''', username)
            
            if not username_filled:
                print("ERROR: Could not find username field. Browser will remain open for manual entry.")
                return {
                    'success': False,
                    'message': 'Could not find username field on Reddit login page. Please enter credentials manually in the browser. Browser will remain open.'
                }
            
            print("Username field filled successfully")
            await asyncio.sleep(1)
            
            # Use JavaScript to find and fill password field
            password_filled = await page.evaluate('''(password) => {
                const selectors = [
                    '#loginPassword',
                    'input[name="password"]',
                    'input[type="password"]',
                    'input[id*="password"]',
                    'input[autocomplete="current-password"]'
                ];
                
                for (const selector of selectors) {
                    try {
                        const input = document.querySelector(selector);
                        if (input && input.offsetParent !== null) {
                            input.focus();
                            input.value = password;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            console.log('Password filled using selector:', selector);
                            return true;
                        }
                    } catch (e) {
                        continue;
                    }
                }
                
                // Fallback: find first visible password input
                const allInputs = document.querySelectorAll('input[type="password"]');
                for (const input of allInputs) {
                    if (input.offsetParent !== null) {
                        input.focus();
                        input.value = password;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                        console.log('Password filled using fallback');
                        return true;
                    }
                }
                
                return false;
            }''', password)
            
            if not password_filled:
                print("ERROR: Could not find password field. Browser will remain open for manual entry.")
                return {
                    'success': False,
                    'message': 'Could not find password field on Reddit login page. Please enter credentials manually in the browser. Browser will remain open.'
                }
            
            print("Password field filled successfully")
            await asyncio.sleep(1)
            
            # Find and click login button using JavaScript (more reliable)
            login_clicked = await page.evaluate('''() => {
                const selectors = [
                    'button[type="submit"]',
                    'button[id*="login"]',
                    'button[class*="login"]',
                    'button[class*="submit"]',
                    'form button[type="submit"]',
                    'button.button-primary',
                    'button'
                ];
                
                for (const selector of selectors) {
                    try {
                        const buttons = document.querySelectorAll(selector);
                        for (const button of buttons) {
                            const text = (button.textContent || button.innerText || '').toLowerCase();
                            if (button.offsetParent !== null && 
                                (text.includes('log in') || text.includes('sign in') || 
                                 text.includes('login') || button.type === 'submit')) {
                                button.focus();
                                button.click();
                                console.log('Login button clicked:', selector);
                                return true;
                            }
                        }
                    } catch (e) {
                        continue;
                    }
                }
                
                // Fallback: submit form
                try {
                    const form = document.querySelector('form');
                    if (form) {
                        form.submit();
                        console.log('Form submitted');
                        return true;
                    }
                } catch (e) {
                    // Ignore
                }
                
                return false;
            }''')
            
            if not login_clicked:
                print("WARNING: Could not automatically click login button. Please click it manually in the browser.")
                # Don't return error - let user click manually and continue
            
            # Wait for navigation after login
            print("Waiting for login to complete...")
            await asyncio.sleep(5)  # Give more time for login
            
            # Check current URL to see if login was successful
            current_url = page.url
            print(f"Current URL after login: {current_url}")
            
            # Check if login was successful (not on login page anymore)
            if 'login' not in current_url.lower() or ('reddit.com' in current_url and '/login' not in current_url):
                print(f"Login appears successful. Navigating to r/{subreddit}...")
                
                # Navigate to subreddit submit page
                await page.goto(f'https://www.reddit.com/r/{subreddit}/submit', {
                    'waitUntil': 'networkidle2',
                    'timeout': 30000
                })
                await asyncio.sleep(2)
                
                # Split content into title and text
                lines = content.split('\n', 1)
                title = lines[0][:300]  # Reddit title max 300 chars
                text = lines[1] if len(lines) > 1 else content
                
                # Try multiple selectors for title field
                title_selectors = [
                    'textarea[placeholder*="Title"]',
                    'textarea[name="title"]',
                    'input[name="title"]',
                    'div[contenteditable="true"][data-testid*="title"]',
                    'textarea[data-testid*="title"]'
                ]
                
                # Fill title using JavaScript
                title_filled = await page.evaluate('''(title) => {
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
                
                title_found = title_filled.get('success', False)
                if title_found:
                    print(f"Title entered using: {title_filled.get('selector')}")
                
                if not title_found:
                    return {
                        'success': False,
                        'message': 'Could not find title field on Reddit submit page. Please check the page.'
                    }
                
                await asyncio.sleep(1)
                
                # Try multiple selectors for text/body field
                text_selectors = [
                    'div[contenteditable="true"][data-testid*="text"]',
                    'textarea[name="text"]',
                    'div[contenteditable="true"]',
                    'textarea[placeholder*="Text"]',
                    'div[role="textbox"]'
                ]
                
                text_found = False
                for selector in text_selectors:
                    try:
                        elements = await page.querySelectorAll(selector)
                        if len(elements) > 1:  # If multiple, use the second one (usually the text field)
                            element = elements[1]
                        elif len(elements) == 1:
                            element = elements[0]
                        else:
                            continue
                        
                        # For contenteditable divs, use evaluate to set text
                        is_contenteditable = await page.evaluate('(el) => el.contentEditable === "true"', element)
                        if is_contenteditable:
                            await page.evaluate('''(text, index) => {
                                const textareas = document.querySelectorAll('div[contenteditable="true"], textarea');
                                if (textareas[index]) {
                                    textareas[index].textContent = text;
                                    textareas[index].dispatchEvent(new Event('input', { bubbles: true }));
                                }
                            }''', text, 1 if len(elements) > 1 else 0)
                        else:
                            await page.type(selector, text, {'delay': 30})
                        text_found = True
                        print(f"Text entered using selector: {selector}")
                        break
                    except Exception as e:
                        print(f"Error with selector {selector}: {str(e)}")
                        continue
                
                await asyncio.sleep(2)
                
                # Try multiple selectors for submit button
                submit_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Post")',
                    'button[data-testid*="submit"]',
                    'button:has-text("Submit")',
                    'form button[type="submit"]'
                ]
                
                # Click submit using JavaScript
                submit_clicked = await page.evaluate('''() => {
                    try {
                        const selectors = [
                            'button[type="submit"]',
                            'button[data-testid*="submit"]',
                            'button:has-text("Post")',
                            'button:has-text("Submit")'
                        ];
                        
                        for (const selector of selectors) {
                            const buttons = document.querySelectorAll(selector);
                            for (const button of buttons) {
                                if (button.offsetParent !== null) {
                                    button.click();
                                    return { success: true, selector: selector };
                                }
                            }
                        }
                        return { success: false };
                    } catch (e) {
                        return { success: false, message: e.toString() };
                    }
                }''')
                
                submit_clicked = submit_clicked.get('success', False)
                if submit_clicked:
                    print(f"Submit button clicked")
                else:
                    print("WARNING: Could not click submit. Please click manually.")
                
                if not submit_clicked:
                    return {
                        'success': False,
                        'message': 'Could not find submit button. Please check the page and submit manually. Browser will remain open.'
                    }
                
                await asyncio.sleep(3)
                
                # Don't close browser automatically - let user see the result
                print("Post submitted! Browser will remain open for 10 seconds...")
                await asyncio.sleep(10)
                
                return {
                    'success': True,
                    'message': f'Content posted to r/{subreddit} successfully'
                }
            else:
                return {
                    'success': False,
                    'message': 'Reddit login failed. Please check your username and password. Browser will remain open for you to verify.'
                }
        except Exception as e:
            print(f"Error during Reddit posting: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Error posting to Reddit: {str(e)}. Browser will remain open for debugging.'
            }
        finally:
            # Keep browser open for user to see
            print("Browser will remain open. Close it manually when done.")
            # await browser.close()  # Commented out so user can see what happened
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Error posting to Reddit: {str(e)}'
        }


def post_to_email_smtp(content: str, credentials: Dict, image_url: Optional[str] = None) -> Dict:
    """
    Send content via Email using SMTP (no Puppeteer needed for email)
    
    Args:
        content: Content to send
        credentials: Email credentials (email, password, recipient_email)
        image_url: Optional image URL to attach
    
    Returns:
        Response dict with success status
    """
    try:
        email = credentials.get('email')
        password = credentials.get('password')
        recipient_email = credentials.get('recipient_email', email)  # Default to sender if not provided
        smtp_server = credentials.get('smtp_server', 'smtp.gmail.com')
        smtp_port = credentials.get('smtp_port', 587)
        subject = credentials.get('subject', 'Marketing Content')
        
        if not all([email, password, recipient_email]):
            return {
                'success': False,
                'message': 'Email credentials incomplete. Need: email, password, recipient_email'
            }
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Add text content
        text_content = MIMEText(content, 'plain')
        msg.attach(text_content)
        
        # Add HTML version
        html_content = f"""
        <html>
          <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
              <h2>{subject}</h2>
              <div style="line-height: 1.6; color: #333;">
                {content.replace(chr(10), '<br>')}
              </div>
            </div>
          </body>
        </html>
        """
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # If image URL provided, fetch and attach image
        if image_url:
            try:
                img_response = requests.get(image_url, timeout=10)
                if img_response.status_code == 200:
                    img = MIMEImage(img_response.content)
                    img.add_header('Content-Disposition', 'attachment', filename='marketing_image.jpg')
                    msg.attach(img)
            except Exception as e:
                print(f"Warning: Could not attach image: {str(e)}")
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email, password)
        server.send_message(msg)
        server.quit()
        
        return {
            'success': True,
            'message': f'Email sent to {recipient_email} successfully'
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Error sending email: {str(e)}'
        }


async def post_to_platform_puppeteer(platform: str, content: str, credentials: Dict, image_url: Optional[str] = None) -> Dict:
    """
    Post content to the specified platform using Puppeteer (or SMTP for email)
    
    Args:
        platform: Platform name (linkedin, reddit, email)
        content: Content to post
        credentials: Platform-specific credentials
        image_url: Optional image URL
    
    Returns:
        Response dict with success status
    """
    platform = platform.lower()
    
    if platform == 'linkedin':
        return await post_to_linkedin_puppeteer(content, credentials, image_url)
    elif platform == 'reddit':
        return await post_to_reddit_puppeteer(content, credentials, image_url)
    elif platform == 'email':
        # Email uses SMTP (synchronous), but we need to return it from async function
        # Run it in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, post_to_email_smtp, content, credentials, image_url)
    else:
        return {
            'success': False,
            'message': f'Platform {platform} posting not yet implemented'
        }
