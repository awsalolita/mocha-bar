import json
import logging

from sqlalchemy import create_engine, select
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)



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


Base = automap_base()
Base.prepare(autoload_with=engine)

enterprise_table = Base.classes.enterprise


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
