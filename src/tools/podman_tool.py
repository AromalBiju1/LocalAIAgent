"""
Podman Management Tool — Manage containers and images.
"""

import logging
import subprocess
from typing import Dict, Any

from src.tools.base import BaseTool

logger = logging.getLogger(__name__)


class PodmanTool(BaseTool):
    """Manage Podman containers and images."""

    @property
    def name(self) -> str:
        return "podman"

    @property
    def description(self) -> str:
        return "Manage Podman containers. Supports running, listing, stopping, removing containers and images."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "enum": ["run", "list_containers", "list_images", "stop", "rm", "rmi", "logs", "inspect"],
                    "description": "The podman command to execute."
                },
                "image": {
                    "type": "string",
                    "description": "Image name (required for 'run')."
                },
                "container_id": {
                    "type": "string",
                    "description": "Container ID or name (required for stop, rm, logs, inspect)."
                },
                "args": {
                    "type": "string",
                    "description": "Additional arguments for the command (e.g., '-d -p 8080:80')."
                }
            },
            "required": ["command"],
        }

    async def execute(self, **kwargs) -> str:
        command = kwargs.get("command")
        image = kwargs.get("image")
        container_id = kwargs.get("container_id")
        args = kwargs.get("args", "")

        cmd = ["podman"]

        if command == "run":
            if not image:
                return "Error: 'image' is required for 'run' command."
            cmd.append("run")
            if args:
                cmd.extend(args.split())
            cmd.append(image)

        elif command == "list_containers":
            cmd.extend(["ps", "-a"])

        elif command == "list_images":
            cmd.append("images")

        elif command == "stop":
            if not container_id:
                return "Error: 'container_id' is required for 'stop' command."
            cmd.extend(["stop", container_id])

        elif command == "rm":
            if not container_id:
                return "Error: 'container_id' is required for 'rm' command."
            cmd.extend(["rm", container_id])

        elif command == "rmi":
            if not image:
                # 'rmi' usually takes an image ID or name, here mapped to 'image' arg for clarity,
                # or could potentialy use container_id if user provides ID there.
                # Let's check if container_id was provided as fallback or enforce image.
                target = image or container_id
                if not target:
                    return "Error: 'image' or 'container_id' is required for 'rmi' command."
                cmd.extend(["rmi", target])

        elif command == "logs":
            if not container_id:
                return "Error: 'container_id' is required for 'logs' command."
            cmd.extend(["logs", container_id])
            if args:
                cmd.extend(args.split())

        elif command == "inspect":
            target = container_id or image
            if not target:
                return "Error: 'container_id' or 'image' is required for 'inspect' command."
            cmd.extend(["inspect", target])

        else:
            return f"Error: Unknown command '{command}'."

        try:
            logger.info("Executing Podman command: %s", " ".join(cmd))
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                return result.stdout.strip() or "Command succeeded with no output."
            else:
                return f"Error (Exit Code {result.returncode}):\n{result.stderr.strip()}"

        except FileNotFoundError:
            return "Error: 'podman' executable not found. Please verify it is installed and in your PATH."
        except Exception as e:
            logger.error("Podman execution error: %s", e)
            return f"Error executing podman: {e}"
