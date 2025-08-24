from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pgvector.sqlalchemy import Vector
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import numpy as np
from app.models.document import Document
from app.core.database import AsyncSessionLocal
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
    
    async def search(self, query: str, topic: str = None, limit: int = 5, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for relevant documents using vector similarity with quality threshold"""
        async with AsyncSessionLocal() as session:
            try:
                # Generate query embedding
                query_embedding = await self.embeddings.aembed_query(query)
                
                # Build query with cosine distance - get more results to filter by threshold
                stmt = select(
                    Document,
                    Document.embedding.cosine_distance(query_embedding).label('distance')
                ).order_by(
                    Document.embedding.cosine_distance(query_embedding)
                ).limit(limit * 2)  # Get extra results to filter by threshold
                
                # Execute query
                result = await session.execute(stmt)
                documents_with_distance = result.all()
                
                # Format results and filter by similarity threshold
                results = []
                for doc, distance in documents_with_distance:
                    # Convert cosine distance to similarity (cosine similarity = 1 - cosine distance)
                    similarity = 1 - distance
                    
                    # Only include results above the similarity threshold
                    if similarity >= similarity_threshold:
                        results.append({
                            "id": str(doc.id),
                            "title": doc.title,
                            "content": doc.content,
                            "metadata": doc.document_metadata,
                            "similarity": float(similarity)
                        })
                    
                    # Stop if we have enough good results
                    if len(results) >= limit:
                        break
                
                logger.info(f"RAG search found {len(results)} high-quality results (similarity >= {similarity_threshold})")
                return results
            except Exception as e:
                logger.error(f"Error searching documents: {e}")
                return []

