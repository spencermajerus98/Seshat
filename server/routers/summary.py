"""Daily summary — the copy-paste artifact for the enterprise ELN."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends

from core import summary

from .. import security
from ..deps import current_session, db as db_lock

router = APIRouter(prefix="/api/summary", tags=["summary"])


@router.get("")
def daily_summary(
    date: Optional[str] = None, sess: security.Session = Depends(current_session)
):
    on_date = dt.date.fromisoformat(date) if date else dt.date.today()
    with db_lock(sess) as conn:
        return summary.build_daily_summary(conn, on_date)
