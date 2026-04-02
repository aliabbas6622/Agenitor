/**
 * @file ffmpeg_renderer.cpp
 * @brief FFmpeg-based renderer implementation.
 */

#include "engine/ffmpeg_renderer.hpp"

#if defined(HAVE_FFMPEG)
extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavfilter/avfilter.h>
#include <libavfilter/buffersink.h>
#include <libavfilter/buffersrc.h>
#include <libavutil/avassert.h>
#include <libavutil/imgutils.h>
#include <libavutil/opt.h>
#include <libavutil/mathematics.h>
#include <libavutil/pixdesc.h>
#include <libswscale/swscale.h>
#include <libswresample/swresample.h>
}
#endif

#include <chrono>
#include <thread>

namespace engine {

FFmpegRenderer::FFmpegRenderer() {
#if defined(HAVE_FFMPEG)
    // Initialize FFmpeg libraries
    avformat_network_init();
#endif
}

FFmpegRenderer::~FFmpegRenderer() {
    cleanup_encoder();
}

std::string FFmpegRenderer::name() const {
    return "FFmpeg";
}

bool FFmpegRenderer::is_rendering() const {
    return rendering_.load();
}

void FFmpegRenderer::cancel() {
    cancelled_.store(true);
}

bool FFmpegRenderer::render(const Timeline& timeline,
                            const ExportConfig& config,
                            ProgressCallback on_progress) {
#if !defined(HAVE_FFMPEG)
    (void)timeline;
    (void)config;
    if (on_progress) on_progress(0, "Error: FFmpeg not available (built without HAVE_FFMPEG)");
    rendering_.store(false);
    return false;
#else
    rendering_.store(true);
    cancelled_.store(false);

    int ret = 0;
    bool success = false;

    // Validate timeline
    if (on_progress) on_progress(5, "Validating timeline");
    if (timeline.track_count() == 0) {
        if (on_progress) on_progress(0, "Error: Empty timeline");
        rendering_.store(false);
        return false;
    }

    // Initialize encoder
    if (on_progress) on_progress(10, "Initializing encoder");
    if (!initialize_encoder(config)) {
        if (on_progress) on_progress(0, "Error: Failed to initialize encoder");
        rendering_.store(false);
        return false;
    }

    if (cancelled_.load()) {
        if (on_progress) on_progress(0, "Cancelled");
        cleanup_encoder();
        rendering_.store(false);
        return false;
    }

    // Calculate total frames for progress
    double duration = timeline.duration();
    int total_frames = static_cast<int>(duration * config.frame_rate);
    int frames_rendered = 0;

    // Render each track
    if (on_progress) on_progress(20, "Rendering frames");

    // For now, render a simple test pattern since we don't have actual asset loading
    // This will be expanded to load real video files in the next iteration
    for (int frame_num = 0; frame_num < total_frames && !cancelled_.load(); ++frame_num) {
        // Create a test frame (gradient pattern)
        AVFrame* frame = av_frame_alloc();
        if (!frame) {
            if (on_progress) on_progress(0, "Error: Failed to allocate frame");
            cleanup_encoder();
            rendering_.store(false);
            return false;
        }

        frame->format = AV_PIX_FMT_RGB24;
        frame->width = video_width_;
        frame->height = video_height_;

        ret = av_frame_get_buffer(frame, 32);
        if (ret < 0) {
            av_frame_free(&frame);
            if (on_progress) on_progress(0, "Error: Failed to allocate frame buffer");
            cleanup_encoder();
            rendering_.store(false);
            return false;
        }

        // Generate gradient pattern (blue to purple based on frame position)
        float progress = static_cast<float>(frame_num) / total_frames;
        for (int y = 0; y < video_height_; ++y) {
            for (int x = 0; x < video_width_; ++x) {
                uint8_t* pixel = frame->data[0] + y * frame->linesize[0] + x * 3;
                // Gradient from blue (start) to purple (end)
                pixel[0] = static_cast<uint8_t>(50 + progress * 100);  // R
                pixel[1] = static_cast<uint8_t>(50);                     // G
                pixel[2] = static_cast<uint8_t>(150 + progress * 50);   // B
            }
        }

        // Add timestamp overlay (simple text rendering would go here)
        // For now, just write the frame

        ret = avcodec_send_frame(enc_ctx_, frame);
        if (ret < 0) {
            av_frame_free(&frame);
            if (on_progress) on_progress(0, "Error: Failed to send frame to encoder");
            cleanup_encoder();
            rendering_.store(false);
            return false;
        }

        while (ret >= 0) {
            AVPacket* pkt = av_packet_alloc();
            ret = avcodec_receive_packet(enc_ctx_, pkt);
            if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) {
                av_packet_free(&pkt);
                break;
            } else if (ret < 0) {
                av_packet_free(&pkt);
                av_frame_free(&frame);
                if (on_progress) on_progress(0, "Error: Encoding failed");
                cleanup_encoder();
                rendering_.store(false);
                return false;
            }

            // Set packet timing
            pkt->stream_index = 0;
            pkt->duration = 1;
            pkt->pts = frame_num;
            pkt->dts = frame_num;

            // Write packet to output
            ret = av_interleaved_write_frame(out_ctx_, pkt);
            av_packet_free(&pkt);

            if (ret < 0) {
                av_frame_free(&frame);
                if (on_progress) on_progress(0, "Error: Failed to write frame");
                cleanup_encoder();
                rendering_.store(false);
                return false;
            }
        }

        av_frame_free(&frame);
        frames_rendered++;

        // Report progress
        if (on_progress) {
            int pct = 20 + (frames_rendered * 75 / total_frames);
            on_progress(pct, "Rendering frame " + std::to_string(frames_rendered) + "/" + std::to_string(total_frames));
        }
    }

    if (cancelled_.load()) {
        if (on_progress) on_progress(0, "Cancelled");
        cleanup_encoder();
        rendering_.store(false);
        return false;
    }

    // Flush encoder
    if (on_progress) on_progress(95, "Flushing encoder");
    ret = avcodec_send_frame(enc_ctx_, nullptr);
    while (ret >= 0) {
        AVPacket* pkt = av_packet_alloc();
        ret = avcodec_receive_packet(enc_ctx_, pkt);
        if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) {
            av_packet_free(&pkt);
            break;
        } else if (ret < 0) {
            av_packet_free(&pkt);
            break;
        }

        pkt->stream_index = 0;
        av_interleaved_write_frame(out_ctx_, pkt);
        av_packet_free(&pkt);
    }

    // Finalize file
    if (on_progress) on_progress(98, "Finalizing output");
    av_write_trailer(out_ctx_);

    success = true;

    cleanup_encoder();

    if (on_progress) on_progress(100, "Export complete");
    rendering_.store(false);

    return success;
#endif
}

bool FFmpegRenderer::initialize_encoder(const ExportConfig& config) {
#if !defined(HAVE_FFMPEG)
    (void)config;
    return false;
#else
    int ret = 0;

    // Find output format
    const AVOutputFormat* oformat = av_guess_format(config.format.c_str(), nullptr, nullptr);
    if (!oformat) {
        // Default to mp4
        oformat = av_guess_format("mp4", nullptr, nullptr);
    }
    if (!oformat) {
        return false;
    }

    // Allocate output context
    out_ctx_ = avformat_alloc_context();
    if (!out_ctx_) {
        return false;
    }
    out_ctx_->oformat = oformat;

    // Create output stream
    AVStream* stream = avformat_new_stream(out_ctx_, nullptr);
    if (!stream) {
        return false;
    }
    stream->id = 0;

    // Set time base (store as (num, den) in header to avoid FFmpeg types there)
    int den = static_cast<int>(config.frame_rate);
    time_base_ = {1, den};
    AVRational tb = av_make_q(time_base_.first, time_base_.second);
    stream->time_base = tb;

    // Find encoder
    const AVCodec* codec = nullptr;
    if (config.codec == "h264" || config.codec == "h265") {
        codec = avcodec_find_encoder_by_name(config.codec == "h264" ? "libx264" : "libx265");
    }
    if (!codec) {
        codec = avcodec_find_encoder(oformat->video_codec);
    }
    if (!codec) {
        return false;
    }

    // Allocate encoder context
    enc_ctx_ = avcodec_alloc_context3(codec);
    if (!enc_ctx_) {
        return false;
    }

    // Configure encoder
    enc_ctx_->codec_id = codec->id;
    enc_ctx_->codec_type = AVMEDIA_TYPE_VIDEO;
    enc_ctx_->width = video_width_;
    enc_ctx_->height = video_height_;
    enc_ctx_->time_base = tb;
    enc_ctx_->framerate = av_make_q(static_cast<int>(config.frame_rate), 1);
    enc_ctx_->gop_size = 30;  // Keyframe interval
    enc_ctx_->pix_fmt = AV_PIX_FMT_YUV420P;
    enc_ctx_->bit_rate = config.bitrate_kbps * 1000;

    // Set H.264 specific options
    if (codec->id == AV_CODEC_ID_H264) {
        ret = av_opt_set(enc_ctx_->priv_data, "preset", "medium", 0);
        ret = av_opt_set(enc_ctx_->priv_data, "crf", "23", 0);
    }

    // Copy stream parameters
    ret = avcodec_parameters_from_context(stream->codecpar, enc_ctx_);
    if (ret < 0) {
        return false;
    }

    // Open output file
    ret = avio_open(&out_ctx_->pb, config.output_path.c_str(), AVIO_FLAG_WRITE);
    if (ret < 0) {
        return false;
    }

    // Write header
    ret = avformat_write_header(out_ctx_, nullptr);
    if (ret < 0) {
        return false;
    }

    // Open encoder
    ret = avcodec_open2(enc_ctx_, codec, nullptr);
    if (ret < 0) {
        return false;
    }

    return true;
#endif
}

void FFmpegRenderer::cleanup_encoder() {
#if !defined(HAVE_FFMPEG)
    return;
#else
    if (enc_ctx_) {
        avcodec_free_context(&enc_ctx_);
    }
    if (out_ctx_) {
        if (out_ctx_->pb) {
            avio_closep(&out_ctx_->pb);
        }
        avformat_free_context(out_ctx_);
        out_ctx_ = nullptr;
    }
    if (sws_ctx_) {
        sws_freeContext(sws_ctx_);
        sws_ctx_ = nullptr;
    }
#endif
}

bool FFmpegRenderer::render_clip(const Clip& clip, AVFormatContext* out_ctx,
                                  AVCodecContext* enc_ctx, ProgressCallback on_progress) {
#if !defined(HAVE_FFMPEG)
    (void)clip;
    (void)out_ctx;
    (void)enc_ctx;
    (void)on_progress;
    return false;
#else
    // This would decode the source asset and render frames
    // For now, the main render() function handles frame generation
    return true;
#endif
}

bool FFmpegRenderer::apply_effects(AVFrame* frame, const std::vector<Effect>& effects) {
#if !defined(HAVE_FFMPEG)
    (void)frame;
    (void)effects;
    return false;
#else
    // Apply effects using libavfilter
    // This is a placeholder for future effect implementation
    return true;
#endif
}

bool FFmpegRenderer::write_frame(AVFrame* frame, AVFormatContext* out_ctx,
                                  AVCodecContext* enc_ctx, int64_t& pts) {
#if !defined(HAVE_FFMPEG)
    (void)frame;
    (void)out_ctx;
    (void)enc_ctx;
    (void)pts;
    return false;
#else
    int ret = avcodec_send_frame(enc_ctx, frame);
    if (ret < 0) {
        return false;
    }

    while (ret >= 0) {
        AVPacket* pkt = av_packet_alloc();
        ret = avcodec_receive_packet(enc_ctx, pkt);
        if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) {
            av_packet_free(&pkt);
            break;
        } else if (ret < 0) {
            av_packet_free(&pkt);
            return false;
        }

        pkt->stream_index = 0;
        pkt->pts = pts++;
        pkt->dts = pkt->pts;

        ret = av_interleaved_write_frame(out_ctx, pkt);
        av_packet_free(&pkt);

        if (ret < 0) {
            return false;
        }
    }

    return true;
#endif
}

AVFrame* FFmpegRenderer::convert_frame(const uint8_t* rgb_data, int width, int height) {
#if !defined(HAVE_FFMPEG)
    (void)rgb_data;
    (void)width;
    (void)height;
    return nullptr;
#else
    // This would convert RGB data to the encoder's pixel format
    // Using sws_scale for conversion
    return nullptr;  // Placeholder
#endif
}

}  // namespace engine
