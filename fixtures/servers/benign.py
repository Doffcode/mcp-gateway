"""Benign fixture whose honest tools use trigger words, each backed by a matching schema.
Used as a false-positive check: L2 should NOT flag these."""

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("benign")


@mcp.tool(description="Read a configuration file from disk and return its parsed keys.")
def read_config(file_path: str) -> str:
    return f"(demo) parsed {file_path}"


@mcp.tool(description="Send an email to a recipient with a subject and body.")
def send_email(to: str, subject: str, body: str) -> str:
    return f"(demo) queued email to {to}"


@mcp.tool(description="Fetch a web page over HTTP and return its text.")
def fetch_url(url: str) -> str:
    return f"(demo) fetched {url}"


@mcp.tool(description="Run the project's test suite with the given shell command.")
def run_tests(command: str) -> str:
    return f"(demo) would run: {command}"


if __name__ == "__main__":
    mcp.run()
