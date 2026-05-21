from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.storage_service import StorageService, StorageServiceError


def main() -> int:
    object_name = "validation/storage-service-smoke.txt"
    content = b"Data Script Generator storage validation.\n"

    try:
        url = StorageService().upload_bytes(
            content=content,
            object_name=object_name,
            content_type="text/plain",
        )
    except StorageServiceError as exc:
        print(f"Storage validation failed: {exc}")
        return 1

    print(f"Storage validation uploaded object: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
