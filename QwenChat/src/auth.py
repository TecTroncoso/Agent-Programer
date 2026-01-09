import asyncio
import nodriver as uc
import json
from .config import Config


class AuthExtractor:
    def __init__(self):
        self.config = Config()

    async def extract_credentials(self):
        self.config.print_status(
            "Starting browser (this might take a sec)...", "yellow"
        )
        browser = await uc.start(
            headless=self.config.HEADLESS,
            browser_executable_path=self.config.BROWSER_PATH,
        )

        try:
            page = await browser.get(f"{self.config.BASE_URL}/")

            self.config.print_status("Waiting for page to load...", "cyan")
            await page.sleep(5)

            # Try to find and click login button
            self.config.print_status("Looking for login button...", "cyan")
            try:
                # User provided selector: #qwen-chat-header-right > div > a:nth-child(1) > button
                login_btn_selector = (
                    "#qwen-chat-header-right > div > a:nth-child(1) > button"
                )

                # Fallback list including the specific one and others just in case
                login_btn = None
                for selector in [
                    login_btn_selector,
                    "button:has-text('Sign in')",
                    "button:has-text('Log in')",
                ]:
                    try:
                        login_btn = await page.find(selector, timeout=3)
                        if login_btn:
                            break
                    except:
                        continue

                if login_btn:
                    await login_btn.click()
                    await page.sleep(3)
            except Exception as e:
                self.config.print_status(f"Could not find login button: {e}", "yellow")
                self.config.print_status(
                    "Please click login manually if needed", "yellow"
                )
                await page.sleep(5)

            # Click Google login button
            self.config.print_status("Clicking Google login button...", "cyan")
            try:
                # User provided selector: #root > div > div > div > div.auth-layout-content > div > div.qwenchat-auth-pc-top > div.qwenchat-auth-pc-other-login > button:nth-child(1)
                google_btn_selector = "#root > div > div > div > div.auth-layout-content > div > div.qwenchat-auth-pc-top > div.qwenchat-auth-pc-other-login > button:nth-child(1)"

                google_btn = None
                for selector in [
                    google_btn_selector,
                    "button:has-text('Google')",
                    "[data-provider='google']",
                ]:
                    try:
                        google_btn = await page.find(selector, timeout=3)
                        if google_btn:
                            break
                    except:
                        continue

                if google_btn:
                    await google_btn.click()
                    await page.sleep(3)
                else:
                    self.config.print_status(
                        "Could not find Google button, please click it manually",
                        "yellow",
                    )
                    await page.sleep(10)
            except Exception as e:
                self.config.print_status(
                    f"Could not click Google button: {e}", "yellow"
                )
                await page.sleep(10)

            # Switch to Google login tab if opened
            tabs = browser.tabs
            if len(tabs) > 1:
                page = tabs[-1]

            self.config.print_status("Entering email...", "cyan")
            email_input = await page.find(
                'input[type="email"]#identifierId', timeout=10
            )
            await email_input.click()
            await page.sleep(0.5)

            for char in self.config.QWEN_EMAIL:
                await email_input.send_keys(char)
                await page.sleep(0.05)

            await page.sleep(0.5)
            await page.send(
                uc.cdp.input_.dispatch_key_event(
                    type_="rawKeyDown",
                    windows_virtual_key_code=13,
                    native_virtual_key_code=13,
                    key="Enter",
                    code="Enter",
                )
            )
            await page.send(
                uc.cdp.input_.dispatch_key_event(
                    type_="keyUp",
                    windows_virtual_key_code=13,
                    native_virtual_key_code=13,
                    key="Enter",
                    code="Enter",
                )
            )
            await page.sleep(4)

            self.config.print_status("Entering password...", "cyan")
            password_input = await page.find(
                'input[type="password"][name="Passwd"]', timeout=10
            )
            await password_input.click()
            await page.sleep(0.5)

            for char in self.config.QWEN_PASSWORD:
                await password_input.send_keys(char)
                await page.sleep(0.05)

            await page.sleep(0.5)
            await page.send(
                uc.cdp.input_.dispatch_key_event(
                    type_="rawKeyDown",
                    windows_virtual_key_code=13,
                    native_virtual_key_code=13,
                    key="Enter",
                    code="Enter",
                )
            )
            await page.send(
                uc.cdp.input_.dispatch_key_event(
                    type_="keyUp",
                    windows_virtual_key_code=13,
                    native_virtual_key_code=13,
                    key="Enter",
                    code="Enter",
                )
            )
            await page.sleep(5)

            self.config.print_status("Waiting for redirect to Qwen...", "cyan")
            await page.sleep(5)

            # Switch back to main tab
            tabs = browser.tabs
            page = tabs[0]
            await page.sleep(3)

            self.config.print_status("Grabbing cookies...", "cyan")
            cookies_raw = await page.send(uc.cdp.network.get_cookies())

            cookie_dict = {}
            for cookie in cookies_raw:
                cookie_dict[cookie.name] = cookie.value

            self.config.print_status("Getting auth token...", "cyan")
            token = None
            try:
                # Try to get token from localStorage - common keys used by Qwen
                for key in ["access_token", "token", "auth_token", "userToken", "jwt"]:
                    token = await page.evaluate(f'localStorage.getItem("{key}")')
                    if token:
                        break

                if not token:
                    # Try to get token from nested objects
                    for key in ["user", "auth", "session"]:
                        try:
                            token_obj = await page.evaluate(
                                f'JSON.parse(localStorage.getItem("{key}"))'
                            )
                            if token_obj and isinstance(token_obj, dict):
                                token = (
                                    token_obj.get("access_token")
                                    or token_obj.get("token")
                                    or token_obj.get("value")
                                )
                                if token:
                                    break
                        except:
                            pass

                if token:
                    self.config.print_status(f"Got token: {token[:30]}...", "green")
                    with open(self.config.TOKEN_FILE, "w") as f:
                        f.write(token)
                else:
                    self.config.print_status(
                        "Couldn't find token in localStorage", "yellow"
                    )
            except Exception as e:
                self.config.print_status(f"Token extraction failed: {e}", "red")

            with open(self.config.COOKIES_FILE, "w") as f:
                json.dump(cookie_dict, f, indent=2)

            self.config.update_login_time()
            self.config.print_status(
                f"Success! Got {len(cookie_dict)} cookies", "green"
            )

            return cookie_dict, token

        except Exception as e:
            self.config.print_status(f"Login failed: {e}", "red")
            return None, None

        finally:
            if browser:
                try:
                    await browser.stop()
                except:
                    pass
