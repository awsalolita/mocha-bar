import logging
from datetime import datetime

from sqlalchemy import (
    create_engine,
    ForeignKey,
    String,
    Integer,
    DateTime,
    Text,
    CHAR,
    func,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    Session,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class MyClass(Base):
    __table__ = Table('DriverProfiles', Base.metadata,
                    autoload=True, autoload_with=some_engine)


# --- Engine builder --------------------------------------------------------
def create_engine_mysql():
    try:
        engine = create_engine(
            "mysql+mysqlconnector://user:password@host:3306/database",
            pool_pre_ping=True,
            future=True,
        )
        # Open a short connection so failures surface here, like the old code.
        with engine.connect():
            logger.info("Connected to Mysql database")
        return engine
    except Exception as e:
        logger.error("Error connecting to database: %s", e)
        return None
        

def create_engine_postgres():
    try:
        engine = create_engine(
            f"postgresql://{POSTGRES_USERNAME}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DATABASE}",
            pool_pre_ping=True,
            future=True,
        )
        with engine.connect():
            logger.info("Connected to Postgres database")
        return engine
    except Exception as e:
        logger.error("Error connecting to database: %s", e)
        return None



def main(engine: Engine):
    try:
        # Make sure the users table exists before we touch it.
        create_users_table(engine)


        with Session(engine) as session, session.begin():
            ######################################## INSERT #################################################
            user = User(name="ali", email="ali@example.com")
            session.add(user)
            session.flush()
            new_id = user.id
            logger.info("inserted user id=%s", new_id)

            ########################### SELECT a single row by primary key -> one object or None #####################################
            one = session.get(User, new_id)
            logger.info("selected one: %s", one.to_dict() if one else None)

            ########################### SELECT many rows -> list of dicts ##############################################
            stmt = select(User).order_by(User.id.desc()).limit(100)
            users = session.scalars(stmt).all()
            rows = [u.to_dict() for u in users]
            logger.info("selected %d rows", len(rows))

            ########################## UPDATE a row: mutate the mapped object, ORM emits the UPDATE #################################
            if one is not None:
                one.name = "ali updated"
                session.flush()
                logger.info("updated user id=%s", new_id)

            ###############################  DELETE a row: hand the object to the session. ############################################
            if one is not None:
                session.delete(one)
                session.flush()
                logger.info("deleted user id=%s", new_id)

            ################################ Join ############################################
            stmt = (
                select(Project)
                .join(Client, Client.project_id == Project.id)
                .where(Client.id == 1)
            )
            project = session.scalars(stmt).first()
            logger.info("join result: %s", project.to_dict() if project else None)

            ####################### Select based on fields ########################
            data_file = session.scalars(
                select(Client)
                .where(Client.id == project_id)
            ).first()

        return rows

    except SQLAlchemyError as err:
        # session.begin() already rolls back on exception; log and re-raise.
        logger.error("database error: %s", err)
        raise
    finally:
        # always clean up the connection pool, even if an error was raised above
        engine.dispose()

