from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

# --- Import all our components ---
from app.database import database, models, schemas
from app import auth

# Create a new router for authentication
router = APIRouter()

@router.post("/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """
    Creates a new user in the database with manual password validation and truncation.
    """
    # First, check if a user with this email already exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )

    # Validate password length
    if len(user.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password is too short. Please use a password with at least 8 characters."
        )

    # --- THE DEFINITIVE FIX ---
    # We truncate the password to a maximum of 72 bytes before hashing.
    # This directly follows the error message's advice and is a foolproof
    # way to prevent the ValueError from occurring.
    safe_password = user.password[:72]
    hashed_password = auth.get_password_hash(safe_password)
    # --- END OF FIX ---

    # Create the new user record using the hashed password
    new_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

# --------------------------------------------------------------------
# Endpoint 2: Log In and Get an Access Token
# --------------------------------------------------------------------
@router.post("/login", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(database.get_db)
):
    """
    Authenticates a user and returns a JWT access token.
    """
    user = auth.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(data={"sub": user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}
