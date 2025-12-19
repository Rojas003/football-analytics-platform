"""
Analytics Engine Service - Runs independently in its own container
Analyzes correlation between life events and player performance
"""
import os
import time
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from scipy import stats
from sqlalchemy import create_engine, Column, Integer, String, Date, Float, Text, DateTime, ForeignKey, Numeric, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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

# Define models
Base = declarative_base()

class Player(Base):
    __tablename__ = 'player'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    team = Column(String(100), nullable=False)
    position = Column(String(50), nullable=False)

class PlayerStats(Base):
    __tablename__ = 'player_stats'
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('player.id'), nullable=False)
    game_date = Column(Date, nullable=False)
    fantasy_points = Column(Float, default=0.0)
    passing_yards = Column(Integer, default=0)
    rushing_yards = Column(Integer, default=0)
    receiving_yards = Column(Integer, default=0)

class LifeEvent(Base):
    __tablename__ = 'life_event'
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('player.id'), nullable=False)
    event_type = Column(String(50), nullable=False)
    event_date = Column(Date, nullable=False)
    event_description = Column(Text)

# Create correlation analysis table if it doesn't exist
class CorrelationAnalysis(Base):
    __tablename__ = 'correlation_analysis'
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('player.id'), nullable=False)
    event_type = Column(String(50))
    correlation_coefficient = Column(Numeric(5, 4))
    sample_size = Column(Integer)
    p_value = Column(Numeric(10, 8))
    mean_before = Column(Float)
    mean_after = Column(Float)
    is_significant = Column(Integer)  # 0 or 1 (boolean)
    analysis_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)

def test_database_connection():
    """Test database connection"""
    try:
        session = Session()
        result = session.execute(text("SELECT 1")).fetchone()
        session.close()
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def create_analysis_table():
    """Create correlation_analysis table if it doesn't exist"""
    try:
        Base.metadata.create_all(engine, tables=[CorrelationAnalysis.__table__])
        logger.info("✅ Correlation analysis table ready")
    except Exception as e:
        logger.error(f"❌ Error creating table: {e}")

def calculate_correlation(player_id, event_type, days_before=30, days_after=30):
    """
    Calculate correlation between a life event and player performance
    
    Args:
        player_id: Player to analyze
        event_type: Type of life event (e.g., 'birth', 'marriage', 'injury')
        days_before: Days to analyze before event
        days_after: Days to analyze after event
    
    Returns:
        dict with correlation results or None
    """
    session = Session()
    try:
        # Get life events for this player and event type
        events = session.query(LifeEvent).filter_by(
            player_id=player_id,
            event_type=event_type
        ).all()
        
        if not events:
            return None
        
        logger.info(f"📊 Analyzing {len(events)} {event_type} events for player {player_id}")
        
        before_scores = []
        after_scores = []
        
        for event in events:
            # Get stats before event
            before_start = event.event_date - timedelta(days=days_before)
            before_stats = session.query(PlayerStats).filter(
                PlayerStats.player_id == player_id,
                PlayerStats.game_date >= before_start,
                PlayerStats.game_date < event.event_date
            ).all()
            
            # Get stats after event
            after_end = event.event_date + timedelta(days=days_after)
            after_stats = session.query(PlayerStats).filter(
                PlayerStats.player_id == player_id,
                PlayerStats.game_date > event.event_date,
                PlayerStats.game_date <= after_end
            ).all()
            
            # Calculate average fantasy points
            if before_stats:
                avg_before = sum(s.fantasy_points for s in before_stats) / len(before_stats)
                before_scores.append(avg_before)
            
            if after_stats:
                avg_after = sum(s.fantasy_points for s in after_stats) / len(after_stats)
                after_scores.append(avg_after)
        
        # Need at least 3 data points for meaningful analysis
        if len(before_scores) < 3 or len(after_scores) < 3:
            logger.info(f"⚠️ Insufficient data: {len(before_scores)} before, {len(after_scores)} after")
            return None
        
        # Perform t-test
        t_stat, p_value = stats.ttest_ind(before_scores, after_scores)
        
        # Calculate correlation
        correlation = np.corrcoef(before_scores, after_scores)[0, 1] if len(before_scores) == len(after_scores) else 0
        
        # Determine if significant (p < 0.05)
        is_significant = 1 if p_value < 0.05 else 0
        
        result = {
            'player_id': player_id,
            'event_type': event_type,
            'correlation_coefficient': float(correlation),
            'sample_size': len(before_scores) + len(after_scores),
            'p_value': float(p_value),
            'mean_before': float(np.mean(before_scores)),
            'mean_after': float(np.mean(after_scores)),
            'is_significant': is_significant
        }
        
        logger.info(f"✅ Analysis complete: r={correlation:.3f}, p={p_value:.4f}, significant={bool(is_significant)}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error calculating correlation: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        session.close()

def run_analysis_cycle():
    """
    Run a full analysis cycle on all players with life events
    """
    logger.info("🔄 Starting analysis cycle...")
    
    session = Session()
    try:
        # Get all players with life events
        players_with_events = session.query(Player.id).join(LifeEvent).distinct().all()
        
        if not players_with_events:
            logger.info("📭 No players with life events to analyze")
            return
        
        logger.info(f"📊 Analyzing {len(players_with_events)} players with life events")
        
        event_types = ['birth', 'marriage', 'injury', 'family_issue', 'contract']
        analyses_run = 0
        
        for player_tuple in players_with_events:
            player_id = player_tuple[0]
            
            for event_type in event_types:
                result = calculate_correlation(player_id, event_type)
                
                if result:
                    # Save to database
                    analysis = CorrelationAnalysis(**result)
                    session.add(analysis)
                    analyses_run += 1
        
        session.commit()
        logger.info(f"✅ Analysis cycle complete: {analyses_run} correlations calculated")
        
    except Exception as e:
        logger.error(f"❌ Error during analysis cycle: {e}")
        session.rollback()
    finally:
        session.close()

def run_service():
    """
    Main service loop
    """
    logger.info("🚀 Analytics Engine Service Starting...")
    logger.info(f"📍 Database URL: {DATABASE_URL}")
    
    # Test database connection
    if not test_database_connection():
        logger.error("Cannot connect to database. Retrying in 10 seconds...")
        time.sleep(10)
        return run_service()
    
    # Create analysis table
    create_analysis_table()
    
    logger.info("⏰ Service will run analysis every 12 hours")
    logger.info("💡 Press Ctrl+C to stop")
    
    # Run initial analysis
    run_analysis_cycle()
    
    # Main loop - analyze every 12 hours
    ANALYSIS_INTERVAL = 12 * 60 * 60  # 12 hours in seconds
    
    try:
        while True:
            logger.info(f"😴 Sleeping for {ANALYSIS_INTERVAL/3600} hours...")
            time.sleep(ANALYSIS_INTERVAL)
            run_analysis_cycle()
    
    except KeyboardInterrupt:
        logger.info("🛑 Service stopped by user")
    except Exception as e:
        logger.error(f"❌ Service crashed: {e}")
        raise

if __name__ == "__main__":
    run_service()