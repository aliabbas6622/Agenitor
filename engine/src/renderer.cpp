/**
 * @file renderer.cpp
 * @brief Stub renderer implementation for initial scaffold.
 *
 * Concrete renderers (FFmpegRenderer, GPURenderer) will be added
 * in later phases. This file ensures the library compiles.
 */

#include "engine/renderer.hpp"
#include "engine/export.hpp"

namespace engine {

ExportController::ExportController(std::shared_ptr<IRenderer> renderer)
    : renderer_(std::move(renderer)) {}

ExportResult ExportController::run(const Timeline& timeline,
                                    const ExportConfig& config,
                                    ProgressCallback on_progress) {
    ExportResult result;
    cancelled_ = false;

    // Stage 1: Validate
    if (on_progress) on_progress(5, "Validating timeline");
    if (!validate(timeline, config)) {
        result.error_message = "Validation failed";
        return result;
    }

    if (cancelled_) { result.error_message = "Cancelled"; return result; }

    // Stage 2: Resolve assets
    if (on_progress) on_progress(15, "Resolving assets");
    if (!resolve_assets(timeline)) {
        result.error_message = "Asset resolution failed";
        return result;
    }

    if (cancelled_) { result.error_message = "Cancelled"; return result; }

    // Stage 3: Render via the injected renderer
    if (on_progress) on_progress(20, "Rendering");
    bool render_ok = renderer_->render(timeline, config,
        [&](int pct, const std::string& stage) {
            // Map renderer progress (0-100) to overall (20-90)
            int overall = 20 + (pct * 70 / 100);
            if (on_progress) on_progress(overall, stage);
        });

    if (!render_ok) {
        result.error_message = "Render failed";
        return result;
    }

    // Stage 4: Finalize
    if (on_progress) on_progress(100, "Complete");
    result.success = true;
    result.output_path = config.output_path;
    result.duration_seconds = timeline.duration();

    return result;
}

void ExportController::cancel() {
    cancelled_ = true;
    if (renderer_) renderer_->cancel();
}

bool ExportController::validate(const Timeline& timeline,
                                 const ExportConfig& /*config*/) {
    return timeline.track_count() > 0;
}

bool ExportController::resolve_assets(const Timeline& /*timeline*/) {
    // TODO: Verify all source_paths exist and are accessible
    return true;
}

}  // namespace engine
