#pragma once

/**
 * @file export.hpp
 * @brief Export controller — orchestrates the render pipeline stages.
 *
 * Implements the Pipeline Pattern:
 *   Validate → Resolve Assets → Render Segments → Concatenate → Output
 */

#include <memory>
#include <string>

#include "engine/renderer.hpp"
#include "engine/timeline.hpp"

namespace engine {

/// Result of an export operation
struct ExportResult {
    bool success = false;
    std::string output_path;
    std::string error_message;
    double duration_seconds = 0.0;
};

/**
 * @class ExportController
 * @brief Drives the multi-stage export pipeline.
 */
class ExportController {
public:
    explicit ExportController(std::shared_ptr<IRenderer> renderer);

    /// Run the full export pipeline
    ExportResult run(const Timeline& timeline,
                     const ExportConfig& config,
                     ProgressCallback on_progress = nullptr);

    /// Cancel the current export
    void cancel();

private:
    bool validate(const Timeline& timeline, const ExportConfig& config);
    bool resolve_assets(const Timeline& timeline);

    std::shared_ptr<IRenderer> renderer_;
    bool cancelled_ = false;
};

}  // namespace engine
