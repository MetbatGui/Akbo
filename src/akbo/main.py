from fastapi import FastAPI

app = FastAPI(title="Akbo API", version="0.1.0")


@app.get("/healthz")
def health():
    return {"status": "ok"}
