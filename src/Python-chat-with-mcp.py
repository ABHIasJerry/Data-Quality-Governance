# pip install chainlit mcp openai
# Create the Host (app.py) -> In your Chainlit app, you will initialize an MCP Client that connects to your local server process.

import chainlit as cl
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 1. Define how to connect to your MCP server (stdio)
server_params = StdioServerParameters(
    command="python", # path to your python executable
    args=["path/to/your/mcp_server.py"], # path to your server script
)

@cl.on_chat_start
async def start():
    # 2. Establish session
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize and list tools
            await session.initialize()
            tools = await session.list_tools()
            cl.user_session.set("mcp_session", session)
            cl.user_session.set("tools", tools)

@cl.on_message
async def main(message: cl.Message):
    session = cl.user_session.get("mcp_session")
    
    # 3. Logic: Send user message to LLM (e.g., OpenAI)
    # If the LLM decides to use a tool, call session.call_tool()
    # Chainlit will handle the UI display
    response = await call_llm_with_tools(message.content, session)
    await cl.Message(content=response).send()
