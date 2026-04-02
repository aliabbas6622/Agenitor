/**
 * @file track.cpp
 * @brief Track implementation.
 */

#include "engine/track.hpp"

#include <algorithm>
#include <stdexcept>

namespace engine {

Track::Track(const std::string& id, TrackType type, const std::string& name)
    : id_(id), type_(type), name_(name) {}

double Track::duration() const {
    double max_end = 0.0;
    for (const auto& clip : clips_) {
        double clip_end = clip.position() + clip.duration();
        if (clip_end > max_end) {
            max_end = clip_end;
        }
    }
    return max_end;
}

void Track::set_opacity(float opacity) {
    if (opacity < 0.0f || opacity > 1.0f) {
        throw std::invalid_argument("opacity must be in [0, 1]");
    }
    opacity_ = opacity;
}

void Track::add_clip(const Clip& clip) {
    clips_.push_back(clip);
}

void Track::remove_clip(const ClipId& clip_id) {
    clips_.erase(
        std::remove_if(clips_.begin(), clips_.end(),
                        [&](const Clip& c) { return c.id() == clip_id; }),
        clips_.end());
}

Clip* Track::find_clip(const ClipId& clip_id) {
    auto it = std::find_if(clips_.begin(), clips_.end(),
                            [&](const Clip& c) { return c.id() == clip_id; });
    return it != clips_.end() ? &(*it) : nullptr;
}

const Clip* Track::find_clip(const ClipId& clip_id) const {
    auto it = std::find_if(clips_.begin(), clips_.end(),
                            [&](const Clip& c) { return c.id() == clip_id; });
    return it != clips_.end() ? &(*it) : nullptr;
}

void Track::sort_clips() {
    std::sort(clips_.begin(), clips_.end(),
              [](const Clip& a, const Clip& b) {
                  return a.position() < b.position();
              });
}

}  // namespace engine
