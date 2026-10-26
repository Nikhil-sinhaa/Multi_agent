import os
import sys
import asyncio

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq

load_dotenv()

llm = ChatGroq(model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"))

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AVIATION_STACK_API_KEY = os.getenv("AVIATION_STACK_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
        },
        "aviationstack": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [
                "-m",
                "aviationstack_mcp",
                "mcp",
                "run"
            ],
            "env": {
                "AVIATION_STACK_API_KEY": AVIATION_STACK_API_KEY
            }
        },
        "Weather": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [
                os.path.join(BASE_DIR, "custom_weather_mcp_server.py")
            ],
            "env": {
                "OPENWEATHER_API_KEY": OPENWEATHER_API_KEY
            }
        }
    }
)

# tools discovery
# Fixed: wrapped in if __name__ == "__main__" so it doesn't run on import
# and blocking asyncio.run(main()) was moved inside the guard

search_tool = None
aviation_tools = []  # Fixed: initialized as list (was only declared inside initialize_mcp via global)

async def initialize_mcp():
    global search_tool
    global aviation_tools

    if search_tool is not None and aviation_tools:
        return

    tools = await client.get_tools()
    print("\nAvailable MCP Tools:")

    for tool in tools:
        print(tool.name)

    # Fixed: next(tool for tool in tools ...) — was next(tools for tool in tools ...)
    search_tool = next(
        tool for tool in tools
        if tool.name == "tavily_search"
    )
    aviation_tools = [
        tool
        for tool in tools
        if tool.name in ("list_airports", "list_airlines", "aviationstack_search")
    ]


async def tavily_mcp_search(query: str):

    await initialize_mcp()

    result = await search_tool.ainvoke(
        {
            "query": query
        }
    )
    return result


async def aviation_mcp_call(
    tool_name: str,
    tool_args: dict = None
):
    tools = await client.get_tools()

    tool = next(
        t for t in tools
        if t.name == tool_name
    )
    result = await tool.ainvoke(
        tool_args or {}
    )
    return result


async def get_airports():
    await initialize_mcp()
    # Fixed: aviation_tools is a list, not a dict — use next() instead of .get()
    tool = next((t for t in aviation_tools if t.name == "list_airports"), None)
    if not tool:
        return "Airport tool unavailable"
    result = await tool.ainvoke({})
    return result


async def get_airlines():  # Fixed: was "async get_airlines():" — missing "def" keyword
    await initialize_mcp()
    # Fixed: aviation_tools is a list, not a dict — use next() instead of .get()
    tool = next((t for t in aviation_tools if t.name == "list_airlines"), None)
    if not tool:
        return "Airlines tool unavailable"
    result = await tool.ainvoke({})
    return result


weather_tool = None
forecast_tool= None

async def initialize_weather_mcp():
    global weather_tool
    global forecast_tool

    if weather_tool is not None and forecast_tool is not None:
        return
    
    tools = await client.get_tools()
    print("\nAvailable MCP Tools:")
    for tool in tools:
        print(tool.name)
    
    weather_tool = next(
        tool for tool in tools
        if tool.name == "get_current_weather"
    )
    
    forecast_tool = next(
        tool for tool in tools
        if tool.name == "get_forecast"
    )

async def weather_mcp_search(city:str):
    await initialize_weather_mcp()
    result = await weather_tool.ainvoke({"city": city})
    return result


async def forecast_mcp_search(city: str):
    await initialize_weather_mcp()
    result = await forecast_tool.ainvoke({"city": city})
    return result

def extract_destination(query:str):
    prompt = f"""
    Extract only the destination city or country

    Query:
    {query}

    return only destination name
    """
    response = llm.invoke(prompt)
    return response.content.strip()




# Fixed: wrapped in __main__ guard so it doesn't execute when imported by main.py
if __name__ == "__main__":
    async def _demo():
        tools = await client.get_tools()
        print("Tools:")
        for tool in tools:
            print(tool.name)

        search_t = next(
            tool for tool in tools
            if tool.name == "tavily_search"
        )
        result = await search_t.ainvoke({"query": "Best hotel in delhi"})
        print(result)

    asyncio.run(_demo())
