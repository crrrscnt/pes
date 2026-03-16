from sqlalchemy import create_engine, text
from app.config import settings
import datetime

engine = create_engine(settings.database_url)

with engine.connect() as conn:
    # Показать статистику до очистки
    result = conn.execute(text("""
        SELECT status, count(*),
               min(created_at) as oldest,
               max(created_at) as newest
        FROM jobs
        GROUP BY status;
    """))
    print("\nТекущая статистика:")
    for row in result:
        print(f"{row.status}: {row.count} jobs ({row.oldest} - {row.newest})")

    # Спросить, что удалять
    print("\nВыберите действие:")
    print("1. Удалить все FAILED")
    print("2. Удалить FAILED старше 7 дней")
    print("3. Удалить все COMPLETED")
    print("4. Удалить все QUEUED")
    print("5. Удалить все RUNNING")
    print("6. Выйти")

    choice = input("\nВведите номер (1-4): ")

    if choice == "1":
        result = conn.execute(text("DELETE FROM jobs WHERE status = 'failed';"))
        conn.commit()
        print(f"Удалено {result.rowcount} записей")

    elif choice == "2":
        result = conn.execute(text(
            "DELETE FROM jobs WHERE status = 'failed' AND created_at < NOW() - INTERVAL '7 days';"
        ))
        conn.commit()
        print(f"Удалено {result.rowcount} записей")

    elif choice == "3":
        result = conn.execute(
            text("DELETE FROM jobs WHERE status = 'completed';"))
        conn.commit()
        print(f"Удалено {result.rowcount} записей")

    elif choice == "4":
        result = conn.execute(text("DELETE FROM jobs WHERE status = 'queued';"))
        conn.commit()
        print(f"Удалено {result.rowcount} записей")

    elif choice == "5":
        result = conn.execute(
            text("DELETE FROM jobs WHERE status = 'running';"))
        conn.commit()
        print(f"Удалено {result.rowcount} записей")

    else:
        print("Выход.")
        exit(0)
