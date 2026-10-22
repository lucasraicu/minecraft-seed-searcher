import {useEffect,useRef,useState} from 'react';
import {requestJson} from '../utils/network';

interface PublicState {
  ok:boolean;configured:boolean;state:string;consumed?:number;reason?:string|null;
  total_budget_seconds?:number;population_worlds?:number;retained_worlds?:number;
  queue?:{jobs:Record<string,number>;campaigns:Array<{id:string;state:string;scheduled_samples:number}>};
}

export function PublicHarvestStatus(){
  const [state,setState]=useState<PublicState|null>(null),[error,setError]=useState('');
  const [busy,setBusy]=useState(false);const generation=useRef(0),active=useRef(true),busyRef=useRef(false);
  const refresh=async(signal?:AbortSignal)=>{
    if(busyRef.current)return;
    const epoch=++generation.current;
    try{
      const {data}=await requestJson<PublicState>('/api/catalog/automation-status',{method:'GET',signal,timeoutMs:8000});
      if(!active.current||signal?.aborted||epoch!==generation.current)return;
      if(!data.ok||typeof data.configured!=='boolean'||typeof data.state!=='string')throw Error('Public worker status is unavailable.');
      setState(data);setError('');
    }catch(e){if(active.current&&!signal?.aborted&&epoch===generation.current)setError(e instanceof Error?e.message:String(e));}
  };
  useEffect(()=>{
    active.current=true;let controller=new AbortController();let timer:ReturnType<typeof setTimeout>;
    const poll=async()=>{await refresh(controller.signal);if(active.current)timer=setTimeout(()=>{controller=new AbortController();void poll();},3000);};
    void poll();return()=>{active.current=false;generation.current++;controller.abort();clearTimeout(timer);};
  },[]);
  const control=async(action:'pause'|'resume'|'allocate')=>{
    if(busyRef.current)return;busyRef.current=true;setBusy(true);generation.current++;
    try{
      const {data}=await requestJson<PublicState>('/api/catalog/automation-control',{method:'POST',body:{revision:'catalog-automation-control-v2',action},timeoutMs:8000});
      if(!active.current)return;
      if(!data.ok)throw Error('Public worker action was rejected.');
      setState(data);setError('');
    }catch(e){if(active.current)setError(e instanceof Error?e.message:String(e));}
    finally{busyRef.current=false;if(active.current)setBusy(false);}
  };
  const spent=state?.consumed||0,total=state?.total_budget_seconds||600;
  return <aside aria-label="Independent public harvesting" className="mx-auto my-3 w-full max-w-7xl rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs space-y-2">
    <h2 className="font-semibold text-emerald-300">Public harvesting · independent of personal search</h2>
    {error&&<p role="alert" className="text-amber-300">{error}</p>}
    {!state&&!error&&<p role="status">Loading public worker status…</p>}
    {state&&!state.configured&&<p className="text-slate-400">Public harvesting is not configured on this server. Personal search remains available.</p>}
    {state?.configured&&<>
      <p role="status">{state.state} · {state.population_worlds} evaluated worlds · {state.retained_worlds} retained worlds</p>
      <p>{Math.ceil(spent)} / {total} seconds of the current public compute budget used.</p>
      <progress aria-label="Public compute budget used" value={Math.min(spent,total)} max={total} className="w-full" />
      {state.queue&&<p>{Object.entries(state.queue.jobs??{}).map(([name,count])=>`${count} ${name}`).join(' · ')||'No public jobs queued.'}</p>}
      {state.reason&&<p className="text-amber-200">{state.reason}</p>}
      <div className="flex flex-wrap gap-3">
        {state.state==='active'?<button type="button" disabled={busy} onClick={()=>void control('pause')}>Pause public harvesting</button>:<>
          <button type="button" disabled={busy||spent>=total} onClick={()=>void control('resume')}>Resume with remaining budget</button>
          <button type="button" disabled={busy} onClick={()=>void control('allocate')}>Resume with a new 10-minute budget</button>
        </>}
      </div>
      <p className="text-slate-400">These controls affect the public worker. A running world drains to its checkpoint; the personal sweep has its own stop control.</p>
    </>}
  </aside>;
}
