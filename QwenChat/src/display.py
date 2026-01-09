from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from rich.rule import Rule

console = Console()


def print_status(message, style="white"):
    console.print(f"[{style}][[Qwen]][/{style}] {message}", justify="left")


def print_response_start():
    console.print()
    console.print(Rule("[bold cyan]Response[/bold cyan]", style="cyan", align="left"))
    console.print()


def stream_thinking(content):
    """Display thinking content in a collapsible/dimmed panel"""
    console.print()
    console.print(Rule("[dim]💭 Thinking...[/dim]", style="dim", align="left"))
    console.print()

    panel = Panel(
        content,
        border_style="dim",
        padding=(1, 2),
        title="[dim]Reasoning[/dim]",
        title_align="left",
        subtitle="[dim italic]thinking phase[/dim italic]",
        subtitle_align="right",
    )
    console.print(panel)


def stream_live(content_generator):
    full_content = ""

    with Live(console=console, refresh_per_second=10) as live:
        for chunk in content_generator:
            if chunk:
                full_content += chunk

                md = Markdown(full_content, code_theme="monokai", justify="left")
                panel = Panel(
                    md,
                    border_style="bright_cyan",
                    padding=(1, 2),
                    title="[bold white]Qwen[/bold white]",
                    title_align="left",
                )
                live.update(panel)

    return full_content


def get_user_input(prompt_text="You"):
    return Prompt.ask(f"\n[bold green]{prompt_text}[/bold green]")


def print_goodbye():
    console.print("\n[yellow]Goodbye![/yellow]\n", justify="left")


def print_tools_help():
    """Display available tools/commands"""
    console.print()
    console.print(
        Panel(
            "[bold cyan]Available Commands:[/bold cyan]\n\n"
            "[green]/exit, /quit, /q[/green] - Exit the chat\n"
            "[green]/new[/green] - Start a new conversation\n"
            "[green]/thinking on[/green] - Enable thinking mode\n"
            "[green]/thinking off[/green] - Disable thinking mode\n"
            "[green]/tools, /help[/green] - Show this help",
            title="[bold]🛠️ Tools[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()
