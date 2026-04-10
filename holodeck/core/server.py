"""
Server-related logic for Holodeck.
This module contains NO bpy imports and can be tested independently.
"""
import http.server
import shutil
import socketserver
from pathlib import Path

from .runtime import get_package_path

# Default player directory name (minimal footprint)
DEFAULT_PLAYER_DIR = ""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that suppresses request logging."""

    def log_message(self, format, *args):
        pass


class QuietServer(socketserver.TCPServer):
    """TCP server that allows address reuse and suppresses errors."""

    allow_reuse_address = True

    def handle_error(self, request, client_address):
        # Suppress BrokenPipeError (browser cancelled request)
        pass


def get_resources_dir() -> Path:
    """Get the path to the bundled resources directory."""
    return get_package_path("resources")


def deploy_player(target_dir: Path, player_dirname: str = DEFAULT_PLAYER_DIR) -> Path:
    """
    Deploy the player files to the target directory.

    Args:
        target_dir: Directory to deploy into
        player_dirname: Name for the player subdirectory

    Returns:
        Path to the deployed player directory

    Raises:
        FileNotFoundError: If bundled resources are missing
    """
    resources = get_resources_dir()
    if not resources.exists() or not (resources / "index.html").exists():
        raise FileNotFoundError(
            f"Bundled player resources not found at {resources}. "
            f"The Holodeck package may be incorrectly installed."
        )

    player_dir = target_dir / player_dirname if player_dirname else target_dir
    player_dir.mkdir(parents=True, exist_ok=True)

    for resource in resources.iterdir():
        destination = player_dir / resource.name
        if resource.is_dir():
            shutil.copytree(resource, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(resource, destination)

    return player_dir


def get_player_url(port: int, player_path: str = DEFAULT_PLAYER_DIR) -> str:
    """
    Construct the URL for the player.

    Args:
        port: The server port
        player_path: Path to the player directory relative to server root

    Returns:
        Full URL to access the player
    """
    normalized_path = player_path.strip("/")
    if not normalized_path:
        return f"http://localhost:{port}/"
    return f"http://localhost:{port}/{normalized_path}/"


def check_player_exists(server_dir: Path, player_path: str = DEFAULT_PLAYER_DIR) -> bool:
    """
    Check if the player directory exists in the server directory.

    Args:
        server_dir: The directory being served
        player_path: Expected player directory name

    Returns:
        True if player exists, False otherwise
    """
    player_dir = server_dir / player_path if player_path else server_dir
    index_file = player_dir / "index.html"
    return player_dir.is_dir() and index_file.is_file()


def create_server(port: int, directory: Path) -> QuietServer:
    """
    Create an HTTP server for the given directory.

    Args:
        port: Port to serve on
        directory: Directory to serve files from

    Returns:
        Configured server instance
    """
    handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(directory), **kwargs)
    return QuietServer(("", port), handler)
