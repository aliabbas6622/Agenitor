/**
 * @file timeline.cpp
 * @brief Timeline implementation.
 */

#include "engine/timeline.hpp"

#include <algorithm>

namespace engine {

Timeline::Timeline(const std::string& id, const std::string& project_name)
    : id_(id), project_name_(project_name) {}

double Timeline::duration() const {
    double max_end = 0.0;
    for (const auto& track : tracks_) {
        double track_dur = track.duration();
        if (track_dur > max_end) {
            max_end = track_dur;
        }
    }
    return max_end;
}

void Timeline::add_track(const Track& track) {
    tracks_.push_back(track);
}

void Timeline::remove_track(const std::string& track_id) {
    tracks_.erase(
        std::remove_if(tracks_.begin(), tracks_.end(),
                        [&](const Track& t) { return t.id() == track_id; }),
        tracks_.end());
}

Track* Timeline::find_track(const std::string& track_id) {
    auto it = std::find_if(tracks_.begin(), tracks_.end(),
                            [&](const Track& t) { return t.id() == track_id; });
    return it != tracks_.end() ? &(*it) : nullptr;
}

const Track* Timeline::find_track(const std::string& track_id) const {
    auto it = std::find_if(tracks_.begin(), tracks_.end(),
                            [&](const Track& t) { return t.id() == track_id; });
    return it != tracks_.end() ? &(*it) : nullptr;
}

Clip* Timeline::find_clip(const ClipId& clip_id) {
    for (auto& track : tracks_) {
        if (auto* clip = track.find_clip(clip_id)) {
            return clip;
        }
    }
    return nullptr;
}

const Clip* Timeline::find_clip(const ClipId& clip_id) const {
    for (const auto& track : tracks_) {
        if (const auto* clip = track.find_clip(clip_id)) {
            return clip;
        }
    }
    return nullptr;
}

std::string Timeline::to_json() const {
    // TODO: Implement with nlohmann/json or rapidjson in Phase 2
    return "{}";
}

Timeline Timeline::from_json(const std::string& /*json_str*/) {
    // TODO: Implement with nlohmann/json or rapidjson in Phase 2
    return Timeline();
}

}  // namespace engine
