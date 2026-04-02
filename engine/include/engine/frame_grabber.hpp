#pragma once

/**
 * @file frame_grabber.hpp
 * @brief Frame extraction from timeline for real-time preview.
 *
 * Extracts individual frames from the timeline at specified timestamps
 * for preview streaming to the frontend.
 */

#include <cstdint>
#include <atomic>
#include <string>
#include <vector>

#include "engine/timeline.hpp"

namespace engine {

/**
 * @struct FrameData
 * @brief Raw RGB frame data with dimensions
 */
struct FrameData {
    std::vector<uint8_t> rgb_data;  // RGB24 format
    int width = 0;
    int height = 0;
    double timestamp = 0.0;  // Timestamp in seconds
    bool valid = false;
};

/**
 * @class IFrameGrabber
 * @brief Interface for frame extraction from timeline
 */
class IFrameGrabber {
public:
    virtual ~IFrameGrabber() = default;

    /// Extract frame at timestamp as RGB bytes
    virtual FrameData grab_frame(const Timeline& timeline,
                                  double timestamp_seconds,
                                  int width = 640,
                                  int height = 360) = 0;

    /// Cancel in-progress grab
    virtual void cancel() = 0;

    /// Check if grab is in progress
    [[nodiscard]] virtual bool is_grabbing() const = 0;
};

/**
 * @class FrameGrabber
 * @brief FFmpeg-based frame extraction implementation
 */
class FrameGrabber : public IFrameGrabber {
public:
    FrameGrabber();
    ~FrameGrabber() override;

    FrameData grab_frame(const Timeline& timeline,
                         double timestamp_seconds,
                         int width = 640,
                         int height = 360) override;

    void cancel() override;
    [[nodiscard]] bool is_grabbing() const override;

private:
    std::atomic<bool> grabbing_{false};
    std::atomic<bool> cancelled_{false};

    /// Decode source asset and extract frame
    FrameData extract_frame_from_asset(const std::string& source_path,
                                        double timestamp,
                                        int width, int height);

    /// Composite multiple tracks at timestamp
    FrameData composite_tracks(const Timeline& timeline,
                               double timestamp,
                               int width, int height);
};

}  // namespace engine
