from passlib.context import CryptContext
pwd = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(p: str) -> str: return pwd.hash(p)
def verify_password(p: str, h: str) -> bool: return pwd.verify(p, h)
def needs_rehash(h: str) -> bool: return pwd.needs_update(h)
