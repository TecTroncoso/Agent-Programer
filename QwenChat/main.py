import sys
import asyncio
from src.config import Config
from src.auth import AuthExtractor
from src.client import QwenClient
from src.display import get_user_input, print_goodbye, print_status
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()


async def ensure_auth():
    """make sure we're logged in and ready to go"""
    if Config.needs_reauth():
        Config.print_status("Session expired, logging in...", "yellow")

        if not Config.QWEN_EMAIL or not Config.QWEN_PASSWORD:
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


def tools_menu(client):
    """Interactive tools submenu"""
    while True:
        thinking_status = (
            "[green]ON[/green]" if client.thinking_enabled else "[red]OFF[/red]"
        )

        console.print()
        console.print(
            Panel(
                f"[bold cyan]Tools Menu[/bold cyan]\n\n"
                f"[yellow]/thinking[/yellow] - Toggle thinking mode (currently: {thinking_status})\n"
                f"[yellow]/back[/yellow] - Return to chat",
                title="[bold]🛠️ Tools[/bold]",
                border_style="cyan",
                padding=(1, 2),
            )
        )

        cmd = Prompt.ask("[bold magenta]Tools[/bold magenta]").strip().lower()

        if cmd in ["/back", "back", "/exit", "exit"]:
            console.print("[dim]Returning to chat...[/dim]")
            break

        elif cmd in ["/thinking", "thinking"]:
            client.thinking_enabled = not client.thinking_enabled
            status = "ON" if client.thinking_enabled else "OFF"
            color = "green" if client.thinking_enabled else "red"
            console.print(
                f"[cyan][[Qwen]][/cyan] Thinking mode: [{color}]{status}[/{color}]"
            )

        else:
            console.print("[yellow]Unknown command. Use /thinking or /back[/yellow]")


def handle_command(prompt, client):
    """Handle special commands. Returns True if command was handled."""
    cmd = prompt.strip().lower()

    if cmd in ["/exit", "/quit", "/q"]:
        print_goodbye()
        return "exit"

    if cmd == "/new":
        client.new_conversation()
        return True

    if cmd == "/tools":
        tools_menu(client)
        return True

    return False


def interactive_mode():
    """run in interactive chat mode"""
    if not asyncio.run(ensure_auth()):
        sys.exit(1)

    client = QwenClient()

    console.print("\n[bold cyan]Qwen Chat - Interactive Mode[/bold cyan]")
    console.print("[dim]Type /tools for settings, /exit to quit[/dim]\n")

    while True:
        try:
            prompt = get_user_input()

            if not prompt:
                continue

            result = handle_command(prompt, client)
            if result == "exit":
                break
            elif result:
                continue

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

    client = QwenClient()
    client.chat(prompt)


def main():
    if len(sys.argv) < 2:
        interactive_mode()
    else:
        prompt = " ".join(sys.argv[1:])
        single_prompt_mode(prompt)


if __name__ == "__main__":
    main()
