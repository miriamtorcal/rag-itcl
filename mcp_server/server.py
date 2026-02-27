import importlib
import pkgutil

from mcp.server.fastmcp import FastMCP

# Inicializar FastMCP
mcp = FastMCP("ITCL MCP Server")

# Cargar dinámicamente todas las tools desde mcp_server/tools/
tools_package = "mcp_server.tools"
for _, modname, ispkg in pkgutil.iter_modules([tools_package.replace(".", "/")]):
    module = importlib.import_module(f"{tools_package}.{modname}")
    for tool_name in getattr(module, "__all__", []):
        tool_func = getattr(module, tool_name)
        mcp.tool()(tool_func)  # registramos la tool en FastMCP

# Run server con FastMCP SSE
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
