import subprocess

if __name__ == "__main__":
    command = ["streamlit", "run", "trabajo_modulado/app/dashboard.py"]
    subprocess.run(command)