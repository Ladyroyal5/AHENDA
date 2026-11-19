from sqlalchemy import inspect
from app.database.connection import engine, Base
import app.models


def audit_explicit_indexes():
    inspector = inspect(engine)
    issues = 0

    print("\n========== AHENDA EXPLICIT INDEX AUDIT ==========\n")

    for table_name, model_table in Base.metadata.tables.items():

        db_indexes = inspector.get_indexes(table_name)

        # Only inspect explicitly named performance indexes.
        db_explicit = {
            tuple(index["column_names"])
            for index in db_indexes
            if index["name"].startswith("idx_")
        }

        python_explicit = {
            tuple(column.name for column in index.columns)
            for index in model_table.indexes
            if index.name and index.name.startswith("idx_")
        }

        missing_in_python = db_explicit - python_explicit
        missing_in_mysql = python_explicit - db_explicit

        if missing_in_python or missing_in_mysql:
            issues += 1
            print(f"\nTABLE: {table_name}")

            if missing_in_python:
                print("MySQL performance indexes missing in Python:")
                print(missing_in_python)

            if missing_in_mysql:
                print("Python performance indexes missing in MySQL:")
                print(missing_in_mysql)

    if issues == 0:
        print("All explicit performance indexes match!")

    else:
        print(f"\nTables with differences: {issues}")

    print("\n=================================================\n")


if __name__ == "__main__":
    audit_explicit_indexes()