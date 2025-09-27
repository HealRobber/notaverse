from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Text, DateTime, func
from datetime import datetime
from db import Base

class Parameter(Base):
    __tablename__ = "parameters"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parameter: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())