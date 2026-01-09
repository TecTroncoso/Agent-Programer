# Workflow Multi-Agente 🤖

Sistema de orquestación multi-agente usando **CrewAI** que integra dos modelos de IA:

- **Qwen** (Orquestador): Planifica, coordina y revisa tareas
- **Xiaomi AI Studio** (Programador): Genera código de alta calidad

## 🏗️ Arquitectura

```
Workflow/
├── main.py                    # Punto de entrada del workflow
├── requirements.txt           # Dependencias
├── llms/
│   ├── qwen_llm.py           # Wrapper CrewAI para Qwen
│   └── xiaomi_llm.py         # Wrapper CrewAI para Xiaomi
├── QwenChat/                  # Cliente Python para chat.qwen.ai
│   ├── main.py               # CLI interactivo
│   └── src/
│       ├── auth.py           # Login automático con browser
│       ├── client.py         # API client + send_message()
│       └── config.py         # Configuración
└── ChatXiaomi/                # Cliente Python para Xiaomi AI Studio
    ├── main.py               # CLI interactivo  
    └── src/
        ├── auth.py           # Login automático OAuth
        ├── client.py         # API client + send_message()
        └── config.py         # Configuración
```

## 🚀 Instalación

```bash
# Crear entorno virtual
python -m venv env
env\Scripts\activate  # Windows
# source env/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
pip install nodriver httpx rich python-dotenv
```

## ⚙️ Configuración

Crear archivos `.env` en cada subproyecto:

**QwenChat/.env:**
```env
QWEN_EMAIL=tu_email@gmail.com
QWEN_PASSWORD=tu_password
```

**ChatXiaomi/.env:**
```env
KIMI_EMAIL=tu_email@gmail.com
KIMI_PASSWORD=tu_password
```

## 🔐 Autenticación Inicial

Antes de usar el workflow, debes iniciar sesión en ambos servicios:

```bash
# Login en Qwen
cd QwenChat
python main.py
# Escribe cualquier mensaje y cierra con /exit

# Login en Xiaomi
cd ../ChatXiaomi
python main.py
# Escribe cualquier mensaje y cierra con /exit
```

Las cookies se guardarán automáticamente para futuras sesiones.

## 💻 Uso

### Modo Interactivo
```bash
python main.py
```

### Tarea Única
```bash
python main.py "Crea una función que calcule el factorial"
```

## 🔄 Flujo de Trabajo

```mermaid
graph TD
    User((Usuario)) --> |"1. Tarea"| Orchestrator[Orquestador\n(Qwen)]
    Orchestrator --> |"2. Especificaciones"| Programmer[Programador\n(Xiaomi)]
    Programmer --> |"3. Código Generado"| Orchestrator
    Orchestrator --> |"4. Revisión"| Decision{¿Aprobado?}
    Decision --> |No| Programmer
    Decision --> |Sí| Result[Resultado Final]

    classDef qwen fill:#bbf,stroke:#333,stroke-width:2px;
    classDef xiaomi fill:#f9f,stroke:#333,stroke-width:2px;
    class Orchestrator qwen;
    class Programmer xiaomi;
```

## 📋 Ejemplo de Salida

```
Tu tarea: Crea una calculadora

🚀 Workflow
Iniciando Workflow Multi-Agente
Tarea: Crea una calculadora

🤖 Agent: Arquitecto de Software
Planificando implementación...

🤖 Agent: Programador Senior  
Generando código...

✅ Resultado Final
[Código de la calculadora generado]
```

## 🛠️ Componentes

| Componente | Descripción |
|------------|-------------|
| `QwenLLM` | Wrapper BaseLLM para Qwen (orquestación) |
| `XiaomiLLM` | Wrapper BaseLLM para Xiaomi (código) |
| `QwenClient` | Cliente HTTP para chat.qwen.ai |
| `KimiClient` | Cliente HTTP para Xiaomi AI Studio |

## 📝 Notas

- Las sesiones expiran después de ~24 horas
- Si hay errores de autenticación, ejecuta el login nuevamente
- El workflow soporta tareas iterativas (el orquestador puede pedir correcciones)

## 📄 Licencia

MIT License
