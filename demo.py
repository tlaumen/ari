import shutil
from pathlib import Path

if __name__ == "__main__":
    try:
        print("IMPLEMENT CORRECTLY WITH STEPRUNNER!")
    except Exception as e:
        print(e)

    shutil.rmtree(Path(__file__).parent / ".ceniac")
