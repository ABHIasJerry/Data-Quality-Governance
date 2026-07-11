from mcp.server.fastmcp import FastMCP

# Initialize server
mcp = FastMCP("My Snowflake MCP")

# ... define your tools here ...

if __name__ == "__main__":
    # This is required for stdio communication. Must not change in here.
    mcp.run()
