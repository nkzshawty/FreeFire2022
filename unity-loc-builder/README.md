# FF Localization Bundle Builder

## Como usar:

1. Abra o Unity Hub
2. Clique em "Projetos" > "Abrir" (ou Add)
3. Selecione esta pasta: unity-loc-builder
4. Aguarde o Unity abrir e importar os assets
5. No menu do Unity, clique: FF Tools > Build Localization Bundle
6. Pronto! O bundle sera criado e copiado automaticamente para o servidor

## O que faz:

- Pega o arquivo loc_en.xml (com as strings de texto do jogo)
- Empacota como AssetBundle no formato Unity 2018.4.11f1
- Copia o resultado para static/ABHotUpdates/.../gameassetbundles/

## Depois de buildar:

- Reinicie o servidor (npm start)
- Abra o jogo no emulador
- Os textos devem aparecer em ingles
