
(function(){
'use strict';
function ready(fn){if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',fn);else fn();}
ready(function(){
 var root=document.getElementById('rd-puzzle-lab');if(!root||root.dataset.ready)return;root.dataset.ready='1';
 var select=document.getElementById('rd-puzzle-select'),field=document.getElementById('rd-playfield'),intro=document.getElementById('rd-puzzle-intro'),status=document.getElementById('rd-puzzle-status');
 var titles={
  artemis:['ARTEMIS POWER SYSTEM','Restore power by rotating relay segments so the core can feed the ship systems. This is a simplified circuit-routing exercise based on the original power-grid puzzle.'],
  yellow:['YELLOW HALL // ROTATING HEX LOCK','Rotate the six outer symbols to complete the line pattern in the central mechanism. The original game varies the sequence by difficulty and puzzle state.'],
  sundial:['ENGINE ROOM // SUNDIAL','Operate the six linked discs until every indicator is yellow. Each control changes a paired set, echoing the original linked-state mechanism.'],
  probe:['PROBE LOGIC CIRCUIT','Reconfigure the nine colored switches to close the gates and restore the probe. A switch affects a color-linked group, not only itself.'],
  blue:['BLUE HALL // HEX OVERLAP LOCK','Rotate the six outer symbols until their projected shapes no longer overlap in the central field.'],
  orbit:['BLUE HALL // PLANETARY ALIGNMENT','Move the four controllable orbital bodies so the fifth, uncontrolled body crosses the star and creates an eclipse. This is a reconstructed training model; published walkthroughs give different coordinate solutions.'],
  orange:['ORANGE HALL // SILHOUETTE MATCH','Stop and pair six matching shape profiles. The pair set includes one mirrored pair, as in the original challenge.'],
  green:['GREEN HALL // MIRROR ROUTING','Rotate mirrors in the triangular field to route each colored beam to its matching perimeter receiver. This compact board is an original training reconstruction of the routing mechanic.'],
  purple:['VIOLET HALL // CLOSED-LOOP CIRCUIT','Complete a continuous closed loop. The original challenge is a short competitive line/loop puzzle; this recreation isolates the loop-building rule.'],
  timed:['FIELD / COMBAT / RESCUE SEQUENCES','Practice the non-puzzle action gates: deploy diagnostics, protect the crew during the Krinn encounter, close shutters, rescue Zack with controlled thrust, and interrupt the force field.']
 };
 function setStatus(s){status.textContent=s;}
 function btn(label,fn,cls){var b=document.createElement('button');b.type='button';b.textContent=label;if(cls)b.className=cls;b.addEventListener('click',fn);return b;}
 function resetField(){field.innerHTML='';}
 function render(){
  var id=select.value;intro.textContent=titles[id][1];resetField();setStatus('TRAINING RECONSTRUCTION // '+titles[id][0]);
  if(id==='artemis'||id==='yellow'||id==='blue'){
   var targets=id==='artemis'?[1,3,2,0,1,2]:id==='yellow'?[2,3,4,5,1,0]:[2,4,1,5,3,0];
   var values=targets.map(function(){return 0;});var labels=id==='artemis'?['CORE','AUX','LIFE','NAV','COMMS','DRIVE']:['A','B','C','D','E','F'];
   var wrap=document.createElement('div');wrap.className='rd-dials';
   function draw(){wrap.innerHTML='';values.forEach(function(v,i){var b=btn('',function(){values[i]=(values[i]+1)%6;draw();check();},'rd-dial');b.innerHTML='<strong>'+labels[i]+' / '+v+'</strong><small>ROTATE RELAY</small>';wrap.appendChild(b);});}
   function check(){if(values.every(function(v,i){return v===targets[i];}))setStatus('LOCK ACCEPTED // ALL RELAY POSITIONS MATCH');}
   field.appendChild(wrap);var actions=document.createElement('div');actions.className='rd-controls';actions.appendChild(btn('RESET PUZZLE',function(){values=targets.map(function(){return 0;});draw();setStatus('RESET // ROTATE EACH SYMBOL');}));actions.appendChild(btn('SHOW TRAINING KEY',function(){values=targets.slice();draw();check();}));field.appendChild(actions);draw();
  }else if(id==='sundial'){
   var state=[0,1,0,0,1,0],wrap=document.createElement('div');wrap.className='rd-dials';
   function draw(){wrap.innerHTML='';state.forEach(function(v,i){var b=btn((i+1)+' / '+(v?'YELLOW':'DARK'),function(){state[i]^=1;state[(i+1)%6]^=1;draw();if(state.every(Boolean))setStatus('SUNDIAL STABLE // ALL SIX INDICATORS YELLOW');},'rd-dial');wrap.appendChild(b);});}
   field.appendChild(wrap);var actions=document.createElement('div');actions.className='rd-controls';actions.appendChild(btn('RESET',function(){state=[0,1,0,0,1,0];draw();setStatus('RESET // EACH PRESS CHANGES TWO NEIGHBORING DISCS');}));field.appendChild(actions);draw();
  }else if(id==='probe'){
   var groups=[[0,1,4],[1,0,2,5],[2,1,3,6],[3,2,4,7],[4,0,3,5,8],[5,1,4,6],[6,2,5,7],[7,3,6,8],[8,4,7]],state=[1,1,0,1,0,1,0,1,0],wrap=document.createElement('div');wrap.className='rd-switches';
   function draw(){wrap.innerHTML='';state.forEach(function(v,i){var b=btn('SWITCH '+(i+1)+'\n'+(v?'OPEN':'CLOSED'),function(){groups[i].forEach(function(k){state[k]^=1;});draw();if(state.every(function(x){return x===0;}))setStatus('PROBE LOGIC RESTORED // ALL GATES CLOSED');},v?'on':'');wrap.appendChild(b);});}
   field.appendChild(wrap);var actions=document.createElement('div');actions.className='rd-controls';actions.appendChild(btn('RESET',function(){state=[1,1,0,1,0,1,0,1,0];draw();setStatus('RESET // COLOR-LINKED GATE STATES');}));field.appendChild(actions);draw();
  }else if(id==='orbit'){
   var profiles={tanguay:{name:'WALKTHROUGH A // CLOCK POSITIONS',values:[330,0,135,40]},alternate:{name:'WALKTHROUGH B // ALTERNATE VERSION',values:[135,90,90,105]}};
   var values=[0,0,0,0],profile='tanguay',wrap=document.createElement('div');wrap.className='rd-orbit-wrap';
   var svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 360 300');svg.setAttribute('class','rd-orbit-svg');svg.setAttribute('role','img');svg.setAttribute('aria-label','Reconstructed orbital alignment diagram');
   var controls=document.createElement('div');controls.className='rd-orbit-controls';wrap.appendChild(svg);wrap.appendChild(controls);field.appendChild(wrap);
   function node(tag,attrs){var n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.keys(attrs).forEach(function(k){n.setAttribute(k,attrs[k]);});svg.appendChild(n);return n;}
   function draw(){svg.innerHTML='';[42,78,114,150].forEach(function(r){node('circle',{cx:180,cy:145,r:r,fill:'none',stroke:'#1a6047','stroke-dasharray':'4 5'});});node('circle',{cx:180,cy:145,r:12,fill:'#f6c96c',stroke:'#fff0bd'});node('text',{x:180,y:122,fill:'#f6c96c','text-anchor':'middle','font-size':'9'}).textContent='STAR';values.forEach(function(v,i){var r=[42,78,114,150][i],rad=v*Math.PI/180,x=180+Math.cos(rad)*r,y=145+Math.sin(rad)*r;node('circle',{cx:x,cy:y,r:7,fill:['#72ffc3','#62b8ff','#e2d86a','#ff9a70'][i],stroke:'#eafff4','stroke-width':'1.3'});node('text',{x:x+9,y:y-7,fill:'#c6f7df','font-size':'9'}).textContent=String.fromCharCode(65+i);});var hiddenAngle=(values[0]+values[1]+values[2]+values[3])%360;var hr=178,ha=hiddenAngle*Math.PI/180;node('circle',{cx:180+Math.cos(ha)*hr,cy:145+Math.sin(ha)*hr,r:5,fill:'#fff',stroke:'#fff'});node('text',{x:180,y:286,fill:'#7eb79e','text-anchor':'middle','font-size':'9'}).textContent='FIFTH BODY // INDIRECTLY POSITIONED';}
   function update(){controls.innerHTML='';var profileSelect=document.createElement('select');profileSelect.innerHTML='<option value="tanguay">WALKTHROUGH A / 11:00 · 4:30 · 1:20</option><option value="alternate">WALKTHROUGH B / ALTERNATE ORBIT SET</option>';profileSelect.value=profile;profileSelect.addEventListener('change',function(){profile=this.value;values=profiles[profile].values.slice();update();});controls.appendChild(profileSelect);values.forEach(function(v,i){var label=document.createElement('label');label.textContent='PLANET '+String.fromCharCode(65+i)+' // '+Math.round(v)+'°';var input=document.createElement('input');input.type='range';input.min='0';input.max='359';input.value=v;input.addEventListener('input',function(){values[i]=Number(this.value);label.firstChild.textContent='PLANET '+String.fromCharCode(65+i)+' // '+values[i]+'°';draw();check();});label.appendChild(input);controls.appendChild(label);});var b=btn('LOAD REFERENCE SOLUTION',function(){values=profiles[profile].values.slice();update();check();});controls.appendChild(b);draw();}
   function check(){var t=profiles[profile].values;var ok=values.every(function(v,i){return Math.abs(((v-t[i]+540)%360)-180)<=4;});setStatus(ok?'ALIGNMENT CONFIRMED // FIFTH BODY OCCULTS THE STAR':'ALIGNMENT NOT YET CONFIRMED // ADJUST ORBITAL POSITIONS');}
   update();setStatus('ALIGNMENT TRAINER // SELECT A REFERENCE PROFILE OR ADJUST THE ORBITS');
  }else if(id==='orange'){
   var pairs=['A','B','C','D','E','F','A','B','C','D','E','F'],order=[4,9,0,7,3,11,1,6,2,8,5,10],selected=null,matched=[],wrap=document.createElement('div');wrap.className='rd-pairs';
   function draw(){wrap.innerHTML='';order.forEach(function(k,pos){var b=btn(matched.indexOf(k)>=0?'MATCHED':'PROFILE '+(pos+1),function(){if(matched.indexOf(k)>=0)return;if(selected===null){selected=k;b.classList.add('selected');setStatus('SELECT SECOND PROFILE');}else{if(pairs[selected]===pairs[k]&&selected!==k){matched.push(selected,k);setStatus('PAIR ACCEPTED // '+pairs[k]);}else setStatus('NO MATCH // TRY ANOTHER PROFILE');selected=null;draw();if(matched.length===12)setStatus('SILHOUETTE LOCK OPEN // ALL SIX PAIRS MATCHED');}},matched.indexOf(k)>=0?'matched':'' );wrap.appendChild(b);});}
   field.appendChild(wrap);var actions=document.createElement('div');actions.className='rd-controls';actions.appendChild(btn('RESET PAIRS',function(){selected=null;matched=[];draw();setStatus('RESET // FIND SIX MATCHING PAIRS');}));field.appendChild(actions);draw();
  }else if(id==='green'){
   var values=[0,0,0,0,0,0],target=[1,0,1,1,0,1],wrap=document.createElement('div');wrap.className='rd-dials';
   function draw(){wrap.innerHTML='';values.forEach(function(v,i){var b=btn('MIRROR '+(i+1)+'\n'+(v?'\\':'/'),function(){values[i]^=1;draw();if(values.every(function(x,j){return x===target[j];}))setStatus('BEAMS ROUTED // ALL RECEIVERS MATCH');},'rd-dial');wrap.appendChild(b);});}
   field.appendChild(wrap);var actions=document.createElement('div');actions.className='rd-controls';actions.appendChild(btn('SHOW ROUTING KEY',function(){values=target.slice();draw();setStatus('ROUTING ACCEPTED // ALL COLOR PATHS REACH THEIR RECEIVERS');}));actions.appendChild(btn('RESET',function(){values=[0,0,0,0,0,0];draw();setStatus('RESET // ROTATE MIRRORS');}));field.appendChild(actions);draw();
  }else if(id==='purple'){
   var edges=[false,false,false,false],wrap=document.createElement('div');wrap.className='rd-loop';var names=['TOP EDGE','RIGHT EDGE','BOTTOM EDGE','LEFT EDGE'];
   function draw(){wrap.innerHTML='';edges.forEach(function(v,i){var b=btn(names[i]+'\n'+(v?'CONNECTED':'OPEN'),function(){edges[i]=!edges[i];draw();if(edges.every(Boolean))setStatus('CLOSED LOOP COMPLETE // CIRCUIT ACCEPTED');},v?'active':'');wrap.appendChild(b);});}
   field.appendChild(wrap);var actions=document.createElement('div');actions.className='rd-controls';actions.appendChild(btn('RESET LOOP',function(){edges=[false,false,false,false];draw();setStatus('RESET // COMPLETE ALL FOUR SIDES');}));field.appendChild(actions);draw();
  }else if(id==='timed'){
   var tasks=['RUN STARTUP → DIAGNOSTICS → DEPLOY','IDENTIFY THE FREIGHTER / DISARM THE DOOR CONTROL','USE FLOODLIGHT BEFORE DARK-AREA EXPLORATION','ENGAGE THE KRIN WITHOUT HITTING ARI OR ZACK','CLOSE THE SHUTTERS WHEN THE VIEWPORT BREACHES','PULSE THRUST TO RESCUE ZACK WITHOUT OVERHEATING','SHUT DOWN THE ADVANCING FORCE FIELD'];
   var done=[];var list=document.createElement('div');list.className='rd-switches';
   function draw(){list.innerHTML='';tasks.forEach(function(t,i){var b=btn((done.indexOf(i)>=0?'✓ ':'□ ')+t,function(){if(done.indexOf(i)<0)done.push(i);draw();if(done.length===tasks.length)setStatus('SEQUENCE REVIEW COMPLETE // ALL ACTION GATES ACKNOWLEDGED');});list.appendChild(b);});}
   field.appendChild(list);draw();
  }
 }
 select.addEventListener('change',render);render();
});
})();
