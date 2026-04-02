cmake_minimum_required(VERSION 3.20)
project(ai_video_engine VERSION 0.1.0 LANGUAGES CXX)

# ── C++ Standard ──────────────────────────────────────────
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ── Compiler Warnings ────────────────────────────────────
if(MSVC)
    add_compile_options(/W4 /WX)
else()
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# ── Find FFmpeg (optional) ───────────────────────────────
# On Windows dev machines, pkg-config/FFmpeg dev libs may not be installed.
# We still want the engine + bindings to build (with stubs) so the editor can run.
find_package(PkgConfig QUIET)
if(PkgConfig_FOUND)
    pkg_check_modules(FFMPEG QUIET
        libavcodec
        libavformat
        libavfilter
        libavutil
        libswscale
        libswresample
    )
endif()

# ── Engine Library ────────────────────────────────────────
file(GLOB_RECURSE ENGINE_SOURCES "src/*.cpp")

add_library(ai_video_engine STATIC ${ENGINE_SOURCES})

target_include_directories(ai_video_engine
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        $<$<BOOL:${FFMPEG_FOUND}>:${FFMPEG_INCLUDE_DIRS}>
)

target_link_libraries(ai_video_engine
    PRIVATE
        $<$<BOOL:${FFMPEG_FOUND}>:${FFMPEG_LIBRARIES}>
)

target_compile_definitions(ai_video_engine
    PRIVATE
        $<$<BOOL:${FFMPEG_FOUND}>:HAVE_FFMPEG=1>
)

# ── Tests ─────────────────────────────────────────────────
option(BUILD_TESTS "Build engine unit tests" ON)

if(BUILD_TESTS)
    enable_testing()
    # Tests will use a lightweight test framework (Catch2 or GoogleTest)
    # Added in a later phase when test infrastructure is set up
endif()

# ── pybind11 Bindings ────────────────────────────────────
option(BUILD_PYTHON_BINDINGS "Build Python bindings via pybind11" OFF)

if(BUILD_PYTHON_BINDINGS)
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../bindings bindings_build)
endif()
