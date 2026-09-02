"""Start the automatic-video SaaS web MVP."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("saas_web:app", host="0.0.0.0", port=8000, reload=False)
