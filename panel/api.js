/* Transporte y lectura de resultados Python. No contiene ecuaciones térmicas. */
(function(root){'use strict';
async function json(url,options={}){const r=await fetch(url,{cache:'no-store',...options});let data;try{data=await r.json();}catch(_){throw Error('No hay una API Python en esta dirección. Inicia servidor_therma.py y abre http://127.0.0.1:8767/.');}if(!r.ok)throw Error(data.message||`Error HTTP ${r.status}`);return data;}
function adaptar(meta,buffer,activeBuffer=null){
 if(!['1.0','1.1'].includes(meta.schema_version)||meta.fields.dtype!=='float32'||meta.fields.byte_order!=='little')throw Error('Contrato de resultados incompatible.');
 const [frames,cells]=meta.fields.shape,n=meta.geometry.shape_xyz;
 if(buffer.byteLength!==frames*cells*4||n.reduce((a,b)=>a*b,1)!==cells||meta.fields.times_s.length!==frames)throw Error('Dimensiones del campo binario inconsistentes.');
 const little=new Uint8Array(new Uint32Array([1]).buffer)[0]===1;
 let data;if(little)data=new Float32Array(buffer);else{data=new Float32Array(frames*cells);const view=new DataView(buffer);for(let i=0;i<data.length;i++)data[i]=view.getFloat32(4*i,true);}
 let activeFrames;
 if(meta.geometry.active_static===false){if(!activeBuffer||activeBuffer.byteLength!==frames*cells||meta.activation?.dtype!=='uint8'||JSON.stringify(meta.activation.shape)!==JSON.stringify([frames,cells]))throw Error('Máscara dinámica ausente o incompatible.');const a=new Uint8Array(activeBuffer);activeFrames=Array.from({length:frames},(_,i)=>a.subarray(i*cells,(i+1)*cells));}
 const m=meta.metrics;
 return {...m,activeFrames,config:meta.config,n,L:meta.geometry.lengths_m,dx:meta.geometry.spacing_m,
   alpha:m.alpha??NaN,dt:m.dt??NaN,dtMax:m.dtMax??NaN,residual:m.residual??NaN,steps:m.steps??Math.max(0,meta.history.length-1),
   history:meta.history.map(h=>({...h,energy:h.energy??NaN,net:h.net??NaN,residual:h.residual??NaN})),
   fields:Array.from({length:frames},(_,i)=>data.subarray(i*cells,(i+1)*cells)),frameTimes:meta.fields.times_s,
   metadata:meta,simulationId:meta.simulation_id,engine:meta.engine,
   label:meta.provenance.mode,metadataUrl:`/api/results/${meta.simulation_id}/metadata.json`};
}
class Backend{
 constructor(example=false){this.example=example;this.stopped=false;this.done=false;this.job=null;}
 async postMessage(p){try{
  if(location.protocol==='file:')throw Error('El modo Python requiere el servidor local: ejecuta servidor_therma.py y abre http://127.0.0.1:8767/.');
  const health=await json('/api/health');if(health.engine!=='termico_cartesiano.py')throw Error('Servidor Python incompatible.');if(this.stopped)return;
  const job=await json(this.example?'/api/examples/3d':'/api/simulations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});this.job=job.simulation_id;
  while(!this.stopped){const s=await json(job.status_url);if(s.status==='FAILED')throw Error(s.message||'Python no pudo ejecutar el cálculo.');
   if(s.status==='COMPLETED'){
    const meta=await json(s.metadata_url),url=`/api/results/${job.simulation_id}/fields.bin`,response=await fetch(url,{cache:'no-store'});if(!response.ok)throw Error('No se pudo leer el campo Python.');const buffer=await response.arrayBuffer();
    if(root.crypto?.subtle){const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',buffer))).map(b=>b.toString(16).padStart(2,'0')).join('');if(hash!==meta.fields.sha256)throw Error('El campo descargado no coincide con su huella SHA-256.');}
    let activeBuffer=null;if(meta.geometry.active_static===false){const response=await fetch(`/api/results/${job.simulation_id}/active.bin`,{cache:'no-store'});if(!response.ok)throw Error('No se pudo leer la actividad constructiva.');activeBuffer=await response.arrayBuffer();if(root.crypto?.subtle){const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',activeBuffer))).map(b=>b.toString(16).padStart(2,'0')).join('');if(hash!==meta.activation.sha256)throw Error('Máscara de actividad con SHA-256 incorrecto.');}}
    const result=adaptar(meta,buffer,activeBuffer);this.done=true;if(!this.stopped)this.onmessage?.({data:{type:'result',result}});return;
   }
   this.onmessage?.({data:{type:'progress',value:s.progress||0}});await new Promise(resolve=>setTimeout(resolve,250));
  }
 }catch(e){if(!this.stopped)this.onmessage?.({data:{type:'error',message:e instanceof TypeError?'No se pudo contactar al servidor Python. Inicia servidor_therma.py y abre http://127.0.0.1:8767/.':e.message}});}}
 terminate(){this.stopped=true;/* El trabajo Python puede terminar y conservar sus archivos. */}
}
root.ThermaBackend=Backend;root.ThermaContract={adaptar};
})(window);
