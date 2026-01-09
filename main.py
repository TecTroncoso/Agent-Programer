"""
Multi-Agent Workflow: Orquestador (Qwen) + Programador (Xiaomi)

This workflow uses CrewAI to coordinate two AI agents:
- Orchestrator (Qwen): Plans and reviews tasks
- Programmer (Xiaomi): Generates code based on orchestrator's plan

Usage:
    python main.py "Create a Python function that calculates fibonacci"
    python main.py  # Interactive mode
"""

import sys
from crewai import Agent, Task, Crew, Process
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from llms.qwen_llm import QwenLLM
from llms.xiaomi_llm import XiaomiLLM

console = Console()

# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

ORCHESTRATOR_SYSTEM_PROMPT = """Eres un experto arquitecto de software y planificador técnico.

Tu rol es:
1. Analizar los requerimientos del usuario
2. Descomponer tareas complejas en subtareas manejables
3. Coordinar con el programador para implementar cada parte
4. Revisar el código generado y pedir correcciones si es necesario
5. Asegurar que la solución final cumple con los requerimientos

Reglas:
- Sé conciso y directo en tus instrucciones
- Especifica claramente qué código necesitas
- Si el código del programador tiene errores, explica qué corregir
- Cuando estés satisfecho con el resultado, indica "TAREA COMPLETADA"

Formato de respuesta para delegar:
```
SUBTAREA: [descripción breve]
REQUISITOS:
- [requisito 1]
- [requisito 2]
LENGUAJE: [Python/JavaScript/etc]
```
"""

PROGRAMMER_SYSTEM_PROMPT = """Eres un programador experto especializado en escribir código limpio, eficiente y bien documentado.

Tu rol es:
1. Recibir especificaciones técnicas del orquestador
2. Escribir código de alta calidad que cumpla los requisitos
3. Incluir comentarios explicativos cuando sea necesario
4. Manejar casos edge y errores apropiadamente

Reglas:
- Escribe código funcional y listo para usar
- Sigue las mejores prácticas del lenguaje
- Incluye type hints en Python
- No expliques demasiado, el código debe ser auto-explicativo
- Si algo no está claro, asume la solución más razonable

Formato de respuesta:
```[lenguaje]
[código aquí]
```

Notas adicionales si son necesarias.
"""


# =============================================================================
# AGENTS
# =============================================================================


def create_orchestrator(llm: QwenLLM) -> Agent:
    """Create the orchestrator agent powered by Qwen."""
    return Agent(
        role="Arquitecto de Software y Orquestador",
        goal="Planificar, coordinar y revisar la implementación de soluciones de software",
        backstory="""Eres un arquitecto de software senior con más de 15 años de experiencia
        liderando equipos de desarrollo. Tu fortaleza es descomponer problemas complejos
        en partes manejables y coordinar su implementación.""",
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=5,
    )


def create_programmer(llm: XiaomiLLM) -> Agent:
    """Create the programmer agent powered by Xiaomi."""
    return Agent(
        role="Programador Senior",
        goal="Escribir código limpio, eficiente y bien documentado",
        backstory="""Eres un programador full-stack con experiencia en múltiples lenguajes.
        Tu código es conocido por ser elegante, eficiente y fácil de mantener.
        Sigues las mejores prácticas y patrones de diseño.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )


# =============================================================================
# TASKS
# =============================================================================


def create_planning_task(orchestrator: Agent, user_request: str) -> Task:
    """Create the planning task for the orchestrator."""
    return Task(
        description=f"""Analiza el siguiente requerimiento del usuario y crea un plan de implementación:

REQUERIMIENTO: {user_request}

Tu tarea:
1. Analiza qué se necesita implementar
2. Define las subtareas necesarias
3. Especifica los requisitos técnicos para el programador
4. Delega la implementación al programador

Recuerda usar el formato especificado para delegar tareas.""",
        expected_output="Un plan claro con las subtareas delegadas al programador y el código final revisado.",
        agent=orchestrator,
    )


def create_coding_task(programmer: Agent, context_task: Task) -> Task:
    """Create the coding task for the programmer."""
    return Task(
        description="""Implementa el código según las especificaciones recibidas del orquestador.

Tu tarea:
1. Lee las especificaciones del orquestador
2. Escribe código limpio y funcional
3. Incluye manejo de errores apropiado
4. Documenta las funciones principales

El código debe estar listo para usar sin modificaciones adicionales.""",
        expected_output="Código funcional y bien documentado que cumple con los requisitos especificados.",
        agent=programmer,
        context=[context_task],
    )


# =============================================================================
# MAIN WORKFLOW
# =============================================================================


import asyncio
import importlib.util
from pathlib import Path


def perform_silent_login(name: str, project_dir: str, module_prefix: str) -> bool:
    """
    Perform silent login for a given project.

    Args:
        name: Display name (e.g., "Qwen")
        project_dir: Directory name (e.g., "QwenChat")
        module_prefix: Prefix to avoid module cache collisions (e.g., "qwen_auth")

    Returns:
        True if login successful, False otherwise.
    """
    try:
        project_path = Path(__file__).parent / project_dir

        # Determine paths
        src_path = project_path / "src"
        main_path = project_path / "main.py"

        # Load Config first to patch print_status
        config_spec = importlib.util.spec_from_file_location(
            f"{module_prefix}_config", src_path / "config.py"
        )
        config_module = importlib.util.module_from_spec(config_spec)
        sys.modules[f"{module_prefix}_config"] = config_module
        config_spec.loader.exec_module(config_module)

        # Patch print_status to be silent
        original_print = config_module.Config.print_status
        config_module.Config.print_status = lambda *args, **kwargs: None

        # Load AuthExtractor
        auth_spec = importlib.util.spec_from_file_location(
            f"{module_prefix}_auth", src_path / "auth.py"
        )
        auth_module = importlib.util.module_from_spec(auth_spec)
        sys.modules[f"{module_prefix}_auth"] = auth_module

        # Patch auth module imports
        with open(src_path / "auth.py", "r", encoding="utf-8") as f:
            auth_code = f.read()
        auth_code = auth_code.replace(
            "from .config import", f"from {module_prefix}_config import"
        )
        exec(compile(auth_code, src_path / "auth.py", "exec"), auth_module.__dict__)

        # Define ensure_auth logic locally to avoid complex main.py imports
        async def ensure_auth():
            if config_module.Config.needs_reauth():
                # We need to re-auth, this might open browser
                extractor = auth_module.AuthExtractor()
                cookies, token = await extractor.extract_credentials()
                return bool(cookies and token)
            return True

        # Run the check
        with console.status(
            f"[bold yellow]Verificando sesión de {name}...[/bold yellow]"
        ):
            result = asyncio.run(ensure_auth())

        if result:
            console.print(f"[green]✔ Sesión de {name} iniciada correctamente[/green]")
        else:
            console.print(f"[red]✘ Error iniciando sesión en {name}[/red]")

        return result

    except Exception as e:
        console.print(f"[red]✘ Error verificando {name}: {e}[/red]")
        return False


def initialize_sessions():
    """Initialize sessions for both services."""
    console.print(
        Panel(
            "[bold]Iniciando validación de credenciales...[/bold]", border_style="blue"
        )
    )

    qwen_ok = perform_silent_login("Qwen", "QwenChat", "qwen_login")
    xiaomi_ok = perform_silent_login("Xiaomi", "ChatXiaomi", "xiaomi_login")

    if not qwen_ok or not xiaomi_ok:
        console.print(
            "\n[bold red]Advertencia:[/bold red] Algunos servicios no pudieron iniciar sesión."
        )
        console.print(
            "Revisa las credenciales en los archivos .env o intenta login manual."
        )
        console.print("El workflow podría fallar.\n")
    else:
        console.print("\n[bold green]¡Todo listo para comenzar![/bold green]\n")


def run_workflow(user_request: str) -> str:
    """
    Run the multi-agent workflow.

    Args:
        user_request: The user's request/task

    Returns:
        The final result from the workflow
    """
    console.print(
        Panel(
            f"[bold cyan]Iniciando Workflow Multi-Agente[/bold cyan]\n\n"
            f"[yellow]Tarea:[/yellow] {user_request}",
            title="🚀 Workflow",
            border_style="cyan",
        )
    )

    # Initialize LLMs
    console.print("\n[dim]Inicializando modelos...[/dim]")
    qwen_llm = QwenLLM(temperature=0.7)
    xiaomi_llm = XiaomiLLM(temperature=0.8)

    # Create agents
    console.print("[dim]Creando agentes...[/dim]")
    orchestrator = create_orchestrator(qwen_llm)
    programmer = create_programmer(xiaomi_llm)

    # Create tasks
    console.print("[dim]Configurando tareas...[/dim]\n")
    planning_task = create_planning_task(orchestrator, user_request)
    coding_task = create_coding_task(programmer, planning_task)

    # Create and run the crew
    crew = Crew(
        agents=[orchestrator, programmer],
        tasks=[planning_task, coding_task],
        process=Process.sequential,  # Orchestrator first, then programmer
        verbose=True,
    )

    # Execute the workflow
    console.print(
        Panel(
            "[bold green]Ejecutando workflow...[/bold green]\n"
            "[dim]El orquestador planificará y el programador implementará.[/dim]",
            border_style="green",
        )
    )

    result = crew.kickoff()

    # Display result
    console.print("\n")
    console.print(Panel(str(result), title="✅ Resultado Final", border_style="green"))

    return str(result)


def interactive_mode():
    """Run in interactive mode."""
    # Perform login at startup
    initialize_sessions()

    console.print(
        Panel(
            "[bold cyan]Workflow Multi-Agente - Modo Interactivo[/bold cyan]\n\n"
            "[dim]Orquestador: Qwen (planificación)[/dim]\n"
            "[dim]Programador: Xiaomi (código)[/dim]\n\n"
            "[yellow]Escribe tu tarea o 'salir' para terminar[/yellow]",
            border_style="cyan",
        )
    )

    while True:
        try:
            user_input = Prompt.ask("\n[bold magenta]Tu tarea[/bold magenta]")

            if user_input.lower() in ["salir", "exit", "quit", "q"]:
                console.print("[dim]¡Hasta luego![/dim]")
                break

            if not user_input.strip():
                continue

            run_workflow(user_input)

        except KeyboardInterrupt:
            console.print("\n[dim]¡Hasta luego![/dim]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Single task mode
        # Also login for single task mode
        initialize_sessions()

        task = " ".join(sys.argv[1:])
        run_workflow(task)
    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
