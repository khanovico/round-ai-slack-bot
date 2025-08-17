from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    func,
)
from app.db.database import Base


class SlackWorkspace(Base):
    __tablename__ = "slack_workspaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String(50), unique=True, nullable=False)
    channel_id = Column(String(50), nullable=False)
    team_name = Column(String(255), nullable=False)
    bot_user_id = Column(String(50), nullable=False)
    bot_token = Column(Text, nullable=False)
    installed_at = Column(DateTime, default=func.current_timestamp())
    is_active = Column(Boolean, default=True)
