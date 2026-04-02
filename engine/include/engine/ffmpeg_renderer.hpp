#pragma once

/**
 * @file ffmpeg_renderer.hpp
 * @brief FFmpeg-based video renderer implementation.
 *
 * Uses libavcodec, libavformat, and libavfilter to render
 * timeline data to video files.
 */

#include <atomic>
#include <memory>
#include <string>
#include <utility>

#include "engine/renderer.hpp"
#include "engine/timeline.hpp"

// Forward declare FFmpeg types to avoid including heavy headers here
struct AVFormatContext;
struct AVCodecContext;
struct AVFrame;
struct SwsContext;

namespace engine {

/**
 * @class FFmpegRenderer
 * @brief Concrete IRenderer implementation using FFmpeg libraries.
 */
class FFmpegRenderer : public IRenderer {
public:
    FFmpegRenderer();
    ~FFmpegRenderer() override;

    bool render(const Timeline& timeline,
                const ExportConfig& config,
                ProgressCallback on_progress) override;

    void cancel() override;
    [[nodiscard]] bool is_rendering() const override;
    [[nodiscard]] std::string name() const override;

private:
    std::atomic<bool> rendering_{false};
    std::atomic<bool> cancelled_{false};

    /// Initialize encoder with config
    bool initialize_encoder(const ExportConfig& config);

    /// Cleanup encoder resources
    void cleanup_encoder();

    /// Render a single clip to the output
    bool render_clip(const Clip& clip, AVFormatContext* out_ctx,
                     AVCodecContext* enc_ctx, ProgressCallback on_progress);

    /// Apply effects to a frame
    bool apply_effects(AVFrame* frame, const std::vector<Effect>& effects);

    /// Write a frame to the output
    bool write_frame(AVFrame* frame, AVFormatContext* out_ctx,
                     AVCodecContext* enc_ctx, int64_t& pts);

    /// Convert RGB frame to encoder format
    AVFrame* convert_frame(const uint8_t* rgb_data, int width, int height);

    // Encoder state
    AVFormatContext* out_ctx_ = nullptr;
    AVCodecContext* enc_ctx_ = nullptr;
    SwsContext* sws_ctx_ = nullptr;
    int video_width_ = 1920;
    int video_height_ = 1080;
    // Avoid referencing FFmpeg AVRational in the header to keep pybind builds lightweight.
    // Converted to AVRational inside ffmpeg_renderer.cpp.
    std::pair<int, int> time_base_ = {1, 30};
};

}  // namespace engine
