from sqlalchemy import text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from src.stats.schemas import PlayerStatRow, ClubStatRow, SeasonOverview

EXCLUDED_EVENTS = (
    'rugby_union_coach_points_1', 
    'rugby_union_coach_points_2', 
    'rugby_union_coach_points_3', 
    'start', 
    'stop', 
    'rugby_union_uncontested_scrum', 
    'rugby_union_blue_card'
)

async def get_player_stats(db: AsyncSession, competition_id: Optional[int] = None) -> List[PlayerStatRow]:
    query = """
        SELECT 
            p.id as player_id, 
            p.name as player_name, 
            c.name as club_name, 
            c.id as club_id,
            COUNT(CASE WHEN ge.event_type = 'try' OR ge.event_type = 'rugby_union_penalty_try' THEN 1 END) as tries,
            COUNT(CASE WHEN ge.event_type = 'conversion' THEN 1 END) as conversions,
            COUNT(CASE WHEN ge.event_type = 'penalty_goal' THEN 1 END) as penalties,
            COUNT(CASE WHEN ge.event_type = 'drop_goal' THEN 1 END) as drop_goals,
            SUM(ge.points) as total_points,
            COUNT(CASE WHEN ge.event_type = 'yellow_card' THEN 1 END) as yellow_cards,
            COUNT(CASE WHEN ge.event_type = 'red_card' THEN 1 END) as red_cards,
            p.thumbnail_url as image_url
        FROM game_events ge 
        JOIN players p ON ge.player_id = p.id
        JOIN teams t ON ge.team_id = t.id
        JOIN clubs c ON t.club_id = c.id
        JOIN games g ON ge.game_id = g.id
        JOIN rounds r ON g.round_id = r.id
        WHERE ge.player_id IS NOT NULL
          AND ge.event_type NOT IN :excluded
    """
    
    params = {"excluded": EXCLUDED_EVENTS}
    if competition_id:
        query += " AND r.competition_id = :comp_id"
        params["comp_id"] = competition_id
        
    query += """
        GROUP BY p.id, p.name, c.id, c.name, p.thumbnail_url
        ORDER BY total_points DESC, tries DESC
        LIMIT 50
    """
    
    # Use bindparams for expanding IN clause
    stmt = text(query).bindparams(bindparam("excluded", expanding=True))
    params["excluded"] = list(EXCLUDED_EVENTS)
    
    result = await db.execute(stmt, params)
    rows = result.fetchall()
    
    stats = []
    for i, row in enumerate(rows):
        stats.append(PlayerStatRow(
            rank=i + 1,
            player_id=row.player_id,
            player_name=row.player_name,
            club_name=row.club_name,
            club_id=row.club_id,
            tries=row.tries,
            conversions=row.conversions,
            penalties=row.penalties,
            drop_goals=row.drop_goals,
            total_points=row.total_points or 0,
            yellow_cards=row.yellow_cards,
            red_cards=row.red_cards,
            image_url=row.image_url
        ))
    return stats

async def get_club_stats(db: AsyncSession, competition_id: Optional[int] = None) -> List[ClubStatRow]:
    query = """
        SELECT 
            c.id as club_id, 
            c.name as club_name,
            COUNT(CASE WHEN ge.event_type = 'try' OR ge.event_type = 'rugby_union_penalty_try' THEN 1 END) as tries,
            COUNT(CASE WHEN ge.event_type = 'conversion' THEN 1 END) as conversions,
            COUNT(CASE WHEN ge.event_type = 'penalty_goal' THEN 1 END) as penalties,
            SUM(ge.points) as total_points,
            COUNT(CASE WHEN ge.event_type = 'yellow_card' THEN 1 END) as yellow_cards,
            COUNT(CASE WHEN ge.event_type = 'red_card' THEN 1 END) as red_cards,
            c.logo_url
        FROM game_events ge
        JOIN teams t ON ge.team_id = t.id
        JOIN clubs c ON t.club_id = c.id
        JOIN games g ON ge.game_id = g.id
        JOIN rounds r ON g.round_id = r.id
        WHERE ge.event_type NOT IN :excluded
    """
    
    params = {"excluded": EXCLUDED_EVENTS}
    if competition_id:
        query += " AND r.competition_id = :comp_id"
        params["comp_id"] = competition_id
        
    query += """
        GROUP BY c.id, c.name, c.logo_url
        ORDER BY total_points DESC
        LIMIT 50
    """
    
    stmt = text(query).bindparams(bindparam("excluded", expanding=True))
    params["excluded"] = list(EXCLUDED_EVENTS)
    
    result = await db.execute(stmt, params)
    rows = result.fetchall()
    
    stats = []
    for i, row in enumerate(rows):
        stats.append(ClubStatRow(
            rank=i + 1,
            club_id=row.club_id,
            club_name=row.club_name,
            tries=row.tries,
            conversions=row.conversions,
            penalties=row.penalties,
            total_points=row.total_points or 0,
            yellow_cards=row.yellow_cards,
            red_cards=row.red_cards,
            logo_url=row.logo_url
        ))
    return stats

async def get_season_overview(db: AsyncSession, competition_id: Optional[int] = None) -> SeasonOverview:
    # 1. General counts
    query_base = """
        SELECT 
            COUNT(CASE WHEN ge.event_type = 'try' OR ge.event_type = 'rugby_union_penalty_try' THEN 1 END) as total_tries,
            COUNT(CASE WHEN ge.event_type = 'conversion' THEN 1 END) as total_conversions,
            COUNT(CASE WHEN ge.event_type = 'penalty_goal' THEN 1 END) as total_penalties,
            COUNT(CASE WHEN ge.event_type = 'yellow_card' THEN 1 END) as total_yellow_cards,
            COUNT(CASE WHEN ge.event_type = 'red_card' THEN 1 END) as total_red_cards
        FROM game_events ge
        JOIN games g ON ge.game_id = g.id
        JOIN rounds r ON g.round_id = r.id
        WHERE ge.event_type NOT IN :excluded
    """
    params = {"excluded": EXCLUDED_EVENTS}
    if competition_id:
        query_base += " AND r.competition_id = :comp_id"
        params["comp_id"] = competition_id
        
    stmt_base = text(query_base).bindparams(bindparam("excluded", expanding=True))
    params["excluded"] = list(EXCLUDED_EVENTS)
    
    res_base = await db.execute(stmt_base, params)
    row_base = res_base.fetchone()
    
    # 2. Games played
    query_games = "SELECT COUNT(*) FROM games g JOIN rounds r ON g.round_id = r.id WHERE g.status = 'completed'"
    if competition_id:
        query_games += " AND r.competition_id = :comp_id"
    res_games = await db.execute(text(query_games), params)
    games_played = res_games.scalar()
    
    # 3. Top scorers
    player_stats = await get_player_stats(db, competition_id)
    top_scorer = player_stats[0] if player_stats else None
    
    # Top try scorer specifically
    query_try = """
        SELECT p.name, COUNT(*) as tries
        FROM game_events ge
        JOIN players p ON ge.player_id = p.id
        JOIN games g ON ge.game_id = g.id
        JOIN rounds r ON g.round_id = r.id
        WHERE ge.event_type = 'try'
    """
    if competition_id:
        query_try += " AND r.competition_id = :comp_id"
    query_try += " GROUP BY p.id, p.name ORDER BY tries DESC LIMIT 1"
    res_try = await db.execute(text(query_try), params)
    row_try = res_try.fetchone()
    
    return SeasonOverview(
        total_tries=row_base.total_tries,
        total_conversions=row_base.total_conversions,
        total_penalties=row_base.total_penalties,
        total_yellow_cards=row_base.total_yellow_cards,
        total_red_cards=row_base.total_red_cards,
        top_scorer_name=top_scorer.player_name if top_scorer else None,
        top_scorer_points=top_scorer.total_points if top_scorer else 0,
        top_try_scorer_name=row_try.name if row_try else None,
        top_try_scorer_tries=row_try.tries if row_try else 0,
        games_played=games_played
    )
