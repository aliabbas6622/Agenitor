#pragma once

/**
 * @file clip.hpp
 * @brief Clip — the atomic unit of the timeline.
 *
 * A Clip references a source asset and defines the in/out points,
 * position on the timeline, and applied effects.
 */

#include <cstdint>
#include <string>
#include <vector>

namespace engine {

/// Unique identifier for clips (matches Python UUID as string)
using ClipId = std::string;

/// Effect applied to a clip — lightweight value type
struct Effect {
    std::string id;
    std::string type;           // maps to Python EffectType enum
    double start_time = 0.0;    // relative to clip start (seconds)
    double duration = -1.0;     // -1 = entire clip
    // Parameters are stored as key-value string pairs
    // Complex params serialized as JSON strings
    std::vector<std::pair<std::string, std::string>> parameters;
};

/// Transition between clips
struct Transition {
    std::string id;
    std::string type;           // "cut", "crossfade", "dissolve", etc.
    double duration = 0.5;      // seconds
};

/**
 * @class Clip
 * @brief A single clip on a track, referencing a source asset.
 */
class Clip {
public:
    Clip() = default;
    Clip(const ClipId& id, const std::string& source_path,
         double in_point, double out_point);

    // ── Accessors ────────────────────────────────────────
    [[nodiscard]] const ClipId& id() const { return id_; }
    [[nodiscard]] const std::string& source_path() const { return source_path_; }
    [[nodiscard]] double position() const { return position_; }
    [[nodiscard]] double in_point() const { return in_point_; }
    [[nodiscard]] double out_point() const { return out_point_; }
    [[nodiscard]] double playback_speed() const { return playback_speed_; }
    [[nodiscard]] float volume() const { return volume_; }

    /// Effective duration accounting for in/out and speed
    [[nodiscard]] double duration() const;

    // ── Mutators ─────────────────────────────────────────
    void set_position(double pos);
    void set_in_point(double in);
    void set_out_point(double out);
    void set_playback_speed(double speed);
    void set_volume(float vol);

    // ── Effects ──────────────────────────────────────────
    void add_effect(const Effect& effect);
    void remove_effect(const std::string& effect_id);
    [[nodiscard]] const std::vector<Effect>& effects() const { return effects_; }

    // ── Transitions ──────────────────────────────────────
    void set_transition_in(const Transition& t) { transition_in_ = t; }
    void set_transition_out(const Transition& t) { transition_out_ = t; }

private:
    ClipId id_;
    std::string source_path_;
    double position_ = 0.0;        // position on timeline (seconds)
    double in_point_ = 0.0;        // source start (seconds)
    double out_point_ = 0.0;       // source end (seconds)
    double playback_speed_ = 1.0;
    float volume_ = 1.0f;
    std::vector<Effect> effects_;
    Transition transition_in_;
    Transition transition_out_;
};

}  // namespace engine
