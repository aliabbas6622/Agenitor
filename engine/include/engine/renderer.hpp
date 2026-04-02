#pragma once

/**
 * @file renderer.hpp
 * @brief Renderer — interface for the video rendering pipeline.
 *
 * Abstract renderer that the Pipeline Pattern implementations
 * (FFmpeg, GPU-accelerated, etc.) will implement.
 */

#include <functional>
#include <string>

#include "engine/timeline.hpp"

namespace engine {

/// Export configuration mirroring Python's ExportSettingsIR
struct ExportConfig {
    std::string format = "mp4";        // mp4, webm, mov, mkv
    std::string resolution = "1080p";
    std::string codec = "h264";
    double frame_rate = 30.0;
    int bitrate_kbps = 8000;
    int audio_bitrate_kbps = 192;
    std::string output_path = "output.mp4";
};

/// Progress callback: (percentage 0-100, stage description)
using ProgressCallback = std::function<void(int, const std::string&)>;

/**
 * @class IRenderer
 * @brief Abstract rendering interface — Strategy Pattern for render backends.
 */
class IRenderer {
public:
    virtual ~IRenderer() = default;

    /// Render the timeline to the output specified in config
    virtual bool render(const Timeline& timeline,
                        const ExportConfig& config,
                        ProgressCallback on_progress = nullptr) = 0;

    /// Cancel an in-progress render
    virtual void cancel() = 0;

    /// Check if a render is currently in progress
    [[nodiscard]] virtual bool is_rendering() const = 0;

    /// Get the name of this renderer implementation
    [[nodiscard]] virtual std::string name() const = 0;
};

/**
 * @class DummyRenderer
 * @brief Placeholder renderer for initial C++ engine testing.
 */
class DummyRenderer : public IRenderer {
public:
    bool render(const Timeline& timeline, const ExportConfig& config, ProgressCallback on_progress) override;
    void cancel() override;
    [[nodiscard]] bool is_rendering() const override;
    [[nodiscard]] std::string name() const override;

private:
    bool rendering_ = false;
    bool cancelled_ = false;
};

}  // namespace engine
