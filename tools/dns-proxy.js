'use strict';
const dgram = require('dgram');
const os = require('os');

const LISTEN_PORT = 53;
const UPSTREAM_DNS = '8.8.8.8';

function getLocalIp() {
  const ifaces = os.networkInterfaces();
  for (const name of Object.keys(ifaces)) {
    for (const iface of ifaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) return iface.address;
    }
  }
  return '127.0.0.1';
}

const LOCAL_IP = process.env.LOCAL_IP || getLocalIp();

const FF_SUFFIXES = ['.ggblueshark.com', '.freefiremobile.com', '.garena.com'];

function isFFDomain(name) {
  const lower = name.toLowerCase().replace(/\.$/, '');
  for (const suffix of FF_SUFFIXES) {
    if (lower.endsWith(suffix)) return true;
  }
  return false;
}

function parseDNSQuestion(buf) {
  let offset = 12;
  const labels = [];
  while (offset < buf.length) {
    const len = buf[offset];
    if (len === 0) { offset++; break; }
    offset++;
    labels.push(buf.slice(offset, offset + len).toString('ascii'));
    offset += len;
  }
  const name = labels.join('.');
  const qtype = buf.readUInt16BE(offset);
  return { name, qtype, questionEnd: offset + 4 };
}

function buildDNSResponse(query, ip) {
  const { questionEnd } = parseDNSQuestion(query);
  const header = Buffer.from(query.slice(0, 12));
  header[2] = 0x81; header[3] = 0x80;
  header[6] = 0x00; header[7] = 0x01;
  const question = query.slice(12, questionEnd);
  const answer = Buffer.alloc(16);
  answer.writeUInt16BE(0xC00C, 0);
  answer.writeUInt16BE(1, 2);
  answer.writeUInt16BE(1, 4);
  answer.writeUInt32BE(60, 6);
  answer.writeUInt16BE(4, 10);
  const parts = ip.split('.');
  answer[12] = parseInt(parts[0]);
  answer[13] = parseInt(parts[1]);
  answer[14] = parseInt(parts[2]);
  answer[15] = parseInt(parts[3]);
  return Buffer.concat([header, question, answer]);
}

const server = dgram.createSocket('udp4');

server.on('message', (msg, rinfo) => {
  try {
    const { name, qtype } = parseDNSQuestion(msg);
    if (qtype === 1 && isFFDomain(name)) {
      console.log('[DNS] ' + name + ' -> ' + LOCAL_IP + ' (intercepted)');
      const response = buildDNSResponse(msg, LOCAL_IP);
      server.send(response, rinfo.port, rinfo.address);
    } else {
      const client = dgram.createSocket('udp4');
      client.send(msg, 53, UPSTREAM_DNS);
      client.on('message', (response) => { server.send(response, rinfo.port, rinfo.address); client.close(); });
      client.on('error', () => client.close());
      setTimeout(() => { try { client.close(); } catch(e) {} }, 5000);
    }
  } catch (e) {}
});

server.on('listening', () => {
  console.log('=== DNS Proxy rodando na porta ' + LISTEN_PORT + ' ===');
  console.log('IP local: ' + LOCAL_IP);
  console.log('Dominios FF interceptados: *' + FF_SUFFIXES.join(', *'));
  console.log('');
});

server.on('error', (err) => {
  if (err.code === 'EACCES') console.error('[ERRO] Porta 53 requer admin. Rode como administrador.');
  else if (err.code === 'EADDRINUSE') console.error('[ERRO] Porta 53 em uso. Pare outro DNS ou rode: net stop dnscache');
  else console.error('[ERRO] ' + err.message);
  process.exit(1);
});

server.bind(LISTEN_PORT);
