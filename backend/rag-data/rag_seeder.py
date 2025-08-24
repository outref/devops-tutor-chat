import asyncio
import os
import sys
import argparse
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import select, func
from langchain_openai import OpenAIEmbeddings
import sys
sys.path.append('..')

from app.services.rag_service import RAGService
from app.services.database import engine, Base, AsyncSessionLocal
from app.models.document import Document
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv('../.env')

class RAGSeeder:
    def __init__(self, csv_file_path: str):
        self.csv_file_path = csv_file_path
        self.embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
        self.rag_service = RAGService(self.embeddings)
    
    async def get_document_count(self) -> int:
        """Get total number of documents in the database"""
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(func.count(Document.id))
                result = await session.execute(stmt)
                return result.scalar() or 0
            except Exception:
                return 0
    
    def read_csv(self) -> pd.DataFrame:
        """Read and validate the CSV file"""
        if not os.path.exists(self.csv_file_path):
            raise FileNotFoundError(f"CSV file not found: {self.csv_file_path}")
            
        df = pd.read_csv(self.csv_file_path)
        
        # Validate required columns
        required_columns = ['course_name', 'chapter_name', 'chapter_url', 'content']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Remove rows with empty content
        df = df.dropna(subset=['content'])
        df = df[df['content'].str.strip() != '']
        
        logger.info(f"Loaded {len(df)} rows from CSV")
        return df
    
    def prepare_documents(self, df: pd.DataFrame) -> list:
        """Convert CSV rows to document format"""
        documents = []
        
        for index, row in df.iterrows():
            document = {
                "title": f"{row['course_name']} - {row['chapter_name']}",
                "content": str(row['content']).strip(),
                "metadata": {
                    "course_name": str(row['course_name']),
                    "chapter_name": str(row['chapter_name']),
                    "chapter_url": str(row['chapter_url']),
                    "source": "rag-data",
                    "row_index": index
                }
            }
            documents.append(document)
        
        return documents
    
    async def seed_database(self, force: bool = False):
        """Seed the database with RAG content"""
        try:
            # Create tables
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            # Check for existing data
            existing_docs = await self.get_document_count()
            if existing_docs > 0 and not force:
                logger.error(f"Database contains {existing_docs} documents. Use --force to add alongside existing data.")
                sys.exit(1)
            
            # Read CSV
            df = self.read_csv()
            if len(df) == 0:
                logger.error("No valid data found in CSV file")
                sys.exit(1)
            
            # Prepare and add documents
            documents = self.prepare_documents(df)
            logger.info(f"Processing {len(documents)} documents...")
            
            batch_size = 50
            total_added = 0
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                ids = await self.rag_service.add_documents_batch(batch)
                total_added += len(ids)
                logger.info(f"Batch {i//batch_size + 1}: Added {len(ids)} documents")
            
            logger.info(f"Successfully added {total_added} documents")
                
        except Exception as e:
            logger.error(f"Seeding failed: {e}")
            raise
        finally:
            await engine.dispose()

async def main():
    parser = argparse.ArgumentParser(description='Seed RAG database')
    parser.add_argument(
        '--csv-file', 
        type=str, 
        default='rag-data.csv',
        help='Path to the CSV file'
    )
    parser.add_argument(
        '--force', 
        action='store_true',
        help='Add alongside existing data'
    )
    
    args = parser.parse_args()
    
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable is required")
        sys.exit(1)
    
    try:
        seeder = RAGSeeder(args.csv_file)
        await seeder.seed_database(force=args.force)
        
    except KeyboardInterrupt:
        logger.info("Interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
