// Civil observation dates are positioned at UTC midnight only for plotting.
// This is not a claim about the actual publication hour.
export const plotTime=(date:string)=>Date.parse(date+'T00:00:00Z');
export const plotDate=(timestamp:number)=>new Date(timestamp).toISOString().slice(0,10);
export function nearestObservation(times:number[],timestamp:number){
 if(!times.length)return null;
 return times.reduce((a,b)=>Math.abs(a-timestamp)<=Math.abs(b-timestamp)?a:b);
}
