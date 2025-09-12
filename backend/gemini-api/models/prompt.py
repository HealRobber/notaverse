from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Text, DateTime, func
from datetime import datetime
from db import Base

# class Prompt(Base):
#     __tablename__ = 'prompts'
#
#     id = Column(Integer, primary_key=True, index=True)
#     prompt = Column(Text, nullable=False)
#     created_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")


class Prompt(Base):
    __tablename__ = "prompts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())