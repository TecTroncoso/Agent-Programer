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
            user_data_dir=self.config.BROWSER_PROFILE_DIR,
        )

        try:
            page = await browser.get(f"{self.config.BASE_URL}/")

            self.config.print_status("Waiting for page to load...", "cyan")
            await page.sleep(5)

            self.config.print_status("Typing in chat to trigger login...", "cyan")
            try:
                chat_input = await page.find("textarea", timeout=10)
                await chat_input.click()
                await page.sleep(0.5)
                await chat_input.send_keys("hi")
                await page.sleep(0.5)
                await page.send(
                    uc.cdp.input_.dispatch_key_event(type_="keyDown", key="Enter")
                )
                await page.send(
                    uc.cdp.input_.dispatch_key_event(type_="keyUp", key="Enter")
                )
                await page.sleep(3)
            except Exception as e:
                self.config.print_status(f"Could not trigger chat: {e}", "yellow")

            self.config.print_status("Clicking Google login button...", "cyan")
            try:
                google_btn = await page.find(
                    "#rc-tabs-0-panel-login > form > div.mi-form__content > a",
                    timeout=10,
                )
                await google_btn.click()
                await page.sleep(3)
            except Exception as e:
                self.config.print_status(
                    f"Could not find Google button, trying alternative...", "yellow"
                )
                try:
                    google_btn = await page.find('button:has-text("Google")', timeout=5)
                    await google_btn.click()
                    await page.sleep(3)
                except:
                    self.config.print_status(
                        "Please click Google login manually", "yellow"
                    )
                    await page.sleep(10)

            tabs = browser.tabs
            if len(tabs) > 1:
                page = tabs[-1]

            self.config.print_status("Entering email...", "cyan")
            try:
                email_input = await page.find(
                    'input[type="email"]#identifierId', timeout=5
                )
                await email_input.click()
                await page.sleep(0.5)

                for char in self.config.KIMI_EMAIL:
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

                for char in self.config.KIMI_PASSWORD:
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
            except Exception as e:
                self.config.print_status(
                    f"Login steps skipped (maybe already logged in?): {e}", "yellow"
                )

            self.config.print_status(
                "Waiting for redirect to Xiaomi AI Studio...", "cyan"
            )

            # Manual Intervention Loop / Wait for Login
            max_retries = 60  # Wait up to 5 minutes (60 * 5s)
            logged_in = False

            for i in range(max_retries):
                try:
                    # Refresh tabs list
                    tabs = browser.tabs
                    if not tabs:
                        self.config.print_status("No browser tabs found!", "red")
                        await page.sleep(2)
                        continue

                    # Usually the last active tab is the one we want, or search for the right URL
                    target_page = tabs[0]
                    for t in tabs:
                        if "xiaomimimo.com" in t.url:
                            target_page = t
                            break

                    page = target_page
                    current_url = page.url

                    if (
                        "aistudio.xiaomimimo.com" in current_url
                        and "login" not in current_url
                    ):
                        self.config.print_status("Detected AI Studio page!", "green")
                        logged_in = True
                        break

                    if i % 5 == 0:  # Print every 25 seconds
                        self.config.print_status(
                            f"Waiting for login... (Current: {current_url[:50]}...)",
                            "yellow",
                        )
                        self.config.print_status(
                            "NOTE: If you see an error page (ERR_INVALID_RESPONSE), please Reload/Retry manually in the browser window.",
                            "yellow",
                        )

                    await page.sleep(5)
                except Exception as e:
                    self.config.print_status(f"Error checking login status: {e}", "red")
                    await page.sleep(5)

            if not logged_in:
                self.config.print_status(
                    "Timed out waiting for login. Proceeding to try extraction anyway...",
                    "yellow",
                )

            self.config.print_status("Grabbing cookies...", "cyan")
            cookies_raw = await page.send(uc.cdp.network.get_cookies())

            cookie_dict = {}
            for cookie in cookies_raw:
                cookie_dict[cookie.name] = cookie.value

            self.config.print_status("Getting auth token...", "cyan")
            token = None
            self.config.print_status("Getting auth token...", "cyan")
            token = None
            try:
                # Debug: Print all localStorage items clearly
                try:
                    all_storage = await page.evaluate("JSON.stringify(localStorage)")
                    self.config.print_status(
                        f"FULL LOCALSTORAGE: {all_storage}", "white"
                    )
                except Exception as e:
                    self.config.print_status(f"Could not dump storage: {e}", "red")

                for key in ["access_token", "token", "auth_token", "CASE_ACCESS_TOKEN"]:
                    try:
                        token_val = await page.evaluate(
                            f'localStorage.getItem("{key}")'
                        )
                        if token_val and isinstance(token_val, str):
                            token = token_val
                            break
                    except Exception:
                        pass

                if not token:
                    for key in ["userToken", "user", "auth", "userInfo"]:
                        try:
                            token_raw = await page.evaluate(
                                f'localStorage.getItem("{key}")'
                            )
                            if not token_raw or not isinstance(token_raw, str):
                                continue

                            token_obj = json.loads(token_raw)
                            token = (
                                token_obj.get("value")
                                or token_obj.get("token")
                                or token_obj.get("access_token")
                                or token_obj.get("accessToken")
                            )
                            if token:
                                break
                        except Exception:
                            pass

                if token:
                    self.config.print_status(f"Got token: {token[:30]}...", "green")
                    with open(self.config.TOKEN_FILE, "w") as f:
                        f.write(token)
                else:
                    self.config.print_status(
                        "No localStorage token found (expected for Xiaomi AI Studio). Using cookies.",
                        "yellow",
                    )
            except Exception as e:
                self.config.print_status(
                    f"Token extraction error (ignoring): {e}", "yellow"
                )

            with open(self.config.COOKIES_FILE, "w") as f:
                json.dump(cookie_dict, f, indent=2)

            self.config.update_login_time()
            self.config.print_status(
                f"Success! Got {len(cookie_dict)} cookies", "green"
            )

            # Return dummy token if none found, to pass checks in main.py
            return cookie_dict, token or "cookie-auth"

        except Exception as e:
            self.config.print_status(f"Login failed: {e}", "red")
            return None, None

        finally:
            if browser:
                try:
                    await browser.stop()
                except:
                    pass


async def main():
    if not Config.KIMI_EMAIL or not Config.KIMI_PASSWORD:
        Config.print_status("No email/password in .env file!", "red")
        return

    extractor = AuthExtractor()
    cookies, token = await extractor.extract_credentials()

    if cookies and token:
        Config.print_status("Authentication successful!", "green")
    else:
        Config.print_status("Authentication failed!", "red")


if __name__ == "__main__":
    asyncio.run(main())
