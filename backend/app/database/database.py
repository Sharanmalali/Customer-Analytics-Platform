from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# --- 1. Define the Database URL ---
# This is the connection string for our SQLite database.
# We will construct a path to a file named 'development.db' which will be
# created inside the 'backend/data/' directory.

# Get the path to the project's root directory (customer_analytics_platform)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Define the path for our database file
DATABASE_FILE_PATH = BASE_DIR / "data" / "development.db"
# The full SQLAlchemy database URL
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_FILE_PATH}"

print(f"Database file will be created at: {DATABASE_FILE_PATH}")


# --- 2. Create the SQLAlchemy Engine ---
# The engine is the central point of communication with the database.
# The 'connect_args' is needed only for SQLite to allow multiple threads to
# interact with the database, which is necessary for web applications.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)


# --- 3. Create a Session Factory ---
# Each instance of SessionLocal will be a database session.
# A session is the primary interface for all database operations (queries, commits, etc.).
# We create this "factory" here, and our API will request a session from it
# whenever it needs to talk to the database.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 4. NEW: Dependency to get a DB session ---
# This function will be called by our API routes.
# It yields a database session for a single request and ensures
# it is always closed afterward, even if an error occurs.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()