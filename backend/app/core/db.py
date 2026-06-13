"""MongoDB connection (Motor) and Beanie initialisation."""

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings
from app.models.audit_log import AuditLog
from app.models.auth_test import AuthTest
from app.models.banner import Banner
from app.models.campaign import Campaign
from app.models.config import AppConfig
from app.models.host import Host
from app.models.mitre import MitreTechnique
from app.models.nikto_scan import NiktoScan
from app.models.port import Port
from app.models.report import Report
from app.models.service import Service
from app.models.sqlmap_scan import SqlmapScan
from app.models.user import User
from app.models.vulnerability import Vulnerability

settings = get_settings()

# Document models to register with Beanie
DOCUMENT_MODELS = [
    User,
    Campaign,
    Host,
    Port,
    Service,
    Banner,
    Vulnerability,
    MitreTechnique,
    AuthTest,
    Report,
    AppConfig,
    SqlmapScan,
    AuditLog,
    NiktoScan,
]


async def init_db() -> None:
    """Initialise the MongoDB connection and Beanie ODM."""
    client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGODB_URL)
    database = client[settings.MONGODB_DB_NAME]

    await init_beanie(
        database=database,
        document_models=DOCUMENT_MODELS,  # type: ignore[list-item]
    )
