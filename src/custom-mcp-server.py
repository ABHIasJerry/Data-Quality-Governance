from typing import Any
import random
import socket
import httpx
import requests
from datetime import datetime
from mcp.server.fastmcp import FastMCP


# Initialize FastMCP server
mcp = FastMCP("custom_mcp_tools ")


@mcp.tool()
async def get_owner_name() -> str:
    """Get the name of the user or repository owner
    """
    # Repo owner name
    owner_name = "Abhinaba G"

    return str(owner_name)


@mcp.tool()
async def get_current_date() -> str:
    """Get current date
    """
    return str(datetime.today().strftime('%Y-%m-%d'))

@mcp.tool()
async def get_mcp_toollist() -> str:
    """Get list of of capable mcp tools
    """
    tools = await mcp.list_tools()
    return str(tools)

@mcp.tool()
async def get_local_ip_address() -> str:
    """Get the local ip address of the system
    """
    # Connect to an external host to determine local IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))  # Google's public DNS
    local_ip = s.getsockname()[0]
    s.close()
    return str(local_ip)

@mcp.tool()
async def get_public_ip_address() -> str:
    """Get the public IP address using an external service."""
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        response.raise_for_status()
        return str(response.json().get("ip"))
    except Exception as e:
        return f"Error getting public IP: {e}"

@mcp.tool()
async def get_system_hostname() -> str:
    """Get the system hostname"""
    hostname = socket.gethostname()
    return str(hostname)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
