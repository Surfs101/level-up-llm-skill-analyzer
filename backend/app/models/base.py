"""The shared SQLAlchemy declarative base.

Every ORM model subclasses Base, so Base.metadata is the single registry Alembic
autogenerates migrations against. Keeping it in its own module avoids import
cycles between the models.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
