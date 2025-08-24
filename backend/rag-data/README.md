# RAG Data Seeding

Simple tool to seed your RAG database.

## Quick Start

```bash
cd backend/rag-data
./seed_rag.sh
```

## Options

- `./seed_rag.sh` - Exits if database has data
- `./seed_rag.sh --force` - Add alongside existing data
- `./seed_rag.sh custom.csv` - Use different CSV file

##Executing in Docker Compose
```bash
docker compose exec backend bash -c "cd /app/rag-data && ./seed_rag.sh"
```

## Requirements

- OpenAI API key in `../.env` file
- CSV file with columns: `course_name`, `chapter_name`, `chapter_url`, `content`
