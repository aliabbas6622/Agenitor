/**
 * @file clip.cpp
 * @brief Clip implementation.
 */

#include "engine/clip.hpp"

#include <algorithm>
#include <stdexcept>

namespace engine {

Clip::Clip(const ClipId& id, const std::string& source_path,
           double in_point, double out_point)
    : id_(id)
    , source_path_(source_path)
    , in_point_(in_point)
    , out_point_(out_point) {
    if (out_point <= in_point) {
        throw std::invalid_argument("out_point must be greater than in_point");
    }
}

double Clip::duration() const {
    return (out_point_ - in_point_) / playback_speed_;
}

void Clip::set_position(double pos) {
    if (pos < 0.0) throw std::invalid_argument("position must be >= 0");
    position_ = pos;
}

void Clip::set_in_point(double in) {
    if (in < 0.0) throw std::invalid_argument("in_point must be >= 0");
    if (in >= out_point_) throw std::invalid_argument("in_point must be < out_point");
    in_point_ = in;
}

void Clip::set_out_point(double out) {
    if (out <= in_point_) throw std::invalid_argument("out_point must be > in_point");
    out_point_ = out;
}

void Clip::set_playback_speed(double speed) {
    if (speed <= 0.0 || speed > 10.0) {
        throw std::invalid_argument("speed must be in (0, 10]");
    }
    playback_speed_ = speed;
}

void Clip::set_volume(float vol) {
    if (vol < 0.0f || vol > 2.0f) {
        throw std::invalid_argument("volume must be in [0, 2]");
    }
    volume_ = vol;
}

void Clip::add_effect(const Effect& effect) {
    effects_.push_back(effect);
}

void Clip::remove_effect(const std::string& effect_id) {
    effects_.erase(
        std::remove_if(effects_.begin(), effects_.end(),
                        [&](const Effect& e) { return e.id == effect_id; }),
        effects_.end());
}

}  // namespace engine
