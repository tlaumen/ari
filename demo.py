from ari.classify_work import agent_loop
import shutil
from pathlib import Path

if __name__ == "__main__":
    try:
        agent_loop()
    except Exception as e:
        print(e)

    shutil.rmtree(Path(__file__).parent / ".ceniac")
