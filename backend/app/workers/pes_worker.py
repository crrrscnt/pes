"""
pes_worker.py — RQ-воркер для PES-скана с многораундовым LinUCB.
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
from ..models import Job, JobStatus, JobRound, MoleculePreset
from ..config import settings
from ..redis_client import redis_client
from ..utils.chart_preview import generate_preview_image

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
logger = logging.getLogger(__name__)

MAX_ROUNDS = 5
QUALITY_THRESHOLD = 0.0005


def _avg_error(results: Dict[str, Any]) -> Optional[float]:
    errors = [
        abs(float(r["vqe"]) - float(r["numpy"]))
        for r in results.values()
        if "error" not in r and "vqe" in r and "numpy" in r
    ]
    return sum(errors) / len(errors) if errors else None


def _merge_results(best: Dict, new: Dict) -> Dict:
    merged = dict(best)
    for dist, res in new.items():
        if "error" in res:
            continue
        if dist not in merged or "error" in merged[dist]:
            merged[dist] = res
        else:
            err_new = abs(res.get("vqe", 0) - res.get("numpy", 0))
            err_best = abs(merged[dist].get("vqe", 0) - merged[dist].get("numpy", 0))
            if err_new < err_best:
                merged[dist] = res
    return merged


@job('pes_queue', connection=redis_client, timeout='4h')
def run_pes_scan(job_id: str):
    try:
        with SessionLocal() as db:
            db_job = db.query(Job).filter(Job.id == job_id).first()
            if not db_job:
                logger.error("Job %s not found.", job_id)
                return

            molecule_preset_id = db_job.molecule_preset_id
            precision_mult = db_job.precision_multiplier
            use_linucb_flag = bool(getattr(db_job, 'use_linucb', False))
            stored_mapper = db_job.mapper
            stored_optimizer = db_job.optimizer

            preset = db.query(MoleculePreset).filter(
                MoleculePreset.id == molecule_preset_id
            ).first()

            if not preset:
                logger.error("Preset %s not found for job %s.",
                             molecule_preset_id, job_id)
                db_job.status = JobStatus.FAILED
                db_job.error_message = f"Molecule preset {molecule_preset_id} not found"
                db.commit()
                return

            db_job.status = JobStatus.RUNNING
            db_job.progress = 0
            db.commit()
            logger.info("Job %s started: %s use_linucb=%s",
                        job_id, molecule_preset_id, use_linucb_flag)

        linucb_context_list = None
        if use_linucb_flag:
            with SessionLocal() as db:
                x = context_extractor.extract_context(molecule_preset_id, db)
                linucb_context_list = x.tolist()
                logger.info("[Job %s] context: %s", job_id, linucb_context_list)

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

        n_rounds = MAX_ROUNDS if use_linucb_flag else 1
        best_results: Dict = {}
        last_arm_id = None
        last_mapper = stored_mapper
        last_optimizer = stored_optimizer

        for round_idx in range(n_rounds):
            round_num = round_idx + 1
            logger.info("[Job %s] Round %d/%d", job_id, round_num, n_rounds)

            if use_linucb_flag:
                x_arr = context_extractor._list_to_array(linucb_context_list)
                with SessionLocal() as db:
                    m_chosen, o_chosen, arm_chosen = linucb.select_arm(x_arr, db)

                actual_mapper = m_chosen
                actual_optimizer = o_chosen
                last_arm_id = arm_chosen
                last_mapper = m_chosen
                last_optimizer = o_chosen

                with SessionLocal() as db:
                    upd = db.query(Job).filter(Job.id == job_id).first()
                    if upd:
                        upd.mapper = m_chosen
                        upd.optimizer = o_chosen
                        db.commit()

                logger.info("[Job %s] Round %d: LinUCB → %s",
                            job_id, round_num, arm_chosen)
            else:
                actual_mapper = stored_mapper
                actual_optimizer = stored_optimizer

            round_offset = int((round_idx / n_rounds) * 90)
            round_span = int(90 / n_rounds)

            def round_progress(pct: int, msg: str, partial=None):
                global_pct = round_offset + int(pct / 100 * round_span)
                prefix = f"[Раунд {round_num}/{n_rounds}] " if use_linucb_flag else ""
                progress_callback(global_pct, prefix + msg, partial)

            scan_result = run_scan(
                molecule_preset_id=molecule_preset_id,
                optimizer=actual_optimizer,
                mapper=actual_mapper,
                distance_min=preset.distance_min,
                distance_max=preset.distance_max,
                step=preset.step,
                precision_multiplier=precision_mult,
                progress_callback=round_progress,
            )

            round_results = scan_result.get("results", {})
            best_results = _merge_results(best_results, round_results)

            avg_err = _avg_error(best_results)
            reward = linucb.compute_reward_from_error(avg_err) \
                if avg_err is not None else 0.0

            with SessionLocal() as db:
                job_round = JobRound(
                    job_id=job_id,
                    arm_id=last_arm_id if last_arm_id else f"{actual_mapper}_{actual_optimizer}",
                    round_number=round_num,
                    reward=reward,
                    avg_error_ha=avg_err,
                    context_vector=linucb_context_list,
                )
                db.add(job_round)
                db.commit()

            logger.info("[Job %s] Round %d done: avg_err=%.4f Ha reward=%.4f",
                        job_id, round_num,
                        avg_err if avg_err else 0, reward)

            if use_linucb_flag and linucb_context_list and last_arm_id:
                x_arr = context_extractor._list_to_array(linucb_context_list)
                with SessionLocal() as db:
                    linucb.update(
                        last_arm_id, actual_mapper, actual_optimizer,
                        x_arr, reward, db
                    )
                    db.commit()

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

        final_avg_err = _avg_error(best_results)
        successful = sum(1 for r in best_results.values() if "error" not in r)

        with SessionLocal() as db:
            db_job = db.query(Job).filter(Job.id == job_id).first()
            if not db_job:
                logger.error("Job %s vanished.", job_id)
                return

            db_job.results = best_results
            db_job.job_metadata = {
                "min_distance": _find_min(best_results),
                "peaks": [],
                "elapsed_time": None,
                "total_points": len(best_results),
                "successful_points": successful,
                "mapper": last_mapper,
                "optimizer": last_optimizer,
                "rounds_completed": round_num if 'round_num' in locals() else 1,
                "final_avg_error_ha": round(final_avg_err, 6)
                                      if final_avg_err is not None else None,
            }

            if successful > 0:
                db_job.preview_image = generate_preview_image(
                    results=best_results, molecule=molecule_preset_id)
                db_job.status = JobStatus.COMPLETED
                db_job.progress = 100
                logger.info("Job %s COMPLETED: %d rounds, avg_err=%.4f Ha",
                            job_id, round_num if 'round_num' in locals() else 1,
                            final_avg_err if final_avg_err else 0)
            else:
                db_job.status = JobStatus.FAILED
                db_job.progress = 100
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
                    upd.status = JobStatus.FAILED
                    upd.error_message = f"Critical error: {e}\n{tb}"
                    db.commit()
        except Exception as db_e:
            logger.error("Cannot mark job %s FAILED: %s", job_id, db_e)
        raise


def _find_min(results: Dict) -> Optional[float]:
    ok = {float(d): r for d, r in results.items()
          if "error" not in r and "vqe" in r}
    if not ok:
        return None
    return min(ok, key=lambda d: ok[d]["vqe"])