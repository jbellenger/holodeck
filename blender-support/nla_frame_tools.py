try:
    import bpy
except ImportError:  # pragma: no cover - exercised by the pytest unit tests.
    bpy = None


bl_info = {
    "name": "NLA Frame Tools",
    "author": "Custom",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "location": "NLA Editor > N-Panel > NLA Tools",
    "description": "Insert or delete frames in the NLA timeline, shifting strips and markers",
    "category": "Animation",
}


class ShiftReport:
    def __init__(self):
        self.shifted_strips = 0
        self.skipped_strips = 0
        self.shifted_markers = 0
        self.clamped_markers = 0
        self.warnings = []

    def add_warning(self, message):
        self.warnings.append(message)


def _strip_name(strip):
    return getattr(strip, "name", "<unnamed strip>")


def _track_name(track):
    return getattr(track, "name", "<unnamed track>")


def _source_name(source):
    return getattr(source, "name", "<unnamed source>")


def _frame_start(strip):
    return float(strip.frame_start)


def _frame_end(strip):
    return float(strip.frame_end)


def _overlaps(first_start, first_end, second_start, second_end):
    return first_start < second_end and first_end > second_start


def _set_strip_interval(strip, new_start, new_end, frame_delta):
    # Set the far edge first so Blender never sees a transiently shortened strip.
    if frame_delta > 0:
        strip.frame_end = new_end
        strip.frame_start = new_start
    else:
        strip.frame_start = new_start
        strip.frame_end = new_end


def _iter_nla_tracks(source):
    animation_data = getattr(source, "animation_data", None)
    if not animation_data:
        return ()
    return getattr(animation_data, "nla_tracks", ()) or ()


def _shift_track_strips(source, track, current_frame, frame_delta, report):
    strips = list(getattr(track, "strips", ()) or ())
    if not strips:
        return

    if frame_delta > 0:
        candidate_cutoff = current_frame
        candidates = [
            strip for strip in strips
            if _frame_start(strip) >= candidate_cutoff
        ]
        candidates.sort(key=_frame_start, reverse=True)
    else:
        candidate_cutoff = current_frame + abs(frame_delta)
        candidates = [
            strip for strip in strips
            if _frame_start(strip) >= candidate_cutoff
        ]
        candidates.sort(key=_frame_start)

    planned = {
        id(strip): (_frame_start(strip), _frame_end(strip))
        for strip in strips
    }

    moves = []
    for strip in candidates:
        old_start, old_end = planned[id(strip)]
        new_start = old_start + frame_delta
        new_end = old_end + frame_delta
        blocker = None

        for other in strips:
            if other is strip:
                continue
            other_start, other_end = planned[id(other)]
            if _overlaps(new_start, new_end, other_start, other_end):
                blocker = other
                break

        if blocker:
            report.skipped_strips += 1
            report.add_warning(
                "Skipped shifting "
                f"{_source_name(source)} / {_track_name(track)} / {_strip_name(strip)} "
                f"to {new_start:g}-{new_end:g}; it would overlap {_strip_name(blocker)}."
            )
            continue

        planned[id(strip)] = (new_start, new_end)
        moves.append((strip, new_start, new_end))

    for strip, new_start, new_end in moves:
        _set_strip_interval(strip, new_start, new_end, frame_delta)
        report.shifted_strips += 1


def shift_sources_and_markers(sources, markers, current_frame, frame_delta):
    report = ShiftReport()
    if frame_delta == 0:
        return report

    for source in sources:
        for track in _iter_nla_tracks(source):
            _shift_track_strips(source, track, current_frame, frame_delta, report)

    if frame_delta > 0:
        for marker in markers:
            if marker.frame > current_frame:
                marker.frame += frame_delta
                report.shifted_markers += 1
    else:
        delete_end = current_frame + abs(frame_delta)
        for marker in markers:
            if marker.frame > delete_end:
                marker.frame += frame_delta
                report.shifted_markers += 1
            elif current_frame < marker.frame <= delete_end:
                marker.frame = current_frame
                report.clamped_markers += 1

    return report


def iter_animation_sources():
    if bpy is None:
        return ()

    data_collections = (
        "objects",
        "scenes",
        "cameras",
        "lights",
        "materials",
        "worlds",
        "curves",
        "meshes",
        "node_groups",
        "collections",
    )
    sources = []
    seen = set()
    for collection_name in data_collections:
        collection = getattr(bpy.data, collection_name, ()) or ()
        for source in collection:
            if id(source) in seen:
                continue
            seen.add(id(source))
            if getattr(source, "animation_data", None):
                sources.append(source)
    return sources


def shift_nla_strips_and_markers(context, current_frame, frame_delta):
    """
    Shift NLA strips and markers by frame_delta.

    Insertions shift strips starting at or after the playhead. Deletions shift
    strips starting after the deleted span. Any strip move that would collide
    with another strip on the same NLA track is skipped and reported instead of
    relying on Blender's overlap clamping, which can visibly shorten a strip.
    """
    scene = context.scene
    sources = iter_animation_sources()
    return shift_sources_and_markers(
        sources,
        scene.timeline_markers,
        current_frame,
        frame_delta,
    )


if bpy is not None:
    class NLA_OT_InsertFrames(bpy.types.Operator):
        """Insert frames at the current playhead, shifting strips and markers to the right"""
        bl_idname = "nla.insert_frames"
        bl_label = "Insert Frames"
        bl_options = {"REGISTER", "UNDO"}

        num_frames: bpy.props.IntProperty(
            name="Frames",
            description="Number of frames to insert",
            default=10,
            min=1,
            soft_max=500,
        )

        def execute(self, context):
            current_frame = context.scene.frame_current
            report = shift_nla_strips_and_markers(context, current_frame, self.num_frames)
            if report.warnings:
                self.report(
                    {"WARNING"},
                    f"Inserted {self.num_frames} frames; skipped "
                    f"{report.skipped_strips} strip(s) to avoid overlap.",
                )
            else:
                self.report(
                    {"INFO"},
                    f"Inserted {self.num_frames} frames at frame {current_frame}",
                )
            return {"FINISHED"}


    class NLA_OT_DeleteFrames(bpy.types.Operator):
        """Delete frames to the right of the current playhead, shifting strips and markers to the left"""
        bl_idname = "nla.delete_frames"
        bl_label = "Delete Frames"
        bl_options = {"REGISTER", "UNDO"}

        num_frames: bpy.props.IntProperty(
            name="Frames",
            description="Number of frames to delete",
            default=10,
            min=1,
            soft_max=500,
        )

        def execute(self, context):
            current_frame = context.scene.frame_current
            report = shift_nla_strips_and_markers(context, current_frame, -self.num_frames)
            if report.warnings:
                self.report(
                    {"WARNING"},
                    f"Deleted {self.num_frames} frames; skipped "
                    f"{report.skipped_strips} strip(s) to avoid overlap.",
                )
            else:
                self.report(
                    {"INFO"},
                    f"Deleted {self.num_frames} frames at frame {current_frame}",
                )
            return {"FINISHED"}


    class NLA_PT_FrameTools(bpy.types.Panel):
        """NLA Frame Tools Panel"""
        bl_label = "NLA Frame Tools"
        bl_idname = "NLA_PT_nla_frame_tools"
        bl_space_type = "NLA_EDITOR"
        bl_region_type = "UI"
        bl_category = "NLA Tools"

        def draw(self, context):
            layout = self.layout
            scene = context.scene

            layout.label(text=f"Playhead: frame {scene.frame_current}", icon="TIME")
            layout.separator()

            col = layout.column(align=True)
            col.label(text="Insert Frames at Playhead:")

            row = col.row(align=True)
            row.prop(scene, "nla_tool_insert_frames", text="")
            op = row.operator("nla.insert_frames", text="Insert", icon="ADD")
            op.num_frames = scene.nla_tool_insert_frames

            layout.separator()

            col = layout.column(align=True)
            col.label(text="Delete Frames after Playhead:")

            row = col.row(align=True)
            row.prop(scene, "nla_tool_delete_frames", text="")
            op = row.operator("nla.delete_frames", text="Delete", icon="REMOVE")
            op.num_frames = scene.nla_tool_delete_frames

            layout.separator()
            layout.label(text="Rules:", icon="INFO")
            col = layout.column(align=True)
            col.scale_y = 0.75
            col.label(text="Insert shifts strips starting at/after playhead")
            col.label(text="Delete shifts strips after deleted range")
            col.label(text="Overlap-risk strip moves are skipped")
            col.label(text="Markers inside deleted range clamp to playhead")


    classes = (
        NLA_OT_InsertFrames,
        NLA_OT_DeleteFrames,
        NLA_PT_FrameTools,
    )
else:
    classes = ()


def register():
    if bpy is None:
        return

    bpy.types.Scene.nla_tool_insert_frames = bpy.props.IntProperty(
        name="Insert Frames",
        default=10,
        min=1,
        soft_max=500,
    )
    bpy.types.Scene.nla_tool_delete_frames = bpy.props.IntProperty(
        name="Delete Frames",
        default=10,
        min=1,
        soft_max=500,
    )

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    if bpy is None:
        return

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.nla_tool_insert_frames
    del bpy.types.Scene.nla_tool_delete_frames


if __name__ == "__main__":
    register()
