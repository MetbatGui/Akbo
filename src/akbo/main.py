from fastapi import FastAPI
app = FastAPI(title="Akbo API")

@app.get("/health")
def health():
    return {"status": "ok"}