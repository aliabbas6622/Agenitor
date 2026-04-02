cmake_minimum_required(VERSION 3.20)

# ── Find pybind11 ─────────────────────────────────────────
find_package(pybind11 QUIET)

if(NOT pybind11_FOUND)
    message(STATUS "pybind11 not found — skipping Python bindings")
    return()
endif()

# ── Binding Module ────────────────────────────────────────
pybind11_add_module(engine_py engine_module.cpp)

target_link_libraries(engine_py PRIVATE ai_video_engine)

target_include_directories(engine_py PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../engine/include
)

# Removed install since we want local pipeline referencing
