#pragma once

/**
 * @file timeline.hpp
 * @brief Timeline — the root data structure of a video project.
 *
 * The Timeline owns all tracks and provides the interface for
 * querying and mutating the project state. The Python orchestration
 * layer drives this through pybind11 bindings.
 */

#include <string>
#include <vector>

#include "engine/track.hpp"

namespace engine {

/**
 * @class Timeline
 * @brief Root container for a video editing project.
 */
class Timeline {
public:
    Timeline() = default;
    explicit Timeline(const std::string& id, const std::string& project_name = "Untitled");

    // ── Accessors ────────────────────────────────────────
    [[nodiscard]] const std::string& id() const { return id_; }
    [[nodiscard]] const std::string& project_name() const { return project_name_; }
    [[nodiscard]] const std::vector<Track>& tracks() const { return tracks_; }
    [[nodiscard]] std::size_t track_count() const { return tracks_.size(); }

    /// Computed duration from the latest clip end across all tracks
    [[nodiscard]] double duration() const;

    // ── Track Management ─────────────────────────────────
    void add_track(const Track& track);
    void remove_track(const std::string& track_id);
    [[nodiscard]] Track* find_track(const std::string& track_id);
    [[nodiscard]] const Track* find_track(const std::string& track_id) const;

    // ── Clip Access (cross-track) ────────────────────────
    [[nodiscard]] Clip* find_clip(const ClipId& clip_id);
    [[nodiscard]] const Clip* find_clip(const ClipId& clip_id) const;

    // ── Serialization ────────────────────────────────────
    /// Serialize to JSON string (for passing to Python layer)
    [[nodiscard]] std::string to_json() const;

    /// Deserialize from JSON string (received from Python layer)
    static Timeline from_json(const std::string& json_str);

private:
    std::string id_;
    std::string project_name_ = "Untitled";
    std::vector<Track> tracks_;
};

}  // namespace engine
