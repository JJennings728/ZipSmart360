/* AeroCIE | Interactive signal-glow enhancement | synthetic visualization only.
   All illuminated ribbons are illustrative UI effects, not traced source evidence. */
(() => {
  'use strict';
  const host = document.getElementById('workspace');
  const existing = document.getElementById('network');
  if (!host || !existing || host.querySelector('#srp-signal-glow')) return;

  const stages = [
    ['L1','Sources','Illustrative source intake'],
    ['L2','Context','Organized research context'],
    ['L3','Relationships','Proposed evidence connections'],
    ['L4','Risk & impact','Questions requiring review'],
    ['L5','Insights','Exploratory patterns'],
    ['L6','Research review','Human verification checkpoint'],
    ['L7','Outcomes','Possible outputs, not findings']
  ];
  const colors = ['#41d9ff','#638eff','#a58aff','#3ce6ee','#ffc47f','#ff74d8','#80f5c2'];
  const style = document.createElement('style');
  style.textContent = `
    .srp-glow-layer{position:absolute;inset:0;width:100%;height:100%;z-index:1;pointer-events:none}
    .srp-stage-rail{position:absolute;z-index:7;left:14px;right:14px;top:147px;display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px}
    .srp-stage{appearance:none;min-width:0;min-height:51px;padding:7px 3px;border:1px solid rgba(71,140,199,.42);border-radius:7px;background:rgba(3,16,38,.88);color:#bdd6ed;font-size:10px;line-height:1.25;text-align:center;backdrop-filter:blur(8px);transition:background .18s,border-color .18s,box-shadow .18s,transform .18s}
    .srp-stage b{display:block;font-size:12px;color:#91dbfb;letter-spacing:.09em;margin-bottom:3px}
    .srp-stage span{display:block;overflow:hidden;text-overflow:ellipsis}
    .srp-stage:hover,.srp-stage:focus-visible,.srp-stage.is-glowing{background:rgba(15,60,98,.94);border-color:var(--stage-color);box-shadow:0 0 20px var(--stage-glow),inset 0 0 16px rgba(49,177,241,.12);color:white;transform:translateY(-3px)}
    .srp-stage.is-glowing b{color:#fff}
    .srp-flow-hint{position:absolute;z-index:5;bottom:66px;left:30px;max-width:calc(100% - 60px);font:650 11px/1.4 'Segoe UI',sans-serif;color:#adecf6;background:rgba(3,16,35,.76);border:1px solid rgba(49,173,221,.28);border-radius:6px;padding:8px 10px;pointer-events:none}
    .srp-flow-hint strong{color:white}
    .srp-stage:focus-visible{outline:2px solid #fff;outline-offset:2px}
    #groupLabels{display:none}
    @media(max-width:1000px){.srp-stage-rail{top:152px;gap:3px;left:8px;right:8px}.srp-stage{font-size:9px;padding:6px 1px}.srp-stage b{font-size:11px}.srp-flow-hint{left:18px;bottom:64px}}
    @media(max-width:700px){.topbar{height:84px;padding:10px 12px;justify-content:center;overflow:hidden}.topbar .brand{width:100%;justify-content:center}.topbar .brand-logo{width:min(265px,82vw);height:60px}.topbar .product-title,.topbar .header-right{display:none}.srp-stage-rail{top:166px;display:flex;overflow-x:auto;padding:0 0 7px;scrollbar-width:thin}.srp-stage{min-width:88px;flex:0 0 88px}.srp-flow-hint{font-size:10px;max-width:calc(100% - 25px)}}
    @media(prefers-reduced-motion:reduce){.srp-stage{transition:none}.srp-stage:hover,.srp-stage.is-glowing{transform:none}}
  `;
  document.head.appendChild(style);

  const canvas = document.createElement('canvas');
  canvas.id = 'srp-signal-glow';
  canvas.className = 'srp-glow-layer';
  canvas.setAttribute('aria-hidden','true');
  host.appendChild(canvas);
  const ctx = canvas.getContext('2d', {alpha: true});
  if (!ctx) return;
  const rail = document.createElement('div');
  rail.className = 'srp-stage-rail';
  rail.setAttribute('role','group');
  rail.setAttribute('aria-label','Explore the seven simulated AeroCIE stages');
  const hint = document.createElement('div');
  hint.className = 'srp-flow-hint';
  hint.setAttribute('role','status');
  hint.setAttribute('aria-live','polite');
  hint.textContent = 'Move across the network or focus a stage to illuminate simulated connections. Click a stage to lock its glow.';
  host.append(rail, hint);

  let hover = -1, pinned = -1, glow = 0, active = -1;
  let width = 1, height = 1, ratio = 1, last = performance.now(), tick = 0;
  const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const buttons = [];
  const pos = i => width*(.065 + i*(.87/6));
  function setHover(index) {
    hover = index;
    const next = hover >= 0 ? hover : pinned;
    if (next !== active) {
      active = next;
      for (let i=0;i<buttons.length;i++) {
        buttons[i].classList.toggle('is-glowing',i===active);
        buttons[i].setAttribute('aria-pressed',String(i===pinned));
      }
      hint.innerHTML = active < 0
        ? 'Hover the network or a stage. Click to pin a glowing pathway. All data is <strong>synthetic</strong>.'
        : '<strong>'+stages[active][0]+' | '+stages[active][1]+'</strong> — '+stages[active][2]+' | SIMULATED';
    }
  }
  for (let i=0;i<stages.length;i++) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'srp-stage';
    button.style.setProperty('--stage-color',colors[i]);
    button.style.setProperty('--stage-glow',colors[i]+'70');
    button.innerHTML='<b>'+stages[i][0]+'</b><span>'+stages[i][1]+'</span>';
    button.setAttribute('aria-label',stages[i][0]+': '+stages[i][1]+'. '+stages[i][2]+'. Hover to illuminate, activate to pin.');
    button.setAttribute('aria-pressed','false');
    button.addEventListener('pointerenter',()=>setHover(i));
    button.addEventListener('pointerleave',()=>setHover(-1));
    button.addEventListener('focus',()=>setHover(i));
    button.addEventListener('blur',()=>setHover(-1));
    button.addEventListener('click',()=>{pinned=pinned===i?-1:i;setHover(pinned>=0?pinned:-1);});
    buttons.push(button); rail.appendChild(button);
  }
  existing.addEventListener('pointermove',e=>{
    if(e.pointerType==='touch')return;
    const b=existing.getBoundingClientRect();
    const x=Math.max(0,Math.min(1,(e.clientX-b.left)/Math.max(1,b.width)));
    setHover(Math.max(0,Math.min(6,Math.round((x-.065)/(.87/6)))));
  });
  existing.addEventListener('pointerleave',()=>setHover(-1));
  existing.addEventListener('pointerdown',e=>{
    if(e.pointerType==='touch') {
      const b=existing.getBoundingClientRect();
      pinned=Math.max(0,Math.min(6,Math.round(((e.clientX-b.left)/Math.max(1,b.width)-.065)/(.87/6))));
      setHover(pinned);
    }
  });
  const reset = document.getElementById('resetBtn');
  if(reset)reset.addEventListener('click',()=>{pinned=-1;setHover(-1)});

  function resize(){
    const b=host.getBoundingClientRect();
    width=Math.max(1,b.width);height=Math.max(1,b.height);
    ratio=Math.min(window.devicePixelRatio||1,1.5);
    canvas.width=Math.max(1,Math.floor(width*ratio));canvas.height=Math.max(1,Math.floor(height*ratio));
    ctx.setTransform(ratio,0,0,ratio,0,0);
  }
  window.addEventListener('resize',resize,{passive:true});
  if(window.ResizeObserver)new ResizeObserver(resize).observe(host);
  resize();
  const bands=72;
  const wave = (index,stage,time) => {
    const phase=index*.23 + stage*.78;
    const spread=(index/(bands-1)-.5)*height*.51;
    const y=height*.585+spread;
    const undulation=Math.sin(index*.34+stage*.91+time*.52)*height*.041;
    return y+undulation;
  };
  function segment(i,j,time){
    const a={x:pos(j),y:wave(i,j,time)},b={x:pos(j+1),y:wave(i,j+1,time)};
    ctx.moveTo(a.x,a.y);
    ctx.bezierCurveTo(a.x+(b.x-a.x)*.48,a.y+Math.sin(i*.17+j)*height*.038,
      b.x-(b.x-a.x)*.46,b.y-Math.cos(i*.25-j)*height*.035,b.x,b.y);
  }
  const stars=Array.from({length:88},(_,i)=>({x:(i*0.6180339887)%1,y:(i*0.319417)%1,size:i%7===0?1.5:.7}));
  function paint(now){
    const dt=Math.min((now-last)/1000,.05);last=now;
    if(!reduced)tick+=dt;
    const target=active>=0?1:0;
    glow+=(target-glow)*Math.min(1,dt*8);
    ctx.clearRect(0,0,width,height);
    if(!width||!height){requestAnimationFrame(paint);return;}

    for(const s of stars){
      ctx.globalAlpha=.12+(Math.sin(tick*1.2+s.x*37)+1)*.045;
      ctx.fillStyle='#bbecff';ctx.beginPath();ctx.arc(width*s.x,height*(.27+s.y*.68),s.size,0,Math.PI*2);ctx.fill();
    }
    ctx.globalAlpha=1;
    if(active>=0 && glow>.01){
      const x=pos(active),rad=Math.max(width*.26,150);
      const wash=ctx.createRadialGradient(x,height*.61,4,x,height*.61,rad);
      wash.addColorStop(0,'rgba(90,209,255,'+(.12*glow)+')');
      wash.addColorStop(.48,'rgba(21,108,238,'+(.045*glow)+')');
      wash.addColorStop(1,'rgba(0,0,0,0)');
      ctx.fillStyle=wash;ctx.fillRect(x-rad,0,rad*2,height);
    }
    // Every strand below represents only a simulated, illustrative flow.
    // Brighten ribbons as a stage is hovered; do not suggest verified graph links.
    for(let i=0;i<bands;i++){
      const col=colors[i%colors.length];
      ctx.beginPath();
      for(let j=0;j<6;j++)segment(i,j,tick);
      ctx.globalAlpha=.055+(i%8===0?.095:0);
      ctx.strokeStyle=col;ctx.lineWidth=i%8===0?1.05:.65;
      ctx.stroke();
    }
    if(active>=0 && glow>.025){
      const first=Math.max(0,active-1),lastSeg=Math.min(5,active);
      ctx.save();ctx.shadowBlur=14*glow;
      for(let i=0;i<bands;i++){
        if(i%2 && glow<.95)continue;
        ctx.strokeStyle=colors[(i+active)%colors.length];
        ctx.globalAlpha=(.38+(i%6===0?.22:0))*glow;
        ctx.lineWidth=i%8===0?2.3:1.25;
        ctx.shadowColor=colors[(i+active)%colors.length];
        ctx.beginPath();for(let j=first;j<=lastSeg;j++)segment(i,j,tick);ctx.stroke();
      }
      ctx.restore();
      const x=pos(active);
      ctx.globalAlpha=.95*glow;
      for(let i=0;i<17;i++){
        const y=height*(.30+i*.034);
        const sparkle=(Math.sin(tick*3+i*.93)+1)*.5;
        const r=1.5+sparkle*3;
        const bloom=ctx.createRadialGradient(x,y,0,x,y,14+r*4);
        bloom.addColorStop(0,'rgba(244,255,255,.9)');
        bloom.addColorStop(.18,colors[active]+'98');
        bloom.addColorStop(1,'rgba(0,0,0,0)');
        ctx.fillStyle=bloom;ctx.beginPath();ctx.arc(x,y,14+r*4,0,Math.PI*2);ctx.fill();
      }
      ctx.globalAlpha=1;
    }
    // Small animated photons move along the concept network.
    if(!reduced){
      for(let k=0;k<22;k++){
        const u=(tick*(.09+(k%4)*.025)+k*.067)%1;
        const x=pos(0)+(pos(6)-pos(0))*u;
        const y=height*(.40+.34*(k%17)/17)+Math.sin(tick*1.4+k*.8)*height*.034;
        ctx.globalAlpha=active<0?.45:.8;
        ctx.fillStyle=colors[k%7];ctx.beginPath();ctx.arc(x,y,active<0?1.3:2.2,0,Math.PI*2);ctx.fill();
      }
    }
    ctx.globalAlpha=1;
    requestAnimationFrame(paint);
  }
  requestAnimationFrame(paint);
  window.AeroCIEHoverEffects={mode:'ILLUSTRATIVE_SYNTHETIC',stages:7,hoverStage:i=>setHover(i),get activeStage(){return active},get pinnedStage(){return pinned}};
})();
