"""
pes_worker.py — RQ-воркер для PES-скана с многораундовым LinUCB.

Концепция "матчей":
  Один job = несколько раундов (rounds).
  Раунд = полный PES-скан с одним набором (mapper, optimizer).

  После каждого раунда:
    1. Считаем avg_error = среднее |VQE - NumPy| по всем точкам
    2. Обновляем LinUCB (reward = 1/(1 + avg_error*1000))
    3. Если avg_error < QUALITY_THRESHOLD → стоп (качество достигнуто)
    4. Иначе → LinUCB выбирает НОВУЮ руку с учётом обновлённых данных → ещё раунд

  Результаты накапливаются: для каждого расстояния d сохраняем
  результат с НАИМЕНЬШЕЙ ошибкой |VQE - NumPy| среди всех раундов.

Параметры:
  MAX_ROUNDS         = 3   — максимум раундов (не даём зависнуть навсегда)
  QUALITY_THRESHOLD  = 0.005 Ha (5 mHa) — "хорошее" качество
  В ручном режиме (use_linucb=False) — всегда 1 раунд.
"""
import json
import logging
import traceback
from typing import Optional, Dict, Any
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from rq.decorators import job

from .launcher_adapter import run_scan
from . import linucb, context_extractor
from ..models import Job, JobStatus
from ..config import settings
from ..redis_client import redis_client
from ..utils.chart_preview import generate_preview_image

engine      = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
logger       = logging.getLogger(__name__)

# ── Параметры качества ────────────────────────────────────────────────────
MAX_ROUNDS        = 5      # максимум раундов в одном job
QUALITY_THRESHOLD = 0.0005  # Ha: avg |VQE-NumPy| < 5 mHa → считаем хорошим


def _avg_error(results: Dict[str, Any]) -> Optional[float]:
    """Средняя абсолютная ошибка VQE vs NumPy по всем точкам без ошибок."""
    errors = [
        abs(float(r["vqe"]) - float(r["numpy"]))
        for r in results.values()
        if "error" not in r and "vqe" in r and "numpy" in r
    ]
    return sum(errors) / len(errors) if errors else None


def _merge_results(best: Dict, new: Dict) -> Dict:
    """
    Объединяет результаты двух раундов:
    для каждого расстояния берём точку с меньшей ошибкой |VQE-NumPy|.
    """
    merged = dict(best)
    for dist, res in new.items():
        if "error" in res:
            continue
        if dist not in merged or "error" in merged[dist]:
            merged[dist] = res
        else:
            err_new  = abs(res.get("vqe", 0) - res.get("numpy", 0))
            err_best = abs(merged[dist].get("vqe", 0) - merged[dist].get("numpy", 0))
            if err_new < err_best:
                merged[dist] = res
    return merged


@job('pes_queue', connection=redis_client, timeout='4h')
def run_pes_scan(job_id: str):
    """RQ worker: PES-скан с многораундовым LinUCB."""
    try:
        # ── 1. Загрузить job, сохранить поля, пометить RUNNING ────────────
        with SessionLocal() as db:
            db_job = db.query(Job).filter(Job.id == job_id).first()
            if not db_job:
                logger.error("Job %s not found.", job_id)
                return

            molecule         = db_job.molecule
            atom_name        = db_job.atom_name
            precision_mult   = db_job.precision_multiplier
            use_linucb_flag  = bool(getattr(db_job, 'use_linucb', False))
            stored_mapper    = db_job.mapper
            stored_optimizer = db_job.optimizer

            db_job.status   = JobStatus.RUNNING
            db_job.progress = 0
            db.commit()
            logger.info("Job %s started: %s use_linucb=%s",
                        job_id, molecule, use_linucb_flag)

        # ── 2. Извлечь контекст для LinUCB (один раз на job) ─────────────
        linucb_context_list = None
        if use_linucb_flag:
            x = context_extractor.extract_context(molecule, atom_name)
            linucb_context_list = x.tolist()
            logger.info("[Job %s] context: %s", job_id, linucb_context_list)

        # ── 3. Прогресс-колбэк ────────────────────────────────────────────
        def progress_callback(progress: int, message: str,
                              partial_result: Optional[Dict] = None):
            try:
                with SessionLocal() as db:
                    upd = db.query(Job).filter(Job.id == job_id).first()
                    if upd:
                        upd.progress = progress
                        db.commit()
                if partial_result:
                    redis_key = f"job:{job_id}:partial_results"
                    redis_client.lpush(redis_key, json.dumps(partial_result))
                    redis_client.expire(redis_key, 3600)
                logger.info("[Job %s] %d%%: %s", job_id, progress, message)
            except Exception as e:
                logger.error("Progress callback error %s: %s", job_id, e)

        # ── 4. Многораундовый цикл ────────────────────────────────────────
        n_rounds  = MAX_ROUNDS if use_linucb_flag else 1
        best_results: Dict = {}          # лучшие точки по всем раундам
        last_arm_id     = None
        last_mapper     = stored_mapper
        last_optimizer  = stored_optimizer
        round_history   = []             # для метаданных job

        for round_idx in range(n_rounds):
            round_num = round_idx + 1
            logger.info("[Job %s] Round %d/%d", job_id, round_num, n_rounds)

            # 4a. LinUCB выбирает руку (или используем ручные параметры)
            if use_linucb_flag:
                x_arr = context_extractor._list_to_array(linucb_context_list)
                with SessionLocal() as db:
                    m_chosen, o_chosen, arm_chosen = linucb.select_arm(x_arr, db)

                actual_mapper    = m_chosen
                actual_optimizer = o_chosen
                last_arm_id      = arm_chosen
                last_mapper      = m_chosen
                last_optimizer   = o_chosen

                # Сохраняем выбор в БД (видно в UI)
                with SessionLocal() as db:
                    upd = db.query(Job).filter(Job.id == job_id).first()
                    if upd:
                        upd.mapper         = m_chosen
                        upd.optimizer      = o_chosen
                        upd.linucb_arm_id  = arm_chosen
                        upd.linucb_context = linucb_context_list
                        db.commit()

                logger.info("[Job %s] Round %d: LinUCB → %s",
                            job_id, round_num, arm_chosen)
            else:
                actual_mapper    = stored_mapper
                actual_optimizer = stored_optimizer

            # 4b. Смещаем прогресс-окно на раунд
            round_offset = int((round_idx / n_rounds) * 90)
            round_span   = int(90 / n_rounds)

            def round_progress(pct: int, msg: str, partial=None):
                global_pct = round_offset + int(pct / 100 * round_span)
                prefix = f"[Раунд {round_num}/{n_rounds}] " if use_linucb_flag else ""
                progress_callback(global_pct, prefix + msg, partial)

            # 4c. Скан
            scan_result = run_scan(
                molecule=molecule,
                atom_name=atom_name,
                optimizer=actual_optimizer,
                mapper=actual_mapper,
                precision_multiplier=precision_mult,
                progress_callback=round_progress,
            )

            round_results = scan_result.get("results", {})

            # 4d. Объединяем: сохраняем лучшее для каждой точки
            best_results = _merge_results(best_results, round_results)

            # 4e. Считаем ошибку по ВСЕМ накопленным результатам
            avg_err = _avg_error(best_results)
            reward  = linucb.compute_reward(0, avg_err) if avg_err is not None else 0

            round_info = {
                "round":        round_num,
                "mapper":       actual_mapper,
                "optimizer":    actual_optimizer,
                "avg_error_ha": round(avg_err, 6) if avg_err is not None else None,
                "reward":       round(reward, 4),
                "n_points":     len(round_results),
            }
            round_history.append(round_info)
            logger.info("[Job %s] Round %d done: avg_err=%.4f Ha reward=%.4f",
                        job_id, round_num,
                        avg_err if avg_err else 0, reward)

            # 4f. LinUCB: обновить модель после раунда
            if use_linucb_flag and linucb_context_list and last_arm_id:
                x_arr = context_extractor._list_to_array(linucb_context_list)
                with SessionLocal() as db:
                    linucb.update(
                        last_arm_id, actual_mapper, actual_optimizer,
                        x_arr, reward, db
                    )
                    db.commit()

            # 4g. Проверка качества — нужен ли следующий раунд?
            if avg_err is not None and avg_err < QUALITY_THRESHOLD:
                logger.info(
                    "[Job %s] Quality OK (%.4f Ha < %.4f Ha). Stop after round %d.",
                    job_id, avg_err, QUALITY_THRESHOLD, round_num)
                if use_linucb_flag:
                    progress_callback(
                        round_offset + round_span,
                        f"Качество достигнуто за {round_num} раунд(а): "
                        f"avg_error={avg_err*1000:.2f} мHa ✓"
                    )
                break
            elif round_num < n_rounds and use_linucb_flag:
                progress_callback(
                    round_offset + round_span,
                    f"Раунд {round_num}: avg_error={avg_err*1000:.2f} мHa. "
                    f"Запускаем раунд {round_num+1}…"
                )

        # ── 5. Сохранить финальные результаты ────────────────────────────
        final_avg_err = _avg_error(best_results)
        final_reward  = (linucb.compute_reward(0, final_avg_err)
                         if final_avg_err is not None else None)
        successful    = sum(1 for r in best_results.values() if "error" not in r)

        with SessionLocal() as db:
            db_job = db.query(Job).filter(Job.id == job_id).first()
            if not db_job:
                logger.error("Job %s vanished.", job_id)
                return

            db_job.results = best_results
            db_job.job_metadata = {
                "min_distance":     _find_min(best_results),
                "peaks":            [],
                "elapsed_time":     None,
                "total_points":     len(best_results),
                "successful_points": successful,
                "mapper":           last_mapper,
                "optimizer":        last_optimizer,
                "rounds_completed": len(round_history),
                "round_history":    round_history,
                "final_avg_error_ha": round(final_avg_err, 6)
                                      if final_avg_err is not None else None,
            }

            if successful > 0:
                db_job.preview_image = generate_preview_image(
                    results=best_results, molecule=molecule)
                db_job.status        = JobStatus.COMPLETED
                db_job.progress      = 100
                if use_linucb_flag:
                    db_job.linucb_reward = final_reward
                logger.info("Job %s COMPLETED: %d rounds, avg_err=%.4f Ha",
                            job_id, len(round_history),
                            final_avg_err if final_avg_err else 0)
            else:
                db_job.status        = JobStatus.FAILED
                db_job.progress      = 100
                db_job.error_message = "Scan failed: no successful points."
                logger.warning("Job %s FAILED.", job_id)

            db.commit()

        progress_callback(100, "Готово!")

    except Exception as e:
        tb = traceback.format_exc()
        logger.critical("Unhandled exception in job %s:\n%s", job_id, tb)
        try:
            with SessionLocal() as db:
                upd = db.query(Job).filter(Job.id == job_id).first()
                if upd:
                    upd.status        = JobStatus.FAILED
                    upd.error_message = f"Critical error: {e}\n{tb}"
                    db.commit()
        except Exception as db_e:
            logger.error("Cannot mark job %s FAILED: %s", job_id, db_e)
        raise


def _find_min(results: Dict) -> Optional[float]:
    """Расстояние с минимальной VQE-энергией."""
    ok = {float(d): r for d, r in results.items()
          if "error" not in r and "vqe" in r}
    if not ok:
        return None
    return min(ok, key=lambda d: ok[d]["vqe"])
