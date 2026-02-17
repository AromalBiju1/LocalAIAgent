#!/usr/bin/env python3
"""
run.py — Unified launcher for ElyssiaAgent.

Usage:
    python run.py --mode cli              # CLI chat
    python run.py --mode web              # Start FastAPI + WebUI
    python run.py --mode web --port 8000  # Custom port
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_cli(args):
    """Launch the Chat CLI interface."""
    import sys
    sys.argv = ["llm_cli.py", "--interactive", "--stream"]
    if args.model:
        sys.argv.extend(["--model", args.model])
    if args.backend:
        sys.argv.extend(["--backend", args.backend])
        
    # Execute the script in the current process
    with open(os.path.join(os.path.dirname(__file__), "llm_cli.py")) as f:
        code = compile(f.read(), "llm_cli.py", 'exec')
        exec(code, {
            "__name__": "__main__",
            "__file__": os.path.join(os.path.dirname(__file__), "llm_cli.py")
        })


def run_web(args):
    """Launch the FastAPI backend server."""
    import uvicorn

    print(f"""
\033[35m\033[1m  ╔═══════════════════════════════════════╗
  ║        ElyssiaAgent  •  WebUI        ║
  ╚═══════════════════════════════════════╝\033[0m

  Backend:  http://0.0.0.0:{args.port}
  API docs: http://localhost:{args.port}/docs
  Frontend: http://localhost:3000 (run: cd web && npm run dev)
""")

    uvicorn.run(
        "src.api.server:app",
        host="0.0.0.0",
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


def run_manage(args):
    """Launch the Management CLI Gateway."""
    from src.cli.cli_gateway import CLIGateway
    
    # We need to strip the initial arguments so argparse inside CLIGateway
    # doesn't get confused by 'run.py --mode manage'
    # CLIGateway uses its own parser.
    # We'll forward the rest of the arguments after '--' if any,
    # or just let it handle sys.argv filtering
    
    # Simple hack: Remove known args from sys.argv for the underlying CLI
    sys.argv = [sys.argv[0]] + args.extras
    
    cli = CLIGateway()
    cli.run()


def main():
    parser = argparse.ArgumentParser(
        description="ElyssiaAgent — Unified Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  chat      Start interactive chat (default)
  web       Start FastAPI backend
  manage    System management (setup, plugins, stats)

Examples:
  python run.py --mode chat
  python run.py --mode web
  python run.py --mode manage setup
  python run.py --mode manage status
""",
    )
    parser.add_argument("--mode", choices=["chat", "web", "manage", "cli"], default="chat", help="Run mode")
    parser.add_argument("--port", type=int, default=8001, help="Web API port")
    parser.add_argument("--reload", action="store_true", help="Auto-reload (web)")
    parser.add_argument("--model", default=None, help="Model override")
    parser.add_argument("--backend", default=None, help="Backend override")
    
    # Capture functionality for manage mode subcommands
    parser.add_argument("extras", nargs=argparse.REMAINDER, help="Arguments for manage mode")

    args = parser.parse_args()

    if args.mode in ["chat", "cli"]:
        run_cli(args)
    elif args.mode == "manage":
        run_manage(args)
    else:
        run_web(args)


if __name__ == "__main__":
    main()
