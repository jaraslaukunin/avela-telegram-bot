"""ORM-модели Avela.

Здесь импортируются ВСЕ модели. Это не стилистика, а необходимость:
строковые ссылки в relationship (например, `User.notifications` →
`Notification`) SQLAlchemy разрешает только для уже зарегистрированных
классов. Импорт любого подмодуля пакета выполняет этот `__init__`, поэтому
набор моделей всегда полный — иначе `configure_mappers()` падает с
«failed to locate a name».
"""
from app.models.appointment import Appointment
from app.models.catalog import Branch, Doctor, DoctorService, Network, Service
from app.models.notification import Notification
from app.models.patient import Patient
from app.models.schedule import ScheduleTemplate, Slot
from app.models.service import ServiceHeartbeat
from app.models.user import AuditLog, BranchAdmin, User

__all__ = [
    "Appointment",
    "AuditLog",
    "Branch",
    "BranchAdmin",
    "Doctor",
    "DoctorService",
    "Network",
    "Notification",
    "Patient",
    "ScheduleTemplate",
    "Service",
    "ServiceHeartbeat",
    "Slot",
    "User",
]
