import sys
import asyncio
from src.config import Config
from src.auth import AuthExtractor
from src.client import KimiClient
from src.display import get_user_input, print_goodbye
from rich.console import Console

console = Console()


async def ensure_auth():
    """make sure we're logged in and ready to go"""
    if Config.needs_reauth():
        Config.print_status("Session expired, logging in...", "yellow")

        if not Config.KIMI_EMAIL or not Config.KIMI_PASSWORD:
            Config.print_status("No email/password in .env file!", "red")
            return False

        extractor = AuthExtractor()
        cookies, token = await extractor.extract_credentials()

        if not cookies or not token:
            Config.print_status("Login failed!", "red")
            return False

        Config.print_status("Login successful!", "green")
    else:
        Config.print_status("Using existing session", "green")

    return True


def interactive_mode():
    """run in interactive chat mode"""
    if not asyncio.run(ensure_auth()):
        sys.exit(1)

    client = KimiClient()

    console.print("\n[bold cyan]Interactive Chat Mode[/bold cyan]")
    console.print("[dim]Type /exit to quit[/dim]\n")

    while True:
        try:
            prompt = get_user_input()

            if not prompt:
                continue

            if prompt.strip().lower() in ["/exit", "/quit", "/q"]:
                print_goodbye()
                break

            client.chat(prompt)

        except KeyboardInterrupt:
            print_goodbye()
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


def single_prompt_mode(prompt):
    """run a single prompt and exit"""
    if not asyncio.run(ensure_auth()):
        sys.exit(1)

    client = KimiClient()
    client.chat(prompt)


def main():
    if len(sys.argv) < 2:
        interactive_mode()
    else:
        prompt = " ".join(sys.argv[1:])
        single_prompt_mode(prompt)


if __name__ == "__main__":
    main()
