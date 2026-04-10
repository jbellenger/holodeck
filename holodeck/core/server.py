"""
Server-related logic for Holodeck.
This module contains NO bpy imports and can be tested independently.
"""
import http.server
import shutil
import socketserver
from pathlib import Path
from urllib.parse import urlparse

from .runtime import get_package_path, get_package_root

# Default player directory name (minimal footprint)
DEFAULT_PLAYER_DIR = ""
CANONICAL_PLAYER_DIRNAME = "holodeck-player"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that suppresses request logging."""

    def log_message(self, format, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", self._get_cache_control_header())
        super().end_headers()

    def _get_cache_control_header(self) -> str:
        request_path = urlparse(self.path).path
        suffix = Path(request_path).suffix.lower()

        if request_path.endswith("/") or suffix in {".html", ".json", ".js", ".css"}:
            return "no-cache"

        if suffix in {".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif"}:
            return "public, max-age=31536000, immutable"

        return "public, max-age=3600"


class QuietServer(socketserver.TCPServer):
    """TCP server that allows address reuse and suppresses errors."""

    allow_reuse_address = True

    def handle_error(self, request, client_address):
        # Suppress BrokenPipeError (browser cancelled request)
        pass


def get_resources_dir() -> Path:
    """Get the player asset directory, preferring the canonical source tree when available."""
    package_root = get_package_root()
    canonical_player_dir = package_root.parent / CANONICAL_PLAYER_DIRNAME
    if canonical_player_dir.is_dir() and (canonical_player_dir / "index.html").is_file():
        return canonical_player_dir
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
