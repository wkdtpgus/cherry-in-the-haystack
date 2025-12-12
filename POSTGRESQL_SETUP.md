# PostgreSQL Setup Guide

Complete guide for connecting to PostgreSQL database for production deployment.

## Prerequisites

- PostgreSQL server running (local or remote)
- Database created
- User with appropriate permissions

## Step 1: Install PostgreSQL Driver

The `psycopg2-binary` driver is already included in `requirements.txt`. If not installed:

```bash
pip install psycopg2-binary
```

## Step 2: Configure Database URL

### Option A: Environment Variable (Recommended)

Create a `.env` file in the project root:

```bash
# .env
DATABASE_URL=postgresql://username:password@host:port/database_name

# Example:
# DATABASE_URL=postgresql://myuser:mypassword@localhost:5432/knowledge_graph
# DATABASE_URL=postgresql://user:pass@db.example.com:5432/production_db
```

### Option B: Inline Environment Variable

```bash
export DATABASE_URL="postgresql://username:password@host:port/database_name"
```

## Step 3: Initialize Database Schema

Run the initialization script to create all tables:

```bash
python scripts/init_db.py
```

Expected output:
```
🔧 Initializing database...
📍 Database URL: postgresql://username:***@host:5432/database_name

📦 Creating tables...
✅ Database initialized successfully!

Created tables:
  - books
  - paragraph_chunks
  - idea_groups
  - key_ideas
  - processing_progress
```

## Step 4: Verify Connection

Test the connection by checking the resume script:

```bash
python scripts/resume_processing.py
```

Expected output if database is empty:
```
No books found in database.
```

## Step 5: Process PDFs

Now you can process PDFs using the PostgreSQL database:

```bash
python scripts/process_pdfs.py --pdf "AI Engineering.pdf"
```

## Database Schema

The following tables will be created:

### `books`
```sql
CREATE TABLE books (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    source_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_pages INTEGER,
    processed_at TIMESTAMP WITH TIME ZONE
);
```

### `paragraph_chunks`
```sql
CREATE TABLE paragraph_chunks (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books(id),
    page_number INTEGER,
    paragraph_index INTEGER,
    body_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    char_count INTEGER
);
```

### `idea_groups`
```sql
CREATE TABLE idea_groups (
    id SERIAL PRIMARY KEY,
    canonical_idea_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### `key_ideas`
```sql
CREATE TABLE key_ideas (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES paragraph_chunks(id),
    book_id INTEGER REFERENCES books(id),
    core_idea_text TEXT NOT NULL,
    idea_group_id INTEGER REFERENCES idea_groups(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    concept VARCHAR(255),
    model_version VARCHAR(100)
);

CREATE INDEX ix_key_ideas_concept ON key_ideas(concept);
```

### `processing_progress`
```sql
CREATE TABLE processing_progress (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books(id),
    page_number INTEGER,
    status VARCHAR(50),
    error_message TEXT,
    attempt_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

## Troubleshooting

### Connection Error

**Error**: `psycopg2.OperationalError: could not connect to server`

**Solutions**:
1. Check if PostgreSQL server is running
2. Verify host, port, username, and password
3. Check firewall settings
4. Ensure PostgreSQL accepts TCP connections (check `pg_hba.conf`)

### Authentication Failed

**Error**: `psycopg2.OperationalError: FATAL: password authentication failed`

**Solutions**:
1. Verify username and password are correct
2. Check user permissions in PostgreSQL
3. Ensure user has CREATE TABLE permissions

### Database Does Not Exist

**Error**: `psycopg2.OperationalError: FATAL: database "..." does not exist`

**Solution**:
```sql
-- Connect to PostgreSQL as superuser
CREATE DATABASE knowledge_graph;
GRANT ALL PRIVILEGES ON DATABASE knowledge_graph TO myuser;
```

### Permission Denied

**Error**: `psycopg2.ProgrammingError: permission denied for schema public`

**Solution**:
```sql
-- Grant schema permissions
GRANT ALL ON SCHEMA public TO myuser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO myuser;
```

## Switching Between SQLite and PostgreSQL

### Use SQLite (Development)

```bash
# Remove or unset DATABASE_URL
unset DATABASE_URL

# Run commands - will use local_dev.db
python scripts/process_pdfs.py --pdf book.pdf
```

### Use PostgreSQL (Production)

```bash
# Set DATABASE_URL
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"

# Run commands - will use PostgreSQL
python scripts/process_pdfs.py --pdf book.pdf
```

## Best Practices

1. **Use Environment Variables**: Never commit credentials to version control
2. **Connection Pooling**: For production, consider using connection pooling (pgBouncer)
3. **Backups**: Regular backups of PostgreSQL database
4. **Monitoring**: Monitor database performance and query times
5. **SSL**: Use SSL/TLS for remote connections in production

## Performance Optimization

### For Large-Scale Processing

1. **Increase Connection Pool Size**:
   ```python
   # In src/db/connection.py
   engine = create_engine(url, pool_size=20, max_overflow=10)
   ```

2. **Batch Insert Optimization**:
   - Already implemented in `src/db/operations.py` using `bulk_insert_mappings`
   - 10-50x faster than individual inserts

3. **Index Optimization**:
   ```sql
   -- Add indexes for common queries
   CREATE INDEX idx_chunks_book_page ON paragraph_chunks(book_id, page_number);
   CREATE INDEX idx_ideas_book ON key_ideas(book_id);
   CREATE INDEX idx_progress_book_status ON processing_progress(book_id, status);
   ```

4. **Vacuum and Analyze**:
   ```sql
   -- Regular maintenance
   VACUUM ANALYZE;
   ```

## Migration from SQLite to PostgreSQL

If you have data in SQLite and want to migrate to PostgreSQL:

```bash
# 1. Export data from SQLite
sqlite3 local_dev.db .dump > sqlite_dump.sql

# 2. Install pgloader
# Mac: brew install pgloader
# Linux: apt-get install pgloader

# 3. Migrate data
pgloader local_dev.db postgresql://user:pass@host:5432/dbname
```

## Next Steps

After PostgreSQL setup is complete:

1. Process your PDFs: `python scripts/process_pdfs.py --pdf "book.pdf"`
2. Monitor progress: `python scripts/resume_processing.py`
3. Query the knowledge graph from your PostgreSQL database
4. Build visualization or API layer on top of the data

## Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy PostgreSQL Dialects](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)
- [psycopg2 Documentation](https://www.psycopg.org/docs/)
