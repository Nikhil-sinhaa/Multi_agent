import os
import asyncio

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AVIATION_STACK_API_KEY = os.getenv("AVIATION_STACK_API_KEY")
client = MultiServerMCPClient(
    {
        "tavily": {
            "transport":"streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
        },
        "aviationstack":{
            "transport":"stdio",
            "command": r"C:\Users\nikhi\OneDrive\Documents\Notes\Rag\multiagent project\aviationstack-mcp\.venv\Scripts\python.exe",
            "args":[
                "-m",
                "aviationstack_mcp",
                "mcp",
                "run"
            ],
            "env":{
                "AVIATION_STACK_API_KEY":AVIATION_STACK_API_KEY
            }

        }
    }
) 
#tools discovery  

async def main():

    tools = await client.get_tools()

    search_tool = next(
        tools
        for tool in tools
        if tool.name == "tavily_search"
    )

    result = await search_tool.ainvoke(
        {
            "query":"Best hotel in delhi"
        }
    )
    print(result)

    for tool in tools:
        print(tool.name)


asyncio.run(main())

search_tool = None
async def initialize_mcp():
    global search_tool
    global aviation_tools

    if search_tool is not None and aviation_tools:
        return
    tools = await client.get_tools()
    print("\nAvailable MCP Tools:")

    for tool in tools:
        print(tool.name)

    search_tool = next(
        tools
        for tool in tools
        if tool.name == "tavily_search"
    )
    aviation_tools = [
        tool
        for tool in tools
        if tool.name == "aviationstack_search"
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
    tool = aviation_tools.get("list_airports")
    if not tool:
        return "Airport tool unavailable"
    result = await tool.ainvoke({})

    return result

async get_airlines():

    await initialize_mcp()
    tool = aviation_tools.get("list_airlines")
    if not tool:
        return "Airlines tool unavailable"
    result = await tool.ainvoke({})
    return result


