"""Command line entry point: `booknest serve` or `booknest mcp`."""

from __future__ import annotations

import argparse

from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="booknest", description="Run the BookNest demo store.")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run the web UI and REST API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")

    sub.add_parser("mcp", help="Run the BookNest MCP server over stdio")

    args = parser.parse_args()
    if args.command == "serve":
        import uvicorn

        uvicorn.run(
            "booknest.app:create_app",
            factory=True,
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
    elif args.command == "mcp":
        from booknest.mcp_server import mcp

        mcp.run()


if __name__ == "__main__":
    main()
