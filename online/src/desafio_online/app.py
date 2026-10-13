from __future__ import annotations

import os
from pathlib import Path

from . import app_core as _core
from .app_core import *  # noqa: F401,F403
from .bank import QuestionBankService
from .questions_api import build_questions_router


_SOURCE_BANK_PATH = REPOSITORY_ROOT / "v3_1" / "projects" / "demo.juego"
_CONFIGURED_BANK_PATH = os.environ.get("QUESTION_BANK_PATH", "").strip()

if _CONFIGURED_BANK_PATH:
    _bank_path = Path(_CONFIGURED_BANK_PATH).expanduser()
    if not _bank_path.is_absolute():
        _bank_path = REPOSITORY_ROOT / _bank_path
    _bank_writes = True
    _bank_storage_mode = "configured_path"
elif environment == "production":
    _bank_path = _SOURCE_BANK_PATH
    _bank_writes = False
    _bank_storage_mode = "read_only_repository"
else:
    _bank_path = _SOURCE_BANK_PATH
    _bank_writes = True
    _bank_storage_mode = "development_repository"

question_bank = QuestionBankService(
    _bank_path,
    seed_path=_SOURCE_BANK_PATH,
    allow_writes=_bank_writes,
    storage_mode=_bank_storage_mode,
)

# Las rutas definidas en app_core consultan su propio global `registry`.
# Lo sustituimos antes de que la aplicación atienda solicitudes para que
# toda sala nueva lea el mismo banco que administra Fase 7.
registry = RoomRegistry(
    question_bank.path,
    max_participants=_core._configured_capacity(),
)
_core.registry = registry

app = _core.app
app.include_router(
    build_questions_router(
        question_bank,
        require_admin=require_admin,
        template_path=REPOSITORY_ROOT / "v3_1" / "templates" / "Banco_preguntas_V2.xlsx",
    )
)
