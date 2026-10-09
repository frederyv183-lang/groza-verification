"""
Работа с БД (SQLAlchemy).
"""
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Float, Boolean,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

Base = declarative_base()


class Fact(Base):
    """Фактические грозы (из METAR)."""
    __tablename__ = "facts"
    id = Column(Integer, primary_key=True)
    station = Column(String(4), index=True)
    datetime = Column(DateTime, index=True)
    has_groz = Column(Boolean, default=False)
    raw_metar = Column(String)


class Forecast(Base):
    """Прогнозы моделей."""
    __tablename__ = "forecasts"
    id = Column(Integer, primary_key=True)
    station = Column(String(4), index=True)
    datetime = Column(DateTime, index=True)
    model_name = Column(String(50), index=True)
    lead_time_hours = Column(Integer)
    predicts_groz = Column(Boolean, default=False)
    value = Column(Float, nullable=True)


class Sounding(Base):
    """Радиозондирование ERA5 + индексы неустойчивости."""
    __tablename__ = "soundings"

    id = Column(Integer, primary_key=True)
    station = Column(String(4), index=True)
    datetime = Column(DateTime, index=True)
    source = Column(String(20), default="ERA5")

    # Температура и точка росы на уровнях
    T_850 = Column(Float); T_700 = Column(Float); T_500 = Column(Float)
    Td_850 = Column(Float); Td_700 = Column(Float); Td_500 = Column(Float)
    Z_850 = Column(Float); Z_700 = Column(Float); Z_500 = Column(Float)

    # Старые индексы
    K_index = Column(Float)
    LI = Column(Float)

    # === НОВЫЕ ИНДЕКСЫ ===
    Ki = Column(Float)           # современный Вайтинг
    VT = Column(Float)           # Vertical Totals
    CT = Column(Float)           # Cross Totals
    TT = Column(Float)           # Total Totals
    Fateev_A = Column(Float)     # Фатеев (без 600 гПа, упрощённый)
    Lebedeva_SD = Column(Float)  # ΣD Лебедевой
    Bailey_no_groz = Column(Boolean)  # True = Бейли говорит "нет гроз"


engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
