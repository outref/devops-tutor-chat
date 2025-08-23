from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pgvector.sqlalchemy import Vector
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import numpy as np
from app.models.document import Document
from app.services.database import AsyncSessionLocal
import logging

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self, embeddings: OpenAIEmbeddings):
        self.embeddings = embeddings
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    async def add_document(self, title: str, content: str, topic: str, metadata: Dict[str, Any] = None) -> str:
        """Add a document to the RAG system"""
        async with AsyncSessionLocal() as session:
            try:
                # Generate embedding
                embedding = await self.embeddings.aembed_query(content)
                
                # Create document
                document = Document(
                    title=title,
                    content=content,
                    topic=topic,
                    embedding=embedding,
                    document_metadata=metadata or {}
                )
                
                session.add(document)
                await session.commit()
                
                return str(document.id)
            except Exception as e:
                logger.error(f"Error adding document: {e}")
                await session.rollback()
                raise
    
    async def add_documents_batch(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Add multiple documents to the RAG system"""
        async with AsyncSessionLocal() as session:
            try:
                ids = []
                for doc_data in documents:
                    # Split content into chunks if it's too long
                    chunks = self.text_splitter.split_text(doc_data["content"])
                    
                    for i, chunk in enumerate(chunks):
                        # Generate embedding
                        embedding = await self.embeddings.aembed_query(chunk)
                        
                        # Create document
                        document = Document(
                            title=f"{doc_data['title']} - Part {i+1}" if len(chunks) > 1 else doc_data['title'],
                            content=chunk,
                            topic=doc_data['topic'],
                            embedding=embedding,
                            document_metadata=doc_data.get('metadata', {})
                        )
                        
                        session.add(document)
                        ids.append(str(document.id))
                
                await session.commit()
                return ids
            except Exception as e:
                logger.error(f"Error adding documents batch: {e}")
                await session.rollback()
                raise
    
    async def search(self, query: str, topic: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents using vector similarity"""
        async with AsyncSessionLocal() as session:
            try:
                # Generate query embedding
                query_embedding = await self.embeddings.aembed_query(query)
                
                # Build query
                stmt = select(Document)
                
                # Filter by topic if provided
                if topic:
                    stmt = stmt.where(Document.topic == topic)
                
                # Order by similarity
                stmt = stmt.order_by(
                    Document.embedding.cosine_distance(query_embedding)
                ).limit(limit)
                
                # Execute query
                result = await session.execute(stmt)
                documents = result.scalars().all()
                
                # Format results
                results = []
                for doc in documents:
                    results.append({
                        "id": str(doc.id),
                        "title": doc.title,
                        "content": doc.content,
                        "topic": doc.topic,
                        "metadata": doc.document_metadata
                    })
                
                return results
            except Exception as e:
                logger.error(f"Error searching documents: {e}")
                return []
    
    async def delete_by_topic(self, topic: str) -> int:
        """Delete all documents for a specific topic"""
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(Document).where(Document.topic == topic)
                result = await session.execute(stmt)
                documents = result.scalars().all()
                
                count = len(documents)
                for doc in documents:
                    await session.delete(doc)
                
                await session.commit()
                return count
            except Exception as e:
                logger.error(f"Error deleting documents: {e}")
                await session.rollback()
                raise
