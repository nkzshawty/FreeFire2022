'use strict';

/**
 * MATCHMAKING / GAMEOPENINGINFO  (GameOpeningInfoReq -> GameOpeningInfoRes)
 *
 * The client asks which game modes are currently open (right after connecting,
 * and when opening the mode-select screen).
 *
 * For FF 1.70 (OB32), only game_mode 15 (Clash Squad) with match_mode 6 is
 * confirmed to work without visual glitches on the mode selection screen.
 * Other game_mode values (1, 2, 3, 12) cause distortion because they don't
 * match the internal mode table of this client version.
 *
 * Training mode is triggered client-side based on newbie_choice in the login
 * request (newbie_choice: 3 = training selected during registration).
 *
 * game_mode_name_list / mode_level_limit_list / ranking_level_limit_list are
 * optional and omitted; the client does not require them.
 */

const { EProtocol, EMatchmaking } = require('../protocol');

// Currently open game modes for FF 1.70 (OB32).
// game_mode 15 (Clash Squad) is confirmed working without visual glitches, and
// game_mode 23 (Training, PVP_AlphaIsland_Training / config_id 7023) has now
// been added so the training button in the mode-select screen is clickable.
const OPEN_MODES = [
  { 
    map_id: 1, 
    game_mode: 15,      // Clash Squad (confirmed working in 1.70)
    match_mode: 6, 
    sort_id: 1, 
    start_time: "00:00",
    end_time: "23:59",
    is_new: false,
    is_live_open: true,
    config_start_time: "2020-01-01 00:00:00",
    config_end_time: "2030-12-31 23:59:59",
    weekday: "1;2;3;4;5;6;7",
    tips: "",
    language: "en",
    limited_count: 0,
    tag: 0,
    difficulty: "1",
    visual_map: ""
  },
  { 
    map_id: 7, 
    game_mode: 23,      // Training (PVP_AlphaIsland_Training, config_id 7023)
    match_mode: 5, 
    sort_id: 2, 
    start_time: "00:00",
    end_time: "23:59",
    is_new: false,
    is_live_open: true,
    config_start_time: "2020-01-01 00:00:00",
    config_end_time: "2030-12-31 23:59:59",
    weekday: "1;2;3;4;5;6;7",
    tips: "",
    language: "en",
    limited_count: 0,
    tag: 0,
    difficulty: "1",
    visual_map: ""
  }
];

function handler(reqObj, ctx) {
  ctx.logger.info(
    `[tcp] GameOpeningInfo region="${reqObj.region || ''}" lang="${reqObj.language || ''}" ` +
    `-> ${OPEN_MODES.length} open mode(s)`
  );
  return {
    opening_info_list: { gameOpeningInfos: OPEN_MODES },
    // server timezone offset (east of UTC) in seconds; only relevant to timed
    // events, of which we advertise none.
    timezone_offset_secs: -new Date().getTimezoneOffset() * 60
  };
}

module.exports = {
  protocol: EProtocol.MATCHMAKING,        // 3
  subcmd: EMatchmaking.GAMEOPENINGINFO,   // 7
  reqType: 'GameOpeningInfoReq',
  resType: 'GameOpeningInfoRes',
  handler
};
