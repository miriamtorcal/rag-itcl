import hashlib
import importlib
import pkgutil

import mcp_server.tools as tools_pkg

TOOLS = {}


def stable_int(key: str, module: int) -> str:
    """
    Devuelve un entero determinista en el rango [0, modulo-1]
    para una clave dada.
    """
    if module <= 0:
        raise ValueError("Module must be > 0")
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()  # hash determinista
    value = int(digest[:8], 16)  # 32 bits de base 16 a int

    return value % module


def load_tools():
    for _, module_name, _ in pkgutil.iter_modules(tools_pkg.__path__):
        module = importlib.import_module(f"mcp_server.tools.{module_name}")
        if hasattr(module, "TOOL"):
            tool = module.TOOL
            TOOLS[tool["name"]] = tool


def list_tools():
    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["input_schema"],
        }
        for _, tool in TOOLS.items()
    ]


def call_tool(name: str, args: dict):
    if name not in TOOLS:
        raise ValueError(f"Tool {name} no encontada")
    return TOOLS[name]["handler"](**args)


load_tools()

if __name__ == "__main__":
    list_tools()