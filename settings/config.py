import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    # звʼязок з БД
    DEBUG: bool = False
    BASE_URL: str
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str

    ADMIN_USER_MODEL: str
    ADMIN_USER_MODEL_USERNAME_FIELD: str
    ADMIN_SECRET_KEY: str | int

    CELERY_BROKER_URL: str

    @property
    def database_url_async(self) -> str:
        return f'postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    @property
    def database_url_sync(self) -> str:
        return f'postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    @property
    def templates(self) -> Jinja2Templates:
        return Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

    @property
    def static(self):
        return StaticFiles(directory=os.path.join(BASE_DIR, "static"))

    model_config = SettingsConfigDict(env_file='.env')


settings = Settings()

# ----------------------------------------------------------------------------------------------
# db_connection_string = 'postgresql://{postgres}:{postgres!23}@{localhost:5432}/{shop_aggrigate}'.format()
# DATABASE_URL = "postgresql+asyncpg://username:password@localhost/dbname"


# TEMPLATES = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
# STATIC = StaticFiles(directory=os.path.join(BASE_DIR, "static"))


# звʼязок з БД

#
# db_async_connection_string = f'postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
# db_connection_string = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
# 'postgresql://postgres:postgres!23@localhost:5432/shop_aggrigate_2'


# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
# class FastAdminSettings:
#     """Settings"""
#
#     # This value is the prefix you used for mounting FastAdmin app for FastAPI.
#     ADMIN_PREFIX: str = os.getenv("ADMIN_PREFIX", "admin")
#
#     # This value is the site name on sign-in page and on header.
#     ADMIN_SITE_NAME: str = os.getenv("ADMIN_SITE_NAME", "FastAdmin")
#
#     # This value is the logo path on sign-in page.
#     ADMIN_SITE_SIGN_IN_LOGO: str = os.getenv("ADMIN_SITE_SIGN_IN_LOGO", "/admin/static/images/sign-in-logo.svg")
#
#     # This value is the logo path on header.
#     ADMIN_SITE_HEADER_LOGO: str = os.getenv("ADMIN_SITE_HEADER_LOGO", "/admin/static/images/header-logo.svg")
#
#     # This value is the favicon path.
#     ADMIN_SITE_FAVICON: str = os.getenv("ADMIN_SITE_FAVICON", "/admin/static/images/favicon.png")
#
#     # This value is the primary color for FastAdmin.
#     ADMIN_PRIMARY_COLOR: str = os.getenv("ADMIN_PRIMARY_COLOR", "#009485")
#
#     # This value is the session id key to store session id in http only cookies.
#     ADMIN_SESSION_ID_KEY: str = os.getenv("ADMIN_SESSION_ID_KEY", "admin_session_id")
#
#     # This value is the expired_at period (in sec) for session id.
#     ADMIN_SESSION_EXPIRED_AT: int = os.getenv("ADMIN_SESSION_EXPIRED_AT", 144000)  # in sec
#
#     # This value is the date format for JS widgets.
#     ADMIN_DATE_FORMAT: str = os.getenv("ADMIN_DATE_FORMAT", "YYYY-MM-DD")
#
#     # This value is the datetime format for JS widgets.
#     ADMIN_DATETIME_FORMAT: str = os.getenv("ADMIN_DATETIME_FORMAT", "YYYY-MM-DD HH:mm")
#
#     # This value is the time format for JS widgets.
#     ADMIN_TIME_FORMAT: str = os.getenv("ADMIN_TIME_FORMAT", "HH:mm:ss")
#
#     # This value is the name for User db/orm model class for authentication.
#     ADMIN_USER_MODEL: str = os.getenv("ADMIN_USER_MODEL")
#
#     # This value is the username field for User db/orm model for for authentication.
#     ADMIN_USER_MODEL_USERNAME_FIELD: str = os.getenv("ADMIN_USER_MODEL_USERNAME_FIELD")
#
#     # This value is the key to securing signed data - it is vital you keep this secure,
#     # or attackers could use it to generate their own signed values.
#     ADMIN_SECRET_KEY: str = os.getenv("ADMIN_SECRET_KEY")
#
#     # This value disables the crop image feature in FastAdmin.
#     ADMIN_DISABLE_CROP_IMAGE: bool = os.getenv("ADMIN_DISABLE_CROP_IMAGE", False)
