import subprocess

if __name__ == "__main__":
    command = [
        "uvicorn",
        "api.main:app",
        "--reload",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    subprocess.run(command)
