# Conectando o Free Fire ao Servidor Local (BlueStacks)

## Visao Geral

Como a APK do Free Fire 1.70.0 tem protecao anti-tamper (strings encriptadas), nao da
pra editar o binario direto. Em vez disso, redirecionamos o trafego de rede: um DNS
local intercepta os dominios da Garena e aponta pro seu PC, onde o servidor responde
no lugar.

```
  Free Fire (BlueStacks)
       |
       | DNS query: "ff-live-sea.ggblueshark.com"
       v
  DNS Proxy (seu PC, porta 53)
       |
       | responde: 192.168.x.x (seu IP local)
       v
  Free Fire faz HTTP pra 192.168.x.x:19134
       |
       v
  Servidor Node (live/login/main/tcp)
```

## Pre-requisitos

- Windows 10/11
- Node.js instalado (voce ja tem v24)
- BlueStacks 5 instalado
- APK do Free Fire 1.70.0 (o .xapk que ja esta na pasta do projeto)

## Passo a Passo

### 1. Subir o Servidor + DNS

**Opcao A (automatica):** Clique direito em `tools/start-with-dns.bat` -> "Executar como administrador"

**Opcao B (manual):**

Terminal 1 (servidor do jogo):
```
cd "C:\Users\Flavio\Downloads\Free Fire Server"
npm start
```

Terminal 2 (DNS proxy — como Admin):
```
cd "C:\Users\Flavio\Downloads\Free Fire Server"
node tools/dns-proxy.js
```

O DNS proxy vai mostrar seu IP local. Anote-o (ex: `192.168.1.50`).

### 2. Desabilitar Firewall temporariamente (ou criar regra)

O BlueStacks precisa alcançar as portas do servidor. Crie excecoes no Windows Firewall
para as portas: **53/UDP** (DNS), **19132-19134/TCP** (HTTP), **8084/TCP** (gateway).

Ou desative o firewall temporariamente:
```
netsh advfirewall set allprofiles state off
```
(Reative depois: `netsh advfirewall set allprofiles state on`)

### 3. Configurar DNS no BlueStacks

1. Abra o **BlueStacks 5**
2. Clique no icone de **engrenagem** (Configuracoes) no painel lateral
3. Va em **Rede**
4. Em "Configuracoes de DNS", marque **"Personalizado"**
5. DNS primario: **seu IP local** (o que o DNS proxy mostrou, ex: `192.168.1.50`)
6. DNS secundario: `8.8.8.8`
7. Clique em **Salvar**
8. **Reinicie o BlueStacks** (feche e abra de novo)

### 4. Instalar o Free Fire no BlueStacks

Opcao 1: Arraste o arquivo `.xapk` direto pra janela do BlueStacks
Opcao 2: Use o APK installer do BlueStacks e aponte pra:
```
C:\Users\Flavio\Downloads\Free Fire Server\Apk Free Fire 1.70.0\Free+Fire_+9th+Anniversary_1.70.0_APKPure.xapk
```

### 5. Abrir o Jogo

1. Abra o Free Fire no BlueStacks
2. Observe o terminal do DNS proxy — se dominos do FF aparecerem sendo interceptados, esta funcionando!
3. Observe o terminal do servidor — se requisicoes HTTP aparecerem, o cliente conectou!

## Troubleshooting

### "Falha no download" persiste
- Verifique se o DNS proxy esta rodando e interceptando (olhe o console)
- Verifique se o firewall nao esta bloqueando
- Tente pingar seu IP de dentro do BlueStacks (abra um terminal/app de rede)

### DNS proxy nao inicia (porta 53 em uso)
- O Windows pode ter o "Serviço Cliente DNS" usando a porta.
- Pare o servico: `net stop dnscache` (como admin)
- Ou use o Hyper-V: desative "Hyper-V" se nao usa (ele reserva a porta 53)

### O jogo conecta mas da erro de criptografia
- A build 1.70.0 pode usar uma chave AES diferente da que o servidor espera.
- Solucao: usar **Frida** pra interceptar em runtime e descobrir a chave real.
- Veja a secao "Descobrindo a chave AES com Frida" abaixo.

### O jogo nao chega nem no DNS
- Confirme que o BlueStacks reiniciou DEPOIS de mudar o DNS
- Alguns BlueStacks ignoram DNS custom — tente editar o hosts do Android:
  1. Ative root no BlueStacks (Configuracoes > Avancado > Modo root)
  2. Use um terminal (Root Explorer, ou adb shell)
  3. Edite `/system/etc/hosts` adicionando:
     ```
     192.168.1.50  ff-live-sea.ggblueshark.com
     192.168.1.50  clientbp.ggblueshark.com
     192.168.1.50  loginbp.ggblueshark.com
     192.168.1.50  dl.cdn.freefiremobile.com
     ```

## Descobrindo a chave AES com Frida (avancado)

Se o cliente conecta mas o servidor nao consegue decriptar as requisicoes, a chave
AES dessa build e diferente. Use Frida pra capturar:

1. Instale Frida no PC: `pip install frida-tools`
2. Baixe o frida-server arm64 e rode no emulador (com root)
3. Hook no Free Fire:
```js
// frida-hook-aes.js
Java.perform(function() {
  // Intercepta javax.crypto.Cipher.init
  var Cipher = Java.use('javax.crypto.Cipher');
  Cipher.init.overload('int', 'java.security.Key', 'java.security.spec.AlgorithmParameterSpec').implementation = function(mode, key, params) {
    var keyBytes = key.getEncoded();
    console.log('[AES] mode=' + mode + ' key=' + bytesToHex(keyBytes));
    if (params.$className.includes('IvParameterSpec')) {
      var iv = Java.cast(params, Java.use('javax.crypto.spec.IvParameterSpec'));
      console.log('[AES] IV=' + bytesToHex(iv.getIV()));
    }
    return this.init(mode, key, params);
  };
});

function bytesToHex(bytes) {
  var hex = [];
  for (var i = 0; i < bytes.length; i++) hex.push(('0' + (bytes[i] & 0xFF).toString(16)).slice(-2));
  return hex.join('');
}
```
4. Rode: `frida -U -f com.dts.freefireth -l frida-hook-aes.js`
5. A chave e IV vao aparecer no console. Atualize `src/protocol/aes.js` com os valores.

## Arquitetura

```
[BlueStacks]                    [Seu PC]
  Free Fire                       Servidor Node
     |                               |
     |-- DNS query ------------>  dns-proxy.js (porta 53)
     |<- IP do seu PC ---------      |
     |                               |
     |-- GET /live/ver.php ---->  live (porta 19134)
     |<- {server_url, cdn_url}       |
     |                               |
     |-- POST /MajorLogin ----->  login (porta 19132)
     |<- {token, account_id}         |
     |                               |
     |-- POST /GetLoginData --->  main (porta 19133)
     |<- {wallet, items, ...}        |
     |                               |
     |-- TCP connect ---------->  gateway (porta 8084)
     |<- push notifications          |
```
