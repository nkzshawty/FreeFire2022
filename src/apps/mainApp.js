const { createBaseApp, finalizeApp } = require('./base');
const createProtocolRouter = require('../protocol/router');
const { AUTH_COMMANDS } = require('../protocol/authCommands');

module.exports = function createMainApp() {
  const app = createBaseApp();

  // GET /app/info/get — matches real connect-server format
  app.get('/app/info/get', (req, res) => {
    res.json({ status: 0, client_log: false });
  });

  // POST /oauth/guest/register — FLAT response (no "data" wrapper) matching real Garena SDK
  app.post('/oauth/guest/register', (req, res) => {
    const uid = 10000000 + Math.floor(Math.random() * 9000000);
    const now = Math.floor(Date.now() / 1000);
    const token = Buffer.from(`guest_${uid}_${Date.now()}`).toString('base64');
    res.json({
      access_token: token,
      code: 0,
      create_time: now,
      expires_in: 1296000,
      expiry_time: now + 1296000,
      main_active_platform: 4,
      open_id: `guest-${uid}`,
      platform: 4,
      refresh_expiry_time: now + 2592000,
      refresh_token: token,
      scope: ['get_user_info', 'get_friends', 'payment', 'send_request'],
      token_type: 'Bearer',
      uid: uid
    });
  });

  // POST /oauth/guest/login
  app.post('/oauth/guest/login', (req, res) => {
    const uid = 10000000 + Math.floor(Math.random() * 9000000);
    const now = Math.floor(Date.now() / 1000);
    const token = Buffer.from(`guest_${uid}_${Date.now()}`).toString('base64');
    res.json({
      access_token: token,
      code: 0,
      create_time: now,
      expires_in: 1296000,
      expiry_time: now + 1296000,
      main_active_platform: 4,
      open_id: `guest-${uid}`,
      platform: 4,
      refresh_expiry_time: now + 2592000,
      refresh_token: token,
      scope: ['get_user_info', 'get_friends', 'payment', 'send_request'],
      token_type: 'Bearer',
      uid: uid
    });
  });

  // POST /oauth/token/facebook/exchange — flat response
  app.post('/oauth/token/facebook/exchange', (req, res) => {
    const uid = 10000000 + Math.floor(Math.random() * 9000000);
    const now = Math.floor(Date.now() / 1000);
    const token = Buffer.from(`fb_${uid}_${Date.now()}`).toString('base64');
    res.json({
      access_token: token,
      code: 0,
      create_time: now,
      expires_in: 1296000,
      expiry_time: now + 1296000,
      main_active_platform: 4,
      open_id: `fb-${uid}`,
      platform: 4,
      refresh_expiry_time: now + 2592000,
      refresh_token: token,
      scope: ['get_user_info', 'get_friends', 'payment', 'send_request'],
      token_type: 'Bearer',
      uid: uid
    });
  });

  // GET /oauth/token/inspect
  app.get('/oauth/token/inspect', (req, res) => {
    const token = req.query.token || req.query.access_token || '';
    const now = Math.floor(Date.now() / 1000);
    let uid = 10000001;
    let prefix = 'guest';
    try {
      const decoded = Buffer.from(token, 'base64').toString('utf8');
      const m = decoded.match(/(guest|fb|grant|refresh)_(\d+)_/);
      if (m) {
        prefix = m[1] === 'fb' ? 'fb' : 'guest';
        uid = parseInt(m[2], 10);
      }
    } catch (e) {}
    console.log('[main] /oauth/token/inspect uid=' + uid);
    res.json({
      expiry_time: now + 86400,
      uid: uid,
      open_id: prefix + '-' + uid,
      main_active_platform: 4,
      app_id: 100067,
      platform: 4,
      create_time: now - 3600,
      scope: ['get_user_info', 'get_friends', 'payment', 'send_request'],
      login_type: 2,
      login_platform: 4
    });
  });

  // POST /oauth/token — refresh
  app.post('/oauth/token', (req, res) => {
    const now = Math.floor(Date.now() / 1000);
    const uid = 10000001;
    const token = Buffer.from(`refresh_${uid}_${Date.now()}`).toString('base64');
    res.json({
      access_token: token,
      expiry_time: now + 86400,
      open_id: 'guest-' + uid,
      refresh_token: token,
      refresh_expiry_time: now + 2592000,
      token_type: 'Bearer',
      uid: uid
    });
  });

  // POST /oauth/guest/token/grant — called by Garena SDK after guest/register
  // Must return a full OAuth token response for the SDK to proceed with MajorLogin
  app.post('/oauth/guest/token/grant', (req, res) => {
    const uid = 10000000 + Math.floor(Math.random() * 9000000);
    const now = Math.floor(Date.now() / 1000);
    const token = Buffer.from('grant_' + uid + '_' + Date.now()).toString('base64');
    console.log('[main] /oauth/guest/token/grant uid=' + uid);
    res.json({
      access_token: token,
      code: 0,
      create_time: now,
      expires_in: 1296000,
      expiry_time: now + 1296000,
      main_active_platform: 4,
      open_id: 'guest-' + uid,
      platform: 4,
      refresh_expiry_time: now + 2592000,
      refresh_token: token,
      scope: ['get_user_info', 'get_friends', 'payment', 'send_request'],
      token_type: 'Bearer',
      uid: uid
    });
  });

  // POST /oauth/token/grant — generic token grant endpoint
  app.post('/oauth/token/grant', (req, res) => {
    const uid = 10000000 + Math.floor(Math.random() * 9000000);
    const now = Math.floor(Date.now() / 1000);
    const token = Buffer.from('grant_' + uid + '_' + Date.now()).toString('base64');
    console.log('[main] /oauth/token/grant uid=' + uid);
    res.json({
      access_token: token,
      code: 0,
      create_time: now,
      expires_in: 1296000,
      expiry_time: now + 1296000,
      main_active_platform: 4,
      open_id: 'guest-' + uid,
      platform: 4,
      refresh_expiry_time: now + 2592000,
      refresh_token: token,
      scope: ['get_user_info', 'get_friends', 'payment', 'send_request'],
      token_type: 'Bearer',
      uid: uid
    });
  });

  // Catch-all oauth
  app.all('/oauth/*', (req, res) => {
    console.log('[main] CATCH-ALL ' + req.method + ' ' + req.url);
    res.json({ code: 0 });
  });

  const protocolRouter = createProtocolRouter({ filter: (cmd) => !AUTH_COMMANDS.has(cmd) });
  app.use('/', protocolRouter);
  app.use('/main', protocolRouter);
  app.use('/api', require('../routes/index'));
  return finalizeApp(app, 'main');
};
