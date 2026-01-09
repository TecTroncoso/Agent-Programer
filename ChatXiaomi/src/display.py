from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.rule import Rule
from rich.prompt import Prompt

console = Console()


def print_status(message, style="white"):
    console.print(f"[{style}][[Xiaomi AI]][/{style}] {message}", justify="left")


def print_response_start():
    console.print()
    console.print(Rule("[bold cyan]Response[/bold cyan]", style="cyan", align="left"))
    console.print()


def stream_live(content_generator):
    full_content = ""

    with Live(console=console, refresh_per_second=10) as live:
        for chunk in content_generator:
            if chunk:
                full_content += chunk

                # Parse thinking content
                think_start = full_content.find("<think>")
                think_end = full_content.find("</think>")

                display_group = []

                if think_start != -1:
                    # We have thinking content
                    if think_end != -1:
                        # Thinking finished
                        thought = full_content[
                            think_start + 7 : think_end
                        ].strip()  # 7 is len(<think>)
                        # Remove null bytes if any
                        thought = thought.replace("\u0000", "")

                        answer = full_content[
                            think_end + 8 :
                        ].strip()  # 8 is len(</think>)
                        # Remove null bytes from answer start if any
                        answer = answer.replace("\u0000", "")

                        # Add Thinking Panel (Dimmed)
                        if thought:
                            display_group.append(
                                Panel(
                                    Markdown(thought),
                                    title="[bold dim]Thinking Process[/bold dim]",
                                    border_style="dim",
                                    padding=(0, 1),
                                )
                            )

                        # Add Answer Panel
                        if answer:
                            display_group.append(
                                Panel(
                                    Markdown(answer, code_theme="monokai"),
                                    title="[bold white]Xiaomi AI[/bold white]",
                                    border_style="cyan",
                                    padding=(1, 2),
                                )
                            )
                        elif not answer:
                            # Show empty panel if answer hasn't started but thinking finished
                            display_group.append(
                                Panel(
                                    "",
                                    title="[bold white]Xiaomi AI[/bold white]",
                                    border_style="cyan",
                                    padding=(1, 2),
                                )
                            )

                    else:
                        # Thinking in progress
                        thought = full_content[think_start + 7 :].strip()
                        thought = thought.replace("\u0000", "")

                        if thought:
                            display_group.append(
                                Panel(
                                    Markdown(thought),
                                    title="[bold dim]Thinking...[/bold dim]",
                                    border_style="yellow",
                                    padding=(0, 1),
                                )
                            )
                else:
                    # No thinking tags found, treat everything as answer
                    answer = full_content.replace("\u0000", "")
                    if answer:
                        display_group.append(
                            Panel(
                                Markdown(answer, code_theme="monokai"),
                                title="[bold white]Xiaomi AI[/bold white]",
                                border_style="cyan",
                                padding=(1, 2),
                            )
                        )

                if display_group:
                    live.update(Group(*display_group))

    return full_content


def get_user_input(prompt_text="You"):
    return Prompt.ask(f"\n[bold green]{prompt_text}[/bold green]")


def print_goodbye():
    console.print("\n[yellow]Goodbye![/yellow]\n", justify="left")
