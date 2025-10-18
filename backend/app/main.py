from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Import our database components ---
from app.database import database, models

# --- Import our API routers ---
# THE FIX IS HERE: Use relative imports with a leading dot (.)
from .api.routes import router as api_router
from .api.auth_router import router as auth_router

from fastapi.openapi.utils import get_openapi


# --- Create the database tables ---
models.Base.metadata.create_all(bind=database.engine)
print("Database tables created successfully (if they didn't already exist).")

# Create the FastAPI app instance
app = FastAPI(
    title="Customer Analytics API",
    description="An API for analyzing customer data, managing datasets, and providing insights.",
    version="1.1.0 - Now with Authentication!"
)

# --- Configure CORS (Cross-Origin Resource Sharing) ---
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "null",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include the API Routers ---
# Use the correct variable `auth_router`
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(api_router, prefix="/api", tags=["API"])

# --- Root Endpoint ---
@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Customer Analytics API."}

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Customer Analytics API",
        version="1.1.0 - Now with Authentication!",
        description="An API for analyzing customer data, managing datasets, and providing insights.",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
    }
    # ✅ FIX HERE
    openapi_schema["security"] = [{"OAuth2PasswordBearer": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi