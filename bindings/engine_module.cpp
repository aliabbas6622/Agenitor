/**
 * @file engine_module.cpp
 * @brief pybind11 bindings exposing the C++ engine to Python.
 *
 * This creates the `engine_py` module that the Python AI orchestration
 * layer imports to drive the C++ timeline and renderer directly.
 *
 * Usage from Python:
 *   import engine_py
 *   timeline = engine_py.Timeline("id-123", "My Project")
 *   timeline.add_track(engine_py.Track("t1", engine_py.TrackType.Video))
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

#include "engine/clip.hpp"
#include "engine/export.hpp"
#include "engine/ffmpeg_renderer.hpp"
#include "engine/frame_grabber.hpp"
#include "engine/renderer.hpp"
#include "engine/timeline.hpp"
#include "engine/track.hpp"

namespace py = pybind11;

PYBIND11_MODULE(engine_py, m) {
    m.doc() = "AI Video Editor — C++ Engine bindings";

    // ── TrackType enum ───────────────────────────────────
    py::enum_<engine::TrackType>(m, "TrackType")
        .value("Video", engine::TrackType::Video)
        .value("Audio", engine::TrackType::Audio)
        .value("Subtitle", engine::TrackType::Subtitle)
        .export_values();

    // ── Effect struct ────────────────────────────────────
    py::class_<engine::Effect>(m, "Effect")
        .def(py::init<>())
        .def_readwrite("id", &engine::Effect::id)
        .def_readwrite("type", &engine::Effect::type)
        .def_readwrite("start_time", &engine::Effect::start_time)
        .def_readwrite("duration", &engine::Effect::duration)
        .def_readwrite("parameters", &engine::Effect::parameters);

    // ── Transition struct ────────────────────────────────
    py::class_<engine::Transition>(m, "Transition")
        .def(py::init<>())
        .def_readwrite("id", &engine::Transition::id)
        .def_readwrite("type", &engine::Transition::type)
        .def_readwrite("duration", &engine::Transition::duration);

    // ── Clip ─────────────────────────────────────────────
    py::class_<engine::Clip>(m, "Clip")
        .def(py::init<>())
        .def(py::init<const std::string&, const std::string&, double, double>(),
             py::arg("id"), py::arg("source_path"),
             py::arg("in_point"), py::arg("out_point"))
        .def("id", &engine::Clip::id)
        .def("source_path", &engine::Clip::source_path)
        .def("position", &engine::Clip::position)
        .def("in_point", &engine::Clip::in_point)
        .def("out_point", &engine::Clip::out_point)
        .def("duration", &engine::Clip::duration)
        .def("playback_speed", &engine::Clip::playback_speed)
        .def("volume", &engine::Clip::volume)
        .def("set_position", &engine::Clip::set_position)
        .def("set_in_point", &engine::Clip::set_in_point)
        .def("set_out_point", &engine::Clip::set_out_point)
        .def("set_playback_speed", &engine::Clip::set_playback_speed)
        .def("set_volume", &engine::Clip::set_volume)
        .def("add_effect", &engine::Clip::add_effect)
        .def("remove_effect", &engine::Clip::remove_effect)
        .def("effects", &engine::Clip::effects);

    // ── Track ────────────────────────────────────────────
    py::class_<engine::Track>(m, "Track")
        .def(py::init<>())
        .def(py::init<const std::string&, engine::TrackType, const std::string&>(),
             py::arg("id"), py::arg("type"), py::arg("name") = "")
        .def("id", &engine::Track::id)
        .def("type", &engine::Track::type)
        .def("name", &engine::Track::name)
        .def("duration", &engine::Track::duration)
        .def("clip_count", &engine::Track::clip_count)
        .def("clips", &engine::Track::clips)
        .def("add_clip", &engine::Track::add_clip)
        .def("remove_clip", &engine::Track::remove_clip)
        .def("sort_clips", &engine::Track::sort_clips)
        .def("set_muted", &engine::Track::set_muted)
        .def("set_locked", &engine::Track::set_locked)
        .def("set_opacity", &engine::Track::set_opacity);

    // ── Timeline ─────────────────────────────────────────
    py::class_<engine::Timeline>(m, "Timeline")
        .def(py::init<>())
        .def(py::init<const std::string&, const std::string&>(),
             py::arg("id"), py::arg("project_name") = "Untitled")
        .def("id", &engine::Timeline::id)
        .def("project_name", &engine::Timeline::project_name)
        .def("duration", &engine::Timeline::duration)
        .def("track_count", &engine::Timeline::track_count)
        .def("tracks", &engine::Timeline::tracks)
        .def("add_track", &engine::Timeline::add_track)
        .def("remove_track", &engine::Timeline::remove_track)
        .def("to_json", &engine::Timeline::to_json)
        .def_static("from_json", &engine::Timeline::from_json);

    // ── ExportConfig ─────────────────────────────────────
    py::class_<engine::ExportConfig>(m, "ExportConfig")
        .def(py::init<>())
        .def_readwrite("format", &engine::ExportConfig::format)
        .def_readwrite("resolution", &engine::ExportConfig::resolution)
        .def_readwrite("codec", &engine::ExportConfig::codec)
        .def_readwrite("frame_rate", &engine::ExportConfig::frame_rate)
        .def_readwrite("bitrate_kbps", &engine::ExportConfig::bitrate_kbps)
        .def_readwrite("output_path", &engine::ExportConfig::output_path);

    // ── ExportResult ─────────────────────────────────────
    py::class_<engine::ExportResult>(m, "ExportResult")
        .def(py::init<>())
        .def_readonly("success", &engine::ExportResult::success)
        .def_readonly("output_path", &engine::ExportResult::output_path)
        .def_readonly("error_message", &engine::ExportResult::error_message)
        .def_readonly("duration_seconds", &engine::ExportResult::duration_seconds);

    // ── Renderer ─────────────────────────────────────────
    py::class_<engine::IRenderer, std::shared_ptr<engine::IRenderer>>(m, "IRenderer")
        .def("name", &engine::IRenderer::name)
        .def("is_rendering", &engine::IRenderer::is_rendering)
        .def("cancel", &engine::IRenderer::cancel);

    py::class_<engine::DummyRenderer, engine::IRenderer, std::shared_ptr<engine::DummyRenderer>>(m, "DummyRenderer")
        .def(py::init<>());

    // ── FFmpegRenderer ───────────────────────────────────
    py::class_<engine::FFmpegRenderer, engine::IRenderer, std::shared_ptr<engine::FFmpegRenderer>>(m, "FFmpegRenderer")
        .def(py::init<>())
        .def("name", &engine::FFmpegRenderer::name)
        .def("is_rendering", &engine::FFmpegRenderer::is_rendering)
        .def("cancel", &engine::FFmpegRenderer::cancel);

    // ── ExportController ─────────────────────────────────
    py::class_<engine::ExportController>(m, "ExportController")
        .def(py::init<std::shared_ptr<engine::IRenderer>>())
        .def("run", &engine::ExportController::run,
             py::arg("timeline"), py::arg("config"),
             py::arg("on_progress") = nullptr)
        .def("cancel", &engine::ExportController::cancel);

    // ── FrameData ────────────────────────────────────────
    py::class_<engine::FrameData>(m, "FrameData")
        .def(py::init<>())
        .def_readonly("rgb_data", &engine::FrameData::rgb_data)
        .def_readonly("width", &engine::FrameData::width)
        .def_readonly("height", &engine::FrameData::height)
        .def_readonly("timestamp", &engine::FrameData::timestamp)
        .def_readonly("valid", &engine::FrameData::valid)
        .def("to_bytes", [](const engine::FrameData& self) {
            return py::bytes(reinterpret_cast<const char*>(self.rgb_data.data()),
                            self.rgb_data.size());
        });

    // ── IFrameGrabber ────────────────────────────────────
    py::class_<engine::IFrameGrabber, std::shared_ptr<engine::IFrameGrabber>>(m, "IFrameGrabber")
        .def("grab_frame", &engine::IFrameGrabber::grab_frame,
             py::arg("timeline"),
             py::arg("timestamp_seconds"),
             py::arg("width") = 640,
             py::arg("height") = 360)
        .def("cancel", &engine::IFrameGrabber::cancel)
        .def("is_grabbing", &engine::IFrameGrabber::is_grabbing);

    // ── FrameGrabber ─────────────────────────────────────
    py::class_<engine::FrameGrabber, engine::IFrameGrabber, std::shared_ptr<engine::FrameGrabber>>(m, "FrameGrabber")
        .def(py::init<>())
        .def("grab_frame", &engine::FrameGrabber::grab_frame,
             py::arg("timeline"),
             py::arg("timestamp_seconds"),
             py::arg("width") = 640,
             py::arg("height") = 360)
        .def("cancel", &engine::FrameGrabber::cancel)
        .def("is_grabbing", &engine::FrameGrabber::is_grabbing);
}
