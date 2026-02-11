import requests
from client.utils.settings import MCP_URL


def discover_tools():
    try:
        resp = requests.get(f"{MCP_URL}/tools", timeout=5)
        data = resp.json()
        print(f"Data -> {data}")
        return [tool["name"] for tool in data.get("tools", [])]
    except Exception:
        return []


def get_available_tools():
    """Obtener tools bajo demanda, no en import."""
    return discover_tools()
