/**
 * LangChain / AI SDK Tool Adapters for Minerals Oracle
 */

import { MineralsOracleClient } from './client.js';
import {
  TungstenVerifyInput,
  RareEarthsVerifyInput,
  NiobiumScandiumVerifyInput,
  CopperVerifyInput
} from './types.js';

export function createMineralsOracleTools(client: MineralsOracleClient = new MineralsOracleClient()) {
  return [
    {
      name: 'verify_tungsten_defense_origin',
      description: 'Audits Western Tungsten / APT origin (Almonty Sangdong / Bakuta) against US NDAA Sec 848 defense procurement standards (WO3 >= 88.5%).',
      execute: async (args: TungstenVerifyInput) => client.verifyTungsten(args)
    },
    {
      name: 'verify_rare_earths_magnet_origin',
      description: 'Audits Allied Rare Earths NdPr (Sarfartoq / Silmet) for NdFeB magnets, screening against China MOFCOM 0.1% extraterritorial export control rules.',
      execute: async (args: RareEarthsVerifyInput) => client.verifyRareEarths(args)
    },
    {
      name: 'verify_niobium_scandium_defense_origin',
      description: 'Audits NioCorp Elk Creek Ferroniobium (ASTM A550) & Scandium Oxide (Sc2O3 >= 99.5%) for aerospace superalloys and US DOE/EXIM loan qualification.',
      execute: async (args: NiobiumScandiumVerifyInput) => client.verifyNiobiumScandium(args)
    },
    {
      name: 'verify_copper_hvdc_origin',
      description: 'Audits Chilean/Peruvian Copper Cathodes for AI datacenter HVDC cables, ASTM B115 Grade 1 electrolytic purity, and COCHILCO quotas.',
      execute: async (args: CopperVerifyInput) => client.verifyCopper(args)
    }
  ];
}
