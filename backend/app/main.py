import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import APP_HOST, APP_PORT, DEBUG
from app.routers import auth, chat, homework, mistakes, challenge, students, reports
from app.database import init_db

os.makedirs("uploads", exist_ok=True)

app = FastAPI(title="AI助学", description="小学3-6年级AI辅导助手")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(homework.router)
app.include_router(mistakes.router)
app.include_router(challenge.router)
app.include_router(students.router)
app.include_router(reports.router)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=DEBUG,
    )
