import threading
import time

from app.database.connection import SessionLocal
from app.models.screening_result import ScreeningResult

RESULT_ID = 1

lock_acquired = threading.Event()
release_lock = threading.Event()


def clinician_a():
    db = SessionLocal()

    try:
        result = (
            db.query(ScreeningResult)
            .filter(ScreeningResult.result_id == RESULT_ID)
            .with_for_update()
            .first()
        )

        print("Clinician A: row locked:", result.result_id)
        lock_acquired.set()

        release_lock.wait(timeout=15)

        db.rollback()
        print("Clinician A: transaction released.")

    finally:
        db.close()


def clinician_b():
    lock_acquired.wait()

    db = SessionLocal()

    try:
        print("Clinician B: attempting to lock the same row...")

        start = time.time()

        result = (
            db.query(ScreeningResult)
            .filter(ScreeningResult.result_id == RESULT_ID)
            .with_for_update()
            .first()
        )

        elapsed = time.time() - start

        print("Clinician B: acquired row lock.")
        print(f"Waited approximately {elapsed:.2f} seconds.")

    finally:
        db.rollback()
        db.close()


thread_a = threading.Thread(target=clinician_a)
thread_b = threading.Thread(target=clinician_b)

thread_a.start()
thread_b.start()

time.sleep(3)
release_lock.set()

thread_a.join()
thread_b.join()

print("Row-locking test completed.")