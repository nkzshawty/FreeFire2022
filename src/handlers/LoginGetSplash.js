/**
 * LoginGetSplash  (CSAnnouncementReq -> LoginSplashRes)  [public handshake]
 *
 * Ported from ported_6.js (handleLoginGetSplash). reference: login_get_splash @
 * htpp.py:2531 -> build_login_splash_protobuf @ htpp.py:2423. Returns a single
 * announcement, a single splash banner and a few activity-info entries.
 */

'use strict';

const { nowSecs } = require('./_shared');

function handleLoginGetSplash(reqObj, ctx) {
  const t = nowSecs();
  ctx.logger.info('[ported_6] LoginGetSplash');
  return {
    accouncement_res: {
      announcements: [
        {
          language: 'pt-BR',
          order_in_this_language: 1,
          title: 'Bem-vindo!',
          image_url: 'http://154.30.4.183:19134/live/ABHotUpdates/banner-assets/room222.png',
          fb_page_id: '',
          image_url_for_lobby: 'http://154.30.4.183:19134/live/ABHotUpdates/banner-assets/room222.png',
          link_url: 'https://discord.gg/room222',
          desc: 'The Remake Of 2022',
          start_time: t - 86400 * 30,
          end_time: t + 86400 * 30,
          region: 'BR',
          id: 0,
          use_embedded_browser: true
        }
      ]
    },
    splash_res: {
      splashBanners: [
        {
          region: 'BR',
          language: 'pt-BR',
          id: 1,
          name: 'Banner Principal',
          sort_id: 1,
          start_time: t - 86400 * 30,
          end_time: t + 86400 * 30,
          image_url: 'http://154.30.4.183:19134/live/ABHotUpdates/banner-assets/room222.png',
          gos_pos: 1,
          gos_url: 'https://example.com',
          use_embedded_browser: true,
          sub_go_pos: '',
          video_url: '',
          bg_img_url: 'http://154.30.4.183:19134/live/ABHotUpdates/banner-assets/room222.png',
          type: 0,
          platform: 0,
          weight: 1,
          country_code: 'BR',
          using_version: 0,
          active_phone_quality: 0,
          id_last_num: ''
        }
      ]
    },
    activity_info_res: {
      activitys: [
        { id: 1, data: 100, state: 1 },
        { id: 2, data: 200, state: 2 },
        { id: 3, data: 300, state: 3 }
      ]
    }
  };
}

module.exports = {
  endpoint: 'LoginGetSplash',
  reqType: 'CSAnnouncementReq',
  resType: 'LoginSplashRes',
  handler: handleLoginGetSplash
};
