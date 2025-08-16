from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    Integer,
    Numeric,
    String,
    Index,
)
from app.db.database import Base


class AppMetrics(Base):
    __tablename__ = "app_metrics"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    app_name = Column(String, nullable=False)
    platform = Column(
        String,
        nullable=False,
        doc="Platform must be 'iOS' or 'Android'"
    )
    date = Column(Date, nullable=False)
    country = Column(String, nullable=False)
    installs = Column(Integer, nullable=False)
    in_app_revenue = Column(Numeric(12, 2), nullable=False, default=0)
    ads_revenue = Column(Numeric(12, 2), nullable=False, default=0)
    ua_cost = Column(Numeric(12, 2), nullable=False, default=0)

    __table_args__ = (
        CheckConstraint("platform IN ('iOS', 'Android')", name="check_platform"),
        CheckConstraint("installs >= 0", name="check_installs_positive"),
        Index("idx_metrics_date", "date"),
        Index("idx_metrics_app_date", "app_name", "date"),
        Index("idx_metrics_country_date", "country", "date"),
        Index("idx_metrics_platform_date", "platform", "date"),
    )