import json
import subprocess
from pathlib import Path
import httpx
from fastapi import FastAPI
from app import app


def generate_openapi_json():
    openapi_data = app.openapi()
    with open("openapi.json", "w") as file:
        json.dump(openapi_data, file, indent=2)
    return "openapi.json"


def generate_models(openapi_spec_path: str):
    output_file = Path("myapp/generated_models.py")
    output_file.parent.mkdir(exist_ok=True)

    cmd = [
        "datamodel-codegen",
        "--input",
        openapi_spec_path,
        "--output",
        str(output_file),
        "--input-file-type",
        "openapi",
        "--use-title-as-name",
        "--reuse-model",
        "--target-python-version",
        "3.9",
        "--use-field-description",
        "--use-default",
    ]

    subprocess.run(cmd, check=True)

    with output_file.open("r+") as f:
        content = f.read()
        f.seek(0, 0)
        f.write(
            "from fastapi import UploadFile, File\n"
            "from typing import Any, Dict, List, Optional, Union\n\n" + content
        )


if __name__ == "__main__":
    openapi_file = generate_openapi_json()
    generate_models(openapi_file)
    print("Models generated successfully!")
