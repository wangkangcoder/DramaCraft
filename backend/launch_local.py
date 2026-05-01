import os

import uvicorn


from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent

os.chdir(BACKEND_DIR)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
