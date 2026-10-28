"""Write the API's OpenAPI schema to a file, for generating clients. Usage: `python scripts/export_openapi.py PATH`."""
import json
import sys
from pathlib import Path

# Make the API's modules importable when run as `python scripts/export_openapi.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import create_app


def main() -> None:
    schema = create_app().openapi()
    Path(sys.argv[1]).write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
