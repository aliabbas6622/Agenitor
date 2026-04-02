from uuid import uuid4
from app.workers.export_worker import run_export_pipeline
from app.schemas.ir import TrackType

def test_native_export_workflow():
    """Manual integration test for the C++ Native Engine bridge."""
    project_id = str(uuid4())
    
    # Minimal valid timeline dict
    timeline_dict = {
        "id": str(uuid4()),
        "project_name": "Native C++ Test",
        "tracks": [
            {
                "id": str(uuid4()),
                "type": "video",
                "name": "V1",
                "clips": [
                    {
                        "id": str(uuid4()),
                        "source_path": "test_video.mp4",
                        "track_id": str(uuid4()), # won't be used directly but required by pydantic
                        "position": 0.0,
                        "in_point": 0.0,
                        "out_point": 10.0
                    }
                ]
            }
        ],
        "duration": 10.0
    }
    
    settings_dict = {
        "format": "mp4",
        "resolution": "1080p",
        "codec": "h264",
        "output_path": "native_test_output.mp4"
    }

    print(f"Starting native export for project {project_id}...")
    
    # We mock 'self' for the celery task
    class MockTask:
        class Request:
            id = "job_native_001"
        request = Request()
        
    mock_self = MockTask()
    
    # Use direct helper for pipeline testing
    result = run_export_pipeline("job_native_001", project_id, timeline_dict, settings_dict)
    
    print("\nExport Result:")
    print(result)
    assert result["status"] == "completed"
    assert result["engine"] == "cpp_native"

if __name__ == "__main__":
    try:
        test_native_export_workflow()
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()
