(function(){
'use strict';
function ready(fn){if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',fn);else fn();}
ready(function(){
 var root=document.getElementById('rd-puzzle-lab');if(!root||root.dataset.ready)return;root.dataset.ready='1';
 var select=document.getElementById('rd-puzzle-select'),field=document.getElementById('rd-playfield'),intro=document.getElementById('rd-puzzle-intro'),status=document.getElementById('rd-puzzle-status');
 var stages=['artemis','yellow','sundial','probe','blue','orbit','orange','green','purple','timed'];
 var titles={
 artemis:['ARTEMIS POWER GRID','Rotate the relay tiles to connect the central power core to every colored ship-system terminal. A valid path must be continuous; dead ends and disconnected branches do not count.'],
 yellow:['YELLOW DOOR // HEX LINE LOCK','Rotate the six outer hexagons. Each rotation changes the corresponding lines projected into the central hex. Fill every central line without skipping a sector.'],
 sundial:['ENGINE ROOM // SUN DIAL','Each control changes two hemispheres. Turn the six linked controls until every hemisphere is yellow.'],
 probe:['PROBE LOGIC CIRCUIT','Close every gate. A switch reverses its own gate and every other gate sharing one of its color codes.'],
 blue:['BLUE DOOR // HEX OVERLAP LOCK','Rotate the six outer hexagons. Their projected colored triangles move in the center. The lock accepts only when no two colored shapes overlap.'],
 orbit:['BLUE HALL // PLANETARY ALIGNMENT','Move the four controllable planets along their orbital tracks. Their combined gravitational phase determines the fifth planet. Place that uncontrolled body directly between the star and the observer to produce an eclipse.'],
 orange:['ORANGE HALL // SILHOUETTE MATCH','Freeze the matching silhouettes in pairs. Shapes can be mirrored; compare the outline, not just the orientation.'],
 green:['GREEN HALL // MIRROR ROUTING','Turn mirrors in the triangular field to route each colored beam to its flashing receiver. Beams may cross or mix at receiver points.'],
 purple:['VIOLET HALL // CLOSED-LOOP CONTEST','Build a closed polygon of four or more edges on the alien node field before the opposing logic system completes its own loop.'],
 timed:['FIELD OPERATIONS // ACTION GATES','These are interactive timing and decision drills from the campaign: startup/diagnostics/deploy, defensive fire discipline, emergency shutters, Zack’s shaft rescue, and force-field shutdown.']
 };
 var solved={};var currentIndex=0;
 function setStatus(s){status.textContent=s;}
 function btn(label,fn,cls){var b=document.createElement('button');b.type='button';b.textContent=label;if(cls)b.className=cls;b.addEventListener('click',fn);return b;}
 function resetField(){field.innerHTML='';}
 function finish(id,msg){solved[id]=true;setStatus(msg+' // STAGE COMPLETE');updateProgress();}
 function updateProgress(){
  var count=stages.filter(function(x){return solved[x];}).length;
  var p=document.getElementById('rd-campaign-progress');
  if(!p){p=document.createElement('div');p.id='rd-campaign-progress';p.className='rd-status';root.insertBefore(p,root.firstChild);}
  p.textContent='CAMPAIGN TRAINING RECORD // '+count+' OF '+stages.length+' CHALLENGES CLEARED';
  var next=document.getElementById('rd-next-stage');
  if(!next){next=btn('NEXT CAMPAIGN CHALLENGE',function(){var i=stages.findIndex(function(x){return !solved[x];});if(i<0){setStatus('ALL RECONSTRUCTED CHALLENGES COMPLETE');return;}select.value=stages[i];render();});next.id='rd-next-stage';next.className='rd-next-stage';root.appendChild(next);}
  next.disabled=count===stages.length;
 }
 function render(){
  var id=select.value;currentIndex=stages.indexOf(id);intro.textContent=titles[id][1];resetField();setStatus((solved[id]?'CLEARED // ':'ACTIVE // ')+titles[id][0]);
  if(id==='artemis'){
   var size=5,paths=[[2,2],[1,2],[0,2],[2,1],[2,0],[2,3],[2,4],[3,2],[4,2]],tiles=[];
   var links={0:[0,2],1:[0,2],2:[0,1,2,3],3:[0,2],4:[0,2],5:[0,2],6:[0,2],7:[0,2],8:[0,2]};
   var route=[{r:2,c:2,dirs:[0,1,2,3]},{r:1,c:2,dirs:[0,2]},{r:0,c:2,dirs:[2]},{r:2,c:1,dirs:[1,3]},{r:2,c:0,dirs:[3]},{r:2,c:3,dirs:[1,3]},{r:2,c:4,dirs:[1]},{r:3,c:2,dirs:[0,2]},{r:4,c:2,dirs:[2]}];
   var board=document.createElement('div');board.className='rd-circuit-board';
   for(var r=0;r<size;r++)for(var c=0;c<size;c++){
    var spec=route.find(function(x){return x.r===r&&x.c===c;});if(!spec)continue;
    var dirs=spec.dirs.slice(),turns=(r*3+c*2+1)%4;for(var t=0;t<turns;t++)dirs=dirs.map(function(d){return (d+1)%4;});
    var tile={r:r,c:c,base:spec.dirs.slice(),turns:turns,dirs:dirs};tiles.push(tile);
    var b=btn('╋',function(t){return function(){t.turns=(t.turns+1)%4;t.dirs=t.base.map(function(d){return (d+t.turns)%4;});draw();};}(tile),'rd-circuit-tile');
    b.dataset.r=r;b.dataset.c=c;b.setAttribute('aria-label','Rotate relay row '+(r+1)+' column '+(c+1));tile.button=b;board.appendChild(b);
   }
   field.appendChild(board);
   var legend=document.createElement('p');legend.className='rd-puzzle-foot';legend.textContent='CORE: CENTER CELL · SYSTEM TERMINALS: OUTER CELLS · ROTATE EACH RELAY 90° CLOCKWISE';field.appendChild(legend);
   function connected(){
    var start=tiles.find(function(x){return x.r===2&&x.c===2;}),seen=[start],q=[start];
    while(q.length){var a=q.shift();a.dirs.forEach(function(d){var nr=a.r+[-1,0,1,0][d],nc=a.c+[0,1,0,-1][d],n=tiles.find(function(x){return x.r===nr&&x.c===nc;});if(!n||seen.indexOf(n)>=0)return;if(n.dirs.indexOf((d+2)%4)>=0){seen.push(n);q.push(n);}});}
    return seen.length===tiles.length;
   }
   function draw(){tiles.forEach(function(x){x.button.textContent=x.dirs.map(function(d){return ['↑','→','↓','←'][d];}).join('');x.button.classList.toggle('connected',connected()&&x.dirs.length>0);});}
   var a=document.createElement('div');a.className='rd-controls';a.appendChild(btn('RESET RELAYS',function(){tiles.forEach(function(x){x.turns=0;x.dirs=x.base.slice();});draw();setStatus('RESET // CONNECT THE CORE TO ALL NINE RELAY POINTS');}));a.appendChild(btn('TEST POWER FLOW',function(){if(connected())finish(id,'POWER RESTORED // ALL RELAYS CONTINUOUS');else setStatus('POWER FAULT // ONE OR MORE RELAYS ARE MISALIGNED OR DISCONNECTED');}));field.appendChild(a);draw();
  }else if(id==='yellow'||id==='blue'){
   var seqs=id==='yellow'?[[2,2,3,3,3,4,4,4,4,5,5,5,5,5],[2,2,3,3,3,3,4,5,5,5,6,6,6,6,6],[1,2,2,3,3,3,4,4,4,4,5,5,5,5,5]]:[[2,2,4,4,4,4,5],[1,2,2,2],[1,1,1,2,2,4,4,4,6,6]];
   var level=0,counts=[0,0,0,0,0,0],labels=['A','B','C','D','E','F'];
   var grid=document.createElement('div');grid.className='rd-dials';field.appendChild(grid);
   var center=document.createElement('div');center.className='rd-hex-center';field.appendChild(center);
   function targetCounts(){var x=Array(6).fill(0);seqs[level].forEach(function(n){x[n-1]++;});return x;}
   function draw(){grid.innerHTML='';labels.forEach(function(l,i){var b=btn(l+' // '+counts[i]+' ROTATIONS',function(){counts[i]++;draw();},'rd-dial');grid.appendChild(b);});var t=targetCounts();center.textContent=(id==='yellow'?'CENTRAL LINE COVERAGE':'CENTRAL TRIANGLE OVERLAP')+' // '+counts.map(function(v,i){return labels[i]+':'+v+'/'+t[i];}).join(' · ');}
   var actions=document.createElement('div');actions.className='rd-controls';
   var lev=document.createElement('select');seqs.forEach(function(_,i){var o=document.createElement('option');o.value=i;o.textContent='DIFFICULTY / LOCK '+(i+1);lev.appendChild(o);});lev.addEventListener('change',function(){level=Number(lev.value);counts=[0,0,0,0,0,0];draw();setStatus('LOCK '+(level+1)+' // ROTATE THE OUTER HEXES');});actions.appendChild(lev);
   actions.appendChild(btn('CHECK CENTRAL FIELD',function(){var t=targetCounts(),ok=counts.every(function(v,i){return v===t[i];});if(ok)finish(id,id==='yellow'?'ALL CENTRAL LINES FILLED':'NO TRIANGLES OVERLAP');else setStatus('LOCK REJECTED // COMPARE EACH OUTER HEX ROTATION COUNT WITH THE CENTRAL FIELD');}));
   actions.appendChild(btn('RESET LOCK',function(){counts=[0,0,0,0,0,0];draw();setStatus('RESET // ROTATE THE SIX OUTER HEXES');}));field.appendChild(actions);draw();
   var note=document.createElement('p');note.className='rd-puzzle-foot';note.textContent='TRAINING RECONSTRUCTION: the original rotates polygon segments and evaluates the central geometry. This build uses documented walkthrough move counts as a verifiable practice lock, not the original proprietary artwork.';field.appendChild(note);
  }else if(id==='sundial'){
   var state=[0,0,0,0,0,0],pairs=[[0,3],[1,4],[2,5],[3,0],[4,1],[5,2]],moves=[1,3,5,6,2,2,6,6],moveIndex=0;
   var wrap=document.createElement('div');wrap.className='rd-dials';
   function draw(){wrap.innerHTML='';state.forEach(function(v,i){var b=btn('HEMISPHERE '+(i+1)+'\\n'+(v?'YELLOW':'DARK'),function(){pairs[i].forEach(function(k){state[k]^=1;});draw();},'rd-dial');wrap.appendChild(b);});}
   var actions=document.createElement('div');actions.className='rd-controls';
   actions.appendChild(btn('CHECK SUN DIAL',function(){if(state.every(Boolean))finish(id,'ALL SIX HEMISPHERES YELLOW');else setStatus('NOT STABLE // EACH PRESS CHANGES A PAIR OF HEMISPHERES');}));
   actions.appendChild(btn('RESET',function(){state=[0,0,0,0,0,0];draw();setStatus('RESET // CLICK CONTROLS TO CHANGE LINKED PAIRS');}));actions.appendChild(btn('WALKTHROUGH MOVE SEQUENCE',function(){moves.forEach(function(n){pairs[n-1].forEach(function(k){state[k]^=1;});});draw();setStatus('REFERENCE SEQUENCE APPLIED // CHECK THE RESULT');}));field.appendChild(wrap);field.appendChild(actions);draw();
   var note=document.createElement('p');note.className='rd-puzzle-foot';note.textContent='The manual confirms each control flips two hemispheres. The pair wiring is reconstructed for this training board; the published move sequence is included as a reference.';field.appendChild(note);
  }else if(id==='probe'){
   var colors=[['R','B'],['G'],['R','Y'],['B','Y'],['R','B'],['G','Y'],['R'],['B'],['Y']],state=[1,1,0,1,0,1,0,1,0],wrap=document.createElement('div');wrap.className='rd-switches';
   function press(i){var chosen=colors[i];state=state.map(function(v,j){var shared=colors[j].some(function(c){return chosen.indexOf(c)>=0;});return shared?(v^1):v;});draw();}
   function draw(){wrap.innerHTML='';state.forEach(function(v,i){var b=btn('GATE '+(i+1)+'\\n'+(v?'OPEN':'CLOSED')+' // '+colors[i].join('+'),function(){press(i);},v?'on':'');wrap.appendChild(b);});}
   var actions=document.createElement('div');actions.className='rd-controls';actions.appendChild(btn('CHECK GATES',function(){if(state.every(function(x){return x===0;}))finish(id,'PROBE ONLINE // ALL GATES CLOSED');else setStatus('CIRCUIT ACTIVE // CLOSE EVERY GATE');}));actions.appendChild(btn('RESET',function(){state=[1,1,0,1,0,1,0,1,0];draw();setStatus('RESET // COLOR CODES DETERMINE WHICH GATES REVERSE');}));field.appendChild(wrap);field.appendChild(actions);draw();
   var note=document.createElement('p');note.className='rd-puzzle-foot';note.textContent='Clicking a colored switch reverses its gate and all other gates sharing at least one displayed color code. Color memberships are a reconstructed board; the manual confirms the shared-code rule.';field.appendChild(note);
  }else if(id==='orbit'){
   var values=[330,180,90,40],wrap=document.createElement('div');wrap.className='rd-orbit-wrap';var svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 360 300');svg.className.baseVal='rd-orbit-svg';var controls=document.createElement('div');controls.className='rd-orbit-controls';wrap.appendChild(svg);wrap.appendChild(controls);field.appendChild(wrap);
   function node(tag,attrs){var n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.keys(attrs).forEach(function(k){n.setAttribute(k,attrs[k]);});svg.appendChild(n);return n;}
   function eclipse(){var phase=(values[0]+values[1]+values[2]+values[3]*2)%360;return Math.abs(((phase-180+540)%360)-180)<5;}
   function draw(){svg.innerHTML='';[40,75,110,145].forEach(function(r){node('circle',{cx:180,cy:145,r:r,fill:'none',stroke:'#1a6047','stroke-dasharray':'4 5'});});node('circle',{cx:180,cy:145,r:13,fill:'#f6c96c'});node('text',{x:180,y:122,fill:'#f6c96c','text-anchor':'middle','font-size':'9'}).textContent='STAR';values.forEach(function(v,i){var r=[40,75,110,145][i],a=v*Math.PI/180,x=180+Math.cos(a)*r,y=145+Math.sin(a)*r;node('circle',{cx:x,cy:y,r:7,fill:['#72ffc3','#62b8ff','#e2d86a','#ff9a70'][i]});node('text',{x:x+9,y:y-7,fill:'#c6f7df','font-size':'9'}).textContent='ABCD'[i];});var a=(values[0]+values[1]+values[2]+values[3]*2)%360*Math.PI/180;var x=180+Math.cos(a)*178,y=145+Math.sin(a)*178;node('circle',{cx:x,cy:y,r:5,fill:'#fff'});node('text',{x:180,y:286,fill:'#7eb79e','text-anchor':'middle','font-size':'9'}).textContent='UNCONTROLLED FIFTH PLANET';}
   values.forEach(function(v,i){var label=document.createElement('label');label.textContent='PLANET '+ 'ABCD'[i]+' // '+v+'°';var input=document.createElement('input');input.type='range';input.min='0';input.max='359';input.value=v;input.addEventListener('input',function(){values[i]=Number(this.value);label.firstChild.textContent='PLANET '+'ABCD'[i]+' // '+values[i]+'°';draw();});label.appendChild(input);controls.appendChild(label);});
   var actions=document.createElement('div');actions.className='rd-controls';actions.appendChild(btn('CHECK ECLIPSE',function(){if(eclipse())finish(id,'FIFTH PLANET ALIGNED // ECLIPSE');else setStatus('NO ECLIPSE // ADJUST THE FOUR ORBITAL BODIES');}));actions.appendChild(btn('LOAD WALKTHROUGH A',function(){values=[330,0,135,40];controls.querySelectorAll('input').forEach(function(x,i){x.value=values[i];x.previousSibling.textContent='PLANET '+'ABCD'[i]+' // '+values[i]+'°';});draw();setStatus('REFERENCE POSITIONS LOADED // FINE ADJUSTMENT MAY BE NEEDED');}));actions.appendChild(btn('RESET ORBITS',function(){values=[0,0,0,0];controls.querySelectorAll('input').forEach(function(x,i){x.value=0;x.previousSibling.textContent='PLANET '+'ABCD'[i]+' // 0°';});draw();}));field.appendChild(actions);draw();
   var note=document.createElement('p');note.className='rd-puzzle-foot';note.textContent='The manual confirms four movable planets and a fifth uncontrolled body. The fifth-body phase model here is an original, simplified orbital reconstruction; it is not claimed to reproduce the game’s hidden calculation.';field.appendChild(note);
  }else if(id==='orange'){
   var shapes=['C','SQUARE-L','SQUARE-S','ARC-¾','HALF-SLOT','O'],cards=shapes.concat(shapes).map(function(s,i){return {shape:s,id:i,matched:false};}),order=[4,9,0,7,3,11,1,6,2,8,5,10],first=null,locked=false,wrap=document.createElement('div');wrap.className='rd-pairs';
   function draw(){wrap.innerHTML='';order.forEach(function(k,pos){var c=cards[k],b=btn(c.matched?'MATCHED':c.shape,function(){if(locked||c.matched)return;if(first===null){first=c; b.classList.add('selected');setStatus('FIRST PROFILE HELD // SELECT ITS MATCH');}else{var prev=first;first=null;locked=true;if(prev.shape===c.shape&&prev.id!==c.id){prev.matched=true;c.matched=true;setStatus('MATCH ACCEPTED // '+c.shape);}else setStatus('NO MATCH // MIRRORED SHAPES MAY STILL MATCH');draw();setTimeout(function(){locked=false;if(cards.every(function(x){return x.matched;}))finish(id,'ALL SIX SILHOUETTE PAIRS MATCHED');},650);}} ,c.matched?'matched':'' );wrap.appendChild(b);});}
   field.appendChild(wrap);var actions=document.createElement('div');actions.className='rd-controls';actions.appendChild(btn('SHUFFLE / RESET',function(){cards.forEach(function(x){x.matched=false;});first=null;order.sort(function(){return Math.random()-.5;});draw();setStatus('RESET // MATCH ALL SIX PAIRS');}));field.appendChild(actions);draw();
   var note=document.createElement('p');note.className='rd-puzzle-foot';note.textContent='Profiles are represented by names rather than copied game artwork. Pair identities follow the walkthrough: C, large square, small square, mirrored three-quarter circle, slotted half-circle, and O.';field.appendChild(note);
  }else if(id==='green'){
   var rows=8,cols=9,mirrors=[],lastReached=0;var board=document.createElement('div');board.className='rd-mirror-grid';
   for(var rr=0;rr<rows;rr++)for(var cc=0;cc<cols;cc++){if((rr+cc)%3!==0)continue;var m={r:rr,c:cc,slash:((rr*7+cc*3)%2===0)};var b=btn(m.slash?'/':'\\\\',function(mm){return function(){mm.slash=!mm.slash;mm.button.textContent=mm.slash?'/':'\\\\';drawBeams();};}(m),'rd-mirror');m.button=b;mirrors.push(m);board.appendChild(b);}
   var canvas=document.createElement('canvas');canvas.className='rd-beam-canvas';canvas.width=540;canvas.height=360;field.appendChild(board);field.appendChild(canvas);
   function drawBeams(){var ctx=canvas.getContext('2d');ctx.clearRect(0,0,540,360);var targets=[{x:500,y:40,c:'#ff6868'},{x:500,y:180,c:'#66e6ff'},{x:500,y:320,c:'#f6e76b'}];targets.forEach(function(t){ctx.fillStyle=t.c;ctx.beginPath();ctx.arc(t.x,t.y,7,0,Math.PI*2);ctx.fill();});var starts=[{x:0,y:40,dx:1,dy:0,c:'#ff6868'},{x:0,y:180,dx:1,dy:0,c:'#66e6ff'},{x:0,y:320,dx:1,dy:0,c:'#f6e76b'}];var reached=0;starts.forEach(function(s){var x=s.x,y=s.y,dx=s.dx,dy=s.dy;ctx.strokeStyle=s.c;ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x,y);for(var k=0;k<80;k++){x+=dx*12;y+=dy*12;var hit=mirrors.find(function(m){return Math.abs(x-(m.c*60+30))<8&&Math.abs(y-(m.r*45+22))<8;});if(hit){if(hit.slash){var ndx=-dy,ndy=-dx;dx=ndx;dy=ndy;}else{var ndx=dy,ndy=dx;dx=ndx;dy=ndy;}}ctx.lineTo(x,y);if(x>=500&&targets.some(function(t){return Math.abs(y-t.y)<10&&t.c===s.c;})){reached++;break;}if(x<0||x>540||y<0||y>360)break;}ctx.stroke();});lastReached=reached;setStatus('BEAM ROUTING // '+reached+' OF 3 RECEIVERS REACHED');}
   field.appendChild(canvas);var actions=document.createElement('div');actions.className='rd-controls';actions.appendChild(btn('CHECK RECEIVERS',function(){if(lastReached===3)finish(id,'RECEIVER FIELD ENERGIZED');else setStatus('ROUTING INCOMPLETE // REPOSITION MIRRORS TO GUIDE ALL THREE BEAMS');}));actions.appendChild(btn('RESET MIRRORS',function(){mirrors.forEach(function(m,i){m.slash=(i%2===0);m.button.textContent=m.slash?'/':'\\\\';});drawBeams();}));field.appendChild(actions);drawBeams();
   var note=document.createElement('p');note.className='rd-puzzle-foot';note.textContent='This is a playable ray-routing reconstruction with interactive mirrors and live beam traces. The original uses a triangular cell grid; the walkthrough’s exact mirror coordinates are retained in the R&D reference notes.';field.appendChild(note);
  }else if(id==='purple'){
   var pts=[[150,20],[230,65],[230,155],[150,200],[70,155],[70,65],[150,110]],edges=[[0,1],[1,2],[2,3],[3,4],[4,5],[5,0],[0,6],[1,6],[2,6],[3,6],[4,6],[5,6]],claimed={},turn='player',svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 300 220');svg.classList.add('rd-loop-svg');field.appendChild(svg);
   function line(a,b,color){var n=document.createElementNS('http://www.w3.org/2000/svg','line');n.setAttribute('x1',pts[a][0]);n.setAttribute('y1',pts[a][1]);n.setAttribute('x2',pts[b][0]);n.setAttribute('y2',pts[b][1]);n.setAttribute('stroke',color);n.setAttribute('stroke-width','5');n.setAttribute('stroke-linecap','round');svg.appendChild(n);}
   function cycleCheck(owner){var adj={};edges.forEach(function(e,i){if(claimed[i]!==owner)return;(adj[e[0]]||(adj[e[0]]=[])).push(e[1]);(adj[e[1]]||(adj[e[1]]=[])).push(e[0]);});var found=false;Object.keys(adj).forEach(function(k){if(adj[k].length>=2){var seen={},stack=[Number(k)];while(stack.length){var n=stack.pop();if(seen[n])continue;seen[n]=true;(adj[n]||[]).forEach(function(v){if(v===Number(k)&&Object.keys(seen).length>=4)found=true;else if(!seen[v])stack.push(v);});}}});return found;}
   function draw(){svg.innerHTML='';edges.forEach(function(e,i){line(e[0],e[1],claimed[i]==='player'?'#59ffbd':claimed[i]==='ai'?'#ff7777':'#244b3a');});pts.forEach(function(p,i){var c=document.createElementNS('http://www.w3.org/2000/svg','circle');c.setAttribute('cx',p[0]);c.setAttribute('cy',p[1]);c.setAttribute('r','9');c.setAttribute('fill','#b9ffdd');svg.appendChild(c);});}
   var actions=document.createElement('div');actions.className='rd-controls';edges.forEach(function(e,i){actions.appendChild(btn('EDGE '+(i+1),function(){if(turn!=='player'||claimed[i])return;claimed[i]='player';if(cycleCheck('player')){draw();finish(id,'PLAYER COMPLETED A CLOSED LOOP');return;}turn='ai';var open=edges.map(function(_,j){return j;}).filter(function(j){return !claimed[j];});if(open.length){var choice=open.find(function(j){var old=claimed[j];claimed[j]='ai';var wins=cycleCheck('ai');claimed[j]=old;return wins;});if(choice===undefined)choice=open[Math.floor(Math.random()*open.length)];claimed[choice]='ai';if(cycleCheck('ai')){draw();setStatus('OPPOSING LOGIC COMPLETED ITS LOOP // RETRY');return;}}turn='player';draw();setStatus('YOUR TURN // CLAIM AN EDGE TO BUILD A FOUR-SIDED LOOP');}));});actions.appendChild(btn('RESET CONTEST',function(){claimed={};turn='player';draw();setStatus('NEW CONTEST // COMPLETE A LOOP BEFORE THE OPPONENT');}));field.appendChild(actions);draw();
   var note=document.createElement('p');note.className='rd-puzzle-foot';note.textContent='The game’s violet challenge is a competitive polygon/loop contest. This node-and-edge board is a new playable reconstruction, not a reproduction of the original AI.';field.appendChild(note);
  }else if(id==='timed'){
   var tasks=[{name:'PROBE DEPLOYMENT',steps:['STARTUP','DIAGNOSTICS','DEPLOY'],time:0},{name:'KRINN FIRE DISCIPLINE',steps:['TARGET KRINN','FIRE — KEEP ARI CLEAR','FIRE — KEEP ZACK CLEAR'],time:0},{name:'EMERGENCY SHUTTERS',steps:['ANALYSIS','SELECT VIOLET','CLOSE SHUTTERS'],time:0},{name:'ZACK SHAFT RESCUE',steps:['WAIT FOR INDICATOR LOW','THRUST','THRUST','THRUST'],time:0},{name:'FORCE-FIELD SHUTDOWN',steps:['ANALYZE FIELD','TRANSMIT 654321'],time:0}],idx=0,step=0,box=document.createElement('div');box.className='rd-action-drill';field.appendChild(box);
   function draw(){box.innerHTML='';if(idx>=tasks.length){finish(id,'ALL ACTION GATES COMPLETED');return;}var task=tasks[idx];var h=document.createElement('h3');h.textContent=task.name;box.appendChild(h);var p=document.createElement('p');p.textContent='ACTION '+(step+1)+' OF '+task.steps.length+' // '+task.steps[step];box.appendChild(p);box.appendChild(btn('EXECUTE ACTION',function(){step++;if(step>=task.steps.length){idx++;step=0;setStatus('ACTION ACCEPTED // NEXT OPERATION');}draw();}));box.appendChild(btn('RESTART CURRENT DRILL',function(){step=0;draw();setStatus('DRILL RESET');}));}
   draw();
  }
 }
 select.addEventListener('change',render);updateProgress();render();
});
})();