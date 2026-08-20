"""SQLAlchemy copy-paste reference for contests / gamedays.

Style: reflect an EXISTING database with automap (no models to write by hand),
then copy the section you need. Every scenario below is self-contained.

Sections
    1. Engine (mysql / postgres)
    2. Reflect tables (automap)
    3. JSON serialization of a reflected row
    4. CRUD (insert / select one / select many / update / delete)
    5. Dynamic column update by name  (update a field you only know at runtime)
    6. Dynamic insert with **kwargs
    7. Filter by field / join
"""

import json
import logging

from sqlalchemy import create_engine, select
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# 1. ENGINE
# =============================================================================
# mysql   ->  pip install mysql-connector-python
# postgres->  pip install psycopg2-binary
#
# pool_pre_ping=True  : drop dead connections instead of erroring mid-request.
# future=True         : SQLAlchemy 2.0 style API.

def create_engine_mysql(user, password, host, database, port=3306):
    url = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}"
    return create_engine(url, pool_pre_ping=True, future=True)


def create_engine_postgres(user, password, host, database, port=5432):
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    return create_engine(url, pool_pre_ping=True, future=True)


# Pick one. Edit the credentials.
engine = create_engine_mysql(
    user="admin",
    password="password",
    host="database-1.cluster-xxxx.us-east-1.rds.amazonaws.com",
    database="unicorn",
)


# =============================================================================
# 2. REFLECT TABLES (automap)
# =============================================================================
# automap reads the live schema and builds ORM classes for you.
# Table names become attributes on Base.classes.<table_name>.
# Requires a primary key on each table you want mapped.

Base = automap_base()
Base.prepare(autoload_with=engine)

# Grab the mapped classes you need (names = actual table names).
enterprise_table = Base.classes.enterprise

# See what got mapped if you're unsure of the table names:
#   print(list(Base.classes.keys()))


# =============================================================================
# 3. JSON SERIALIZATION OF A REFLECTED ROW
# =============================================================================
# A reflected row is an ORM object, not JSON-serializable on its own.
# Two ways: a to_dict() helper (preferred) or a json.JSONEncoder.

def row_to_dict(row):
    """Turn one reflected ORM row into a plain dict of its columns."""
    if row is None:
        return None
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


class AlchemyEncoder(json.JSONEncoder):
    """Use with json.dumps(row, cls=AlchemyEncoder) when you don't have to_dict."""

    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith("_") and x != "metadata"]:
                data = getattr(obj, field)
                try:
                    json.dumps(data)  # keep only JSON-safe values
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            return fields
        return super().default(obj)


# =============================================================================
# 4. CRUD
# =============================================================================
# session.begin() opens a transaction and auto-commits on success /
# auto-rolls-back on exception. session.flush() sends SQL now (so you can read
# an auto-generated id) without committing yet.

def crud_examples():
    with Session(engine) as session, session.begin():
        # ---- INSERT ---------------------------------------------------------
        row = enterprise_table(name="ali")
        session.add(row)
        session.flush()                     # populates row.id
        new_id = row.id
        logger.info("inserted id=%s", new_id)

        # ---- SELECT one by primary key -> object or None --------------------
        one = session.get(enterprise_table, new_id)
        logger.info("one: %s", row_to_dict(one))

        # ---- SELECT many -> list of dicts -----------------------------------
        stmt = select(enterprise_table).order_by(enterprise_table.id.desc()).limit(100)
        rows = [row_to_dict(r) for r in session.scalars(stmt).all()]
        logger.info("selected %d rows", len(rows))

        # ---- UPDATE (mutate the object, ORM emits UPDATE) -------------------
        if one is not None:
            one.name = "ali updated"
            session.flush()

        # ---- DELETE ---------------------------------------------------------
        if one is not None:
            session.delete(one)
            session.flush()

        return rows


# =============================================================================
# 5. DYNAMIC COLUMN UPDATE BY NAME
# =============================================================================
# When the column to change is decided at runtime (e.g. {"id":1,"column":"age",
# "value":30}). Use setattr; insert with **{column: value} if the row is new.

def update_column_by_name(row_id, column, value):
    with Session(engine) as session, session.begin():
        one = session.get(enterprise_table, row_id)
        if one is not None:
            setattr(one, column, value)     # dynamic field update
            session.flush()
            return {"updated": row_id}

        # not found -> insert a new row with just id + that one dynamic column
        new_row = enterprise_table(id=row_id, **{column: value})
        session.add(new_row)
        session.flush()
        return {"inserted": new_row.id}


# =============================================================================
# 6. DYNAMIC INSERT WITH **kwargs
# =============================================================================
# Build a row from an arbitrary dict of column -> value.

def insert_from_dict(values: dict):
    with Session(engine) as session, session.begin():
        row = enterprise_table(**values)
        session.add(row)
        session.flush()
        return row_to_dict(row)


# =============================================================================
# 7. FILTER BY FIELD / JOIN
# =============================================================================

def select_where(column, value):
    with Session(engine) as session:
        stmt = select(enterprise_table).where(getattr(enterprise_table, column) == value)
        return [row_to_dict(r) for r in session.scalars(stmt).all()]


def join_example():
    # Assumes two mapped tables with a foreign key between them.
    a = Base.classes.enterprise
    b = Base.classes.client                 # rename to your real table
    with Session(engine) as session:
        stmt = select(a).join(b, b.enterprise_id == a.id).where(b.id == 1)
        first = session.scalars(stmt).first()
        return row_to_dict(first)


if __name__ == "__main__":
    print(crud_examples())
