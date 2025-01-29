from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI(
    title="IFC Exchange API",
    description="API for IFC files processing and exchange",
    version="1.0.0"
)
# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)


# Global storages
IFCS = dict()
OIFCS=dict()
# TASKS dict will store:
# { task_id: { "status": "pending"|"done"|"error", "result": Optional[list[Collision]] } }
TASKS = {}
