import {createContext,useContext} from 'react';
import type {State,Section} from './types';
export interface Store {state:State;update:(fn:(s:State)=>State)=>void;notify:(message:string)=>void;go:(section:Section)=>void;openAction:(action:string)=>void}
export const HealthContext=createContext<Store|null>(null);
export function useHealth(){const value=useContext(HealthContext);if(!value)throw new Error('Missing health context');return value}
