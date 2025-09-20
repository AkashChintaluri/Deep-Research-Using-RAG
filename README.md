# Codemate - ArXiv Data Processing Platform

A comprehensive platform for processing, analyzing, and visualizing ArXiv research papers data. Built with Python backend and React frontend.

## 🚀 Features

- **Data Ingestion**: Process large ArXiv datasets (2.8M+ papers) with streaming
- **PostgreSQL Integration**: Robust database storage with full-text search
- **Text Normalization**: Clean and normalize LaTeX-heavy academic text
- **Web Interface**: Modern React-based dashboard for data exploration
- **Analytics**: Interactive visualizations and insights
- **Search**: Full-text search across papers, titles, and abstracts
- **Real-time Processing**: Live progress tracking and logging

## 📁 Project Structure

```
Codemate/
├── backend/                    # Python backend
│   ├── api/                   # API endpoints and queries
│   ├── data_processing/       # Data ingestion pipeline
│   ├── models/               # Data models
│   ├── utils/                # Utility functions
│   ├── config.py             # Configuration settings
│   └── app.py                # Main backend application
├── frontend/                  # React frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── App.jsx           # Main app component
│   │   └── main.jsx          # Entry point
│   ├── public/               # Static assets
│   └── package.json          # Frontend dependencies
├── scripts/                  # Utility scripts
├── docs/                     # Documentation
├── Raw Data/                 # Input data directory
└── processed_data/           # Output data directory
```

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL 12+
- Git

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Codemate
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup PostgreSQL database**
   ```bash
   python scripts/setup_postgres.py --host localhost --port 5432 --user postgres --password akash --database Codemate
   ```

4. **Test database connection**
   ```bash
   python scripts/test_connection.py
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

## 🚀 Usage

### Data Processing

Process the full ArXiv dataset:

```bash
# Using the main backend app
python backend/app.py --mode ingest --input "Raw Data/arxiv-metadata-oai-snapshot.json" --output processed_data

# Or using the direct script
python backend/data_processing/data_ingestion_postgres.py --input "Raw Data/arxiv-metadata-oai-snapshot.json" --output processed_data --db-name Codemate --db-user postgres --db-password akash
```

### Querying Data

Run analytics and queries:

```bash
# Query interface
python backend/app.py --mode query

# Or direct query script
python backend/api/query_postgres.py
```

### Web Interface

1. **Start the backend** (if not already running)
   ```bash
   python backend/app.py --mode ingest
   ```

2. **Start the frontend**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Open your browser**
   Navigate to `http://localhost:3000`

## 📊 Features Overview

### Dashboard
- Real-time statistics and metrics
- Recent papers overview
- Quick action buttons
- System status monitoring

### Search
- Full-text search across papers
- Advanced filtering by category, year, author
- Relevance-based ranking
- Real-time search results

### Analytics
- Interactive data visualizations
- Category distribution analysis
- Author productivity metrics
- Publication timeline trends
- Version analysis

### Data Processing
- Live progress tracking
- Configurable processing parameters
- Real-time logging
- Error handling and recovery

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=Codemate
DB_USER=postgres
DB_PASSWORD=akash

# Processing Configuration
BATCH_SIZE=1000
MAX_WORKERS=4
LOG_LEVEL=INFO

# File Paths
RAW_DATA_DIR=Raw Data
PROCESSED_DATA_DIR=processed_data
```

### Database Schema

The system creates the following PostgreSQL tables:

- `papers`: Main papers table with full-text search indexes
- Indexes on categories, dates, versions, and search vectors
- JSONB support for structured data

## 📈 Performance

- **Processing Speed**: ~900+ papers/second
- **Memory Usage**: Streaming processing for large files
- **Database**: Optimized with proper indexing
- **Search**: Full-text search with PostgreSQL

## 🧪 Testing

Run the test suite:

```bash
# Backend tests
python scripts/test_postgres_ingestion.py

# Connection test
python scripts/test_connection.py
```

## 📝 API Documentation

### Backend API Endpoints

- `GET /api/papers` - List papers with pagination
- `GET /api/papers/search` - Search papers
- `GET /api/analytics/categories` - Category statistics
- `GET /api/analytics/authors` - Author statistics
- `POST /api/processing/start` - Start data processing

### Database Queries

Example queries for data analysis:

```sql
-- Top categories
SELECT categories, COUNT(*) as count 
FROM papers 
GROUP BY categories 
ORDER BY count DESC 
LIMIT 10;

-- Full-text search
SELECT id, title, authors, abstract
FROM papers 
WHERE to_tsvector('english', title || ' ' || abstract) 
@@ plainto_tsquery('english', 'machine learning');
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

- Create an issue in the repository
- Check the documentation in the `docs/` directory
- Review the test files for usage examples

## 🔮 Roadmap

- [ ] Real-time data streaming
- [ ] Machine learning integration
- [ ] Advanced analytics dashboard
- [ ] API rate limiting
- [ ] Docker containerization
- [ ] Cloud deployment guides
- [ ] Data export features
- [ ] Collaborative filtering
- [ ] Citation analysis
- [ ] Research trend prediction

---

**Codemate** - Empowering research through data processing and analysis.