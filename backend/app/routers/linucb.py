"""
routers/linucb.py — API для просмотра и управления состоянием LinUCB-бандита.

Endpoints:
  GET  /api/linucb/arms         — статистика всех 9 рук (admin only)
  POST /api/linucb/reset        — сбросить всю историю (admin only)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User, LinUCBArm
from ..workers import linucb

router_linucb = APIRouter(prefix="/api/linucb", tags=["linucb"])


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router_linucb.get("/arms", response_model=List[Dict[str, Any]])
async def get_arm_stats(
        db: Session = Depends(get_db),
        current_user: User = Depends(_require_admin),
):
    """
    Возвращает статистику всех 9 рук LinUCB-бандита.

    Поля каждой руки:
    - arm_id:       идентификатор ("Parity_SLSQP" и т.д.)
    - mapper:       название маппера
    - optimizer:    название оптимизатора
    - n_pulls:      сколько раз выбиралась эта рука
    - avg_reward:   средняя награда ∈ (0,1] (null если не было запусков)
    - total_reward: суммарная награда
    """
    return linucb.get_arm_stats(db)


@router_linucb.post("/reset")
async def reset_bandit(
        db: Session = Depends(get_db),
        current_user: User = Depends(_require_admin),
):
    """
    Сбрасывает всё состояние LinUCB-бандита (удаляет все строки из таблицы).
    Используется для перезапуска обучения с нуля.
    """
    deleted = db.query(LinUCBArm).delete()
    db.commit()
    return {"message": f"LinUCB state reset: {deleted} arms deleted"}
