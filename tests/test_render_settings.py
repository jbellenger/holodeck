import pytest

from holodeck.core.render_settings import (
    DEFAULT_RESOLUTION_PERCENTAGE,
    HOLODECK_RENDER_FILE_FORMAT,
    HOLODECK_RENDER_MEDIA_TYPE,
    configure_scene_for_holodeck_render,
)


class _FakeImageSettings:
    def __init__(self):
        self.file_format = None


class _FakeRender:
    def __init__(self):
        self.engine = "CYCLES"
        self.filepath = ""
        self.use_file_extension = False
        self.resolution_percentage = 42
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


class _VideoImageSettings:
    def __init__(self):
        self.media_type = "VIDEO"
        self._file_format = "FFMPEG"

    @property
    def file_format(self):
        return self._file_format

    @file_format.setter
    def file_format(self, value):
        if value == HOLODECK_RENDER_FILE_FORMAT and self.media_type != HOLODECK_RENDER_MEDIA_TYPE:
            raise TypeError(f'enum "{value}" not found in (\'FFMPEG\')')
        self._file_format = value


class _RejectingRender(_FakeRender):
    def __init__(self):
        super().__init__()
        self.image_settings = _RejectingImageSettings()


class _VideoRender(_FakeRender):
    def __init__(self):
        super().__init__()
        self.image_settings = _VideoImageSettings()


class _LegacyEeveeRender(_FakeRender):
    def __init__(self):
        super().__init__()
        self._engine = "CYCLES"

    @property
    def engine(self):
        return self._engine

    @engine.setter
    def engine(self, value):
        if value == "BLENDER_EEVEE_NEXT":
            raise TypeError("enum not found")
        self._engine = value


class _RejectingScene:
    def __init__(self):
        self.render = _RejectingRender()


class _VideoScene:
    def __init__(self):
        self.render = _VideoRender()


class _LegacyEeveeScene:
    def __init__(self):
        self.render = _LegacyEeveeRender()


class TestConfigureSceneForHolodeckRender:
    def test_forces_avif_sequence_settings(self, tmp_path):
        scene = _FakeScene()
        render_dir = tmp_path / "render"

        configure_scene_for_holodeck_render(scene, render_dir)

        assert scene.render.filepath == str(render_dir) + "/"
        assert scene.render.use_file_extension is True
        assert scene.render.resolution_percentage == DEFAULT_RESOLUTION_PERCENTAGE
        assert scene.render.image_settings.file_format == HOLODECK_RENDER_FILE_FORMAT

    def test_keeps_blend_render_engine_by_default(self, tmp_path):
        scene = _FakeScene()

        configure_scene_for_holodeck_render(scene, tmp_path / "render")

        assert scene.render.engine == "CYCLES"

    def test_overrides_resolution_percentage(self, tmp_path):
        scene = _FakeScene()

        configure_scene_for_holodeck_render(
            scene,
            tmp_path / "render",
            resolution_percentage=50,
        )

        assert scene.render.resolution_percentage == 50

    def test_overrides_render_engine(self, tmp_path):
        scene = _FakeScene()

        configure_scene_for_holodeck_render(
            scene,
            tmp_path / "render",
            render_engine="workbench",
        )

        assert scene.render.engine == "BLENDER_WORKBENCH"

    def test_supports_legacy_eevee_engine_id(self, tmp_path):
        scene = _LegacyEeveeScene()

        configure_scene_for_holodeck_render(
            scene,
            tmp_path / "render",
            render_engine="eevee",
        )

        assert scene.render.engine == "BLENDER_EEVEE"

    def test_rejects_unknown_render_engine(self, tmp_path):
        scene = _FakeScene()

        with pytest.raises(ValueError, match="Render engine"):
            configure_scene_for_holodeck_render(
                scene,
                tmp_path / "render",
                render_engine="internal",
            )

    def test_converts_video_output_to_image_sequence_before_setting_avif(self, tmp_path):
        scene = _VideoScene()

        configure_scene_for_holodeck_render(scene, tmp_path / "render")

        assert scene.render.image_settings.media_type == HOLODECK_RENDER_MEDIA_TYPE
        assert scene.render.image_settings.file_format == HOLODECK_RENDER_FILE_FORMAT

    def test_raises_when_blender_cannot_write_avif(self, tmp_path):
        scene = _RejectingScene()

        try:
            configure_scene_for_holodeck_render(scene, tmp_path / "render")
        except RuntimeError as exc:
            assert HOLODECK_RENDER_FILE_FORMAT in str(exc)
        else:
            raise AssertionError("Expected RuntimeError when AVIF is unsupported")

    def test_raises_when_resolution_percentage_is_not_positive(self, tmp_path):
        scene = _FakeScene()

        with pytest.raises(ValueError, match="Resolution percentage"):
            configure_scene_for_holodeck_render(
                scene,
                tmp_path / "render",
                resolution_percentage=0,
            )
