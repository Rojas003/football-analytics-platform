from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import os
from app.data_collector import NFLDataCollector, test_nfl_data_connection
from dotenv import load_dotenv
# import redis
# from flask_session import Session
load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')

# Database configuration - supports both SQLite (dev) and PostgreSQL (production)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:////app/data/football_analytics.db')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# # Redis session configuration
# app.config['SESSION_TYPE'] = 'redis'
# REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
# app.config['SESSION_REDIS'] = redis.from_url(REDIS_URL, decode_responses=True)
# app.config['SESSION_PERMANENT'] = False
# app.config['SESSION_USE_SIGNER'] = True
# Session(app)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# ==================== DATABASE MODELS ====================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='viewer')  # admin, analyst, viewer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_analyst(self):
        return self.role in ['admin', 'analyst']
    
    def is_viewer(self):
        return self.role in ['admin', 'analyst', 'viewer']

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    team = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    stats = db.relationship('PlayerStats', backref='player', lazy=True, cascade='all, delete-orphan')
    life_events = db.relationship('LifeEvent', backref='player', lazy=True, cascade='all, delete-orphan')

class PlayerStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    game_date = db.Column(db.Date, nullable=False)
    
    passing_yards = db.Column(db.Integer, default=0)
    passing_tds = db.Column(db.Integer, default=0)
    interceptions = db.Column(db.Integer, default=0)
    completions = db.Column(db.Integer, default=0)
    pass_attempts = db.Column(db.Integer, default=0)
    
    rushing_yards = db.Column(db.Integer, default=0)
    rushing_tds = db.Column(db.Integer, default=0)
    carries = db.Column(db.Integer, default=0)
    
    receptions = db.Column(db.Integer, default=0)
    receiving_yards = db.Column(db.Integer, default=0)
    receiving_tds = db.Column(db.Integer, default=0)
    targets = db.Column(db.Integer, default=0)
    
    fumbles = db.Column(db.Integer, default=0)
    fantasy_points = db.Column(db.Float, default=0.0)
    
class LifeEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    event_category = db.Column(db.String(100), nullable=False)
    event_description = db.Column(db.Text, nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TeamDefenseStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_abbr = db.Column(db.String(10), nullable=False)  # e.g., "KC", "BUF"
    season = db.Column(db.Integer, nullable=False)
    week = db.Column(db.Integer, nullable=False)
    
    # Defensive stats against positions
    pass_yards_allowed_per_game = db.Column(db.Float, default=0.0)
    rush_yards_allowed_per_game = db.Column(db.Float, default=0.0)
    passing_tds_allowed = db.Column(db.Integer, default=0)
    rushing_tds_allowed = db.Column(db.Integer, default=0)
    sacks = db.Column(db.Integer, default=0)
    
    # Position-specific (vs RBs, WRs, TEs)
    rec_yards_allowed_to_rbs = db.Column(db.Float, default=0.0)
    rec_yards_allowed_to_wrs = db.Column(db.Float, default=0.0)
    rec_yards_allowed_to_tes = db.Column(db.Float, default=0.0)
    
    # Rankings
    pass_defense_rank = db.Column(db.Integer, default=0)  # 1-32
    rush_defense_rank = db.Column(db.Integer, default=0)  # 1-32
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('team_abbr', 'season', 'week'),)

class UpcomingGame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    game_date = db.Column(db.Date, nullable=False)
    opponent = db.Column(db.String(10), nullable=False)  # Team abbreviation
    home_away = db.Column(db.String(10), nullable=False)  # 'HOME' or 'AWAY'
    week = db.Column(db.Integer, nullable=False)
    season = db.Column(db.Integer, nullable=False)
    
    # Betting lines (optional - you can add manually)
    prop_receiving_yards = db.Column(db.Float, nullable=True)
    prop_receptions = db.Column(db.Float, nullable=True)
    prop_rush_yards = db.Column(db.Float, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PlayerVsTeamHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    opponent_team = db.Column(db.String(10), nullable=False)
    game_date = db.Column(db.Date, nullable=False)
    
    # Performance against this team
    receiving_yards = db.Column(db.Integer, default=0)
    receptions = db.Column(db.Integer, default=0)
    receiving_tds = db.Column(db.Integer, default=0)
    rushing_yards = db.Column(db.Integer, default=0)
    rushing_tds = db.Column(db.Integer, default=0)
    fantasy_points = db.Column(db.Float, default=0.0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
# ==================== FLASK-LOGIN SETUP ====================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==================== ROLE-BASED DECORATORS ====================

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('You need administrator privileges to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def analyst_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_analyst():
            flash('You need analyst privileges to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== AUDIT LOGGING ====================

def log_action(action, details=None):
    try:
        log_entry = AuditLog(
            user_id=current_user.id if current_user.is_authenticated else None,
            action=action,
            details=details,
            ip_address=request.remote_addr
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")

# ==================== CREATE TABLES & DEFAULT ADMIN ====================

with app.app_context():
    db.create_all()
    
    # Create default admin user if no users exist
    if User.query.count() == 0:
        admin = User(
            username='admin',
            email='admin@football-analytics.com',
            role='admin'
        )
        admin.set_password('admin123')  # Change this in production!
        db.session.add(admin)
        db.session.commit()
        print("Default admin user created: username='admin', password='admin123'")

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            log_action('login', f'User {username} logged in')
            flash(f'Welcome back, {user.username}!', 'success')
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            log_action('failed_login', f'Failed login attempt for username: {username}')
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log_action('logout', f'User {current_user.username} logged out')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html')
        
        # Create new user (default role: viewer)
        new_user = User(
            username=username,
            email=email,
            role='viewer'
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        log_action('user_registered', f'New user registered: {username}')
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# ==================== MAIN ROUTES ====================

@app.route('/')
@login_required
def index():
    players = Player.query.all()
    return render_template('index.html', players=players)

@app.route('/player/<int:player_id>')
@login_required
def player_detail(player_id):
    player = Player.query.get_or_404(player_id)
    stats = PlayerStats.query.filter_by(player_id=player_id).order_by(PlayerStats.game_date.desc()).all()
    life_events = LifeEvent.query.filter_by(player_id=player_id).order_by(LifeEvent.event_date.desc()).all()
    return render_template('player_detail.html', player=player, stats=stats, life_events=life_events)

@app.route('/add_player', methods=['GET', 'POST'])
@login_required
@analyst_required
def add_player():
    if request.method == 'POST':
        name = request.form['name']
        team = request.form['team']
        position = request.form['position']
        
        new_player = Player(name=name, team=team, position=position)
        db.session.add(new_player)
        db.session.commit()
        
        log_action('player_added', f'Added player: {name}')
        flash(f'Player {name} added successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('add_player.html')

@app.route('/add_stats/<int:player_id>', methods=['GET', 'POST'])
@login_required
@analyst_required
def add_stats(player_id):
    player = Player.query.get_or_404(player_id)
    
    if request.method == 'POST':
        game_date = datetime.strptime(request.form['game_date'], '%Y-%m-%d').date()
        
        new_stats = PlayerStats(
            player_id=player_id,
            game_date=game_date,
            passing_yards=int(request.form.get('passing_yards', 0)),
            passing_tds=int(request.form.get('passing_tds', 0)),
            interceptions=int(request.form.get('interceptions', 0)),
            completions=int(request.form.get('completions', 0)),
            pass_attempts=int(request.form.get('pass_attempts', 0)),
            rushing_yards=int(request.form.get('rushing_yards', 0)),
            rushing_tds=int(request.form.get('rushing_tds', 0)),
            carries=int(request.form.get('carries', 0)),
            receptions=int(request.form.get('receptions', 0)),
            receiving_yards=int(request.form.get('receiving_yards', 0)),
            receiving_tds=int(request.form.get('receiving_tds', 0)),
            targets=int(request.form.get('targets', 0)),
            fumbles=int(request.form.get('fumbles', 0)),
            fantasy_points=float(request.form.get('fantasy_points', 0))
        )
        db.session.add(new_stats)
        db.session.commit()
        
        log_action('stats_added', f'Added stats for {player.name} on {game_date}')
        flash('Stats added successfully!', 'success')
        return redirect(url_for('player_detail', player_id=player_id))
    
    return render_template('add_stats.html', player=player)

@app.route('/add_life_event/<int:player_id>', methods=['GET', 'POST'])
@login_required
@analyst_required
def add_life_event(player_id):
    player = Player.query.get_or_404(player_id)
    
    if request.method == 'POST':
        event_type = request.form['event_type']
        event_category = request.form['event_category']
        event_description = request.form['event_description']
        event_date = datetime.strptime(request.form['event_date'], '%Y-%m-%d').date()
        
        new_event = LifeEvent(
            player_id=player_id,
            event_type=event_type,
            event_category=event_category,
            event_description=event_description,
            event_date=event_date
        )
        db.session.add(new_event)
        db.session.commit()
        
        log_action('life_event_added', f'Added life event for {player.name}: {event_category}')
        flash('Life event added successfully!', 'success')
        return redirect(url_for('player_detail', player_id=player_id))
    
    return render_template('add_life_event.html', player=player)

@app.route('/analytics')
@login_required
def analytics():
    total_players = Player.query.count()
    total_stats = PlayerStats.query.count()
    total_events = LifeEvent.query.count()
    
    players_with_data = []
    for player in Player.query.all():
        stats_count = PlayerStats.query.filter_by(player_id=player.id).count()
        events_count = LifeEvent.query.filter_by(player_id=player.id).count()
        
        if stats_count > 0 and events_count > 0:
            players_with_data.append({
                'id': player.id,
                'name': player.name,
                'team': player.team,
                'position': player.position,
                'stats_count': stats_count,
                'events_count': events_count
            })
    
    return render_template('analytics.html', 
                         total_players=total_players,
                         total_stats=total_stats,
                         total_events=total_events,
                         players_with_data=players_with_data)

@app.route('/player_analytics/<int:player_id>')
@login_required
def player_analytics(player_id):
    """Detailed analytics for a specific player showing life event correlations."""
    player = Player.query.get_or_404(player_id)
    
    # Get all stats ordered by date
    stats = PlayerStats.query.filter_by(player_id=player_id).order_by(PlayerStats.game_date).all()
    
    # Get all life events ordered by date
    life_events = LifeEvent.query.filter_by(player_id=player_id).order_by(LifeEvent.event_date).all()
    
    # Initialize analytics data
    event_analysis = []
    betting_insights = {}
    recent_form = []
    season_comparison = {}
    proximity_analysis = {}
    
    if stats:
        # Calculate season averages
        total_games = len(stats)
        season_avg = {
            'fantasy_points': sum(s.fantasy_points for s in stats) / total_games,
            'receiving_yards': sum(s.receiving_yards for s in stats) / total_games,
            'receptions': sum(s.receptions for s in stats) / total_games,
            'receiving_tds': sum(s.receiving_tds for s in stats) / total_games,
            'targets': sum(s.targets for s in stats) / total_games,
            'rushing_yards': sum(s.rushing_yards for s in stats) / total_games,
            'rushing_tds': sum(s.rushing_tds for s in stats) / total_games,
        }
        
        # Recent form (last 5 games)
        recent_stats = stats[-5:] if len(stats) >= 5 else stats
        for stat in recent_stats:
            # Check if near any life event
            near_event = None
            for event in life_events:
                days_diff = abs((stat.game_date - event.event_date).days)
                if days_diff <= 7:
                    near_event = {
                        'type': event.event_type,
                        'category': event.event_category,
                        'days_away': days_diff
                    }
                    break
            
            recent_form.append({
                'date': stat.game_date.strftime('%Y-%m-%d'),
                'fantasy_points': float(stat.fantasy_points),
                'receiving_yards': stat.receiving_yards,
                'receptions': stat.receptions,
                'tds': stat.receiving_tds + stat.rushing_tds,
                'near_event': near_event,
                'above_avg': stat.fantasy_points > season_avg['fantasy_points']
            })
        
        # Event proximity analysis (7, 14, 30 day windows)
        for window in [7, 14, 30]:
            games_near_events = []
            for stat in stats:
                for event in life_events:
                    days_diff = abs((stat.game_date - event.event_date).days)
                    if days_diff <= window:
                        games_near_events.append(stat)
                        break
            
            if games_near_events:
                proximity_analysis[f'{window}_day'] = {
                    'count': len(games_near_events),
                    'avg_fantasy': sum(s.fantasy_points for s in games_near_events) / len(games_near_events),
                    'avg_rec_yards': sum(s.receiving_yards for s in games_near_events) / len(games_near_events),
                    'avg_receptions': sum(s.receptions for s in games_near_events) / len(games_near_events),
                    'avg_tds': sum(s.receiving_tds + s.rushing_tds for s in games_near_events) / len(games_near_events),
                }
        
        # Analyze performance around each life event
        for event in life_events:
            before_stats = [s for s in stats if s.game_date < event.event_date]
            after_stats = [s for s in stats if s.game_date > event.event_date]
            
            before_avg = {}
            after_avg = {}
            
            if len(before_stats) >= 3:
                recent_before = before_stats[-3:]
                before_avg = {
                    'fantasy_points': sum(s.fantasy_points for s in recent_before) / len(recent_before),
                    'receiving_yards': sum(s.receiving_yards for s in recent_before) / len(recent_before),
                    'receptions': sum(s.receptions for s in recent_before) / len(recent_before),
                    'receiving_tds': sum(s.receiving_tds for s in recent_before) / len(recent_before),
                }
            
            if len(after_stats) >= 3:
                recent_after = after_stats[:3]
                after_avg = {
                    'fantasy_points': sum(s.fantasy_points for s in recent_after) / len(recent_after),
                    'receiving_yards': sum(s.receiving_yards for s in recent_after) / len(recent_after),
                    'receptions': sum(s.receptions for s in recent_after) / len(recent_after),
                    'receiving_tds': sum(s.receiving_tds for s in recent_after) / len(recent_after),
                }
            
            if before_avg and after_avg:
                changes = {}
                for key in before_avg.keys():
                    if before_avg[key] > 0:
                        change_pct = ((after_avg[key] - before_avg[key]) / before_avg[key]) * 100
                        changes[key] = {
                            'before': round(before_avg[key], 1),
                            'after': round(after_avg[key], 1),
                            'change': round(after_avg[key] - before_avg[key], 1),
                            'change_pct': round(change_pct, 1)
                        }
                
                event_analysis.append({
                    'event': event,
                    'changes': changes,
                    'improved': after_avg['fantasy_points'] > before_avg['fantasy_points'],
                    'sample_size': f"{len(recent_before)}-{len(recent_after)}"
                })
        
        # Calculate betting insights
        if event_analysis:
            # Average performance change after ALL events
            total_fp_change = sum(e['changes']['fantasy_points']['change'] for e in event_analysis if 'fantasy_points' in e['changes'])
            total_yd_change = sum(e['changes']['receiving_yards']['change'] for e in event_analysis if 'receiving_yards' in e['changes'])
            
            # Positive vs negative events
            positive_events = [e for e in event_analysis if e['event'].event_type == 'positive']
            negative_events = [e for e in event_analysis if e['event'].event_type == 'negative']
            
            betting_insights = {
                'total_events': len(event_analysis),
                'avg_fp_change': round(total_fp_change / len(event_analysis), 1) if event_analysis else 0,
                'avg_yd_change': round(total_yd_change / len(event_analysis), 1) if event_analysis else 0,
                'improved_pct': round((sum(1 for e in event_analysis if e['improved']) / len(event_analysis)) * 100, 0) if event_analysis else 0,
                'positive_events_count': len(positive_events),
                'negative_events_count': len(negative_events),
                'positive_avg_change': round(sum(e['changes']['fantasy_points']['change'] for e in positive_events) / len(positive_events), 1) if positive_events else 0,
                'negative_avg_change': round(sum(e['changes']['fantasy_points']['change'] for e in negative_events) / len(negative_events), 1) if negative_events else 0,
            }
        
        # Season vs Event comparison
        if proximity_analysis.get('7_day'):
            prox = proximity_analysis['7_day']
            season_comparison = {
                'fantasy_points': {
                    'season': round(season_avg['fantasy_points'], 1),
                    'near_events': round(prox['avg_fantasy'], 1),
                    'diff': round(prox['avg_fantasy'] - season_avg['fantasy_points'], 1),
                    'diff_pct': round(((prox['avg_fantasy'] - season_avg['fantasy_points']) / season_avg['fantasy_points']) * 100, 1) if season_avg['fantasy_points'] > 0 else 0
                },
                'receiving_yards': {
                    'season': round(season_avg['receiving_yards'], 1),
                    'near_events': round(prox['avg_rec_yards'], 1),
                    'diff': round(prox['avg_rec_yards'] - season_avg['receiving_yards'], 1),
                    'diff_pct': round(((prox['avg_rec_yards'] - season_avg['receiving_yards']) / season_avg['receiving_yards']) * 100, 1) if season_avg['receiving_yards'] > 0 else 0
                },
                'receptions': {
                    'season': round(season_avg['receptions'], 1),
                    'near_events': round(prox['avg_receptions'], 1),
                    'diff': round(prox['avg_receptions'] - season_avg['receptions'], 1),
                    'diff_pct': round(((prox['avg_receptions'] - season_avg['receptions']) / season_avg['receptions']) * 100, 1) if season_avg['receptions'] > 0 else 0
                },
            }
    
    # Prepare data for charts
    chart_data = {
        'dates': [s.game_date.strftime('%Y-%m-%d') for s in stats],
        'fantasy_points': [float(s.fantasy_points) for s in stats],
        'receiving_yards': [s.receiving_yards for s in stats],
        'receptions': [s.receptions for s in stats],
        'touchdowns': [s.receiving_tds + s.rushing_tds + s.passing_tds for s in stats],
        'targets': [s.targets for s in stats],
        'event_dates': [e.event_date.strftime('%Y-%m-%d') for e in life_events],
        'event_types': [e.event_type for e in life_events],
        'event_descriptions': [e.event_description[:50] + '...' if len(e.event_description) > 50 else e.event_description for e in life_events]
    }
    
    return render_template('player_analytics.html',
                         player=player,
                         stats=stats,
                         life_events=life_events,
                         season_avg=season_avg if stats else {},
                         event_analysis=event_analysis,
                         betting_insights=betting_insights,
                         recent_form=recent_form,
                         season_comparison=season_comparison,
                         proximity_analysis=proximity_analysis,
                         chart_data=chart_data)
@app.route('/delete_stats/<int:stats_id>', methods=['POST'])
@login_required
@admin_required
def delete_stats(stats_id):
    stats = PlayerStats.query.get_or_404(stats_id)
    player_id = stats.player_id
    db.session.delete(stats)
    db.session.commit()
    
    log_action('stats_deleted', f'Deleted stats ID: {stats_id}')
    flash('Stats deleted successfully!', 'success')
    return redirect(url_for('player_detail', player_id=player_id))

@app.route('/delete_life_event/<int:event_id>', methods=['POST'])
@login_required
@admin_required
def delete_life_event(event_id):
    event = LifeEvent.query.get_or_404(event_id)
    player_id = event.player_id
    db.session.delete(event)
    db.session.commit()
    
    log_action('life_event_deleted', f'Deleted life event ID: {event_id}')
    flash('Life event deleted successfully!', 'success')
    return redirect(url_for('player_detail', player_id=player_id))

@app.route('/edit_stats/<int:stats_id>', methods=['GET', 'POST'])
@login_required
@analyst_required
def edit_stats(stats_id):
    stats = PlayerStats.query.get_or_404(stats_id)
    player = Player.query.get_or_404(stats.player_id)
    
    if request.method == 'POST':
        stats.game_date = datetime.strptime(request.form['game_date'], '%Y-%m-%d').date()
        stats.passing_yards = int(request.form.get('passing_yards', 0))
        stats.passing_tds = int(request.form.get('passing_tds', 0))
        stats.interceptions = int(request.form.get('interceptions', 0))
        stats.completions = int(request.form.get('completions', 0))
        stats.pass_attempts = int(request.form.get('pass_attempts', 0))
        stats.rushing_yards = int(request.form.get('rushing_yards', 0))
        stats.rushing_tds = int(request.form.get('rushing_tds', 0))
        stats.carries = int(request.form.get('carries', 0))
        stats.receptions = int(request.form.get('receptions', 0))
        stats.receiving_yards = int(request.form.get('receiving_yards', 0))
        stats.receiving_tds = int(request.form.get('receiving_tds', 0))
        stats.targets = int(request.form.get('targets', 0))
        stats.fumbles = int(request.form.get('fumbles', 0))
        stats.fantasy_points = float(request.form.get('fantasy_points', 0))
        
        db.session.commit()
        log_action('stats_edited', f'Edited stats ID: {stats_id}')
        flash('Stats updated successfully!', 'success')
        return redirect(url_for('player_detail', player_id=player.id))
    
    return render_template('edit_stats.html', player=player, stats=stats)

@app.route('/edit_life_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
@analyst_required
def edit_life_event(event_id):
    event = LifeEvent.query.get_or_404(event_id)
    player = Player.query.get_or_404(event.player_id)
    
    if request.method == 'POST':
        event.event_type = request.form['event_type']
        event.event_category = request.form['event_category']
        event.event_description = request.form['event_description']
        event.event_date = datetime.strptime(request.form['event_date'], '%Y-%m-%d').date()
        
        db.session.commit()
        log_action('life_event_edited', f'Edited life event ID: {event_id}')
        flash('Life event updated successfully!', 'success')
        return redirect(url_for('player_detail', player_id=player.id))
    
    return render_template('edit_life_event.html', player=player, event=event)

@app.route('/api_test')
@login_required
def api_test():
    return render_template('api_test.html')

@app.route('/api_search_player', methods=['POST'])
@login_required
def api_search_player():
    player_name = request.form.get('player_name')
    if not player_name:
        return {'error': 'Player name required'}, 400
    
    try:
        collector = NFLDataCollector()
        results = collector.search_player(player_name)
        return {'players': results}
    except Exception as e:
        print(f"Error in api_search_player: {e}")
        return {'error': str(e)}, 500

@app.route('/api_fetch_stats/<int:player_id>', methods=['POST'])
@login_required
@analyst_required
def api_fetch_stats(player_id):
    player = Player.query.get_or_404(player_id)
    nfl_player_id = request.form.get('nfl_player_id')
    season = request.form.get('season', 2025)
    
    if not nfl_player_id:
        flash('NFL player ID required.', 'danger')
        return redirect(url_for('player_detail', player_id=player_id))
    
    try:
        collector = NFLDataCollector()
        print(f"DEBUG: Attempting to fetch stats for player_id={nfl_player_id}, season={season}")
        game_logs = collector.get_player_game_log(nfl_player_id, int(season))
        
        print(f"DEBUG: Received {len(game_logs)} games from API")
        
        if len(game_logs) == 0:
            flash(f'No game data found for season {season}. The API may not have current season data yet, or the player ID might be incorrect.', 'warning')
            return redirect(url_for('player_detail', player_id=player_id))
        
        imported_count = 0
        for game in game_logs:
            existing = PlayerStats.query.filter_by(
                player_id=player_id,
                game_date=game['game_date']
            ).first()
            
            if not existing:
                new_stats = PlayerStats(
                    player_id=player_id,
                    game_date=game['game_date'],
                    targets=game['targets'],
                    receptions=game['receptions'],
                    receiving_yards=game['receiving_yards'],
                    receiving_tds=game['receiving_tds'],
                    carries=game['carries'],
                    rushing_yards=game['rushing_yards'],
                    rushing_tds=game['rushing_tds'],
                    completions=game['completions'],
                    pass_attempts=game['pass_attempts'],
                    passing_yards=game['passing_yards'],
                    passing_tds=game['passing_tds'],
                    interceptions=game['interceptions'],
                    fumbles=game['fumbles'],
                    fantasy_points=game['fantasy_points']
                )
                db.session.add(new_stats)
                imported_count += 1
        
        db.session.commit()
        
        if imported_count > 0:
            log_action('stats_imported', f'Imported {imported_count} games for {player.name}')
            flash(f'Successfully imported {imported_count} games from NFL Data API!', 'success')
        else:
            flash('All games from this season were already imported.', 'info')
    
    except Exception as e:
        print(f"ERROR in api_fetch_stats: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error fetching stats: {str(e)}', 'danger')
    
    return redirect(url_for('player_detail', player_id=player_id))
# ==================== ADMIN ROUTES ====================

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/change_role/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def change_user_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    
    if new_role not in ['admin', 'analyst', 'viewer']:
        flash('Invalid role.', 'danger')
        return redirect(url_for('admin_users'))
    
    user.role = new_role
    db.session.commit()
    
    log_action('role_changed', f'Changed {user.username} role to {new_role}')
    flash(f'User {user.username} role changed to {new_role}.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/audit_logs')
@login_required
@admin_required
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('audit_logs.html', logs=logs)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
@app.route('/edit_player/<int:player_id>', methods=['GET', 'POST'])
@login_required
@analyst_required
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    
    if request.method == 'POST':
        player.name = request.form['name']
        player.team = request.form['team']
        player.position = request.form['position']
        
        db.session.commit()
        log_action('player_edited', f'Edited player: {player.name}')
        flash(f'Player {player.name} updated successfully!', 'success')
        return redirect(url_for('player_detail', player_id=player_id))
    
    return render_template('edit_player.html', player=player)

@app.route('/delete_player/<int:player_id>', methods=['POST'])
@login_required
@admin_required
def delete_player(player_id):
    player = Player.query.get_or_404(player_id)
    player_name = player.name
    
    db.session.delete(player)
    db.session.commit()
    
    log_action('player_deleted', f'Deleted player: {player_name}')
    flash(f'Player {player_name} deleted successfully!', 'success')
    return redirect(url_for('index'))
# ==================== MATCHUP PREDICTION ROUTES ====================

@app.route('/add_upcoming_game/<int:player_id>', methods=['GET', 'POST'])
@login_required
@analyst_required
def add_upcoming_game(player_id):
    player = Player.query.get_or_404(player_id)
    
    if request.method == 'POST':
        game_date = datetime.strptime(request.form['game_date'], '%Y-%m-%d').date()
        opponent = request.form['opponent']
        home_away = request.form['home_away']
        week = int(request.form['week'])
        season = int(request.form['season'])
        
        # Optional prop lines
        prop_rec_yards = request.form.get('prop_receiving_yards')
        prop_recs = request.form.get('prop_receptions')
        prop_rush_yards = request.form.get('prop_rush_yards')
        
        new_game = UpcomingGame(
            player_id=player_id,
            game_date=game_date,
            opponent=opponent,
            home_away=home_away,
            week=week,
            season=season,
            prop_receiving_yards=float(prop_rec_yards) if prop_rec_yards else None,
            prop_receptions=float(prop_recs) if prop_recs else None,
            prop_rush_yards=float(prop_rush_yards) if prop_rush_yards else None
        )
        
        db.session.add(new_game)
        db.session.commit()
        
        log_action('upcoming_game_added', f'Added upcoming game for {player.name} vs {opponent}')
        flash('Upcoming game added successfully!', 'success')
        return redirect(url_for('player_detail', player_id=player_id))
    
    return render_template('add_upcoming_game.html', player=player)

@app.route('/add_team_defense', methods=['GET', 'POST'])
@login_required
@analyst_required
def add_team_defense():
    if request.method == 'POST':
        team_abbr = request.form['team_abbr']
        season = int(request.form['season'])
        week = int(request.form['week'])
        
        defense = TeamDefenseStats(
            team_abbr=team_abbr,
            season=season,
            week=week,
            pass_yards_allowed_per_game=float(request.form.get('pass_yards_allowed', 0)),
            rush_yards_allowed_per_game=float(request.form.get('rush_yards_allowed', 0)),
            passing_tds_allowed=int(request.form.get('passing_tds_allowed', 0)),
            rushing_tds_allowed=int(request.form.get('rushing_tds_allowed', 0)),
            sacks=int(request.form.get('sacks', 0)),
            rec_yards_allowed_to_rbs=float(request.form.get('rec_yards_to_rbs', 0)),
            rec_yards_allowed_to_wrs=float(request.form.get('rec_yards_to_wrs', 0)),
            rec_yards_allowed_to_tes=float(request.form.get('rec_yards_to_tes', 0)),
            pass_defense_rank=int(request.form.get('pass_defense_rank', 16)),
            rush_defense_rank=int(request.form.get('rush_defense_rank', 16))
        )
        
        db.session.add(defense)
        db.session.commit()
        
        log_action('defense_stats_added', f'Added defense stats for {team_abbr}')
        flash(f'Defense stats added for {team_abbr}!', 'success')
        return redirect(url_for('add_team_defense'))
    
    return render_template('add_team_defense.html')

def calculate_matchup_prediction(player, upcoming_game, life_events, stats):
    """
    Calculate prediction for upcoming game based on:
    1. Life event impact
    2. Opponent defensive strength
    3. Historical performance vs opponent
    4. Recent form
    """
    prediction = {
        'base_projection': 0,
        'event_adjustment': 0,
        'opponent_adjustment': 0,
        'final_projection': 0,
        'confidence': 0,
        'recommendation': 'HOLD',
        'factors': []
    }
    
    if not stats:
        return prediction
    
    # 1. Calculate base projection (season average)
    season_avg_rec_yards = sum(s.receiving_yards for s in stats) / len(stats)
    season_avg_rush_yards = sum(s.rushing_yards for s in stats) / len(stats)
    
    prediction['base_projection'] = season_avg_rec_yards if player.position in ['WR', 'TE'] else season_avg_rush_yards
    
    # 2. Check for recent life events (within 7 days)
    event_impact = 0
    recent_events = []
    for event in life_events:
        days_until_game = (upcoming_game.game_date - event.event_date).days
        if 0 <= days_until_game <= 7:
            recent_events.append(event)
            # Positive events boost, negative events hurt
            if event.event_type == 'positive':
                event_impact += 0.12  # +12%
            else:
                event_impact -= 0.08  # -8%
    
    if recent_events:
        prediction['event_adjustment'] = prediction['base_projection'] * event_impact
        for event in recent_events:
            prediction['factors'].append(f"{'✅' if event.event_type == 'positive' else '❌'} {event.event_category} ({(upcoming_game.game_date - event.event_date).days}d ago)")
    
    # 3. Opponent defensive adjustment
    defense = TeamDefenseStats.query.filter_by(
        team_abbr=upcoming_game.opponent,
        season=upcoming_game.season,
        week=upcoming_game.week
    ).first()
    
    if defense:
        # Adjust based on defensive ranking (1=best, 32=worst)
        if player.position in ['WR', 'TE']:
            rank = defense.pass_defense_rank
            rank_multiplier = 1 + ((rank - 16) * 0.02)  # Each rank = 2%
            prediction['opponent_adjustment'] = prediction['base_projection'] * (rank_multiplier - 1)
            
            if rank <= 10:
                prediction['factors'].append(f"🛡️ Tough matchup (#{rank} pass defense)")
            elif rank >= 23:
                prediction['factors'].append(f"🎯 Favorable matchup (#{rank} pass defense)")
        else:  # RB
            rank = defense.rush_defense_rank
            rank_multiplier = 1 + ((rank - 16) * 0.02)
            prediction['opponent_adjustment'] = prediction['base_projection'] * (rank_multiplier - 1)
            
            if rank <= 10:
                prediction['factors'].append(f"🛡️ Tough matchup (#{rank} run defense)")
            elif rank >= 23:
                prediction['factors'].append(f"🎯 Favorable matchup (#{rank} run defense)")
    
    # 4. Historical performance vs this opponent
    vs_team_history = PlayerVsTeamHistory.query.filter_by(
        player_id=player.id,
        opponent_team=upcoming_game.opponent
    ).all()
    
    if vs_team_history:
        if player.position in ['WR', 'TE']:
            avg_vs_team = sum(h.receiving_yards for h in vs_team_history) / len(vs_team_history)
        else:
            avg_vs_team = sum(h.rushing_yards for h in vs_team_history) / len(vs_team_history)
        
        if avg_vs_team > prediction['base_projection'] * 1.15:
            prediction['factors'].append(f"📈 Strong history vs {upcoming_game.opponent} ({len(vs_team_history)} games)")
        elif avg_vs_team < prediction['base_projection'] * 0.85:
            prediction['factors'].append(f"📉 Struggles vs {upcoming_game.opponent} ({len(vs_team_history)} games)")
    
    # 5. Calculate final projection
    prediction['final_projection'] = round(
        prediction['base_projection'] + 
        prediction['event_adjustment'] + 
        prediction['opponent_adjustment'],
        1
    )
    
    # 6. Determine confidence (based on data availability)
    confidence_factors = 0
    if recent_events:
        confidence_factors += 25
    if defense:
        confidence_factors += 35
    if vs_team_history:
        confidence_factors += 20
    if len(stats) >= 5:
        confidence_factors += 20
    
    prediction['confidence'] = confidence_factors
    
    # 7. Generate recommendation
    if upcoming_game.prop_receiving_yards or upcoming_game.prop_rush_yards:
        prop_line = upcoming_game.prop_receiving_yards if player.position in ['WR', 'TE'] else upcoming_game.prop_rush_yards
        if prop_line:
            diff = prediction['final_projection'] - prop_line
            if diff >= 8 and prediction['confidence'] >= 60:
                prediction['recommendation'] = 'STRONG OVER'
            elif diff >= 4:
                prediction['recommendation'] = 'LEAN OVER'
            elif diff <= -8 and prediction['confidence'] >= 60:
                prediction['recommendation'] = 'STRONG UNDER'
            elif diff <= -4:
                prediction['recommendation'] = 'LEAN UNDER'
            else:
                prediction['recommendation'] = 'HOLD'
                
    stats = PlayerStats.query.filter_by(player_id=player.id).all()
    if stats and len(stats) > 0:
        stats_year = stats[0].game_date.year if hasattr(stats[0].game_date, 'year') else 2024
        if upcoming_game.season != stats_year:
            prediction['confidence'] = int(prediction['confidence'] * 0.85)
            prediction['factors'].append('⚠️ Cross-season baseline (2024→2025)')
    
    return prediction
@app.route('/import_team_defense', methods=['GET', 'POST'])
@login_required
@analyst_required
def import_team_defense():
    if request.method == 'POST':
        season = int(request.form.get('season', 2024))
        week = int(request.form.get('week', 1))
        
        try:
            collector = NFLDataCollector()
            defense_stats = collector.get_team_defense_stats(season)
            
            if not defense_stats:
                flash('No defense stats found for this season. Try a different season.', 'warning')
                return redirect(url_for('import_team_defense'))
            
            imported_count = 0
            updated_count = 0
            
            for team_abbr, stats in defense_stats.items():
                # Check if stats already exist for this team/season/week
                existing = TeamDefenseStats.query.filter_by(
                    team_abbr=team_abbr,
                    season=season,
                    week=week
                ).first()
                
                if existing:
                    # Update existing
                    existing.pass_yards_allowed_per_game = stats['pass_yards_allowed_per_game']
                    existing.rush_yards_allowed_per_game = stats['rush_yards_allowed_per_game']
                    existing.passing_tds_allowed = stats['passing_tds_allowed']
                    existing.rushing_tds_allowed = stats['rushing_tds_allowed']
                    existing.sacks = stats['sacks']
                    existing.pass_defense_rank = stats['pass_defense_rank']
                    existing.rush_defense_rank = stats['rush_defense_rank']
                    updated_count += 1
                else:
                    # Create new
                    new_defense = TeamDefenseStats(
                        team_abbr=team_abbr,
                        season=season,
                        week=week,
                        pass_yards_allowed_per_game=stats['pass_yards_allowed_per_game'],
                        rush_yards_allowed_per_game=stats['rush_yards_allowed_per_game'],
                        passing_tds_allowed=stats['passing_tds_allowed'],
                        rushing_tds_allowed=stats['rushing_tds_allowed'],
                        sacks=stats['sacks'],
                        pass_defense_rank=stats['pass_defense_rank'],
                        rush_defense_rank=stats['rush_defense_rank']
                    )
                    db.session.add(new_defense)
                    imported_count += 1
            
            db.session.commit()
            log_action('defense_stats_imported', f'Imported/updated defense stats for {imported_count + updated_count} teams')
            flash(f'Successfully imported {imported_count} new and updated {updated_count} existing team defense stats!', 'success')
            
        except Exception as e:
            flash(f'Error importing defense stats: {str(e)}', 'danger')
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        
        return redirect(url_for('import_team_defense'))
    
    return render_template('import_team_defense.html')
@app.route('/view_team_defense')
@login_required
def view_team_defense():
    """View team defense stats - showing cumulative season averages"""
    from sqlalchemy import func
    
    # Get all defense stats
    all_stats = TeamDefenseStats.query.all()
    
    if not all_stats:
        return render_template('view_team_defense.html', grouped_stats={})
    
    # Calculate cumulative averages for each team per season
    from collections import defaultdict
    team_season_stats = defaultdict(lambda: {
        'games': 0,
        'total_pass_yards': 0,
        'total_rush_yards': 0,
        'total_sacks': 0,
        'total_pass_tds': 0,
        'total_rush_tds': 0,
        'latest_week': 0
    })
    
    # Aggregate stats across all weeks
    for stat in all_stats:
        key = (stat.team_abbr, stat.season)
        team_season_stats[key]['games'] += 1
        team_season_stats[key]['total_pass_yards'] += stat.pass_yards_allowed_per_game
        team_season_stats[key]['total_rush_yards'] += stat.rush_yards_allowed_per_game
        team_season_stats[key]['total_sacks'] += stat.sacks
        team_season_stats[key]['total_pass_tds'] += stat.passing_tds_allowed
        team_season_stats[key]['total_rush_tds'] += stat.rushing_tds_allowed
        team_season_stats[key]['latest_week'] = max(team_season_stats[key]['latest_week'], stat.week)
    
    # Calculate averages and create stat objects
    cumulative_stats = []
    for (team_abbr, season), data in team_season_stats.items():
        games = data['games']
        cumulative_stats.append({
            'team_abbr': team_abbr,
            'season': season,
            'games_played': games,
            'pass_yards_allowed_per_game': round(data['total_pass_yards'] / games, 1),
            'rush_yards_allowed_per_game': round(data['total_rush_yards'] / games, 1),
            'sacks': data['total_sacks'],
            'passing_tds_allowed': data['total_pass_tds'],
            'rushing_tds_allowed': data['total_rush_tds'],
            'latest_week': data['latest_week']
        })
    
    # Sort by season
    cumulative_stats.sort(key=lambda x: x['season'], reverse=True)
    
    # Calculate rankings within each season
    from collections import defaultdict
    grouped_stats = defaultdict(list)
    
    for season in set(stat['season'] for stat in cumulative_stats):
        season_stats = [s for s in cumulative_stats if s['season'] == season]
        
        # Calculate pass defense rankings
        season_stats_sorted = sorted(season_stats, key=lambda x: x['pass_yards_allowed_per_game'])
        for rank, stat in enumerate(season_stats_sorted, 1):
            stat['pass_defense_rank'] = rank
        
        # Calculate rush defense rankings
        season_stats_sorted = sorted(season_stats, key=lambda x: x['rush_yards_allowed_per_game'])
        for rank, stat in enumerate(season_stats_sorted, 1):
            stat['rush_defense_rank'] = rank
        
        # Get the latest week for this season
        latest_week = max(s['latest_week'] for s in season_stats)
        
        # Convert to objects that the template can use
        class StatObject:
            def __init__(self, data):
                self.team_abbr = data['team_abbr']
                self.season = data['season']
                self.games_played = data['games_played']
                self.pass_yards_allowed_per_game = data['pass_yards_allowed_per_game']
                self.rush_yards_allowed_per_game = data['rush_yards_allowed_per_game']
                self.sacks = data['sacks']
                self.passing_tds_allowed = data['passing_tds_allowed']
                self.rushing_tds_allowed = data['rushing_tds_allowed']
                self.pass_defense_rank = data['pass_defense_rank']
                self.rush_defense_rank = data['rush_defense_rank']
        
        stat_objects = [StatObject(s) for s in season_stats]
        key = f"{season} Season - Average through Week {latest_week}"
        grouped_stats[key] = stat_objects
    
    log_action('view_team_defense', f'Viewed team defense stats')
    return render_template('view_team_defense.html', grouped_stats=grouped_stats)