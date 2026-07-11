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

# Get the directory where chat_app.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load variables from .env file
load_dotenv()

client = AsyncOpenAI()

# 1. Configuration for your custom local MCP server
server_params = StdioServerParameters(
    command="python", 
    args=[os.path.join(BASE_DIR, "mcp-server.py")],
)

@cl.on_chat_start
async def start():
    transport = await stdio_client(server_params).__aenter__()
    session = await ClientSession(transport[0], transport[1]).__aenter__()
    await session.initialize()
    cl.user_session.set("mcp_session", session)
    await cl.Message(content="System Ready. Snowflake MCP Server Connected.").send()

@cl.on_message
async def main(message: cl.Message):
    session = cl.user_session.get("mcp_session")
    mcp_tools = await session.list_tools()
    
    openai_tools = [
        {"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.inputSchema}}
        for tool in mcp_tools.tools
    ]

    messages = [{"role": "user", "content": message.content}]
    total_usage = {"prompt": 0, "completion": 0, "total": 0}
    
    # 3. LLM Processing Loop
    for i in range(5): 
        async with cl.Step(name="LLM Processing", type="llm") as step:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=openai_tools or None
            )
            
            # Aggregate Usage
            if response.usage:
                total_usage["prompt"] += response.usage.prompt_tokens
                total_usage["completion"] += response.completion_tokens or 0
                total_usage["total"] += response.usage.total_tokens

            msg = response.choices[0].message
            messages.append(msg)
        
        if not msg.tool_calls:
            tokens_text = (
                f"\n\n---\n**Total Token Usage:** {total_usage['total']} "
                f"(Prompt: {total_usage['prompt']}, Completion: {total_usage['completion']})"
            )
            await cl.Message(content=msg.content + tokens_text).send()
            break
        
        # 4. Handle Tool Execution
        for tool_call in msg.tool_calls:
            async with cl.Step(name=f"Tool: {tool_call.function.name}", type="tool") as tool_step:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                tool_step.input = tool_args
                
                result = await session.call_tool(tool_name, arguments=tool_args)
                
                tool_step.output = str(result.content)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result.content)
                })
