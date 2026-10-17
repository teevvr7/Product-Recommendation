import uvicorn
from backend.config import settings

if __name__ == "__main__":
    print(f"============================================================")
    print(f"  {settings.APP_NAME}")
    print(f"  Version: {settings.APP_VERSION}")
    print(f"  Server starting at: http://{settings.HOST}:{settings.PORT}")
    print(f"  Swagger API Docs at: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"============================================================")
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level="info"
    )
