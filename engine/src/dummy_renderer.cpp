#include "engine/renderer.hpp"
#include <thread>
#include <chrono>

namespace engine {

bool DummyRenderer::render(const Timeline& /*timeline*/, const ExportConfig& /*config*/, ProgressCallback on_progress) {
    rendering_ = true;
    cancelled_ = false;

    // Simulate 5 steps
    for (int i = 0; i <= 5; ++i) {
        if (cancelled_) {
            rendering_ = false;
            return false;
        }
        if (on_progress) {
            on_progress(i * 20, "Rendering frame " + std::to_string(i * 100));
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
    }
    
    rendering_ = false;
    return true;
}

void DummyRenderer::cancel() {
    cancelled_ = true;
}

bool DummyRenderer::is_rendering() const {
    return rendering_;
}

std::string DummyRenderer::name() const {
    return "DummyRenderer";
}

} // namespace engine
