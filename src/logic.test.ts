import {describe,it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {defaultState,balance,waterTotal,occurs,eventsOn,nutrition,weightTrend,hydrationSlots,remainingSeconds,exportState,validateImport,shiftDate} from './logic';
import {journey,affirmations,guides} from './content';
import type {CalendarEvent} from './types';
const data=JSON.parse(readFileSync(new URL('../public/recipes.json',import.meta.url),'utf8'));
describe('bundled wellness content',()=>{
 it('contains 100 unique complete recipes with known ingredients',()=>{expect(data.recipes).toHaveLength(100);expect(new Set(data.recipes.map((r:any)=>r.name)).size).toBe(100);for(const recipe of data.recipes){expect(recipe.instructions.length).toBeGreaterThanOrEqual(3);expect(recipe.ingredients.length).toBeGreaterThanOrEqual(3);expect(recipe.servings).toBeGreaterThan(0);for(const ingredient of recipe.ingredients)expect(data.ingredients[ingredient.id]).toBeTruthy()}});
 it('contains 100 open journey days, 70 affirmations and 8 source-linked guides',()=>{expect(journey).toHaveLength(100);expect(affirmations).toHaveLength(70);expect(guides).toHaveLength(8);expect(journey.at(-1)?.day).toBe(100)});
 it('recalculates nutrition for a known equal-weight ingredient substitution',()=>{const recipe=data.recipes[0];const original=nutrition(recipe,data.ingredients);const swapped=nutrition(recipe,data.ingredients,{yogurt:'cottage'});expect(swapped.kcal).toBeGreaterThan(original.kcal);expect(swapped.fat).toBeGreaterThan(original.fat)});
});
describe('personal logging',()=>{
 it('logs water by local date and caps balance credit',()=>{const s=defaultState();s.preferences.categories=['hydration'];s.hydration=[{id:'a',date:'2026-10-06',ml:3000},{id:'b',date:'2026-10-05',ml:200}];expect(waterTotal(s,'2026-10-06')).toBe(3000);expect(balance(s,'2026-10-06')).toBe(100)});
 it('honors optional categories and personalized meal targets',()=>{const s=defaultState();s.preferences.categories=['nutrition','movement'];s.preferences.mealTarget=2;s.meals=[{id:'a',date:'2026-10-06',name:'Lunch'}];expect(balance(s,'2026-10-06')).toBe(25);s.completed_tasks=[{id:'b',date:'2026-10-06',category:'movement',label:'walk'}];expect(balance(s,'2026-10-06')).toBe(75);s.preferences.categories=[];expect(balance(s)).toBe(0)});
 it('smooths measurement history rather than reacting to one number',()=>{expect(weightTrend([{id:'a',date:'2026-10-01',kg:80},{id:'b',date:'2026-10-02',kg:82}])[1].value).toBe(81)});
 it('exports and imports core personal history',()=>{const s=defaultState();s.profile.name='Alex';expect(validateImport(JSON.parse(exportState(s))).profile.name).toBe('Alex');expect(()=>validateImport({product:'other'})).toThrow()});
});
describe('calendar and reminders',()=>{
 const event:CalendarEvent={id:'a',title:'Walk',type:'Movement',date:'2026-10-06',time:'12:00',duration:10,repeat:'weekly',completed:[],excluded:[]};
 it('handles weekly repeats, start boundaries and deleted occurrences',()=>{expect(occurs(event,'2026-10-13')).toBe(true);expect(occurs(event,'2026-10-12')).toBe(false);expect(occurs(event,'2026-09-29')).toBe(false);expect(occurs({...event,excluded:['2026-10-13']},'2026-10-13')).toBe(false)});
 it('orders events by scheduled time',()=>{expect(eventsOn([event,{...event,id:'b',time:'09:00'}],'2026-10-06')[0].id).toBe('b')});
 it('distributes reminders between wake and sleep including overnight windows',()=>{expect(hydrationSlots('07:00','22:00',120)).toEqual(['09:00','11:00','13:00','15:00','17:00','19:00','21:00']);expect(hydrationSlots('22:00','06:00',120)).toEqual(['00:00','02:00','04:00'])});
 it('uses wall-clock end times and never returns negative timer values',()=>{expect(remainingSeconds(61000,1000)).toBe(60);expect(remainingSeconds(61000,60001)).toBe(1);expect(remainingSeconds(61000,99000)).toBe(0)});
 it('shifts calendar days across a month boundary',()=>expect(shiftDate('2026-10-31',1)).toBe('2026-11-01'));
});
