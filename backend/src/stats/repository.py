from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from src.stats.schemas import PlayerStatRow, ClubStatRow, SeasonOverview, ClubDepthRow, TeamFormStats
from src.core.cache import ttl_cache


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

@ttl_cache(ttl_seconds=300)
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
        WHERE g.status IN ('completed', 'in_progress')
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

    # 5. Club count
    query_clubs = """
        SELECT COUNT(DISTINCT t.club_id)
        FROM teams t
        JOIN competitions comp ON t.competition_id = comp.id
        LEFT JOIN competition_mapping m ON comp.competition_mapping_id = m.id
        WHERE 1=1
    """
    if competition_id:
        query_clubs += " AND comp.id = :comp_id"
    if parent_competition:
        query_clubs += " AND m.parent_competition = :parent"
    if division:
        query_clubs += " AND m.division = :div"
    res_clubs = await db.execute(text(query_clubs), params)
    club_count = res_clubs.scalar() or 0

    # 6. Player count
    query_players = """
        SELECT COUNT(DISTINCT ph.player_id)
        FROM player_history ph
        JOIN games g ON ph.game_id = g.id
        JOIN rounds r ON g.round_id = r.id
        JOIN competitions comp ON r.competition_id = comp.id
        LEFT JOIN competition_mapping m ON comp.competition_mapping_id = m.id
        WHERE 1=1
    """
    if competition_id:
        query_players += " AND r.competition_id = :comp_id"
    if parent_competition:
        query_players += " AND m.parent_competition = :parent"
    if division:
        query_players += " AND m.division = :div"
    res_players = await db.execute(text(query_players), params)
    player_count = res_players.scalar() or 0
    
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
        games_played=games_played or 0,
        club_count=club_count,
        player_count=player_count
    )

async def get_club_depth_stats(
    db: AsyncSession, 
    competition_id: Optional[int] = None,
    parent_competition: Optional[str] = None,
    division: Optional[str] = None
) -> List[ClubDepthRow]:
    query = """
        WITH player_appearances AS (
            SELECT 
                ph.player_id,
                t.club_id,
                COUNT(DISTINCT ph.game_id) AS games_played,
                COUNT(DISTINCT ph.team_id) AS teams_played
            FROM player_history ph
            JOIN teams t ON ph.team_id = t.id
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
            GROUP BY ph.player_id, t.club_id
        )
        SELECT 
            c.id AS club_id,
            c.name AS club_name,
            c.logo_url,
            COUNT(pa.player_id) AS total_players,
            SUM(CASE WHEN pa.games_played >= 5 THEN 1 ELSE 0 END) AS core_players,
            SUM(CASE WHEN pa.teams_played = 1 THEN 1 ELSE 0 END) AS dedicated_players,
            SUM(CASE WHEN pa.teams_played >= 2 THEN 1 ELSE 0 END) AS swing_players,
            AVG(pa.games_played) AS avg_games
        FROM clubs c
        JOIN player_appearances pa ON c.id = pa.club_id
        GROUP BY c.id, c.name, c.logo_url
        ORDER BY total_players DESC
    """
    
    result = await db.execute(text(query), params)
    rows = result.fetchall()
    
    stats = []
    for i, row in enumerate(rows):
        stats.append(ClubDepthRow(
            rank=i + 1,
            club_id=row.club_id,
            club_name=row.club_name,
            logo_url=row.logo_url,
            total_players=row.total_players or 0,
            core_players=int(row.core_players or 0),
            dedicated_players=int(row.dedicated_players or 0),
            swing_players=int(row.swing_players or 0),
            avg_games=float(row.avg_games or 0.0)
        ))
    return stats


async def get_team_form_stats(db: AsyncSession, team_id: int) -> TeamFormStats:
    """Fetch aggregated tries and cards for a team's last 5 games."""
    query = """
        WITH recent_games AS (
            SELECT id FROM games 
            WHERE (home_team_id = :team_id OR away_team_id = :team_id)
            AND status = 'completed'
            ORDER BY game_date DESC
            LIMIT 5
        )
        SELECT 
            :team_id as team_id,
            COUNT(DISTINCT ph.game_id) as games_played,
            COALESCE(SUM(ph.tries), 0) as total_tries,
            COALESCE(SUM(ph.conversions), 0) as total_conversions,
            COALESCE(SUM(ph.yellow_cards), 0) as total_yellow_cards,
            COALESCE(SUM(ph.red_cards), 0) as total_red_cards
        FROM player_history ph
        WHERE ph.team_id = :team_id
        AND ph.game_id IN (SELECT id FROM recent_games)
    """
    result = await db.execute(text(query), {"team_id": team_id})
    row = result.fetchone()
    
    if not row or row.games_played == 0:
        return TeamFormStats(
            team_id=team_id,
            games_played=0,
            total_tries=0,
            total_conversions=0,
            total_yellow_cards=0,
            total_red_cards=0
        )
        
    return TeamFormStats(
        team_id=row.team_id,
        games_played=row.games_played,
        total_tries=row.total_tries,
        total_conversions=row.total_conversions,
        total_yellow_cards=row.total_yellow_cards,
        total_red_cards=row.total_red_cards
    )


