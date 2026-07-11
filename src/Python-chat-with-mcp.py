# pip install chainlit mcp openai
# Create the Host (app.py) -> In your Chainlit app, you will initialize an MCP Client that connects to your local server process.
# Create a .env file and add -> OPENAI_API_KEY=sk-your-actual-api-key-here
# Run the code -> chainlit run <filename>.py

import os
from dotenv import load_dotenv
import chainlit as cl
import json
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load variables from .env file
load_dotenv()

# Initialize OpenAI 
# AsyncOpenAI automatically pulls OPENAI_API_KEY from os.environ
client = AsyncOpenAI()

# 1. Configuration for your custom local MCP server
server_params = StdioServerParameters(
    command="python", 
    args=["path/to/your/mcp_server.py"], 
)

@cl.on_chat_start
async def start():
    # 2. Establish persistent session for the chat duration
    # We use a context manager to hold the connection
    transport = await stdio_client(server_params).__aenter__()
    session = await ClientSession(transport[0], transport[1]).__aenter__()
    
    await session.initialize()
    
    # Store session in user_session for access in @on_message
    cl.user_session.set("mcp_session", session)
    await cl.Message(content="System Ready. MCP Server Connected.").send()

@cl.on_message
async def main(message: cl.Message):
    session = cl.user_session.get("mcp_session")
    mcp_tools = await session.list_tools()
    
    # Format tools for OpenAI
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            },
        }
        for tool in mcp_tools.tools
    ]

    messages = [{"role": "user", "content": message.content}]
    
    # 3. LLM Processing Loop
    # We loop to allow the model to call multiple tools or finish its response
    for _ in range(5): 
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=openai_tools or None
        )
        
        msg = response.choices[0].message
        messages.append(msg)
        
        if not msg.tool_calls:
            await cl.Message(content=msg.content).send()
            break
        
        # 4. Handle Tool Execution
        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            
            # Use MCP session to execute
            result = await session.call_tool(tool_name, arguments=tool_args)
            
            # Send result back to LLM
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result.content)
            })
