(function(){
'use strict';
var G=6.67430e-20,EARTH=5.9722e24,DAY=86400;
function cloneBodies(){return [
{id:'nirn',name:'NIRN / PELAGOS-01',kind:'PLANET',parent:null,mass:1*EARTH,radius:6371,visual:15,color:'#55d69a',x:0,y:0,z:0,vx:0,vy:0,vz:0,spin:24.0,spinAngle:0,spinAxis:[0,0,1],lore:'Mortal world; gravitational reference body in this reconstruction.'},
{id:'masser',name:'MASSER / JODE',kind:'MOON',parent:'nirn',mass:.00008*EARTH,radius:325,visual:7,color:'#d78b63',orbit:0,periodDays:24,phase:0.2,spin:655.7,spinAxis:[0.03,0,1],lore:'Larger visible moon. Physical parameters are reconstruction assumptions.'},
{id:'secunda',name:'SECUNDA / JONE',kind:'MOON',parent:'nirn',mass:.00002*EARTH,radius:190,visual:4.5,color:'#aebed0',orbit:0,periodDays:30,phase:2.1,spin:480,spinAxis:[0.08,0,1],lore:'Smaller moon; nested around Masser in this interpretation of the sky.'},
{id:'zenithar',name:'ZENITHAR',kind:'DIVINE PLANET',parent:'nirn',mass:.0012*EARTH,radius:4200,visual:8,color:'#e7c56e',orbit:12000000,phase:.5,spin:30,spinAxis:[.04,.02,1],lore:'Aedric planetary body. Finite mass and radius are model parameters, not canon.'},
{id:'mara',name:'MARA',kind:'DIVINE PLANET',parent:'zenithar',mass:.00012*EARTH,radius:1500,visual:4.5,color:'#e99dbd',orbit:145000,phase:1.4,spin:42,spinAxis:[0,0,1],lore:'Nested with Zenithar in the traditional orrery reconstruction.'},
{id:'dibella',name:'DIBELLA',kind:'DIVINE PLANET',parent:'mara',mass:.00004*EARTH,radius:900,visual:3.5,color:'#d88bb7',orbit:38000,phase:2.4,spin:28,spinAxis:[0,0,1],lore:'Nested with Mara in the traditional orrery reconstruction.'},
{id:'arkay',name:'ARKAY',kind:'DIVINE PLANET',parent:'nirn',mass:.0008*EARTH,radius:3500,visual:7,color:'#c6d9e8',orbit:17500000,phase:2.7,spin:34,spinAxis:[.1,0,1],lore:'Orrery depictions give Arkay an unusual tilted/looping path; rendered here as a bounded orbit approximation.'},
{id:'kynareth',name:'KYNARETH',kind:'DIVINE PLANET',parent:'nirn',mass:.0007*EARTH,radius:3900,visual:7,color:'#71d8a2',orbit:23500000,phase:3.6,spin:31,spinAxis:[0,.08,1],lore:'Aedric planetary body; dimensions and mass are reconstruction parameters.'},
{id:'akatosh',name:'AKATOSH',kind:'DIVINE PLANET',parent:'nirn',mass:.0015*EARTH,radius:5000,visual:9,color:'#e8ae5c',orbit:29500000,phase:4.5,spin:26,spinAxis:[.02,.1,1],lore:'Aedric planetary body; dimensions and mass are reconstruction parameters.'},
{id:'julianos',name:'JULIANOS',kind:'DIVINE PLANET',parent:'nirn',mass:.0011*EARTH,radius:4600,visual:8,color:'#79bce8',orbit:36500000,phase:5.4,spin:29,spinAxis:[.06,.02,1],lore:'Aedric planetary body; Stendarr is nested around it in the orrery tradition.'},
{id:'stendarr',name:'STENDARR',kind:'DIVINE PLANET',parent:'julianos',mass:.00009*EARTH,radius:1300,visual:4, color:'#d5e5f0',orbit:125000,phase:1.8,spin:38,spinAxis:[0,0,1],lore:'Nested with Julianos in the traditional orrery reconstruction.'}
];}
function initialize(source){
var bodies=source||cloneBodies(),byId={};bodies.forEach(function(b){byId[b.id]=b;});
function place(b){
 if(!b.parent)return;var p=byId[b.parent];if(!p||b._placed)return;place(p);
 var a=b.phase||0,r=b.orbit||(b.periodDays?Math.cbrt(G*(p.mass+b.mass)*Math.pow((b.periodDays*DAY)/(Math.PI*2),2)):100000),inc=b.id==='arkay'?.42:(b.id==='kynareth'?.13:.04),x=r*Math.cos(a),y=r*Math.sin(a)*Math.cos(inc),z=r*Math.sin(a)*Math.sin(inc);
 b.x=p.x+x;b.y=p.y+y;b.z=p.z+z;
 var mu=G*(p.mass+b.mass),speed=Math.sqrt(mu/r),tx=-Math.sin(a),ty=Math.cos(a)*Math.cos(inc),tz=Math.cos(a)*Math.sin(inc),norm=Math.hypot(tx,ty,tz);
 b.vx=p.vx+speed*tx/norm;b.vy=p.vy+speed*ty/norm;b.vz=p.vz+speed*tz/norm;b._placed=true;
}
bodies.forEach(place);bodies.forEach(function(b){delete b._placed;});
var total=0,cx=0,cy=0,cz=0,cvx=0,cvy=0,cvz=0;bodies.forEach(function(b){total+=b.mass;cx+=b.mass*b.x;cy+=b.mass*b.y;cz+=b.mass*b.z;cvx+=b.mass*b.vx;cvy+=b.mass*b.vy;cvz+=b.mass*b.vz;});cx/=total;cy/=total;cz/=total;cvx/=total;cvy/=total;cvz/=total;bodies.forEach(function(b){b.x-=cx;b.y-=cy;b.z-=cz;b.vx-=cvx;b.vy-=cvy;b.vz-=cvz;});return bodies;
}
function accelerations(bodies){
var a=bodies.map(function(){return [0,0,0];});
for(var i=0;i<bodies.length;i++)for(var j=i+1;j<bodies.length;j++){
var p=bodies[i],q=bodies[j],dx=q.x-p.x,dy=q.y-p.y,dz=q.z-p.z,r2=dx*dx+dy*dy+dz*dz;
if(r2<1)r2=1;var inv=1/(r2*Math.sqrt(r2)),f=G*inv;
a[i][0]+=f*q.mass*dx;a[i][1]+=f*q.mass*dy;a[i][2]+=f*q.mass*dz;
a[j][0]-=f*p.mass*dx;a[j][1]-=f*p.mass*dy;a[j][2]-=f*p.mass*dz;
}
return a;
}
function step(bodies,dt){
var a=accelerations(bodies);
bodies.forEach(function(b,i){b.x+=b.vx*dt+.5*a[i][0]*dt*dt;b.y+=b.vy*dt+.5*a[i][1]*dt*dt;b.z+=b.vz*dt+.5*a[i][2]*dt*dt;});
var next=accelerations(bodies);
bodies.forEach(function(b,i){b.vx+=.5*(a[i][0]+next[i][0])*dt;b.vy+=.5*(a[i][1]+next[i][1])*dt;b.vz+=.5*(a[i][2]+next[i][2])*dt;b.spinAngle=(b.spinAngle+dt/(b.spin*3600)*Math.PI*2)%(Math.PI*2);});
return bodies;
}
function collisions(bodies){
var out=[];
for(var i=0;i<bodies.length;i++)for(var j=i+1;j<bodies.length;j++){
var a=bodies[i],b=bodies[j],d=Math.hypot(a.x-b.x,a.y-b.y,a.z-b.z),sum=a.radius+b.radius;
if(d<=sum)out.push({a:a.id,b:b.id,distanceKm:d,overlapKm:sum-d,status:'COLLISION'});
else if(d<sum*5)out.push({a:a.id,b:b.id,distanceKm:d,clearanceKm:d-sum,status:'CLOSE APPROACH'});
}
return out.sort(function(a,b){return a.distanceKm-b.distanceKm;});
}
var core={G:G,DAY:DAY,cloneBodies:cloneBodies,initialize:initialize,accelerations:accelerations,step:step,collisions:collisions};
if(typeof window!=='undefined')window.VigilNirnGravityCore=core;
if(typeof module!=='undefined'&&module.exports)module.exports=core;
function boot(){
var host=document.getElementById('elder-scrolls-astronomy-folder');if(!host||host.dataset.gravityReady)return;
host.dataset.gravityReady='1';
var tabs=host.querySelector('.es-astro-tabs'),pages=host.querySelector('[data-es-page="calendar"]');
if(!tabs||!pages)return;
var tab=document.createElement('button');tab.type='button';tab.dataset.esTab='gravity';tab.textContent='03 NIRN GRAVITY MODEL';tab.setAttribute('aria-selected','false');tabs.appendChild(tab);
var launch=document.getElementById('vigil-open-nirn-gravity');if(launch)launch.addEventListener('click',function(){var openFolder=document.getElementById('rd-open-elder-scrolls-folder');if(host.hidden&&openFolder)openFolder.click();tab.click();});
var page=document.createElement('section');page.className='es-astro-page es-gravity-page';page.dataset.esPage='gravity';page.hidden=true;
page.innerHTML='<div class="es-gravity-head"><div><b>NIRN-CENTERED NEWTONIAN RECONSTRUCTION</b><small>PAIRWISE GRAVITY · 3D ROTATION · PHYSICAL-RADIUS COLLISION CHECKS</small></div><span id="es-gravity-state">PAUSED / INITIAL CONDITIONS</span></div><div class="es-gravity-layout"><div class="es-gravity-viewport"><canvas id="es-gravity-canvas" width="1200" height="700" aria-label="Rotating three-dimensional gravitational model of Nirn, its moons and the divine planets"></canvas><div class="es-gravity-legend"><span>● NIRN</span><span>● MOONS</span><span>● DIVINE PLANETS</span><span>◇ LORE LIGHTS / NON-MASSIVE</span></div></div><aside class="es-gravity-side"><div class="es-gravity-controls"><button id="es-gravity-run">▶ RUN</button><button id="es-gravity-pause">Ⅱ PAUSE</button><button id="es-gravity-reset">RESET</button><label>SIM SPEED<select id="es-gravity-speed"><option value="0.25">0.25×</option><option value="1" selected>1×</option><option value="5">5×</option><option value="20">20×</option><option value="100">100×</option></select></label><label>CAMERA ROTATION<input id="es-gravity-rotation" type="range" min="0" max="360" value="24"></label><label><input id="es-gravity-autospin" type="checkbox" checked> AUTO-ROTATE VIEW</label><label><input id="es-gravity-trails" type="checkbox" checked> ORBIT TRAILS</label></div><div class="es-gravity-readouts"><div><small>SIMULATION TIME</small><b id="es-gravity-time">T+ 0.00 DAYS</b></div><div><small>COLLISION STATUS</small><b id="es-gravity-collision">NO COLLISIONS DETECTED</b></div><div><small>ACTIVE BODIES</small><b id="es-gravity-count">11</b></div></div><div class="es-gravity-alerts"><h4>COLLISION / CLOSE-APPROACH MONITOR</h4><div id="es-gravity-alert-list">INITIAL CONDITIONS CLEAR · PHYSICAL RADII ACTIVE</div></div><div class="es-gravity-object"><h4>OBJECT INSPECTOR</h4><select id="es-gravity-object-select" aria-label="Select celestial object"></select><div id="es-gravity-object-detail">Select a body to inspect its mass, radius, spin, and parent relationship.</div></div><p class="es-gravity-caveat">MODEL LIMITS: Nirn\'s mass, the divine planets&#39; masses/radii, and most orbital elements and spin rates are not specified canonically. This is a Newtonian, finite-mass reconstruction using explicit adjustable assumptions—not a claim that the lore&#39;s infinite divine planes are ordinary planets. Magnus is the Sun/aperture; Mnemoli is the Blue Star and is shown separately, with its possible second-sun reading marked as disputed. The plural-suns passage is obscure developer lore. The Dark Moon / Den of Lorkhaj is marked as a hidden lunar-realm tradition, not a third measured moon. These lore markers are not assigned invented Newtonian masses.</p></aside></div><div class="es-gravity-footer"><span>PHYSICS: SI UNITS · km / kg / s · VELOCITY-VERLET N-BODY INTEGRATION</span><span>DISPLAY RADII / DISTANCES ARE COMPRESSED; COLLISIONS USE PHYSICAL RADII ONLY</span></div>';
host.insertBefore(page,pages);
var allTabs=Array.prototype.slice.call(host.querySelectorAll('[data-es-tab]')),allPages=Array.prototype.slice.call(host.querySelectorAll('[data-es-page]'));
allTabs.forEach(function(t){t.addEventListener('click',function(){allTabs.forEach(function(x){var on=x===t;x.classList.toggle('active',on);x.setAttribute('aria-selected',String(on));});allPages.forEach(function(p){p.hidden=p.dataset.esPage!==t.dataset.esTab;});if(t===tab){draw();run();}});});
var canvas=page.querySelector('#es-gravity-canvas'),ctx=canvas.getContext('2d'),bodies=initialize(),running=false,simSeconds=0,last=0,accum=0,raf=0,rotation=24*Math.PI/180,trail=[],selected='nirn',events=[],lastCollisionKey='';
var speed=page.querySelector('#es-gravity-speed'),auto=page.querySelector('#es-gravity-autospin'),trails=page.querySelector('#es-gravity-trails'),rot=page.querySelector('#es-gravity-rotation'),state=page.querySelector('#es-gravity-state');
var select=page.querySelector('#es-gravity-object-select');bodies.forEach(function(b){var o=document.createElement('option');o.value=b.id;o.textContent=b.name;select.appendChild(o);});
function project(b){
var co=Math.cos(rotation),si=Math.sin(rotation),cp=Math.cos(pitch),sp=Math.sin(pitch),x=b.x*co-b.y*si,y=b.x*si+b.y*co,z=b.z;
var yp=y*cp-z*sp,zp=y*sp+z*cp,max=4.0e7,span=Math.min(canvas.width,canvas.height)*.43,rad=Math.hypot(x,yp,zp),compressed=rad?Math.pow(rad/max,.48)*span:0,scale=rad?compressed/rad:0,depth=1/(1+Math.max(-.8,Math.min(.8,zp/max))*.32),px=canvas.width/2+x*scale*depth,py=canvas.height/2-yp*scale*depth;
if(b.parent&&b.parent!=='nirn'){var parent=bodies.find(function(q){return q.id===b.parent;});if(parent){var pp=project(parent),lx=b.x-parent.x,ly=b.y-parent.y,lz=b.z-parent.z,rx=lx*co-ly*si,ry=lx*si+ly*co,ryp=ry*cp-lz*sp,rz=ry*sp+lz*cp,ln=Math.hypot(rx,ryp,rz)||1,orbit=b.kind==='MOON'?23:17;px=pp.x+(rx/ln)*orbit;py=pp.y-(ryp/ln)*orbit;}}
return {x:px,y:py,r:Math.max(3,b.visual*depth),z:zp};
}
function draw(){
var w=canvas.width,h=canvas.height;ctx.clearRect(0,0,w,h);var bg=ctx.createLinearGradient(0,0,0,h);bg.addColorStop(0,'#07131d');bg.addColorStop(1,'#02070d');ctx.fillStyle=bg;ctx.fillRect(0,0,w,h);
ctx.strokeStyle='rgba(102,153,180,.11)';ctx.lineWidth=1;for(var x=0;x<w;x+=50){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}for(var y=0;y<h;y+=50){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
var center=project(bodies[0]);ctx.strokeStyle='rgba(120,175,205,.18)';ctx.setLineDash([5,8]);ctx.beginPath();ctx.ellipse(center.x,center.y,56,56*Math.cos(pitch),0,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);
if(trails.checked)trail.forEach(function(t){ctx.globalAlpha=.24;ctx.fillStyle=t.color;ctx.beginPath();ctx.arc(t.x,t.y,1.35,0,Math.PI*2);ctx.fill();});ctx.globalAlpha=1;
var ordered=bodies.map(function(b){return {b:b,p:project(b)};}).sort(function(a,b){return a.p.z-b.p.z;});
ordered.forEach(function(o){var b=o.b,p=o.p;var grad=ctx.createRadialGradient(p.x-p.r*.35,p.y-p.r*.4,1,p.x,p.y,p.r*1.6);grad.addColorStop(0,'#ffffff');grad.addColorStop(.22,b.color);grad.addColorStop(1,'#03070b');ctx.fillStyle=grad;ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);ctx.fill();var axis=b.spinAxis||[0,0,1],an=Math.hypot(axis[0],axis[1],axis[2])||1,ax=axis[0]/an,ay=axis[1]/an,az=axis[2]/an,ang=b.spinAngle||0,cs=Math.cos(ang),sn=Math.sin(ang),dot=ax,svx=cs+ax*dot*(1-cs),svy=az*sn+ay*dot*(1-cs),svz=-ay*sn+az*dot*(1-cs),vpx=svx*Math.cos(rotation)-svy*Math.sin(rotation),vpy=svx*Math.sin(rotation)+svy*Math.cos(rotation),vpy2=vpy*Math.cos(pitch)-svz*Math.sin(pitch);ctx.strokeStyle='rgba(245,250,255,.86)';ctx.lineWidth=1.6;ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(p.x+vpx*p.r*.78,p.y-vpy2*p.r*.78);ctx.stroke();ctx.fillStyle='#f7f4df';ctx.beginPath();ctx.arc(p.x+vpx*p.r*.62,p.y-vpy2*p.r*.62,Math.max(1.4,p.r*.13),0,Math.PI*2);ctx.fill();if(b.id===selected){ctx.strokeStyle='#fff2b0';ctx.lineWidth=2;ctx.beginPath();ctx.arc(p.x,p.y,p.r+7,0,Math.PI*2);ctx.stroke();}ctx.fillStyle='#d8e7f2';ctx.font='bold 12px Courier New';ctx.textAlign='left';var lx=p.x+p.r+7,ly=p.y+4;if(b.id==='secunda'||b.id==='dibella')ly+=18;if(b.id==='mara'||b.id==='stendarr')ly-=14;var labelWidth=ctx.measureText(b.name).width;ctx.fillStyle='rgba(2,8,14,.88)';ctx.fillRect(lx-3,ly-11,labelWidth+6,15);ctx.fillStyle='#d8e7f2';ctx.fillText(b.name,lx,ly);});
var magnusX=w-110,magnusY=92;ctx.fillStyle='#ffe6a0';ctx.shadowColor='#ffe6a0';ctx.shadowBlur=18;ctx.beginPath();ctx.arc(magnusX,magnusY,15,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;ctx.fillStyle='#f2dfb4';ctx.font='bold 13px Courier New';ctx.textAlign='center';ctx.fillText('MAGNUS',magnusX,magnusY+35);ctx.fillStyle='#9db2c2';ctx.font='10px Courier New';ctx.fillText('LORE LIGHT / NOT A MASS POINT',magnusX,magnusY+50);
var stars=[['MNEMOLI · BLUE STAR',w-130,175],['POSSIBLE SECOND-SUN READING',w-130,215],['MAGNA-GE / STAR-HOLES',w-130,255],['PLURAL “SUNS” TEXT REFERENCE',w-130,295],['DARK MOON / DEN OF LORKHAJ',w-130,335]];stars.forEach(function(s){ctx.fillStyle=s[0].indexOf('MNEMOLI')===0?'#8ccaff':'#c2d6e8';ctx.beginPath();ctx.arc(s[1],s[2],s[0].indexOf('MNEMOLI')===0?6:4,0,Math.PI*2);ctx.fill();ctx.fillStyle='#b9c9d6';ctx.font='10px Courier New';ctx.textAlign='center';ctx.fillText(s[0],s[1],s[2]+18);});
ctx.fillStyle='#8aa6b9';ctx.font='11px Courier New';ctx.textAlign='left';ctx.fillText('SCHEMATIC CAMERA PROJECTION · POSITION SOLVER IS 3D',18,h-20);
}
function detail(){
var b=bodies.find(function(x){return x.id===selected;})||bodies[0],parent=b.parent?bodies.find(function(x){return x.id===b.parent;}):null,orbiters=bodies.filter(function(x){return x.parent===b.id;}),orbitText=orbiters.length?'ORBITING BODIES ('+orbiters.length+'): '+orbiters.map(function(x){return x.name;}).join(', '):'NO MODELED ORBITING BODIES';
page.querySelector('#es-gravity-object-detail').textContent=b.kind+' · MASS '+(b.mass/EARTH).toExponential(3)+' EARTH MASSES · RADIUS '+b.radius.toLocaleString()+' km · AXIAL DAY '+b.spin+' h · '+(parent?'PARENT '+parent.name:'SYSTEM REFERENCE')+' · '+orbitText+'. '+b.lore;
}
function monitor(){
events=collisions(bodies);var collisionsOnly=events.filter(function(e){return e.status==='COLLISION';}),close=events.filter(function(e){return e.status==='CLOSE APPROACH';});
var out=page.querySelector('#es-gravity-alert-list');out.textContent='';
if(!events.length){out.textContent='NO COLLISIONS / NO CLOSE APPROACHES · ALL PAIRS CLEAR';}
else events.slice(0,8).forEach(function(e){var row=document.createElement('div');row.className='es-gravity-event '+(e.status==='COLLISION'?'critical':'warning');row.textContent=e.status+' · '+e.a.toUpperCase()+' / '+e.b.toUpperCase()+' · '+(e.distanceKm/1000).toFixed(1)+'k km'+(e.overlapKm?' · OVERLAP '+e.overlapKm.toFixed(1)+' km':'');out.appendChild(row);});
var statusText=collisionsOnly.length?collisionsOnly.length+' COLLISION(S)':close.length?close.length+' CLOSE APPROACH(ES)':'NO COLLISIONS DETECTED';
page.querySelector('#es-gravity-collision').textContent=statusText;page.querySelector('#es-gravity-collision').style.color=collisionsOnly.length?'#ff7777':close.length?'#f0c879':'#9be3b7';
var key=collisionsOnly.map(function(e){return e.a+':'+e.b;}).join('|');if(key&&key!==lastCollisionKey){state.textContent='COLLISION EVENT DETECTED';}else state.textContent=running?'INTEGRATING / LIVE':'PAUSED / STABLE INITIALIZATION';lastCollisionKey=key;
}
function renderReadout(){page.querySelector('#es-gravity-time').textContent='T+ '+(simSeconds/DAY).toFixed(2)+' DAYS';page.querySelector('#es-gravity-count').textContent=String(bodies.length);monitor();}
function frame(now){
if(!running)return;if(!last)last=now;var elapsed=Math.min(.1,(now-last)/1000);last=now;var factor=Number(speed.value)||1;accum+=elapsed*factor*DAY;
var dt=3600,steps=0;while(accum>=dt&&steps<120){step(bodies,dt);accum-=dt;simSeconds+=dt;steps++;if(steps%6===0){bodies.forEach(function(body){var p=project(body);trail.push({id:body.id,x:p.x,y:p.y,color:body.color});});if(trail.length>2400)trail.splice(0,trail.length-2400);}}
if(auto.checked){rotation+=elapsed*.12;rot.value=String(Math.round(rotation*180/Math.PI)%360);}
draw();renderReadout();raf=requestAnimationFrame(frame);
}
function run(){if(running)return;running=true;last=0;state.textContent='INTEGRATING / LIVE';raf=requestAnimationFrame(frame);}
function pause(){running=false;if(raf)cancelAnimationFrame(raf);state.textContent='PAUSED / STABLE INITIALIZATION';}
function reset(){pause();bodies=initialize();simSeconds=0;accum=0;last=0;trail=[];lastCollisionKey='';renderReadout();draw();detail();}
page.querySelector('#es-gravity-run').addEventListener('click',run);page.querySelector('#es-gravity-pause').addEventListener('click',pause);page.querySelector('#es-gravity-reset').addEventListener('click',reset);
rot.addEventListener('input',function(){rotation=Number(rot.value)*Math.PI/180;draw();});select.addEventListener('change',function(){selected=select.value;detail();draw();});
canvas.addEventListener('pointerdown',function(e){canvas.setPointerCapture(e.pointerId);canvas.dataset.dragX=e.clientX;canvas.dataset.dragRotation=String(rotation);});
canvas.addEventListener('pointermove',function(e){if(!canvas.hasPointerCapture(e.pointerId))return;rotation=Number(canvas.dataset.dragRotation)+(e.clientX-Number(canvas.dataset.dragX))*.008;pitch=Math.max(-.85,Math.min(.85,pitch+(e.movementY||0)*.003));rot.value=String(Math.round(rotation*180/Math.PI)%360);draw();});
canvas.addEventListener('pointerup',function(e){if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);});
canvas.addEventListener('pointercancel',function(){});
renderReadout();draw();detail();
}
if(typeof document!=='undefined'){if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();}
})();
