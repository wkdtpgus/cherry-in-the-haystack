# CLI Usage Guide

## Quick Start

### 1. Initialize Database

```bash
python scripts/init_db.py
```

### 2. Process a PDF

```bash
# Process new PDF
python scripts/process_pdfs.py --pdf "path/to/AI Engineering.pdf"

# Process with custom model
python scripts/process_pdfs.py --pdf book.pdf --model gemini-2.0-pro

# Enable debug logging
python scripts/process_pdfs.py --pdf book.pdf --log-level DEBUG

# JSON logging for production
python scripts/process_pdfs.py --pdf book.pdf --json-logs
```

### 3. Check Processing Status

```bash
# List all books and their processing status
python scripts/resume_processing.py

# Show details for specific book
python scripts/resume_processing.py --book-id 5
```

### 4. Resume Interrupted Processing

```bash
# Resume processing for book ID 5
python scripts/process_pdfs.py --resume --book-id 5
```

## CLI Commands Reference

### `process_pdfs.py` - Main Processing Script

**Arguments**:

- `--pdf PATH`: Path to PDF file to process (required for new processing)
- `--resume`: Resume processing from last checkpoint
- `--book-id ID`: Book ID for resume mode (required with --resume)
- `--model VERSION`: LLM model version (default: gemini-2.5-flash)
- `--log-level LEVEL`: Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
- `--json-logs`: Output logs in JSON format for production

**Examples**:

```bash
# Process new PDF
python scripts/process_pdfs.py --pdf "AI Engineering.pdf"

# Resume book ID 3
python scripts/process_pdfs.py --resume --book-id 3

# Process with debug logging
python scripts/process_pdfs.py --pdf book.pdf --log-level DEBUG
```

### `resume_processing.py` - Status and Resume Helper

**Arguments**:

- `--book-id ID`: Show detailed status for specific book (optional)

**Examples**:

```bash
# List all books and their status
python scripts/resume_processing.py

# Show details for book ID 5
python scripts/resume_processing.py --book-id 5
```

## Workflow Examples

### Process Multiple PDFs

```bash
# Process first book
python scripts/process_pdfs.py --pdf "AI Engineering.pdf"

# Process second book
python scripts/process_pdfs.py --pdf "LLM Engineers Handbook.pdf"
```

### Handle Interruptions

```bash
# Start processing
python scripts/process_pdfs.py --pdf book.pdf

# If interrupted (Ctrl+C), check status
python scripts/resume_processing.py

# Resume from checkpoint
python scripts/process_pdfs.py --resume --book-id 1
```

### Debug Failed Pages

```bash
# Check detailed status
python scripts/resume_processing.py --book-id 5

# Resume with debug logging
python scripts/process_pdfs.py --resume --book-id 5 --log-level DEBUG
```

## Environment Configuration

### SQLite (Development)

Default behavior - uses `local_dev.db` in current directory.

```bash
# No configuration needed
python scripts/process_pdfs.py --pdf book.pdf
```

### PostgreSQL (Production)

Set `DATABASE_URL` environment variable:

```bash
# Linux/Mac
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
python scripts/process_pdfs.py --pdf book.pdf

# Or inline
DATABASE_URL="postgresql://..." python scripts/process_pdfs.py --pdf book.pdf
```

## Exit Codes

- `0`: Success
- `1`: Error (file not found, processing failed, etc.)
- `130`: Interrupted by user (Ctrl+C)

## Progress Tracking

The system automatically tracks progress at the page level:

- **pending**: Page waiting to be processed
- **processing**: Page currently being processed
- **completed**: Page successfully processed
- **failed**: Page processing failed (with error message)

You can resume at any time using the `--resume` flag.

## Logging

### Development (Human-Readable)

```bash
python scripts/process_pdfs.py --pdf book.pdf --log-level DEBUG
```

Output:
```
2025-11-30 10:30:45 [INFO] pdf_processor:main:45 - PDF Processing Started
2025-11-30 10:30:46 [INFO] pdf_processor:main:52 - Processing PDF: /path/to/book.pdf
```

### Production (JSON Format)

```bash
python scripts/process_pdfs.py --pdf book.pdf --json-logs
```

Output:
```json
{"timestamp": "2025-11-30T10:30:45Z", "level": "INFO", "logger": "pdf_processor", "message": "PDF Processing Started", "module": "process_pdfs", "function": "main", "line": 45}
```

## Tips

1. **Always check status before resuming**:
   ```bash
   python scripts/resume_processing.py
   ```

2. **Use debug logging for troubleshooting**:
   ```bash
   python scripts/process_pdfs.py --resume --book-id 5 --log-level DEBUG
   ```

3. **Monitor progress with tqdm progress bars** - they show real-time progress during processing

4. **Resume is automatic** - the system tracks progress and handles stuck pages

5. **Use JSON logs for production** - easier to parse and analyze with log aggregation tools
