import { http, HttpResponse } from 'msw'

export const handlers = [
  // Health
  http.get('/api/health', () => HttpResponse.json({ status: 'healthy' })),

  // Competitions
  http.get('/api/competitions', () => HttpResponse.json([
    { id: 1, name: 'Kentwell Cup', team_count: 8, round_count: 14, division: null, grade: null },
    { id: 2, name: 'Shute Shield', team_count: 10, round_count: 18, division: null, grade: null },
  ])),
  http.get('/api/competitions/:id', ({ params }) => {
    if (params.id === '999') return new HttpResponse(null, { status: 404 })
    return HttpResponse.json({
      id: Number(params.id),
      name: 'Kentwell Cup',
      external_id: 101,
      rounds: [
        { id: 201, name: 'Round 1', number: 1, game_count: 4, completed_game_count: 4, latest_game_date: '2026-06-06T15:00:00' }
      ],
      team_count: 8
    })
  }),

  // Clubs
  http.get('/api/clubs', () => HttpResponse.json([
    { id: 1, name: 'Colleagues', short_name: 'Colleagues', logo_url: null, has_womens_team: false }
  ])),
  http.get('/api/clubs/:id', ({ params }) => {
    if (params.id === '999') return new HttpResponse(null, { status: 404 })
    return HttpResponse.json({
      id: Number(params.id),
      name: 'Colleagues',
      short_name: 'Colleagues',
      logo_url: null,
      about_text: 'Test club description',
      division_info: 'Division 1',
      grades_count: 5,
      training_info: 'Tues/Thurs',
      has_womens_team: false,
      home_ground_name: 'Woollahra Oval',
      home_ground_map_url: null,
      website_url: null,
      facebook_url: null,
      instagram_url: null,
      teams: [
        { id: 5001, club_id: Number(params.id), competition_id: 1, name: 'Colleagues 1st Grade', external_id: 5001 }
      ]
    })
  }),

  // Games
  http.get('/api/games', () => HttpResponse.json([])),
  http.get('/api/games/live', () => HttpResponse.json([])),
  http.get('/api/games/:id', ({ params }) => {
    if (params.id === '999') return new HttpResponse(null, { status: 404 })
    return HttpResponse.json({
      id: Number(params.id),
      round_id: 201,
      home_team_id: 5001,
      away_team_id: 5002,
      game_date: '2026-06-06T15:00:00',
      location: 'Woollahra Oval',
      home_score: 25,
      away_score: 10,
      status: 'completed',
      external_id: 10001,
      video_url: null,
      events: []
    })
  }),

  // Players
  http.get('/api/players', () => HttpResponse.json([
    { id: 1, name: 'George Gregan', external_id: 1001, thumbnail_url: null, current_team: 'Colleagues' }
  ])),
  http.get('/api/players/:id', ({ params }) => {
    if (params.id === '999') return new HttpResponse(null, { status: 404 })
    return HttpResponse.json({
      id: Number(params.id),
      name: 'George Gregan',
      dob: '1973-04-19',
      image_url: null,
      thumbnail_url: null,
      external_id: 1001,
      teams: [
        { team_id: 5001, team_name: 'Colleagues 1st', club_name: 'Colleagues', competition_name: 'Kentwell Cup' }
      ],
      stats: {
        total_tries: 5,
        total_conversions: 10,
        total_penalty_goals: 0,
        total_drop_goals: 0,
        total_yellow_cards: 0,
        total_red_cards: 0,
        total_points: 45,
        games_played: 12
      },
      recent_club: 'Colleagues'
    })
  }),

  // Standings
  http.get('/api/standings/:id', ({ params }) => {
    return HttpResponse.json({
      competition_id: Number(params.id),
      competition_name: 'Kentwell Cup',
      standings: [
        { position: 1, team_id: 5001, team_name: 'Colleagues 1st', club_name: 'Colleagues', club_id: 1, played: 1, won: 1, drawn: 0, lost: 0, byes: 0, points_for: 25, points_against: 10, points_diff: 15, competition_points: 4 }
      ]
    })
  }),

  // Stats
  http.get('/api/stats/players', () => HttpResponse.json([])),
  http.get('/api/stats/clubs', () => HttpResponse.json([])),
  http.get('/api/stats/clubs/depth', () => HttpResponse.json([])),
  http.get('/api/stats/overview', () => HttpResponse.json({
    total_tries: 0,
    total_conversions: 0,
    total_penalties: 0,
    total_yellow_cards: 0,
    total_red_cards: 0,
    top_scorer_name: null,
    top_scorer_points: 0,
    top_try_scorer_name: null,
    top_try_scorer_tries: 0,
    games_played: 0
  })),
  http.get('/api/stats/team/:id/form', ({ params }) => HttpResponse.json({
    team_id: Number(params.id),
    games_played: 5,
    total_tries: 12,
    total_conversions: 8,
    total_yellow_cards: 1,
    total_red_cards: 0
  })),

  // RefZone Login
  http.post('/api/refzone/login', async ({ request }) => {
    const { email } = await request.json()
    if (email === 'bad@test.com' || email === 'encrypted-bad@test.com') {
      return new HttpResponse(JSON.stringify({ message: 'Incorrect email or password' }), { status: 401 })
    }
    return HttpResponse.json({
      jwtTokens: { accessToken: 'test-token-abc' },
      userId: 'user-123',
      profile: { firstName: 'Test', lastName: 'User' },
    })
  }),

  // RefZone Appointments
  http.get('/api/refzone/appointments', ({ request }) => {
    const authHeader = request.headers.get('Authorization')
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return new HttpResponse(null, { status: 401 })
    }
    const now = Date.now()
    
    // Dynamically calculate a Saturday moment in Sydney time so it falls on the weekend
    const sydneyNowStr = new Date().toLocaleDateString('en-CA', { timeZone: 'Australia/Sydney' });
    const [sYear, sMonth, sDay] = sydneyNowStr.split('-').map(Number);
    const sydneyDate = new Date(sYear, sMonth - 1, sDay);
    const dayOfWeek = sydneyDate.getDay();
    let satDiff = 0;
    if (dayOfWeek === 6) satDiff = 0;
    else if (dayOfWeek === 0) satDiff = -1;
    else satDiff = 6 - dayOfWeek;
    
    const satDate = new Date(sydneyDate);
    satDate.setDate(sydneyDate.getDate() + satDiff);
    const satMoment = satDate.getTime() + 12 * 3600 * 1000; // 12:00 PM on Saturday
    
    return HttpResponse.json([
      {
        _id: 'app-weekend-1',
        isActive: true,
        status: 'approved',
        type: 'Referee',
        db_game_id: 1,
        match: {
          moment: satMoment,
          homeTeam: { name: 'Colleagues' },
          awayTeam: { name: 'Mosman' },
          competition: { name: 'Kentwell Cup' },
          venue: { name: 'Woollahra Oval' }
        },
        otherReferees: [
          { _id: 'ref-2', firstname: 'John', lastname: 'Doe', type: 'Assistant Referee 1' }
        ]
      },
      {
        _id: 'app-upcoming-1',
        isActive: true,
        status: 'pending',
        type: 'Referee',
        db_game_id: null,
        match: {
          moment: now + 86400000 * 10, // 10 days from now
          homeTeam: { name: 'Colleagues' },
          awayTeam: { name: 'Sydney Uni' },
          competition: { name: 'Kentwell Cup' },
          venue: { name: 'St Pauls Oval' }
        }
      },
      {
        _id: 'app-past-1',
        isActive: true,
        status: 'confirmed',
        type: 'Referee',
        db_game_id: 1,
        match: {
          moment: now - 86400000 * 5, // 5 days ago
          homeTeam: { name: 'Mosman' },
          awayTeam: { name: 'Colleagues' },
          competition: { name: 'Kentwell Cup' },
          venue: { name: 'Rawson Park' }
        }
      }
    ])
  }),

  // Ingestion
  http.get('/api/ingestion/status', () => HttpResponse.json({ running: false })),
  http.post('/api/ingestion/trigger', () => HttpResponse.json({ status: 'started', message: 'Started' })),

  // Notifications VAPID
  http.get('/api/notifications/vapid-public-key', () => HttpResponse.json("test-vapid-key")),
]
