from holodeck.core.render_settings import (
    HOLODECK_RENDER_FILE_FORMAT,
    configure_scene_for_holodeck_render,
)


class _FakeImageSettings:
    def __init__(self):
        self.file_format = None


class _FakeRender:
    def __init__(self):
        self.filepath = ""
        self.use_file_extension = False
        self.image_settings = _FakeImageSettings()


class _FakeScene:
    def __init__(self):
        self.render = _FakeRender()


class _RejectingImageSettings:
    @property
    def file_format(self):
        return None

    @file_format.setter
    def file_format(self, _value):
        raise TypeError("enum not found")


class _RejectingRender(_FakeRender):
    def __init__(self):
        super().__init__()
        self.image_settings = _RejectingImageSettings()


class _RejectingScene:
    def __init__(self):
        self.render = _RejectingRender()


class TestConfigureSceneForHolodeckRender:
    def test_forces_avif_sequence_settings(self, tmp_path):
        scene = _FakeScene()
        render_dir = tmp_path / "render"

        configure_scene_for_holodeck_render(scene, render_dir)

        assert scene.render.filepath == str(render_dir) + "/"
        assert scene.render.use_file_extension is True
        assert scene.render.image_settings.file_format == HOLODECK_RENDER_FILE_FORMAT

    def test_raises_when_blender_cannot_write_avif(self, tmp_path):
        scene = _RejectingScene()

        try:
            configure_scene_for_holodeck_render(scene, tmp_path / "render")
        except RuntimeError as exc:
            assert HOLODECK_RENDER_FILE_FORMAT in str(exc)
        else:
            raise AssertionError("Expected RuntimeError when AVIF is unsupported")
