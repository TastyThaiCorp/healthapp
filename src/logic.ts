import type {State,Category,CalendarEvent,Recipe,Ingredient,WeightEntry} from './types';
export const dateKey=(date=new Date())=>`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
export const shiftDate=(date:string,days:number)=>{const d=new Date(`${date}T12:00:00`);d.setDate(d.getDate()+days);return dateKey(d)};
export const uid=()=>crypto.randomUUID();
export const categories:Category[]=['nutrition','hydration','movement','mindfulness','sleep','selfcare'];
export const defaultState=():State=>({profile:{name:'',start:dateKey(),onboarded:false},preferences:{categories:[...categories],weightEnabled:false,units:'metric',waterTarget:2000,wake:'07:00',sleep:'22:00',reminderMinutes:120,goalKg:null,mealTarget:3,supportRegion:'US',playEnabled:true},hydration:[],weight_entries:[],moods:[],completed_tasks:[],favorites:[],calendar_events:[],journey:{mode:'guided',completed:[],selected:1},notification_preferences:{enabled:false},intentions:{},reflections:{},meals:[],timer:null});
export const waterTotal=(state:State,date=dateKey())=>state.hydration.filter(x=>x.date===date).reduce((sum,x)=>sum+x.ml,0);
export function balance(state:State,date=dateKey()){const selected=state.preferences.categories;if(!selected.length)return 0;return Math.round(selected.reduce((sum,category)=>sum+(category==='hydration'?Math.min(1,waterTotal(state,date)/state.preferences.waterTarget):category==='nutrition'?Math.min(1,state.meals.filter(m=>m.date===date).length/(state.preferences.mealTarget||3)):state.completed_tasks.some(t=>t.date===date&&t.category===category)?1:0),0)/selected.length*100)}
export function occurs(event:CalendarEvent,date:string){if(event.excluded.includes(date)||date<event.date)return false;if(event.repeat==='none')return date===event.date;if(event.repeat==='daily')return true;return new Date(`${event.date}T12:00:00`).getDay()===new Date(`${date}T12:00:00`).getDay()}
export function eventsOn(events:CalendarEvent[],date:string){return events.filter(e=>occurs(e,date)).sort((a,b)=>a.time.localeCompare(b.time))}
export function nutrition(recipe:Recipe,ingredients:Record<string,Ingredient>,swaps:Record<string,string>={}){const sums={kcal:0,protein:0,carbs:0,fat:0,fiber:0};recipe.ingredients.forEach(item=>{const data=ingredients[swaps[item.id]||item.id];if(data)for(const key of Object.keys(sums) as (keyof typeof sums)[])sums[key]+=data[key]*item.grams/100/recipe.servings});return Object.fromEntries(Object.entries(sums).map(([key,value])=>[key,Math.round(value)])) as typeof sums}
export function weightTrend(entries:WeightEntry[]){const sorted=[...entries].sort((a,b)=>a.date.localeCompare(b.date));return sorted.map((entry,i)=>({date:entry.date,value:sorted.slice(Math.max(0,i-6),i+1).reduce((sum,x)=>sum+x.kg,0)/Math.min(i+1,7)}))}
export function hydrationSlots(wake:string,sleep:string,minutes:number){const toMinutes=(s:string)=>{const [h,m]=s.split(':').map(Number);return h*60+m};const start=toMinutes(wake);let end=toMinutes(sleep);if(end<=start)end+=1440;const slots=[];for(let m=start+minutes;m<end;m+=Math.max(30,minutes))slots.push(`${String(Math.floor(m/60)%24).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`);return slots}
export const remainingSeconds=(endsAt:number,now=Date.now())=>Math.max(0,Math.ceil((endsAt-now)/1000));
export function exportState(state:State){return JSON.stringify({product:'HealthUp',version:1,state},null,2)}
export function validateImport(value:unknown):State {
  const data=value as {product?:string;version?:number;state?:State};
  if(data.product!=='HealthUp'||data.version!==1||!data.state||typeof data.state!=='object')throw new Error('Choose a HealthUp data export.');
  const incoming=data.state;
  for(const key of ['hydration','weight_entries','moods','completed_tasks','favorites','calendar_events','meals'] as const)if(!Array.isArray(incoming[key]))throw new Error('The backup is missing a collection.');
  if(typeof incoming.profile?.name!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(incoming.profile?.start)||!Array.isArray(incoming.journey?.completed)||!Array.isArray(incoming.preferences?.categories))throw new Error('The backup contains invalid preferences.');
  if(!incoming.preferences.categories.every(c=>categories.includes(c))||!Number.isFinite(incoming.preferences.waterTarget)||incoming.preferences.waterTarget<100||incoming.preferences.waterTarget>10000)throw new Error('The backup contains invalid targets.');
  if(incoming.hydration.some(x=>!Number.isFinite(x.ml)||x.ml<0)||incoming.weight_entries.some(x=>!Number.isFinite(x.kg)||x.kg<=0)||incoming.moods.some(x=>!Number.isInteger(x.mood)||x.mood<0||x.mood>4))throw new Error('The backup contains invalid log values.');
  if(incoming.calendar_events.some(x=>typeof x.id!=='string'||typeof x.title!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(x.date)||!/^\d{2}:\d{2}$/.test(x.time)||!['none','daily','weekly'].includes(x.repeat)||!Array.isArray(x.completed)||!Array.isArray(x.excluded)))throw new Error('The backup contains invalid calendar events.');
  const base=defaultState();return {...base,...incoming,preferences:{...base.preferences,...incoming.preferences}};
}
