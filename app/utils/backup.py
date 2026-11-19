"""
Falcon Kibertexnology School - Ma'lumotlar bazasi zaxira nusxasi (backup).
Kunlik avtomatik SQLite faylini backups/ jildiga nusxalash.
"""

import logging
import os
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)


def perform_db_backup(
    db_file_path: str = "falcon_school.db",
    backup_folder: str = "backups",
) -> str:
    """
    SQLite ma'lumotlar bazasi faylidan zaxira nusxa oladi.
    Qaytaradi: yaratilgan zaxira fayl yo'li.
    """
    if not os.path.exists(db_file_path):
        logger.warning(f"[BACKUP SKIPPED] Baza fayli mavjud emas: {db_file_path}")
        return ""

    os.makedirs(backup_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"falcon_school_backup_{timestamp}.db"
    dest_path = os.path.join(backup_folder, backup_filename)

    try:
        shutil.copy2(db_file_path, dest_path)
        logger.info(f"[BACKUP SUCCESS] Zaxira nusxa yaratildi: {dest_path}")
        return dest_path
    except Exception as e:
        logger.error(f"[BACKUP FAILED] Zaxiralashda xatolik: {e}")
        return ""
