#pragma once

/**
 * @file track.hpp
 * @brief Track — an ordered sequence of clips (video, audio, or subtitle).
 */

#include <string>
#include <vector>

#include "engine/clip.hpp"

namespace engine {

enum class TrackType : uint8_t {
    Video = 0,
    Audio = 1,
    Subtitle = 2,
};

/**
 * @class Track
 * @brief An ordered container of clips on the timeline.
 */
class Track {
public:
    Track() = default;
    Track(const std::string& id, TrackType type, const std::string& name = "");

    // ── Accessors ────────────────────────────────────────
    [[nodiscard]] const std::string& id() const { return id_; }
    [[nodiscard]] TrackType type() const { return type_; }
    [[nodiscard]] const std::string& name() const { return name_; }
    [[nodiscard]] bool is_muted() const { return muted_; }
    [[nodiscard]] bool is_locked() const { return locked_; }
    [[nodiscard]] float opacity() const { return opacity_; }
    [[nodiscard]] const std::vector<Clip>& clips() const { return clips_; }
    [[nodiscard]] std::size_t clip_count() const { return clips_.size(); }

    /// Duration from start to the end of the last clip
    [[nodiscard]] double duration() const;

    // ── Mutators ─────────────────────────────────────────
    void set_name(const std::string& name) { name_ = name; }
    void set_muted(bool muted) { muted_ = muted; }
    void set_locked(bool locked) { locked_ = locked; }
    void set_opacity(float opacity);

    // ── Clip Management ──────────────────────────────────
    void add_clip(const Clip& clip);
    void remove_clip(const ClipId& clip_id);
    [[nodiscard]] Clip* find_clip(const ClipId& clip_id);
    [[nodiscard]] const Clip* find_clip(const ClipId& clip_id) const;

    /// Sort clips by position
    void sort_clips();

private:
    std::string id_;
    TrackType type_ = TrackType::Video;
    std::string name_;
    bool muted_ = false;
    bool locked_ = false;
    float opacity_ = 1.0f;
    std::vector<Clip> clips_;
};

}  // namespace engine
