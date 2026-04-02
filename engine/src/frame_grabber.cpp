/**
 * @file frame_grabber.cpp
 * @brief FFmpeg-based frame extraction implementation.
 */

#include "engine/frame_grabber.hpp"

#if defined(HAVE_FFMPEG)
extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/avutil.h>
#include <libavutil/imgutils.h>
#include <libswscale/swscale.h>
}
#endif

#include <algorithm>

namespace engine {

FrameGrabber::FrameGrabber() {
#if defined(HAVE_FFMPEG)
    avformat_network_init();
#endif
}

FrameGrabber::~FrameGrabber() = default;

bool FrameGrabber::is_grabbing() const {
    return grabbing_.load();
}

void FrameGrabber::cancel() {
    cancelled_.store(true);
}

FrameData FrameGrabber::grab_frame(const Timeline& timeline,
                                    double timestamp_seconds,
                                    int width,
                                    int height) {
    grabbing_.store(true);
    cancelled_.store(false);

    FrameData result;
    result.width = width;
    result.height = height;
    result.timestamp = timestamp_seconds;

    // Find which clip is active at this timestamp
    const Clip* active_clip = nullptr;
    const Track* active_track = nullptr;

    for (const auto& track : timeline.tracks()) {
        for (const auto& clip : track.clips()) {
            double clip_start = clip.position();
            double clip_end = clip_start + clip.duration();

            if (timestamp_seconds >= clip_start && timestamp_seconds < clip_end) {
                active_clip = &clip;
                active_track = &track;
                break;
            }
        }
        if (active_clip) break;
    }

    if (!active_clip) {
        // No active clip at this timestamp - return blank frame
        result.rgb_data.resize(width * height * 3, 0);  // Black frame
        result.valid = true;
        grabbing_.store(false);
        return result;
    }

    // Extract frame from the active clip's source
    result = extract_frame_from_asset(active_clip->source_path(),
                                       timestamp_seconds - active_clip->position() + active_clip->in_point(),
                                       width, height);

    if (!result.valid) {
        // If extraction failed, return colored frame with clip info
        result.rgb_data.resize(width * height * 3, 0);
        // Draw a simple gradient to indicate clip position
        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                size_t idx = (y * width + x) * 3;
                result.rgb_data[idx] = static_cast<uint8_t>(100);     // R
                result.rgb_data[idx + 1] = static_cast<uint8_t>(150); // G
                result.rgb_data[idx + 2] = static_cast<uint8_t>(200); // B
            }
        }
        result.valid = true;  // Mark as valid placeholder
    }

    grabbing_.store(false);
    return result;
}

FrameData FrameGrabber::extract_frame_from_asset(const std::string& source_path,
                                                   double timestamp,
                                                   int width,
                                                   int height) {
    FrameData result;
    result.width = width;
    result.height = height;

#if !defined(HAVE_FFMPEG)
    (void)source_path;
    (void)timestamp;
    // FFmpeg not available at build time. Return an invalid result so the caller
    // can fall back to a placeholder frame.
    result.valid = false;
    return result;
#else
    AVFormatContext* fmt_ctx = nullptr;
    AVCodecContext* codec_ctx = nullptr;
    AVFrame* frame = nullptr;
    AVFrame* rgb_frame = nullptr;
    SwsContext* sws_ctx = nullptr;

    int ret;

    // Open input file
    ret = avformat_open_input(&fmt_ctx, source_path.c_str(), nullptr, nullptr);
    if (ret < 0) {
        goto cleanup;
    }

    // Find stream info
    ret = avformat_find_stream_info(fmt_ctx, nullptr);
    if (ret < 0) {
        goto cleanup;
    }

    // Find video stream
    int video_stream_idx = -1;
    for (unsigned int i = 0; i < fmt_ctx->nb_streams; ++i) {
        if (fmt_ctx->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO) {
            video_stream_idx = static_cast<int>(i);
            break;
        }
    }

    if (video_stream_idx < 0) {
        goto cleanup;
    }

    AVStream* video_stream = fmt_ctx->streams[video_stream_idx];

    // Find decoder
    const AVCodec* codec = avcodec_find_decoder(video_stream->codecpar->codec_id);
    if (!codec) {
        goto cleanup;
    }

    // Allocate decoder context
    codec_ctx = avcodec_alloc_context3(codec);
    if (!codec_ctx) {
        goto cleanup;
    }

    // Copy codec parameters
    ret = avcodec_parameters_to_context(codec_ctx, video_stream->codecpar);
    if (ret < 0) {
        goto cleanup;
    }

    // Open decoder
    ret = avcodec_open2(codec_ctx, codec, nullptr);
    if (ret < 0) {
        goto cleanup;
    }

    // Calculate target timestamp in stream time base
    AVRational time_base = video_stream->time_base;
    int64_t target_ts = static_cast<int64_t>(timestamp / av_q2d(time_base));

    // Seek to approximate position
    ret = av_seek_frame(fmt_ctx, video_stream_idx, target_ts, AVSEEK_FLAG_BACKWARD);
    if (ret < 0) {
        goto cleanup;
    }

    // Allocate frames
    frame = av_frame_alloc();
    rgb_frame = av_frame_alloc();
    if (!frame || !rgb_frame) {
        goto cleanup;
    }

    // Initialize SWS context for conversion to RGB24
    sws_ctx = sws_getContext(
        codec_ctx->width, codec_ctx->height, codec_ctx->pix_fmt,
        width, height, AV_PIX_FMT_RGB24,
        SWS_BILINEAR, nullptr, nullptr, nullptr
    );
    if (!sws_ctx) {
        goto cleanup;
    }

    // Allocate buffer for RGB frame
    ret = av_image_alloc(rgb_frame->data, rgb_frame->linesize,
                         width, height, AV_PIX_FMT_RGB24, 32);
    if (ret < 0) {
        goto cleanup;
    }

    // Read frames until we get one at or past our timestamp
    AVPacket* pkt = av_packet_alloc();
    bool got_frame = false;

    while (av_read_frame(fmt_ctx, pkt) >= 0) {
        if (cancelled_.load()) {
            av_packet_free(&pkt);
            goto cleanup;
        }

        if (pkt->stream_index == video_stream_idx) {
            ret = avcodec_send_packet(codec_ctx, pkt);
            if (ret >= 0) {
                ret = avcodec_receive_frame(codec_ctx, frame);
                if (ret == 0) {
                    // Check if this frame is at or past our target timestamp
                    if (frame->pts >= target_ts) {
                        // Convert to RGB
                        sws_scale(sws_ctx, frame->data, frame->linesize, 0,
                                  codec_ctx->height, rgb_frame->data, rgb_frame->linesize);

                        // Copy RGB data
                        result.rgb_data.resize(width * height * 3);
                        for (int y = 0; y < height; ++y) {
                            std::memcpy(
                                result.rgb_data.data() + y * width * 3,
                                rgb_frame->data[0] + y * rgb_frame->linesize[0],
                                width * 3
                            );
                        }
                        result.valid = true;
                        got_frame = true;
                        av_packet_free(&pkt);
                        break;
                    }
                }
            }
        }
        av_packet_unref(pkt);
    }

    av_packet_free(&pkt);

cleanup:
    if (sws_ctx) sws_freeContext(sws_ctx);
    if (rgb_frame) {
        if (rgb_frame->data[0]) av_freep(&rgb_frame->data[0]);
        av_frame_free(&rgb_frame);
    }
    if (frame) av_frame_free(&frame);
    if (codec_ctx) avcodec_free_context(&codec_ctx);
    if (fmt_ctx) avformat_close_input(&fmt_ctx);

    return result;
#endif
}

FrameData FrameGrabber::composite_tracks(const Timeline& timeline,
                                          double timestamp,
                                          int width,
                                          int height) {
    // For now, just grab from the topmost visible track
    // Full compositing would blend all tracks based on opacity, blend modes, etc.
    return grab_frame(timeline, timestamp, width, height);
}

}  // namespace engine
