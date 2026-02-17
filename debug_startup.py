
import sys
import os

with open("debug_log.txt", "w") as f:
    f.write("Step 1: Imports started\n")
    f.flush()

    try:
        from fastapi import FastAPI
        f.write("Step 2: FastAPI imported\n")
        f.flush()
        
        from src.core.llm_factory import LLMFactory
        f.write("Step 3: LLMFactory imported\n")
        f.flush()

        from src.api.routes import router
        f.write("Step 4: Router imported\n")
        f.flush()
        
    except Exception as e:
        f.write(f"Error: {e}\n")
        f.flush()

    f.write("Imports done\n")
