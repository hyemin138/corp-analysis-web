export type Row = Record<string, any>;
export interface MarketData {
  routes: Row[]; china: Row[]; features: Row[]; states: Row[]; runs: Row[];
  transitions: Row[]; transit: Row[]; predictions: Row[]; metrics: Row[];
  targets: Row[]; thresholds: Row; meta: Row;
}
export interface MarketDataProvider { load(signal?: AbortSignal): Promise<MarketData> }
export class LocalSnapshotProvider implements MarketDataProvider {
  constructor(private readonly url = `${import.meta.env.BASE_URL}data/market.json`) {}
  async load(signal?: AbortSignal): Promise<MarketData> {
    const response = await fetch(this.url, { signal });
    if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) throw new Error('팀 내부 연구 스냅샷을 먼저 가져오세요. C_DASHBOARD_README.md의 data:import 명령을 확인하세요. 공개 저장소에는 재배포 권한이 확인되지 않은 원자료를 포함하지 않습니다.');
    let data: MarketData;
    try { data = await response.json(); } catch { throw new Error('자료 파일의 JSON 형식이 손상되었습니다. 내부 스냅샷을 다시 가져오세요.'); }
    const arrays=['routes','china','features','states','runs','transitions','transit','predictions','metrics','targets'] as const;
    if (!data || data.meta?.schemaVersion !== 'c-market-desk/1.0' || data.states?.length !== 201 || !arrays.every(key=>Array.isArray(data[key])&&data[key].length>0) || !data.predictions.some(x=>x.actual_available===true&&x.target==='EUMED_H28')) throw new Error('지원하지 않는 데이터 형식입니다. C_V2_DATA_API_REQUIREMENTS.md를 확인하세요.');
    return data;
  }
}
// Replace this factory with your API adapter; pages depend only on MarketDataProvider.
export const createDataProvider = (): MarketDataProvider => new LocalSnapshotProvider();
