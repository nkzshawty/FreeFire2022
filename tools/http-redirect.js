'use strict';
const http = require('http');

const LIVE_PORT = 19134;
const LOGIN_PORT = 19132;
const MAIN_PORT = 19133;

function getTargetPort(url) {
  if (url.startsWith('/live')) return LIVE_PORT;
  if (url.startsWith('/cdn')) return LIVE_PORT;
  if (url.startsWith('/MajorLogin') || url.startsWith('/MajorRegister') ||
      url.startsWith('/Login') || url.startsWith('/PlatformLogin')) return LOGIN_PORT;
  return MAIN_PORT;
}

const proxy = http.createServer((req, res) => {
  const targetPort = getTargetPort(req.url);
  const options = {
    hostname: '127.0.0.1',
    port: targetPort,
    path: req.url,
    method: req.method,
    headers: Object.assign({}, req.headers, { host: '127.0.0.1:' + targetPort })
  };
  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });
  proxyReq.on('error', (err) => {
    console.error('[proxy] ' + req.method + ' ' + req.url + ' -> :' + targetPort + ' ERRO: ' + err.message);
    res.writeHead(502); res.end('Bad Gateway');
  });
  req.pipe(proxyReq);
  console.log('[proxy] ' + req.method + ' ' + req.url + ' -> :' + targetPort);
});

proxy.listen(80, '0.0.0.0', () => {
  console.log('=== HTTP Proxy rodando na porta 80 ===');
  console.log('Roteamento: /live/* -> :' + LIVE_PORT + ', /MajorLogin -> :' + LOGIN_PORT + ', resto -> :' + MAIN_PORT);
  console.log('');
});

proxy.on('error', (err) => {
  if (err.code === 'EACCES') console.error('[ERRO] Porta 80 requer admin.');
  else if (err.code === 'EADDRINUSE') console.error('[ERRO] Porta 80 em uso.');
  else console.error('[ERRO] ' + err.message);
  process.exit(1);
});
