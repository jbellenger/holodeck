# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "Holodeck",
    "author": "James Bellenger",
    "description": "Generate a slide deck from a blender animation",
    "blender": (4, 4, 0),
    "version": (0, 1, 0),
}

import importlib
import sys

_modules = [
    "core",
    "core.manifest_generator",
    "core.server",
    "handlers",
    "handlers.render_handlers",
    "handlers.ui_panel",
]


def _reload_modules():
    """Reload all sub-modules during development."""
    for module_name in _modules:
        full_name = f"{__name__}.{module_name}"
        if full_name in sys.modules:
            importlib.reload(sys.modules[full_name])


def register():
    _reload_modules()
    from .handlers import render_handlers, ui_panel
    render_handlers.register()
    ui_panel.register()


def unregister():
    from .handlers import render_handlers, ui_panel
    ui_panel.unregister()
    render_handlers.unregister()
