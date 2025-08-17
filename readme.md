# App Analytics - Natural Language to SQL Agent

A FastAPI-based application that converts natural language questions into SQL queries and executes them against a PostgreSQL database containing app metrics data. The system features an AI-powered NL2SQL agent that understands complex analytics questions and provides intelligent responses with support for Slack bot integration and CSV exports. Built with modern Python technologies including LangChain, OpenAI GPT models, and Redis caching for optimal performance.

## Project Setup

### Prerequisites
- Python 3.11 or higher
- PostgreSQL database
- Redis server
- OpenAI API key

### Step-by-Step Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd round-app-portfolio
   ```

2. **Install Poetry** (if not already installed)
   ```bash
   # Create virtual environment
   python -m venv .venv
   
   # Activate virtual environment
   # On Windows:
   .venv\Scripts\activate
   
   # On macOS/Linux:
   source .venv/bin/activate
   
   # Install Poetry
   pip install poetry
   ```

3. **Install dependencies**
   ```bash
   poetry install
   ```


4. **Set up database**
   ```bash
   # Option 1: Using psql (recommended)
   psql -U postgres -c "CREATE DATABASE app_analytics;"
   psql -U postgres -c "CREATE USER your_db_user WITH PASSWORD 'your_db_password';"
   psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE app_analytics TO your_db_user;"
   
   # Option 2: Using pgAdmin or any PostgreSQL GUI tool
   # Create database named 'app_analytics' manually
   
   # Run migrations
   poetry run alembic upgrade head
   ```

5. **Start the application**
   ```bash
   poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

The application will be available at `http://localhost:8000`

## Environment Variables (.env)

Create a `.env` file in the root directory with the following variables:

### Database Configuration
```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=app_analytics
```
**How to get**: 
- `DB_HOST`: Your PostgreSQL server hostname (use `localhost` for local development)
- `DB_PORT`: PostgreSQL port (default is `5432`)
- `DB_USER`: Database username (create a user: `CREATE USER your_db_user WITH PASSWORD 'your_password';`)
- `DB_PASSWORD`: Database password you set for the user
- `DB_NAME`: Database name (create: `CREATE DATABASE app_analytics;`)

### OpenAI Configuration
```env
OPENAI_API_KEY=sk-your-openai-api-key
```
**How to get**: 
- Visit [OpenAI API Keys](https://platform.openai.com/api-keys)
- Create a new API key
- Copy the key starting with `sk-`

### Redis Configuration
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_DB=0
```
**How to get**:
- `REDIS_HOST`: Redis server hostname (use `localhost` for local development)
- `REDIS_PORT`: Redis port (default is `6379`)
- `REDIS_PASSWORD`: Redis password (set with: `redis-server --requirepass your_password`)
- `REDIS_DB`: Redis database number (use `0` for default)

### Slack Configuration (Optional)
```env
SLACK_CLIENT_ID=your_slack_client_id
SLACK_CLIENT_SECRET=your_slack_client_secret
SLACK_SIGNING_SECRET=your_slack_signing_secret
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_REDIRECT_URI=https://your-domain.com/slack/oauth/callback
DEFAULT_SLACK_CHANNEL=rounds_ai_analyze
```
**How to get**:

For more information, visit [AI Bot Installation Guide](https://www.notion.so/Rounds-AI-Bot-Installation-Guide-22d4a312c589809abccaf0677ca0d6da)

### LangSmith Configuration (Optional)
```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=app-analytics
```
**How to get**:
- Visit [LangSmith](https://smith.langchain.com/)
- Create an account and get your API key
- Set `LANGCHAIN_PROJECT` to your project name

### Google Drive Configuration (Optional)
```env
GOOGLE_DRIVE_CREDENTIALS_FILE=path/to/credentials.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
```
**How to get**:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable Google Drive API
3. Create service account credentials
4. Download JSON file and set path in `GOOGLE_DRIVE_CREDENTIALS_FILE`
5. `GOOGLE_DRIVE_FOLDER_ID`: ID of the folder where files will be uploaded

## Slack Bot Installation

### Prerequisites
- Slack workspace with admin permissions
- Slack app configured (see environment variables section above)

### Step-by-Step Installation

1. **Go to Installation URL**
   ```
   https://proxy-server-edry.onrender.com/slack/oauth/install
   ```

2. **Install in Workspace**
   - Navigate to the returned OAuth URL (field of "oauth_url" of returned JSON)
   - Authorize the app
   - You should see a success message

3. **Verify Channel Creation**
   - Check your Slack workspace
   - A new channel `#rounds_ai_analyze` should be created
   - The bot should send a welcome message

