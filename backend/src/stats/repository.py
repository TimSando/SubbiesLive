from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from src.stats.schemas import PlayerStatRow, ClubStatRow, SeasonOverview


async def get_player_stats(
    db: AsyncSession, 
    competition_id: Optional[int] = None,
    parent_competition: Optional[str] = None,
    division: Optional[str] = None
) -> List[PlayerStatRow]:
    query = """
        SELECT 
            p.id as player_id, 
            p.name as player_name, 
            c.name as club_name, 
            c.id as club_id,
            SUM(ph.tries) as tries,
            SUM(ph.conversions) as conversions,
            SUM(ph.penalty_goals) as penalties,
            SUM(ph.drop_goals) as drop_goals,
            SUM(ph.points) as total_points,
            SUM(ph.yellow_cards) as yellow_cards,
            SUM(ph.red_cards) as red_cards,
            COUNT(ph.game_id) as games_played,
            p.thumbnail_url as image_url
        FROM player_history ph
        JOIN players p ON ph.player_id = p.id
        JOIN teams t ON ph.team_id = t.id
        JOIN clubs c ON t.club_id = c.id
        JOIN games g ON ph.game_id = g.id
        JOIN rounds r ON g.round_id = r.id
        JOIN competitions comp ON r.competition_id = comp.id
        LEFT JOIN competition_mapping m ON comp.competition_mapping_id = m.id
        WHERE 1=1
    """
    
    params = {}
    if competition_id:
        query += " AND r.competition_id = :comp_id"
        params["comp_id"] = competition_id
    if parent_competition:
        query += " AND m.parent_competition = :parent"
        params["parent"] = parent_competition
    if division:
        query += " AND m.division = :div"
        params["div"] = division
        
    query += """
        GROUP BY p.id, p.name, c.id, c.name, p.thumbnail_url
        ORDER BY total_points DESC, tries DESC
        LIMIT 50
    """
    
    result = await db.execute(text(query), params)
    rows = result.fetchall()
    
    stats = []
    for i, row in enumerate(rows):
        stats.append(PlayerStatRow(
            rank=i + 1,
            player_id=row.player_id,
            player_name=row.player_name,
            club_name=row.club_name,
            club_id=row.club_id,
            tries=row.tries or 0,
            conversions=row.conversions or 0,
            penalties=row.penalties or 0,
            drop_goals=row.drop_goals or 0,
            total_points=row.total_points or 0,
            yellow_cards=row.yellow_cards or 0,
            red_cards=row.red_cards or 0,
            games_played=row.games_played or 0,
            image_url=row.image_url
        ))
    return stats

async def get_club_stats(
    db: AsyncSession, 
    competition_id: Optional[int] = None,
    parent_competition: Optional[str] = None,
    division: Optional[str] = None
) -> List[ClubStatRow]:
    query = """
        SELECT 
            c.id as club_id, 
            c.name as club_name,
            SUM(ph.tries) as tries,
            SUM(ph.conversions) as conversions,
            SUM(ph.penalty_goals) as penalties,
            SUM(ph.drop_goals) as drop_goals,
            SUM(ph.points) as total_points,
            SUM(ph.yellow_cards) as yellow_cards,
            SUM(ph.red_cards) as red_cards,
            COUNT(DISTINCT ph.game_id) as games_played,
            c.logo_url
        FROM player_history ph
        JOIN teams t ON ph.team_id = t.id
        JOIN clubs c ON t.club_id = c.id
        JOIN games g ON ph.game_id = g.id
        JOIN rounds r ON g.round_id = r.id
        JOIN competitions comp ON r.competition_id = comp.id
        LEFT JOIN competition_mapping m ON comp.competition_mapping_id = m.id
        WHERE 1=1
    """
    
    params = {}
    if competition_id:
        query += " AND r.competition_id = :comp_id"
        params["comp_id"] = competition_id
    if parent_competition:
        query += " AND m.parent_competition = :parent"
        params["parent"] = parent_competition
    if division:
        query += " AND m.division = :div"
        params["div"] = division
        
    query += """
        GROUP BY c.id, c.name, c.logo_url
        ORDER BY total_points DESC
        LIMIT 50
    """
    
    result = await db.execute(text(query), params)
    rows = result.fetchall()
    
    stats = []
    for i, row in enumerate(rows):
        stats.append(ClubStatRow(
            rank=i + 1,
            club_id=row.club_id,
            club_name=row.club_name,
            tries=row.tries or 0,
            conversions=row.conversions or 0,
            penalties=row.penalties or 0,
            drop_goals=row.drop_goals or 0,
            total_points=row.total_points or 0,
            yellow_cards=row.yellow_cards or 0,
            red_cards=row.red_cards or 0,
            games_played=row.games_played or 0,
            logo_url=row.logo_url
        ))
    return stats

async def get_season_overview(
    db: AsyncSession, 
    competition_id: Optional[int] = None,
    parent_competition: Optional[str] = None,
    division: Optional[str] = None
) -> SeasonOverview:
    params = {}
    
    # 1. General counts from player_history
    query_base = """
        SELECT 
            SUM(ph.tries) as total_tries,
            SUM(ph.conversions) as total_conversions,
            SUM(ph.penalty_goals) as total_penalties,
            SUM(ph.yellow_cards) as total_yellow_cards,
            SUM(ph.red_cards) as total_red_cards
        FROM player_history ph
        JOIN games g ON ph.game_id = g.id
        JOIN rounds r ON g.round_id = r.id
        JOIN competitions comp ON r.competition_id = comp.id
        LEFT JOIN competition_mapping m ON comp.competition_mapping_id = m.id
        WHERE 1=1
    """
    
    if competition_id:
        query_base += " AND r.competition_id = :comp_id"
        params["comp_id"] = competition_id
    if parent_competition:
        query_base += " AND m.parent_competition = :parent"
        params["parent"] = parent_competition
    if division:
        query_base += " AND m.division = :div"
        params["div"] = division
        
    res_base = await db.execute(text(query_base), params)
    row_base = res_base.fetchone()
    
    # 2. Games played (from games table)
    query_games = """
        SELECT COUNT(*) 
        FROM games g 
        JOIN rounds r ON g.round_id = r.id 
        JOIN competitions comp ON r.competition_id = comp.id
        LEFT JOIN competition_mapping m ON comp.competition_mapping_id = m.id
        WHERE g.status = 'completed'
    """
    if competition_id:
        query_games += " AND r.competition_id = :comp_id"
    if parent_competition:
        query_games += " AND m.parent_competition = :parent"
    if division:
        query_games += " AND m.division = :div"
        
    res_games = await db.execute(text(query_games), params)
    games_played = res_games.scalar()
    
    # 3. Top scorer (reuses the refactored player stats function)
    player_stats = await get_player_stats(db, competition_id, parent_competition, division)
    top_scorer = player_stats[0] if player_stats else None
    
    # 4. Top try scorer specifically
    query_try = """
        SELECT p.name, SUM(ph.tries) as tries
        FROM player_history ph
        JOIN players p ON ph.player_id = p.id
        JOIN games g ON ph.game_id = g.id
        JOIN rounds r ON g.round_id = r.id
        JOIN competitions comp ON r.competition_id = comp.id
        LEFT JOIN competition_mapping m ON comp.competition_mapping_id = m.id
        WHERE 1=1
    """
    if competition_id:
        query_try += " AND r.competition_id = :comp_id"
    if parent_competition:
        query_try += " AND m.parent_competition = :parent"
    if division:
        query_try += " AND m.division = :div"
    query_try += " GROUP BY p.id, p.name ORDER BY tries DESC LIMIT 1"
    
    res_try = await db.execute(text(query_try), params)
    row_try = res_try.fetchone()
    
    return SeasonOverview(
        total_tries=row_base.total_tries or 0,
        total_conversions=row_base.total_conversions or 0,
        total_penalties=row_base.total_penalties or 0,
        total_yellow_cards=row_base.total_yellow_cards or 0,
        total_red_cards=row_base.total_red_cards or 0,
        top_scorer_name=top_scorer.player_name if top_scorer else None,
        top_scorer_points=top_scorer.total_points if top_scorer else 0,
        top_try_scorer_name=row_try.name if row_try else None,
        top_try_scorer_tries=row_try.tries if row_try else 0,
        games_played=games_played or 0
    )
