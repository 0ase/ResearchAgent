from fastapi import FastAPI

# title 参数为 API 指定一个标题，会出现在自动生成的交互式文档（/docs）中，便于识别
app = FastAPI(title="多Agent学术研究助手")

from backend.api.routes_research import router as research_router

app.include_router(research_router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok"}