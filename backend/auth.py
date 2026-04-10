"""
Authentication & Authorization System
JWT-based auth with multi-tenant isolation
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from models import User, Client, ApiKey, get_session_factory

# Configuration
SECRET_KEY = "your-secret-key-change-this-in-production"  # Change in production!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


# ==================== PASSWORD UTILS ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ==================== JWT TOKENS ====================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create long-lived refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ==================== DEPENDENCIES ====================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(lambda: None)  # Will be overridden
) -> User:
    """Get current authenticated user from JWT token"""
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    # Note: db session needs to be properly injected
    from fastapi import Depends
    from database import get_db
    
    db = next(get_db())
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure user is active"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role"""
    if current_user.role not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ==================== API KEY AUTH ====================

async def get_client_from_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(lambda: None)
) -> Client:
    """Authenticate via API key"""
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    api_key = credentials.credentials
    
    # Hash the provided key and look it up
    from database import get_db
    db = next(get_db())
    
    # Find by prefix (first 8 chars)
    key_prefix = api_key[:8] if len(api_key) >= 8 else api_key
    
    api_key_record = db.query(ApiKey).filter(
        ApiKey.key_prefix == key_prefix,
        ApiKey.is_active == True
    ).first()
    
    if not api_key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Verify full key
    if not pwd_context.verify(api_key, api_key_record.key_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Check expiration
    if api_key_record.expires_at and api_key_record.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired"
        )
    
    # Update last used
    api_key_record.last_used_at = datetime.utcnow()
    db.commit()
    
    return api_key_record.client


# ==================== TENANT ISOLATION ====================

class TenantContext:
    """Context manager for tenant isolation"""
    
    def __init__(self, client_id: int):
        self.client_id = client_id
    
    def filter_query(self, query, model):
        """Add client_id filter to query"""
        if hasattr(model, 'client_id'):
            return query.filter(model.client_id == self.client_id)
        return query


def get_tenant_context(current_user: User = Depends(get_current_user)) -> TenantContext:
    """Get tenant context for current user"""
    return TenantContext(current_user.client_id)


# ==================== LOGIN/REGISTER ====================

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate user credentials"""
    # Demo account - always works (accept both "demo" and full email)
    demo_email = "demo@complaicore.com"
    if email.lower() in ["demo", demo_email] and password == "demo123":
        # Check if demo user exists, create if not
        user = db.query(User).filter(User.email == demo_email).first()
        if not user:
            # Create demo client if needed
            from slugify import slugify
            client_slug = "demo-client"
            client = db.query(Client).filter(Client.slug == client_slug).first()
            if not client:
                client = Client(
                    company_name="Demo Lending Corp",
                    slug=client_slug,
                    email="admin@demolending.com",
                    plan="trial",
                    trial_ends_at=datetime.utcnow() + timedelta(days=365)
                )
                db.add(client)
                db.flush()
            
            # Create demo user
            user = User(
                client_id=client.id,
                email=demo_email,
                first_name="Demo",
                last_name="User",
                role="admin"
            )
            user.set_password(password)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    
    # Regular authentication
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not user.check_password(password):
        return None
    return user


def register_client(db: Session, company_name: str, email: str, password: str, 
                   admin_first_name: str, admin_last_name: str) -> Client:
    """Register a new client with admin user"""
    
    from slugify import slugify
    
    # Create slug from company name
    slug = slugify(company_name)
    
    # Check if slug exists
    existing = db.query(Client).filter(Client.slug == slug).first()
    if existing:
        slug = f"{slug}-{datetime.utcnow().strftime('%Y%m%d')}"
    
    # Create client
    client = Client(
        company_name=company_name,
        slug=slug,
        email=email,
        plan="trial",
        trial_ends_at=datetime.utcnow() + timedelta(days=14)
    )
    db.add(client)
    db.flush()  # Get client.id
    
    # Create admin user
    admin = User(
        client_id=client.id,
        email=email,
        first_name=admin_first_name,
        last_name=admin_last_name,
        role="admin"
    )
    admin.set_password(password)
    db.add(admin)
    
    db.commit()
    
    return client, admin
