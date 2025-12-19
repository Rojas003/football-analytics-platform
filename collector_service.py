"""
Data Collection Service - Runs independently in its own container
Periodically collects NFL player stats and updates the database
"""
import os
import time
import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Date, Float, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://football_user:football_pass@db:5432/football_analytics')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Define models (simplified versions for the collector)
Base = declarative_base()

class Player(Base):
    __tablename__ = 'player'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    team = Column(String(100), nullable=False)
    position = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class PlayerStats(Base):
    __tablename__ = 'player_stats'
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('player.id'), nullable=False)
    game_date = Column(Date, nullable=False)
    passing_yards = Column(Integer, default=0)
    passing_tds = Column(Integer, default=0)
    interceptions = Column(Integer, default=0)
    completions = Column(Integer, default=0)
    pass_attempts = Column(Integer, default=0)
    rushing_yards = Column(Integer, default=0)
    rushing_tds = Column(Integer, default=0)
    carries = Column(Integer, default=0)
    receptions = Column(Integer, default=0)
    receiving_yards = Column(Integer, default=0)
    receiving_tds = Column(Integer, default=0)
    targets = Column(Integer, default=0)
    fumbles = Column(Integer, default=0)
    fantasy_points = Column(Float, default=0.0)

def test_database_connection():
    """Test database connection"""
    try:
        session = Session()
        result = session.execute("SELECT 1").fetchone()
        session.close()
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def collect_data():
    """
    Main data collection function
    This is a placeholder - you can expand this to actually collect data
    """
    logger.info("🔄 Starting data collection cycle...")
    
    session = Session()
    try:
        # Example: Count players in database
        player_count = session.query(Player).count()
        logger.info(f"📊 Current players in database: {player_count}")
        
        # Here you would add actual data collection logic:
        # - Import from NFL API
        # - Update player stats
        # - Collect life events
        # etc.
        
        logger.info("✅ Data collection cycle complete")
        
    except Exception as e:
        logger.error(f"❌ Error during data collection: {e}")
        session.rollback()
    finally:
        session.close()

def run_service():
    """
    Main service loop
    """
    logger.info("🚀 Data Collection Service Starting...")
    logger.info(f"📍 Database URL: {DATABASE_URL}")
    
    # Test database connection
    if not test_database_connection():
        logger.error("Cannot connect to database. Retrying in 10 seconds...")
        time.sleep(10)
        return run_service()
    
    logger.info("⏰ Service will collect data every 6 hours")
    logger.info("💡 Press Ctrl+C to stop")
    
    # Run initial collection
    collect_data()
    
    # Main loop - collect every 6 hours
    COLLECTION_INTERVAL = 6 * 60 * 60  # 6 hours in seconds
    
    try:
        while True:
            logger.info(f"😴 Sleeping for {COLLECTION_INTERVAL/3600} hours...")
            time.sleep(COLLECTION_INTERVAL)
            collect_data()
    
    except KeyboardInterrupt:
        logger.info("🛑 Service stopped by user")
    except Exception as e:
        logger.error(f"❌ Service crashed: {e}")
        raise

if __name__ == "__main__":
    run_service()