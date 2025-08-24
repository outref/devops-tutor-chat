from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.sql import func
import uuid
from app.services.database import Base

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    content = Column(String, nullable=False)
    embedding = Column(Vector(1536))  # OpenAI embeddings dimension
    document_metadata = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
