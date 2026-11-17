(() => {
  'use strict';
  const $=id=>document.getElementById(id), D=window.ThermaViewData;
  const catalog=JSON.parse($('dashData').textContent);
  const colors=['#61d8c3','#ffb474','#c1adff','#f079a1','#77baff'];
  const fmt=(v,n=2)=>Number.isFinite(v)?v.toLocaleString('es-CL',{maximumFractionDigits:n}):'—';
  const node=(tag,text)=>Object.assign(document.createElement(tag),{textContent:text});
  let r,frame,tab='section',stats,probe,layers,models=[],hit;
  const overview=document.createElement('section');
  overview.className='panel run-dashboard';overview.hidden=true;
  $('resultViewerSlot').before(overview);
  overview.append($('runDashboard').querySelector('h2'),$('dashIdentity'),$('dashCards'));
  $('simulationGuide').open=false;
  const iceDrawer=document.createElement('details');
  iceDrawer.className='panel workflow-details';iceDrawer.append(node('summary','Ensayo separado · comparación de la mezcla con y sin hielo'));
  $('resultsPage').append(iceDrawer);iceDrawer.append($('iceResults'));iceDrawer.hidden=$('iceResults').hidden;
  new MutationObserver(()=>{iceDrawer.hidden=$('iceResults').hidden;}).observe($('iceResults'),{attributes:true,attributeFilter:['hidden']});
  $('iceCompareLink').addEventListener('click',()=>{iceDrawer.open=true;$('iceResults').scrollIntoView();});
  const dataAt=(i,f)=>i>=0 && D.active(r,i,f) && Number.isFinite(r.fields[f][i])?r.fields[f][i]:null;
  function prepare() {
    const [nx,ny,nz]=r.n,x=Math.floor(nx/2),y=Math.floor(ny/2),z=Math.floor(nz/2);
    probe={center:D.index(x,y,z,r.n),top:-1,side:-1};
    layers=new Map();
    r.config.mask.forEach((id,i)=>{
      if(!id)return;
      const [a,b,c]=D.ijk(i,r.n);
      if(a===x&&b===y)probe.top=i;
      if(b===y&&c===z)probe.side=i;
      const layer=layers.get(id)||{count:0,min:c,max:c};
      layer.count++;layer.max=Math.max(layer.max,c);layer.min=Math.min(layer.min,c);layers.set(id,layer);
    });
    stats=r.fields.map((field,f)=>{
      let sum=0,count=0,max=-Infinity,hot=-1;
      for(let i=0;i<field.length;i++)if(dataAt(i,f)!==null){
        count++;sum+=field[i];if(field[i]>max){max=field[i];hot=i;}
      }
      return {hot,max:count?max:null,mean:count?sum/count:null};
    });
    resetSlice();models=[];
  }
  const planeAxes=()=>({XZ:[0,2,1],YZ:[1,2,0],XY:[0,1,2]})[$('dashPlane').value];
  function resetSlice(){const a=planeAxes()[2];$('dashSlice').max=r.n[a]-1;$('dashSlice').value=Math.floor(r.n[a]/2);}
  function map() {
    const [a,b,normal]=planeAxes(),slice=Number($('dashSlice').value),canvas=$('dashMap'),g=canvas.getContext('2d');
    const w=Math.max(320,canvas.clientWidth),h=260,dpr=Math.min(devicePixelRatio,2);
    canvas.width=w*dpr;canvas.height=h*dpr;g.scale(dpr,dpr);
    const unit=Math.min((w-100)/r.L[a],(h-80)/r.L[b]),dx=r.dx[a]*unit,dy=r.dx[b]*unit;
    const left=(w-r.n[a]*dx)/2,bottom=27+(h-80+r.n[b]*dy)/2;
    const o=r.metadata.geometry.origin_m,soil=r.metadata.environment?.soil;
    hit={a,b,normal,slice,left,bottom,dx,dy,w,h};
    const cell=[0,0,0];cell[normal]=slice;
    for(let j=0;j<r.n[b];j++)for(let i=0;i<r.n[a];i++){
      cell[a]=i;cell[b]=j;const ix=D.index(...cell,r.n),v=dataAt(ix,frame);
      if(v===null)continue;
      g.fillStyle='rgb('+D.color(v,0,80).map(k=>Math.round(k*255)).join(',')+')';
      g.fillRect(left+i*dx,bottom-(j+1)*dy,dx+.15,dy+.15);
      if(ix===stats[frame].hot){g.strokeStyle='#fff';g.strokeRect(left+i*dx,bottom-(j+1)*dy,dx,dy);}
      if(b===2&&j===0&&soil&&$('dashSoil').checked){g.fillStyle='#b99566';g.fillRect(left+i*dx,bottom+1,dx+.1,3);}
    }
    g.fillStyle='#c2d2df';g.font='12px Segoe UI';
    g.fillText('XYZ'[a]+'  '+fmt(o[a])+' → '+fmt(o[a]+r.L[a])+' m',left,bottom+22);
    g.fillText('XYZ'[b]+'  '+fmt(o[b])+' → '+fmt(o[b]+r.L[b])+' m',left,16);
    $('dashSliceNote').textContent='Plano '+$('dashPlane').value+' · '+'XYZ'[normal]+' = '+fmt(o[normal]+(slice+.5)*r.dx[normal])+' m · día '+fmt(r.frameTimes[frame]/86400)+
      ' · escala fija 0–80 °C'+(soil&&b===2&&$('dashSoil').checked?' · trazo ocre: contacto basal a '+fmt(soil.temperature_C)+' °C':'');
    $('dashPick').textContent='Mueve el cursor sobre una celda para leer sus coordenadas y temperatura.';
    const body=$('dashPours');body.replaceChildren();
    for(const [id,l] of layers){
      const p=r.config.construction?.pours.find(v=>v.id===id),st=r.metadata.construction?.snapshots[frame]?.active_pour_ids;
      const row=body.insertRow();
      for(const text of ['V'+id,fmt(o[2]+l.min*r.dx[2])+' – '+fmt(o[2]+(l.max+1)*r.dx[2]),fmt(l.count,0),fmt(l.count*r.dx.reduce((u,v)=>u*v,1)),fmt(p?.start_h),!st||st.includes(id)?'Activa':'Por colocar'])row.insertCell().textContent=text;
    }
  }
  $('dashMap').onpointermove=e=>{
    if(!hit)return;
    const {a,b,normal,slice,left,bottom,dx,dy,w,h}=hit,rect=e.target.getBoundingClientRect();
    const cell=[0,0,0];cell[normal]=slice;cell[a]=Math.floor(((e.clientX-rect.left)*w/rect.width-left)/dx);cell[b]=Math.floor((bottom-(e.clientY-rect.top)*h/rect.height)/dy);
    const i=D.index(...cell,r.n);
    $('dashPick').textContent=cell.every((v,k)=>v>=0&&v<r.n[k])&&dataAt(i,frame)!==null?'V'+r.config.mask[i]+' · XYZ ('+D.xyz(r,i).map(v=>fmt(v)).join('; ')+') m · '+fmt(r.fields[frame][i])+' °C':'Sin hormigón activo en este punto.';
  };
  function chart(title,unit,series,isTime=true,reference=null){
    const box=node('section',''),legend=node('p',''),cv=document.createElement('canvas');
    if(!isTime)box.dataset.profile='true';
    box.append(node('h3',title),legend,cv);$('dashCharts').append(box);
    const valid=series.filter(s=>s.points.some(p=>Number.isFinite(p[1])));
    if(!valid.length){legend.textContent='Serie ausente en esta corrida.';cv.hidden=true;return;}
    valid.forEach((s,i)=>{const label=node('span','━ '+s.name+'  ');label.style.color=colors[i%colors.length];legend.append(label);});
    let xmin=Infinity,xmax=-Infinity,ymin=Infinity,ymax=-Infinity;
    for(const s of valid)for(const [x,y] of s.points)if(Number.isFinite(y)){xmin=Math.min(xmin,x);xmax=Math.max(xmax,x);ymin=Math.min(ymin,y);ymax=Math.max(ymax,y);}
    if(isTime){xmin=0;xmax=r.frameTimes.at(-1)/86400;}
    if(reference!==null)ymax=Math.max(ymax,reference);
    ymin=Math.floor(ymin);ymax=Math.max(ymin+1,Math.ceil(ymax));
    const w=560,h=204,L=48,R=540,T=21,B=164,X=x=>L+(x-xmin)/(xmax-xmin||1)*(R-L),Y=y=>B-(y-ymin)/(ymax-ymin)*(B-T);
    cv.width=w*2;cv.height=h*2;cv.setAttribute('aria-label',title);const g=cv.getContext('2d');g.scale(2,2);g.font='12px Segoe UI';
    for(let j=0;j<5;j++){const y=ymin+(ymax-ymin)*j/4;g.strokeStyle='#304454';g.beginPath();g.moveTo(L,Y(y));g.lineTo(R,Y(y));g.stroke();g.fillStyle='#c0cdd5';g.fillText(fmt(y,1),3,Y(y)+4);g.fillText(fmt(xmin+(xmax-xmin)*j/4,2),L+(R-L)*j/4-8,B+17);}
    g.fillText(unit,3,13);g.fillText(isTime?'Tiempo [días]':'Altura Z [m]',235,200);
    valid.forEach((s,j)=>{g.beginPath();let pen=false;g.strokeStyle=colors[j%colors.length];g.lineWidth=s.current?3:1.8;for(const [x,y] of s.points){if(!Number.isFinite(y)){pen=false;continue;}if(pen)g.lineTo(X(x),Y(y));else g.moveTo(X(x),Y(y));pen=true;}g.stroke();});
    if(reference!==null){g.setLineDash([4,4]);g.strokeStyle='#eeba83';g.beginPath();g.moveTo(L,Y(reference));g.lineTo(R,Y(reference));g.stroke();g.setLineDash([]);legend.append(node('span',' ┄ Límite '+reference+' °C'));}
    if(isTime){
      const cursor=node('i','');const shell=node('div','');shell.className='dash-chart-shell';cv.before(shell);shell.append(cv,cursor);
      models.push(()=>{cursor.style.left=(100*X(r.frameTimes[frame]/86400)/w)+'%';});
      cv.onclick=e=>{const box=cv.getBoundingClientRect(),u=((e.clientX-box.left)*w/box.width-L)/(R-L);window.therma.setFrame(D.nearest(r.frameTimes,Math.max(0,Math.min(1,u))*r.frameTimes.at(-1)));};
    }
  }
  function profile(){
    $('dashCharts').querySelector('[data-profile]')?.remove();
    const targets=[0,.25,.5,.75,1].map(frac=>D.nearest(r.frameTimes,r.frameTimes.at(-1)*frac));
    const [x,y]=D.ijk(probe.center,r.n);
    chart('Perfil vertical por la columna central','°C',[...new Set([...targets,frame])].map(f=>({current:f===frame,name:'Día '+fmt(r.frameTimes[f]/86400,1)+(f===frame?' · actual':''),points:Array.from({length:r.n[2]},(_,k)=>{const i=D.index(x,y,k,r.n);return [D.xyz(r,i)[2],dataAt(i,f)];})})),false);
  }
  function charts() {
    models=[];$('dashCharts').replaceChildren();
    const snapshots=(name,fn)=>({name,points:r.frameTimes.map((t,f)=>[t/86400,fn(f)])});
    const history=(name,key)=>({name,points:r.history.map(h=>[h.t/86400,h[key]])});
    if(tab==='temperature'){
      chart('Núcleo, exterior y aire','°C',[snapshots('Sonda central',f=>dataAt(probe.center,f)),snapshots('Voxel superior',f=>dataAt(probe.top,f)),snapshots('Voxel lateral',f=>dataAt(probe.side,f)),history('Máxima activa','max'),history('Aire','air_temperature_C')],true,70);
      $('dashCharts').append(node('p','Las tres sondas son centros fijos de voxel. Las sondas exteriores empiezan a registrar al colocarse su vertida. S25 se consulta en el gráfico de control a 25 mm.'));
      profile();
    }else if(tab==='generation'){
      chart('Calor de hidratación por vertida','W/m³',[...layers.keys()].map(id=>snapshots('V'+id,f=>{const p=r.metadata.construction?.snapshots[f].pours.find(p=>p.id===id);return p?.active?p.source_W_m3:null;})));
      chart('Generación media del hormigón activo','W/m³',[history('Media volumétrica','q')]);
    }else if(tab==='climate'){
      chart('Temperatura del aire aplicada','°C',[history('Aire','air_temperature_C')]);
      chart('Intercambio con el terreno','W',[history('Potencia hacia el hormigón','soil_into_concrete_W')]);
      const cfg=r.config.weather,snapshot=cfg?.provenance?.snapshot||cfg?.provenance;
      const raw=catalog.weather[snapshot?.raw_sha256],start=Date.parse(cfg?.start_utc)/1000;
      for(const [key,title,unit] of [['wind_speed_10m','Viento a 10 m','m/s'],['shortwave_radiation','Radiación de onda corta','W/m²']]){
        const points=raw?.[key]?.map((v,i)=>[(raw.time[i]-start)/86400,v]).filter(([day])=>day>=0&&day<=r.frameTimes.at(-1)/86400)||[];
        chart(title,unit,[{name:'Pronóstico archivado · contexto',points}]);
      }
      $('dashCharts').append(node('p','El solver utiliza la temperatura del aire y la condición basal. Las series meteorológicas de contexto terminan en el último dato archivado. El terreno se representa mediante un reservorio térmico.'));
    }
  }
  function update(result,f,force=false){
    const valid=result?.config.geometry==='foundation'&&result.metadata&&result.config.mask&&result.n.length===3;
    overview.hidden=$('runDashboard').hidden=!valid;
    if(!valid||$('resultsPage').hidden)return;
    const fresh=r!==result,changed=frame!==f;r=result;frame=f;
    if(fresh){prepare();$('dashIdentity').textContent='Corrida '+r.simulationId.slice(0,12)+' · '+(r.config.construction?.curve?.column||r.config.construction?.model||'fundación')+' · malla '+r.n.join(' × ')+' · '+fmt(r.frameTimes.at(-1)/86400)+' días';}
    if(!fresh&&!changed&&!force)return;
    const current=stats[frame];$('dashCards').replaceChildren();
    for(const [key,v] of [['Máxima activa',fmt(current.max)+' °C'],['Sonda central',dataAt(probe.center,frame)===null?'Sin colocar':fmt(dataAt(probe.center,frame))+' °C'],['Media activa',fmt(current.mean)+' °C'],['Instante mostrado',fmt(r.frameTimes[frame]/86400)+' días']]){
      const card=node('div','');card.append(node('span',key),node('strong',v));$('dashCards').append(card);
    }
    $('dashSection').hidden=tab!=='section';$('dashCharts').hidden=tab==='section';
    if(tab==='section')map();else if(fresh||force)charts();else if(tab==='temperature')profile();
    models.forEach(move=>move());
  }
  const refresh=()=>{if(r)update(r,frame,true);};
  $('dashPlane').onchange=()=>{resetSlice();refresh();};$('dashSlice').oninput=refresh;$('dashSoil').onchange=refresh;
  $('dashHot').onclick=()=>{if(stats[frame].hot>=0)$('dashSlice').value=D.ijk(stats[frame].hot,r.n)[planeAxes()[2]];refresh();};
  document.querySelectorAll('[data-analysis]').forEach(button=>button.onclick=()=>{tab=button.dataset.analysis;document.querySelectorAll('[data-analysis]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));refresh();});
  window.addEventListener('resize',refresh);
  $('openThermalExample').onclick=async()=>{
    const button=$('openThermalExample');button.disabled=true;
    try{
      if(!catalog.demo)throw Error('La corrida de ejemplo no está publicada en este equipo.');
      $('openThermalStatus').textContent='Cargando el campo guardado…';await window.therma.openArchived(catalog.demo);
      window.ThermaNavigation.go('results');const result=window.therma.getResult();
      window.therma.setFrame(D.nearest(result.frameTimes,result.metadata.metrics.global_peak_time_s));
      overview.scrollIntoView();$('openThermalStatus').textContent='';
    }catch(e){$('openThermalStatus').textContent=e.message+' Puedes abrir otra corrida desde 03 Simulaciones.';}
    finally{button.disabled=false;}
  };
  window.ThermaRunDashboard={update};
})();
