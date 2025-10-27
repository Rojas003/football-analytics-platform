# Football Analytics Platform

A comprehensive analytics platform that analyzes the correlation between football players' personal life events and their on-field performance. This project challenges the traditional view that only on-field factors affect player performance by incorporating off-field personal circumstances into performance analysis.

## Project Overview

Traditional football analytics focus solely on on-field performance metrics, but this platform provides a holistic view by integrating personal life events (marriages, births, family issues, injuries) with statistical performance trends. The goal is to create more accurate performance predictions and uncover insights into how life events influence athletic performance.

## Current Status: Midterm Submission

This repository contains the completed midterm implementation featuring a single-container architecture with core functionality.

### Completed Features

- **Containerized Application**: Docker container running Ubuntu base image
- **Web Application**: Python Flask web application with responsive UI
- **Database**: SQLite database for data persistence
- **Player Statistics Dashboard**: Interface for viewing player performance trends
- **Data Entry System**: Manual entry system for personal life events
- **Correlation Analysis**: Basic statistical analysis between life events and performance metrics
- **User Authentication**: Secure user authentication and session management
- **Data Visualization**: Interactive charts and graphs for performance insights

## Technology Stack

- **Backend**: Python, Flask
- **Database**: SQLite
- **Frontend**: HTML, CSS, JavaScript
- **Containerization**: Docker
- **Data Visualization**: Chart.js / Plotly (or your specific library)

## Installation & Setup

### Prerequisites

- Docker installed on your system
- Git

### Running the Application

1. Clone the repository:
```bash
git clone https://github.com/Rojas003/football-analytics-platform.git
cd football-analytics-platform
```

2. Build and run the Docker container:
```bash
docker build -t football-analytics .
docker run -p 5000:5000 football-analytics
```

3. Access the application at `http://localhost:5000`

## Usage

1. **Create an Account**: Register for a new account through the web interface
2. **Add Players**: Input player information and statistics
3. **Record Life Events**: Document personal life events for tracked players
4. **View Analytics**: Access the dashboard to see correlation analysis and performance trends
5. **Generate Reports**: Create visual reports showing the relationship between life events and performance

## Security Features

- Secure user authentication and password hashing
- Session management
- Input validation and sanitization
- SQL injection prevention

## Future Development (Final Phase)

The final phase will implement a multi-container architecture including:

- Docker Compose orchestration
- PostgreSQL database
- Automated data collection container
- Advanced machine learning analytics engine
- Redis cache for session management
- Enhanced security features (AES-256 encryption, MFA, RBAC)
- Integration with live sports data APIs

## Project Goals

- Challenge assumptions about performance analysis in sports
- Provide data-driven insights into the "dad strength" phenomenon
- Create tools for fantasy football players, sports analysts, and researchers
- Demonstrate real-world application of containerization and security principles

## Documentation

Comprehensive documentation including system architecture, deployment guides, and user manuals will be provided in the final submission.

## Author

Sherry Rojas

## Acknowledgments

This project was developed as part of a server management and information security course, with AI assistance from Claude (Anthropic) for technical structure and formatting.

## License

This project is for educational purposes.