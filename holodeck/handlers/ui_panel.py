"""
Blender UI panel for Holodeck controls.
"""
import bpy
import sys
import threading
import webbrowser
from pathlib import Path

from ..core import (
    create_server,
    get_player_url,
    validate_server_directory,
    check_player_exists,
    deploy_player,
)

# Platform-specific modifier key
_MODIFIER_KEY = "Cmd" if sys.platform == "darwin" else "Ctrl"

# Global server state
_server = None
_server_thread = None


class HOLODECK_OT_start_server(bpy.types.Operator):
    """Start the presentation server"""
    bl_idname = "holodeck.start_server"
    bl_label = "Start Server"
    bl_description = "Start HTTP server to view the presentation in a browser"

    def execute(self, context):
        global _server, _server_thread

        if _server is not None:
            self.report({'WARNING'}, "Server is already running")
            return {'CANCELLED'}

        # Validate blend file is saved
        blend_dir = validate_server_directory(bpy.data.filepath)
        if blend_dir is None:
            self.report({'ERROR'}, "Save the blend file first")
            return {'CANCELLED'}

        # Always deploy player files to ensure latest version
        try:
            deploy_player(blend_dir)
        except FileNotFoundError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        # Verify deployment succeeded
        if not check_player_exists(blend_dir):
            self.report({'ERROR'}, f"Failed to deploy player files to {blend_dir}")
            return {'CANCELLED'}

        port = context.scene.holodeck_server_port

        try:
            _server = create_server(port, blend_dir)

            def serve():
                _server.serve_forever()

            _server_thread = threading.Thread(target=serve, daemon=True)
            _server_thread.start()

            url = get_player_url(port)
            self.report({'INFO'}, f"Server started at {url}")

            # Optionally open browser
            if context.scene.holodeck_open_browser:
                webbrowser.open(url)

        except OSError as e:
            self.report({'ERROR'}, f"Failed to start server: {e}")
            _server = None
            return {'CANCELLED'}

        return {'FINISHED'}


class HOLODECK_OT_stop_server(bpy.types.Operator):
    """Stop the presentation server"""
    bl_idname = "holodeck.stop_server"
    bl_label = "Stop Server"
    bl_description = "Stop the HTTP server"

    def execute(self, context):
        global _server, _server_thread

        if _server is None:
            self.report({'WARNING'}, "Server is not running")
            return {'CANCELLED'}

        _server.shutdown()
        _server = None
        _server_thread = None

        self.report({'INFO'}, "Server stopped")
        return {'FINISHED'}


class HOLODECK_PT_main_panel(bpy.types.Panel):
    """Holodeck panel in the N-sidebar"""
    bl_label = "Holodeck"
    bl_idname = "HOLODECK_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Holodeck'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Server controls
        layout.label(text="Presentation Server:")

        row = layout.row()
        row.prop(scene, "holodeck_server_port", text="Port")

        row = layout.row()
        row.prop(scene, "holodeck_open_browser", text="Open Browser")

        row = layout.row(align=True)
        if _server is None:
            row.operator("holodeck.start_server", icon='PLAY')
        else:
            row.operator("holodeck.stop_server", icon='SNAP_FACE')

        # Status
        if _server is not None:
            port = scene.holodeck_server_port
            layout.label(text=f"Running on port {port}", icon='CHECKMARK')
        else:
            layout.label(text="Server stopped", icon='X')

        layout.separator()

        # Info
        layout.label(text="Workflow:")
        col = layout.column(align=True)
        col.scale_y = 0.8
        col.label(text="1. Add timeline markers (M)")
        col.label(text="2. Set output to render/")
        col.label(text=f"3. Render animation ({_MODIFIER_KEY}+F12)")
        col.label(text="4. Start server above")


def register():
    bpy.utils.register_class(HOLODECK_OT_start_server)
    bpy.utils.register_class(HOLODECK_OT_stop_server)
    bpy.utils.register_class(HOLODECK_PT_main_panel)

    bpy.types.Scene.holodeck_server_port = bpy.props.IntProperty(
        name="Server Port",
        description="Port for the HTTP server",
        default=8000,
        min=1024,
        max=65535,
    )
    bpy.types.Scene.holodeck_open_browser = bpy.props.BoolProperty(
        name="Open Browser",
        description="Automatically open browser when starting server",
        default=True,
    )


def unregister():
    global _server, _server_thread

    # Stop server if running
    if _server is not None:
        _server.shutdown()
        _server = None
        _server_thread = None

    del bpy.types.Scene.holodeck_server_port
    del bpy.types.Scene.holodeck_open_browser

    bpy.utils.unregister_class(HOLODECK_PT_main_panel)
    bpy.utils.unregister_class(HOLODECK_OT_stop_server)
    bpy.utils.unregister_class(HOLODECK_OT_start_server)
