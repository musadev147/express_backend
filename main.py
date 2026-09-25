import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CRM_BACKEND_DIR = os.path.join(BASE_DIR, "express_crm_backend")

if CRM_BACKEND_DIR not in sys.path:
    sys.path.insert(0, CRM_BACKEND_DIR)

from app.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
