# Football Analytics Platform

A comprehensive analytics platform that analyzes the correlation between football players' personal life events and their on-field performance. This project challenges the traditional view that only on-field factors affect player performance by incorporating off-field personal circumstances into performance analysis.

## Project Overview

Traditional football analytics focus solely on on-field performance metrics, but this platform provides a holistic view by integrating personal life events (marriages, births, family issues, injuries) with statistical performance trends. The goal is to create more accurate performance predictions and uncover insights into how life events influence athletic performance, including the "dad strength" phenomenon observed in professional sports.

## Architecture: Multi-Container Microservices

This application implements a **5-container microservices architecture** using Docker Compose for orchestration.

### Container Architecture

```
┌──────────────┐
│   Browser    │
└──────┬───────┘
       │
       ▼
┌─────────────────┐
│  Web Container  │◄──────────┐
│   (Flask:5001)  │           │
└────────┬────────┘           │
         │                    │
    ┌────▼────┐          ┌────▼─────┐
    │  Redis  │          │PostgreSQL│
    │  Cache  │          │ Database │
    └────┬────┘          └────┬─────┘
         │                    │
    ┌────▼────────────────────▼─────┐
    │      Data Collector           │
    │   (Background Service)        │
    └────────────┬──────────────────┘
                 │
    ┌────────────▼──────────────────┐
    │   Analytics Engine            │
    │  (ML Correlation Analysis)    │
    └───────────────────────────────┘
```

### Containers

1. **PostgreSQL Database** (`football_db`)
   - Persistent data storage
   - Player information, game statistics, life events
   - Correlation analysis results

2. **Redis Cache** (`football_redis`)
   - Session management
   - Caching layer for performance
   - Rate limiting infrastructure

3. **Flask Web Application** (`football_web`)
   - User interface and authentication
   - Player management dashboard
   - Analytics visualization
   - Role-based access control (Admin, Analyst, Viewer)

4. **Data Collector Service** (`football_collector`)
   - Automated NFL data collection every 6 hours
   - Background service for stats updates
   - Independent operation from web app

5. **Analytics Engine** (`football_analytics`)
   - ML-powered correlation analysis every 12 hours
   - Statistical significance testing (t-tests, p-values)
   - "Dad strength" effect analysis
   - Automated result storage

## Technology Stack

### Core Technologies
- **Backend**: Python 3.10, Flask 3.0
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Orchestration**: Docker Compose
- **Containerization**: Docker

### Data Analysis
- **NFL Data**: nfl-data-py 0.3.2
- **Analysis**: Pandas 2.1.4, NumPy 1.26.2
- **Statistics**: SciPy 1.11.4, Scikit-learn 1.3.2

### Security & Authentication
- **Authentication**: Flask-Login 0.6.3
- **Password Hashing**: Werkzeug 3.0.1
- **ORM**: SQLAlchemy 2.0.23

## Features

### User Interface
-  User authentication and role-based access control
-  Player management dashboard
-  Interactive analytics visualizations
-  Team defense statistics tracking
-  Audit logging system
-  NFL data import via API

### Background Services
-  Automated data collection (every 6 hours)
-  Automated correlation analysis (every 12 hours)
-  Statistical significance testing
-  Performance trend analysis

### Analytics
-  Correlation coefficient calculation
-  T-test for statistical significance
-  "Dad strength" phenomenon analysis
-  Before/after life event performance comparison

## Installation & Setup

### Prerequisites

- Docker and Docker Compose installed
- Git
- 4GB+ RAM available
- 10GB+ disk space

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/Rojas003/football-analytics-platform.git
cd football-analytics-platform
```

2. **Start all containers**
```bash
docker-compose up -d --build
```

3. **Verify all containers are running**
```bash
docker-compose ps
```

You should see 5 containers:
- `football_db` (healthy)
- `football_redis` (healthy)
- `football_web` (up)
- `football_collector` (up)
- `football_analytics` (up)

4. **Access the application**
- Open browser: `http://localhost:5001`
- Default login: `admin` / `admin123`

### Database Initialization

The database schema is automatically created on first startup. Tables include:
- `users` - User accounts and authentication
- `player` - NFL player information
- `player_stats` - Game-by-game statistics
- `life_event` - Personal life events
- `correlation_analysis` - ML analysis results
- `team_defense_stats` - Defensive statistics
- `audit_log` - System audit trail

## Usage

### Adding Players
1. Navigate to "Add Player" or "API Import"
2. Search for NFL players by name
3. Import player data and statistics

### Recording Life Events
1. Select a player
2. Add life event (birth, marriage, injury, etc.)
3. Specify event date and details

### Viewing Analytics
1. Navigate to "Analytics" dashboard
2. View correlation analysis results
3. Examine statistical significance
4. Review "dad strength" effect findings

### Background Services
- **Data Collector**: Runs every 6 hours automatically
- **Analytics Engine**: Runs every 12 hours automatically
- Manual trigger: `docker-compose restart analytics`

## Container Management

### View Logs
```bash
# All containers
docker-compose logs -f

# Specific container
docker-compose logs -f analytics
```

### Restart Services
```bash
# Restart specific service
docker-compose restart web

# Restart all
docker-compose restart
```

### Stop/Start
```bash
# Stop all
docker-compose down

# Start all
docker-compose up -d
```

### Database Access
```bash
# Connect to PostgreSQL
docker-compose exec db psql -U football_user -d football_analytics

# View tables
\dt

# Query data
SELECT * FROM correlation_analysis;

# Exit
\q
```

## Security Features

-  Password hashing (Werkzeug)
-  Role-based access control (Admin/Analyst/Viewer)
-  Audit logging for all actions
-  SQL injection prevention (SQLAlchemy ORM)
-  Network isolation (Docker bridge network)
-  Environment variable configuration

## Project Requirements Met

This project fulfills requirements for weeks 9-12 of the course:

### Weeks 9-10: Container Architecture 
- Multi-container microservices design
- Docker Compose orchestration
- 5 specialized containers
- Network isolation
- Health checks and monitoring

### Weeks 11-12: Advanced Analytics 
- Machine learning integration
- Statistical correlation analysis
- Automated background processing
- Real-time data collection

## Architecture Highlights

- **Microservices Design**: Each container has a single responsibility
- **Scalability**: Containers can be scaled independently
- **Resilience**: Auto-restart policies and health checks
- **Maintainability**: Clear separation of concerns
- **Production-Ready**: Proper orchestration and monitoring

## Development

### Environment Configuration
Copy `.env.example` to `.env` and configure:
- Database credentials
- Redis password
- API keys
- Secret keys

### Adding Features
1. Web features: Modify `app/main.py`
2. Data collection: Update `collector_service.py`
3. Analytics: Modify `analytics_service.py`

### Testing
- Manual testing via web interface
- Container health: `docker-compose ps`
- Logs: `docker-compose logs [service]`

## Future Enhancements

- Cloud deployment (AWS/Digital Ocean)
- Advanced security (MFA, SSL/TLS)
- Monitoring and alerting
- Horizontal scaling with load balancing
- Comprehensive automated testing

## Research Goals

This platform investigates:
- Correlation between personal life events and athletic performance
- "Dad strength" phenomenon in professional sports
- Impact of various life circumstances on player statistics
- Predictive modeling for fantasy football and sports betting

## Author

**Sherry Rojas**  
Master's Student in Information Security, NJIT

## Acknowledgments

- Course: IT 610/620 - Server Management and Information Security
- NFL Data: nfl-data-py open source library
- AI Assistance: Claude (Anthropic) for technical architecture and documentation
- Inspiration: Analysis of "dad strength" effect in MLB

## License

This project is for educational purposes as part of graduate coursework at NJIT.

---

## Quick Reference

### Common Commands
```bash
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# View status
docker-compose ps

# View logs
docker-compose logs -f [service]

# Rebuild after changes
docker-compose up -d --build [service]

# Access database
docker-compose exec db psql -U football_user -d football_analytics

# Trigger analytics
docker-compose restart analytics
```

### Access Points
- **Web App**: http://localhost:5001
- **Database**: localhost:5432
- **Redis**: localhost:6379

### Default Credentials
- **Username**: admin
- **Password**: admin123
- **Role**: Administrator

---

**Note**: This is a containerized microservices application. Ensure Docker and Docker Compose are properly installed before running.