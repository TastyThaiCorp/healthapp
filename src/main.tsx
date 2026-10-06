import '@fontsource/dm-sans/latin-400.css';
import '@fontsource/dm-sans/latin-500.css';
import '@fontsource/dm-sans/latin-600.css';
import '@fontsource/dm-sans/latin-700.css';
import '@fontsource/cormorant-garamond/latin-400.css';
import '@fontsource/cormorant-garamond/latin-300-italic.css';
import '@fontsource/cormorant-garamond/latin-400-italic.css';
import React,{Component,type ReactNode} from 'react';import {createRoot} from 'react-dom/client';import App from './App';import './style.css';
class Boundary extends Component<{children:ReactNode},{error:boolean}>{state={error:false};static getDerivedStateFromError(){return {error:true}}render(){return this.state.error?<main className="fatal-error"><h1>Let’s take a small pause.</h1><p>HealthUp couldn’t display this view. Your saved local history remains on this device.</p><button className="button" onClick={()=>{location.hash='today';location.reload()}}>Return to today</button></main>:this.props.children}}
document.documentElement.style.setProperty('--nature-atlas',`url("${import.meta.env.BASE_URL}assets/natural-atlas.png")`);
createRoot(document.getElementById('root')!).render(<Boundary><App/></Boundary>);
