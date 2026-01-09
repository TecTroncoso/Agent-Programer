import json
import uuid
import httpx
from .config import Config
from .display import print_status, print_response_start, stream_live


class KimiClient:
    def __init__(self):
        self.config = Config()
        self.cookies = self._load_cookies()
        # Ensure we have the critical auth cookies
        if not self.cookies.get("serviceToken"):
            print_status("Warning: 'serviceToken' cookie missing!", "yellow")

        self.conversation_id = uuid.uuid4().hex
        self.client = httpx.Client(
            timeout=60.0, cookies=self.cookies, headers=self.config.BASE_HEADERS
        )

    def _load_cookies(self):
        try:
            with open(self.config.COOKIES_FILE, "r") as f:
                cookies = json.load(f)
                # Parse/Clean cookies
                cleaned_cookies = {}
                for k, v in cookies.items():
                    if isinstance(v, str):
                        # Strip simple quotes
                        v = v.strip('"')
                    cleaned_cookies[k] = v

                # Debug: Print loaded cookies
                print_status(f"Loaded {len(cleaned_cookies)} cookies:", "dim")
                for k, v in cleaned_cookies.items():
                    val_preview = v[:10] + "..." if isinstance(v, str) else str(v)
                    print_status(f"  {k}: {val_preview}", "dim")
                return cleaned_cookies
        except FileNotFoundError:
            return {}

    def chat(self, prompt):
        if not self.cookies:
            print_status("No cookies found. Please login first.", "red")
            return

        msg_id = uuid.uuid4().hex

        # Payload based on user cURL
        payload = {
            "msgId": msg_id,
            "conversationId": self.conversation_id,
            "query": prompt,
            "isEditedQuery": False,
            "modelConfig": {
                "enableThinking": True,
                "temperature": 0.8,
                "topP": 0.95,
                "webSearchStatus": "disabled",
                "model": "mimo-v2-flash-studio",
            },
            "multiMedias": [],
        }

        # Add xiaomichatbot_ph header if present in cookies (seems required by cURL)
        headers = self.config.BASE_HEADERS.copy()
        if "xiaomichatbot_ph" in self.cookies:
            # URL Decode if needed, but usually raw value works or needs format
            pass

        print_status("Sending message...", "cyan")

        try:
            with self.client.stream(
                "POST",
                f"{self.config.BASE_URL}/open-apis/bot/chat",
                params={
                    "xiaomichatbot_ph": self.cookies.get("xiaomichatbot_ph", "")
                },  # Add query param as seen in URL
                json=payload,
            ) as resp:
                if resp.status_code != 200:
                    print_status(f"Request failed: {resp.status_code}", "red")
                    try:
                        print_status(f"Response: {resp.read().decode()}", "dim")
                    except:
                        pass
                    return

                print_response_start()

                def content_generator():
                    for line in resp.iter_lines():
                        if not line:
                            continue

                        if line.startswith("event:dialogId"):
                            # Next line is data:{"content":"..."}
                            pass

                        if line.startswith("data:"):
                            json_str = line[5:].strip()
                            if not json_str:
                                continue

                            if json_str == "[DONE]":
                                break

                            try:
                                data = json.loads(json_str)
                                # Handle {"content": "..."} for dialogId event
                                if "content" in data and "type" not in data:
                                    # Might be dialog ID, ignore or store
                                    pass

                                # Handle {"type":"text","content":"..."}
                                if data.get("type") == "text":
                                    yield data.get("content", "")

                            except json.JSONDecodeError:
                                pass

                full_content = stream_live(content_generator())
                return full_content

        except Exception as e:
            print_status(f"Connection error: {e}", "red")

    def send_message(self, prompt: str, system_prompt: str = None) -> str:
        """
        Send a message and return the response as a string (no console output).
        Used for programmatic access (e.g., CrewAI integration).
        
        Args:
            prompt: The user message to send
            system_prompt: Optional system prompt to prepend
            
        Returns:
            The complete response as a string
        """
        if not self.cookies:
            return "Error: No cookies found. Please login first."

        msg_id = uuid.uuid4().hex

        # Prepend system prompt to user message if provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"[System Instructions: {system_prompt}]\n\nUser Request: {prompt}"

        payload = {
            "msgId": msg_id,
            "conversationId": self.conversation_id,
            "query": full_prompt,
            "isEditedQuery": False,
            "modelConfig": {
                "enableThinking": True,
                "temperature": 0.8,
                "topP": 0.95,
                "webSearchStatus": "disabled",
                "model": "mimo-v2-flash-studio",
            },
            "multiMedias": [],
        }

        try:
            with self.client.stream(
                "POST",
                f"{self.config.BASE_URL}/open-apis/bot/chat",
                params={
                    "xiaomichatbot_ph": self.cookies.get("xiaomichatbot_ph", "")
                },
                json=payload,
            ) as resp:
                if resp.status_code != 200:
                    return f"Error: Request failed with status {resp.status_code}"

                full_content = ""

                for line in resp.iter_lines():
                    if not line:
                        continue

                    if line.startswith("data:"):
                        json_str = line[5:].strip()
                        if not json_str:
                            continue

                        if json_str == "[DONE]":
                            break

                        try:
                            data = json.loads(json_str)
                            if data.get("type") == "text":
                                full_content += data.get("content", "")
                        except json.JSONDecodeError:
                            pass

                return full_content

        except Exception as e:
            return f"Error: {str(e)}"
