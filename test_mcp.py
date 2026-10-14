import asyncio
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async def run_test():
    url = "http://localhost:8000/sse"
    print(f"Conectando a {url}...")
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                # 1. Inicialización
                await session.initialize()
                print("✅ Sesión inicializada")

                # 2. Listar herramientas
                response = await session.list_tools()
                print(f"Herramientas detectadas: {[t.name for t in response.tools]}")

                # 3. Probar Tool 1: fx_rate (Dinámica)
                print("\n--- Probando fx_rate ---")
                res_fx = await session.call_tool("fx_rate", arguments={"base": "EUR", "quote": "USD"})
                print(f"Resultado FX: {res_fx.content[0].text}")

                # 4. Probar Tool 2: market_status (Dinámica)
                print("\n--- Probando market_status ---")
                # Probamos con un nombre de mercado para ver la lógica de longitud par/impar
                res_market = await session.call_tool("market_status", arguments={"market": "NASDAQ"})
                print(f"Resultado Mercado (NASDAQ): {res_market.content[0].text}")
                
                res_market2 = await session.call_tool("market_status", arguments={"market": "NYSE"})
                print(f"Resultado Mercado (NYSE): {res_market2.content[0].text}")

    except Exception as e:
        print(f"❌ Error durante el test: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())