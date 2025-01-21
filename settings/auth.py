from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Додайте свою логіку для перевірки токена
    # Наприклад, розшифровка JWT або перевірка у базі даних
    if not token or token != "valid_token":  # Замініть на реальну перевірку
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"username": "authorized_user"}  # Повертає інформацію про користувача