(function(){
'use strict';
if(window.vigilMech3DViewLoaded)return;window.vigilMech3DViewLoaded=true;
var css=document.createElement('style');css.textContent='#vigil-mech-3d #m3-environment-webgl{display:block;width:100%;height:clamp(220px,34vh,380px);min-height:220px;background:radial-gradient(ellipse at 50% 55%,#152a1c,#020806 78%);border:1px solid #286344;touch-action:none}#vigil-mech-3d #m3-environment-pane{margin-top:12px}#vigil-mech-3d{display:none;position:fixed;inset:0;z-index:99999;background:#010604;color:#bfffd7;font:12px/1.4 ui-monospace,monospace;overflow:auto;padding:10px;box-sizing:border-box}#vigil-mech-3d *{box-sizing:border-box;min-width:0}#vigil-mech-3d.open{display:block}#vigil-mech-3d .mh{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;border-bottom:1px solid #286344;padding:8px}#vigil-mech-3d button,#vigil-mech-3d select{max-width:100%;background:#092116;color:#bfffd7;border:1px solid #397b56;padding:8px;font:inherit;cursor:pointer;white-space:normal;overflow-wrap:anywhere}#vigil-mech-3d button:active,#vigil-mech-3d button.active{background:#1c6841;border-color:#c5b56d;color:#fff0b4}#vigil-mech-3d .layout{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(280px,.85fr);gap:12px;margin-top:10px;align-items:start}#vigil-mech-3d .visual-column,#vigil-mech-3d .cockpit-column{min-width:0;width:100%}#vigil-mech-3d canvas{display:block;width:100%;height:clamp(260px,48vh,520px);background:radial-gradient(ellipse at 50% 55%,#102c1c,#020806 72%);border:1px solid #286344}#vigil-mech-3d .pane{border:1px solid #28533a;background:#041009;padding:10px;margin:10px 0 0;min-width:0;max-width:100%;overflow:hidden}#vigil-mech-3d h3{color:#9de7ba;font-size:11px;letter-spacing:1px;margin:0 0 8px}#vigil-mech-3d .stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin-top:8px}#vigil-mech-3d .compass{display:block;width:min(100%,220px);height:auto;margin:8px auto;background:radial-gradient(circle,#0a2114,#010604 72%);border:1px solid #28533a}#vigil-mech-3d .stats div{border:1px solid #234531;padding:6px;overflow:hidden}#vigil-mech-3d .stats b{display:block;color:#e0ffe9;font-size:16px;overflow-wrap:anywhere}#vigil-mech-3d .controls{display:flex;gap:6px;flex-wrap:wrap;align-items:center}#vigil-mech-3d .controls button{flex:0 1 auto}#vigil-mech-3d .equipment-picker{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;max-height:210px;overflow:auto;padding:2px}#vigil-mech-3d .equipment-picker button{text-align:left;min-height:42px;display:flex;flex-direction:column;justify-content:center;gap:2px;overflow-wrap:anywhere}#vigil-mech-3d .equipment-picker small{color:#8db99a;font-size:9px}#vigil-mech-3d .selected-module{border:1px solid #9b8950;background:#0b1a10;padding:10px;margin-top:9px;min-height:125px;overflow:hidden}#vigil-mech-3d .selected-module h4{margin:0 0 8px;color:#f0dfa2;overflow-wrap:anywhere}#vigil-mech-3d .muted{color:#78a98a;font-size:10px;overflow-wrap:anywhere}#vigil-mech-3d .loadout{max-height:140px;overflow:auto;overflow-wrap:anywhere}#vigil-mech-3d .fusion-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px}#vigil-mech-3d .fusion-metrics div{border:1px solid #234531;padding:6px;min-width:0}#vigil-mech-3d .fusion-metrics b{display:block;color:#e0ffe9;font-size:14px;overflow-wrap:anywhere}#vigil-mech-3d .fusion-track-list{max-height:190px;overflow:auto;margin-top:8px}#vigil-mech-3d .fusion-track{border-top:1px solid #234531;padding:6px 2px;overflow-wrap:anywhere}#vigil-mech-3d .fusion-track strong{color:#e0ffe9}#vigil-mech-3d .fusion-track small{display:block;color:#78a98a;font-size:9px}@media(max-width:820px){#vigil-mech-3d .layout{grid-template-columns:minmax(0,1fr)}#vigil-mech-3d canvas{height:40vh;min-height:240px}}@media(max-width:420px){#vigil-mech-3d{padding:5px}#vigil-mech-3d .equipment-picker{grid-template-columns:minmax(0,1fr)}#vigil-mech-3d .stats b{font-size:13px}#vigil-mech-3d .mh strong{max-width:68%}}';document.head.appendChild(css);
var layoutCss=document.createElement('style');
layoutCss.textContent='#vigil-mech-3d{width:100vw;height:100vh;height:100dvh;overflow:hidden;padding:0;display:none;flex-direction:column}#vigil-mech-3d.open{display:flex}#vigil-mech-3d .mh{flex:0 0 auto;padding:10px 14px}#vigil-mech-3d .layout{flex:1 1 auto;min-height:0;overflow:hidden;margin:0;padding:10px 12px;align-items:stretch}#vigil-mech-3d .visual-column,#vigil-mech-3d .cockpit-column{min-height:0;overflow:auto;overscroll-behavior:contain;padding:0 2px 10px}#vigil-mech-3d #m3-compass-pane{flex:0 0 auto;width:100%;margin:0;padding:5px 12px 8px;border-width:1px 0 0;background:#031009}#vigil-mech-3d #m3-compass-pane h3{margin:0;text-align:center}#vigil-mech-3d #m3-compass-pane .compass{width:112px;max-height:112px;margin:2px auto}#vigil-mech-3d #m3-compass-pane .muted{text-align:center}@media(max-width:820px){#vigil-mech-3d .layout{overflow:auto;display:block;padding:7px}#vigil-mech-3d .visual-column,#vigil-mech-3d .cockpit-column{overflow:visible}#vigil-mech-3d #m3-compass-pane{position:relative}#vigil-mech-3d #m3-compass-pane .compass{width:96px}}#vigil-mech-3d .m3-hud-kicker{font-size:9px;letter-spacing:1.3px;color:#87b99a}#vigil-mech-3d .m3-role-line{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;align-items:center;margin:5px 0 9px;color:#d8f5df}#vigil-mech-3d .m3-weapon-groups{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}#vigil-mech-3d .m3-weapon-group{border:1px solid #28533a;background:#020906;min-width:0}#vigil-mech-3d .m3-weapon-group.active{border-color:#d7bd69;box-shadow:inset 0 0 0 1px #d7bd6944}#vigil-mech-3d .m3-group-head{display:flex;width:100%;align-items:center;justify-content:space-between;text-align:left;background:#071a10;color:#d7f5df;border:0;border-bottom:1px solid #234a33;padding:7px;font:inherit;cursor:pointer}#vigil-mech-3d .m3-weapon-group.active .m3-group-head{background:#263016;color:#fff0ae}#vigil-mech-3d .m3-group-head strong{font-size:15px}#vigil-mech-3d .m3-group-head small{font-size:9px;color:#91b89e}#vigil-mech-3d .m3-group-list{padding:5px;display:grid;gap:5px;min-height:28px}#vigil-mech-3d .m3-weapon-module{border-top:1px solid #1d3e2b;padding:6px 2px;min-width:0}#vigil-mech-3d .m3-weapon-module.destroyed{opacity:.42;filter:grayscale(1)}#vigil-mech-3d .m3-weapon-module-head{display:flex;justify-content:space-between;gap:6px;align-items:start}#vigil-mech-3d .m3-weapon-module-head strong{font-size:10px;color:#def8e5;overflow-wrap:anywhere}#vigil-mech-3d .m3-weapon-module-head small{font-size:8px;color:#83ad92}#vigil-mech-3d .m3-weapon-assignment{margin:5px 0;width:100%;padding:4px;background:#07170e;color:#c8efd4;border:1px solid #315c40;font:9px monospace}#vigil-mech-3d .m3-weapon-readout{display:grid;grid-template-columns:auto 1fr;gap:3px 6px;font-size:9px;color:#93b99d}#vigil-mech-3d .m3-weapon-readout b{color:#e0f4e4;text-align:right;font-weight:600}#vigil-mech-3d .m3-meter{height:5px;background:#15271b;border:1px solid #34543b;overflow:hidden;margin:3px 0 5px}#vigil-mech-3d .m3-meter span{display:block;height:100%;width:0;background:#56d58d;transition:width .12s linear}#vigil-mech-3d .m3-meter.heat span{background:#d4a44d}#vigil-mech-3d .m3-meter.integrity span{background:#72bd8c}#vigil-mech-3d .m3-weapon-module.destroyed .m3-meter span{width:0!important}#vigil-mech-3d .m3-group-actions{display:flex;gap:5px;flex-wrap:wrap;margin:8px 0}#vigil-mech-3d .m3-group-actions button{font-size:9px;padding:7px 9px}#vigil-mech-3d .m3-unassigned{border:1px dashed #34583d;padding:6px;margin-top:7px}#vigil-mech-3d .m3-reticle-panel{display:grid;grid-template-columns:82px minmax(0,1fr);gap:9px;align-items:center;margin-top:8px;padding:8px;border:1px solid #315d42;background:#020906}#vigil-mech-3d .m3-reticle-art{height:76px;display:grid;place-items:center;border:1px solid #315d42;background:radial-gradient(circle,#0b2115,#010503 75%);color:#7fffb0;font-size:39px;font-family:monospace}#vigil-mech-3d .m3-reticle-art.arc{color:#e2c36b}#vigil-mech-3d .m3-reticle-art.lock{color:#e5b66a}#vigil-mech-3d .m3-reticle-art.sniper{color:#c9f5d6}#vigil-mech-3d .m3-reticle-art.spread{color:#81d9a0}#vigil-mech-3d .m3-reticle-copy strong{display:block;color:#dff8e6;font-size:10px}#vigil-mech-3d .m3-reticle-copy small{display:block;color:#89b497;font-size:9px;margin-top:4px;line-height:1.45}#vigil-mech-3d #m3-weapon-pip{display:none;width:100%;height:96px;margin-top:7px;border:1px solid #8bc6a0;background:#020906}#vigil-mech-3d #m3-role-display{border-left:3px solid #609b71;padding:8px 10px;background:#05110a;margin-top:8px}#vigil-mech-3d #m3-role-display strong{display:block;color:#d9f4e0;letter-spacing:.8px;font-size:10px}#vigil-mech-3d #m3-role-display p{margin:4px 0 0;color:#91b79b;font-size:9px;line-height:1.5}#vigil-mech-3d .m3-role-readouts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px;margin-top:7px}
#vigil-mech-3d .m3-role-readout{display:flex;justify-content:space-between;gap:6px;padding:5px;border:1px solid #1e402c;background:#020905;min-width:0}
#vigil-mech-3d .m3-role-readout span{font-size:8px;color:#83ac91;letter-spacing:.4px}
#vigil-mech-3d .m3-role-readout strong{font-size:9px;color:#dbf5e1;text-align:right;overflow-wrap:anywhere}
#vigil-mech-3d[data-role="scout"] .m3-role-readout{border-color:#27634a}
#vigil-mech-3d[data-role="sniper"] .m3-role-readout{border-color:#365869}
#vigil-mech-3d[data-role="heavy-gunner"] .m3-role-readout{border-color:#625232}
#vigil-mech-3d[data-role="tactics-commander"] .m3-role-readout{border-color:#32616a}
@media(max-width:420px){#vigil-mech-3d .m3-role-readouts{grid-template-columns:1fr}}#vigil-mech-3d[data-role="heavy-gunner"] #m3-role-display{border-left-color:#d2ad55}#vigil-mech-3d[data-role="sniper"] #m3-role-display{border-left-color:#a9d7e9}#vigil-mech-3d[data-role="tactics-commander"] #m3-role-display{border-left-color:#79c9d4}#vigil-mech-3d[data-cockpit="CP-H"],#vigil-mech-3d[data-cockpit="CP-XH"]{border-top:3px solid #4e7259}#vigil-mech-3d[data-cockpit="CP-XH"] .m3-weapon-groups{grid-template-columns:repeat(4,minmax(0,1fr))}@media(max-width:820px){#vigil-mech-3d[data-cockpit="CP-XH"] .m3-weapon-groups{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:420px){#vigil-mech-3d .m3-weapon-groups{grid-template-columns:1fr}#vigil-mech-3d .m3-reticle-panel{grid-template-columns:64px minmax(0,1fr)}#vigil-mech-3d .m3-reticle-art{height:64px;font-size:31px}}';
document.head.appendChild(layoutCss);
var root=document.createElement('section');root.id='vigil-mech-3d';root.setAttribute('role','dialog');root.setAttribute('aria-modal','true');root.innerHTML='<div class="mh"><strong>VIGIL // HOUND LAND SYSTEMS // 3D PILOT STATION</strong><span id="m3-unit">NO MECH SELECTED</span><button id="m3-close">RETURN TO HANGER</button></div><div class="layout"><div class="visual-column"><div id="m3-webgl-host" aria-label="Actual HOUND WebGL assembly renderer"></div><div class="pane" id="m3-environment-pane"><h3>TACTICAL ENVIRONMENT // SENSOR-FUSED WEBGL</h3><canvas id="m3-environment-webgl" aria-label="3D simulated terrain environment rendered from installed mech sensor capabilities"></canvas><p class="muted" id="m3-environment-status">WAITING FOR INSTALLED SENSOR PROFILE</p></div><div class="stats"><div><span class="muted">ACTUAL HEADING</span><b id="m3-heading">---°</b></div><div><span class="muted">ORDERED COURSE</span><b id="m3-course">---°</b></div><div><span class="muted">GROUND SPEED</span><b id="m3-speed">0.000</b></div></div><div class="pane" id="m3-compass-pane"><h3>INERTIAL COMPASS // ACTUAL HEADING + ORDERED COURSE</h3><svg class="compass" viewBox="0 0 220 220" role="img" aria-label="Mech inertial compass showing actual heading and ordered course"><circle cx="110" cy="110" r="91" fill="none" stroke="#397b56" stroke-width="2"/><circle cx="110" cy="110" r="76" fill="none" stroke="#28533a" stroke-dasharray="2 5"/><g stroke="#8db99a" stroke-width="2"><path d="M110 13V30 M110 190V207 M13 110H30 M190 110H207 M41 41L53 53 M167 167L179 179 M179 41L167 53 M53 167L41 179"/></g><g fill="#9de7ba" font-size="11" text-anchor="middle"><text x="110" y="10">N</text><text x="214" y="114">E</text><text x="110" y="219">S</text><text x="6" y="114">W</text></g><g id="m3-course-marker" transform="rotate(0 110 110)"><path d="M110 25L104 47L110 42L116 47Z" fill="#f0dfa2" stroke="#f0dfa2"/></g><g id="m3-compass-needle" transform="rotate(0 110 110)"><path d="M110 37L101 111L110 101L119 111Z" fill="#4fffb0" stroke="#c5ffe0" stroke-width="1"/><path d="M110 183L101 109L110 119L119 109Z" fill="#315d45" stroke="#8db99a" stroke-width="1"/></g><circle cx="110" cy="110" r="5" fill="#e0ffe9"/></svg><div class="muted" style="text-align:center">GREEN = ACTUAL // GOLD = COMMANDED</div></div><div class="pane" id="m3-navigation-pane"><h3>MECH NAVIGATION // INSTALLED CONTROL SYSTEMS</h3><div class="muted" id="m3-navigation-note">Checking mobility and control modules…</div><div class="controls" id="m3-navigation-controls"></div><p class="muted" id="m3-status">Awaiting selected HOUND telemetry.</p></div></div><div class="cockpit-column"><div class="pane" id="m3-weapon-hud"><div class="m3-hud-kicker">WEAPON CONTROL // GROUPS 1–4</div><div class="m3-role-line"><strong id="m3-weapon-hud-title">HOUND WEAPON SYSTEMS</strong><span id="m3-cockpit-tier">COCKPIT —</span></div><div class="m3-weapon-groups" id="m3-weapon-groups"></div><div class="m3-unassigned"><div class="m3-hud-kicker">UNASSIGNED WEAPON MODULES</div><div class="m3-group-list" id="m3-weapon-unassigned">NONE</div></div><div class="m3-group-actions"><button type="button" id="m3-group-arm">ARM GROUP</button><button type="button" id="m3-group-fire">FIRE GROUP</button><button type="button" id="m3-group-reload">RELOAD GROUP</button><button type="button" id="m3-group-safe">SAFE GROUP</button></div><div class="m3-reticle-panel"><div class="m3-reticle-art" id="m3-reticle-art">＋</div><div class="m3-reticle-copy"><strong id="m3-reticle-title">NORMAL SCOPE // SELECT A WEAPON GROUP</strong><small id="m3-reticle-detail">RETICLE AND TARGETING PHYSICS WILL FOLLOW THE ACTIVE GROUP.</small></div></div><canvas id="m3-weapon-pip" width="480" height="180" aria-label="Digital weapon optic picture-in-picture from the rendered environment view"></canvas><div id="m3-role-display"><strong id="m3-role-title">SOLDIER // MEDIUM COCKPIT</strong><p id="m3-role-detail">Balanced combat systems and weapon telemetry.</p><div class="m3-role-readouts" id="m3-role-readouts"></div></div></div><div class="pane"><h3>COCKPIT // INSTALLED EQUIPMENT SELECTOR</h3><p class="muted">Select a fitted component or hardpoint. Only that component\'s controls are shown below; commands remain bound to its exact slot and part ID.</p><div class="equipment-picker" id="m3-equipment-picker"></div><div class="selected-module" id="m3-selected-module"><h4>NO MODULE SELECTED</h4><p class="muted">Choose an installed part to open its controls.</p></div></div><div class="pane" id="m3-spatial-fusion-pane"><h3>SPATIAL INTELLIGENCE // LIVE SENSOR FUSION</h3><div class="fusion-metrics"><div><span class="muted">FUSED TRACKS</span><b id="m3-fusion-count">0</b></div><div><span class="muted">ACTIVE CHANNELS</span><b id="m3-fusion-sensors">0</b></div><div><span class="muted">RF MOTION ENERGY</span><b id="m3-fusion-csi">—</b></div></div><p class="muted" id="m3-fusion-summary">WAITING FOR SIMULATION SENSOR INPUTS</p><div class="fusion-track-list" id="m3-fusion-track-list">NO FUSED TRACKS AVAILABLE</div></div><div class="pane"><h3>UNIT CONFIGURATION // INSTALLED PARTS</h3><div class="muted loadout" id="m3-loadout"></div></div></div></div>';
document.body.appendChild(root);
bindWeaponHudControls();
var compassPane=root.querySelector('#m3-compass-pane');if(compassPane)root.appendChild(compassPane);
var webglHost=root.querySelector('#m3-webgl-host'),canvas=document.createElement('canvas'),environmentCanvas=root.querySelector('#m3-environment-webgl'),environmentGL=null,environmentProgram=null,environmentYaw=-.42,environmentPitch=.18,unitId='',requestedUnitId='',buildId='',buildSignature='',weaponHudSignature='',activeWeaponGroup=1,weaponHudEntries=[],active=false,course=0,selectedBuild=null,selectedEquipment=null,equipmentState={},mechGL=null,mechProgram=null,mechYaw=-.55,mechPitch=.12,lastMechSensorPublishAt=0,latestFusedSpatialModel=null;
canvas.id='vigil-mech-pilot-webgl';canvas.setAttribute('aria-label','Independent HOUND mech pilot 3D renderer');webglHost.appendChild(canvas);
function initMechRenderer(){mechGL=canvas.getContext('webgl',{alpha:false,antialias:true});if(!mechGL)return false;var gl=mechGL,vs=gl.createShader(gl.VERTEX_SHADER),fs=gl.createShader(gl.FRAGMENT_SHADER);gl.shaderSource(vs,'attribute vec3 p;uniform mat4 m;void main(){gl_Position=m*vec4(p,1.0);}');gl.shaderSource(fs,'precision mediump float;uniform vec4 c;void main(){gl_FragColor=c;}');gl.compileShader(vs);gl.compileShader(fs);mechProgram=gl.createProgram();gl.attachShader(mechProgram,vs);gl.attachShader(mechProgram,fs);gl.linkProgram(mechProgram);return gl.getProgramParameter(mechProgram,gl.LINK_STATUS);}
function mat(a,b){var o=new Float32Array(16);for(var c=0;c<4;c++)for(var r=0;r<4;r++)o[c*4+r]=a[r]*b[c*4]+a[4+r]*b[c*4+1]+a[8+r]*b[c*4+2]+a[12+r]*b[c*4+3];return o;}
function perspective(f,a,n,z){var q=1/Math.tan(f/2),v=1/(n-z),m=new Float32Array(16);m[0]=q/a;m[5]=q;m[10]=(z+n)*v;m[11]=-1;m[14]=2*z*n*v;return m;}
function mechBox(gl,mvp,x,y,z,sx,sy,sz,color){
 /* Eight-sided chamfered prism. Every fitted chassis, limb and payload part gets
    bevelled edges instead of the old hard-edged cube mesh. */
 var ring=[[-.30,-.5],[.30,-.5],[.5,-.30],[.5,.30],[.30,.5],[-.30,.5],[-.5,.30],[-.5,-.30]],verts=[];
 function push(a,b,c){verts.push(a[0],a[1],a[2],b[0],b[1],b[2],c[0],c[1],c[2]);}
 var low=[],high=[];
 ring.forEach(function(p){low.push([x+p[0]*sx,y-sy*.5,z+p[1]*sz]);high.push([x+p[0]*sx,y+sy*.5,z+p[1]*sz]);});
 for(var i=0;i<8;i++){var j=(i+1)%8;push(low[i],low[j],high[j]);push(low[i],high[j],high[i]);}
 var top=[x,y+sy*.5,z],bottom=[x,y-sy*.5,z];
 for(var k=0;k<8;k++){var n=(k+1)%8;push(top,high[k],high[n]);push(bottom,low[n],low[k]);}
 var b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(verts),gl.STREAM_DRAW);
 var model=new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]);
 gl.uniformMatrix4fv(gl.getUniformLocation(mechProgram,'m'),false,mat(mvp,model));gl.uniform4fv(gl.getUniformLocation(mechProgram,'c'),color);
 var loc=gl.getAttribLocation(mechProgram,'p');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,0,0);gl.drawArrays(gl.TRIANGLES,0,verts.length/3);gl.deleteBuffer(b);
}
function renderMech3D(b){
 if(!mechGL&&!initMechRenderer()){say('INDEPENDENT MECH WEBGL INITIALIZATION FAILED');return;}
 var gl=mechGL,w=canvas.clientWidth||720,h=canvas.clientHeight||420,dpr=Math.min(devicePixelRatio||1,2);
 canvas.width=Math.max(1,w*dpr);canvas.height=Math.max(1,h*dpr);gl.viewport(0,0,canvas.width,canvas.height);gl.enable(gl.DEPTH_TEST);gl.clearColor(.006,.025,.014,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(mechProgram);
 var f=perspective(.8,canvas.width/canvas.height,.1,40),view=new Float32Array([Math.cos(mechYaw),Math.sin(mechPitch)*Math.sin(mechYaw),Math.cos(mechPitch)*Math.sin(mechYaw),0,0,Math.cos(mechPitch),-Math.sin(mechPitch),0,-Math.sin(mechYaw),Math.sin(mechPitch)*Math.cos(mechYaw),Math.cos(mechPitch)*Math.cos(mechYaw),0,0,-.1,-7,1]),vp=mat(f,view);
 var paint=(b&&b.paint)||'#8a9b78',n=parseInt(paint.slice(1),16),base=[((n>>16)&255)/255,((n>>8)&255)/255,(n&255)/255,1],dark=[.12,.2,.14,1],metal=[.42,.5,.4,1],accent=[.66,.72,.55,1];
 function box(x,y,z,sx,sy,sz,c){mechBox(gl,vp,x,y,z,sx,sy,sz,c||base);}
 var parts=b&&b.parts||{},mounts=b&&b.mounts||{},mob=String(parts['MOBILITY BASE']||'BIPED-04'),cockpit=String(parts.COCKPIT||'CP-M');
 /* Shared upper chassis; dimensions and lower running gear follow the installed mobility base. */
 box(0,.18,0,1.02,.48,.68,dark);
 var cabScale=cockpit==='CP-XH'?1.28:cockpit==='CP-H'?1.16:cockpit==='CP-L'?.82:1;
 box(0,.86,0,.78*cabScale,.78*cabScale,.56*cabScale,base);
 box(0,1.36,.05,.42*cabScale,.34*cabScale,.38*cabScale,metal);
 box(0,1.38,.26,.25*cabScale,.12*cabScale,.035,accent);
 if(mob==='TRACK-03'){
  box(0,-.28,0,1.55,.38,1.22,dark);
  [-1,1].forEach(function(s){box(s*.78,-.28,0,.28,.68,1.52,metal);for(var i=0;i<5;i++)box(s*.79,-.28,-.56+i*.28,.31,.16,.14,accent);});
  box(0,.02,0,1.08,.3,.9,base);
 }else if(mob==='WHEEL-04'){
  box(0,-.18,0,1.08,.32,1.12,base);
  [-1,1].forEach(function(s){[-.48,.48].forEach(function(z){box(s*.7,-.32,z,.3,.48,.34,dark);box(s*.7,-.32,z,.32,.16,.36,metal);});});
 }else if(mob==='HOVER-02'){
  box(0,-.16,0,1.18,.26,1.12,base);
  [-1,1].forEach(function(s){box(s*.76,-.22,0,.34,.2,1.5,metal);box(s*.76,-.22,-.62,.3,.12,.22,accent);box(s*.76,-.22,.62,.3,.12,.22,accent);});
 }else if(mob==='MULTI-06'){
  box(0,-.12,0,1.12,.32,.9,base);
  for(var leg=0;leg<6;leg++){var side=leg%2?1:-1,row=Math.floor(leg/2)-.5,z=row*.72;box(side*.78,-.1,z,.3,.22,.3,metal);box(side*1.08,-.42,z*1.35,.18,.72,.18,base);box(side*1.3,-.78,z*1.55,.42,.14,.3,dark);}
 }else{
  box(0,-.1,0,.88,.34,.68,base);
  [-1,1].forEach(function(s){
   box(s*.62,.78,0,.34,.36,.4,metal);box(s*.72,.22,0,.27,.82,.3,base);
   if(mob==='REV-02'){box(s*.72,-.25,-.12,.24,.42,.25,metal);box(s*.55,-.55,.12,.3,.45,.34,base);box(s*.38,-.86,.22,.48,.18,.58,dark);}
   else{box(s*.72,-.28,.08,.3,.24,.36,dark);box(s*.32,-.65,0,.34,.72,.36,metal);box(s*.32,-1.1,.12,.48,.2,.62,dark);}
  });
 }
 /* Power plant and control computer are visible only when installed. */
 if(parts.GENERATOR){box(0,.72,-.48,.58,.48,.28,[.28,.38,.3,1]);box(0,.72,-.64,.34,.26,.08,accent);}
 if(parts['SYSTEM COM']){box(0,1.66,-.02,.22,.3,.2,metal);box(0,1.84,-.02,.08,.16,.08,accent);}
 var positions={'LEFT ARM':[-1.02,.22,.08],'RIGHT ARM':[1.02,.22,.08],'SHOULDER 1':[-.48,1.28,0],'SHOULDER 2':[.48,1.28,0],'BACK':[0,.72,-.68],'UTILITY':[0,-.02,.56]};
 Object.keys(mounts).forEach(function(slot){
  var id=String(mounts[slot]||'');if(!id)return;var p=positions[slot]||[0,.35,0],heavy=id.indexOf('HA-')===0,weapon=heavy||id.indexOf('LA-')===0,sensor=id.indexOf('AS-')===0;
  var color=sensor?[.18,.62,.48,1]:heavy?[.65,.52,.28,1]:[.56,.62,.49,1];
  box(p[0],p[1],p[2],sensor?.34:heavy?.56:.42,sensor?.3:.38,sensor?.36:.58,color);
  if(weapon){
   var barrel=id==='HA-HW'||id==='HA-MT'?1.05:id==='HA-AC'||id==='HA-SC'?.82:.55;
   box(p[0],p[1],p[2]+barrel*.48,.16,.16,barrel,[.72,.75,.63,1]);
   if(id==='LA-MG'||id==='LA-MR'||id==='HA-AC'){box(p[0]-.12,p[1]-.05,p[2]+barrel*.48,.07,.07,barrel*.88,metal);box(p[0]+.12,p[1]-.05,p[2]+barrel*.48,.07,.07,barrel*.88,metal);}
   if(id==='LA-RK'||id==='HA-ML'){for(var tube=0;tube<4;tube++)box(p[0]+(tube%2-.5)*.18,p[1]+(Math.floor(tube/2)-.5)*.18,p[2]+.34,.11,.11,.62,accent);}
   if(id==='HA-PILE'){box(p[0],p[1],p[2]+.72,.28,.28,.52,[.72,.72,.58,1]);}
  }else if(sensor){box(p[0],p[1],p[2]+.22,.18,.18,.22,[.2,.86,.68,1]);}
  else if(id==='AS-JAM'){[-1,1].forEach(function(s){box(p[0]+s*.24,p[1]+.3,p[2],.06,.52,.06,accent);});}
 });
}

canvas.addEventListener('pointerdown',function(e){canvas.dataset.drag='1';canvas.dataset.x=e.clientX;canvas.dataset.y=e.clientY;canvas.setPointerCapture(e.pointerId);});canvas.addEventListener('pointermove',function(e){if(canvas.dataset.drag!=='1')return;mechYaw+=(e.clientX-Number(canvas.dataset.x))*.008;mechPitch=Math.max(-.65,Math.min(.65,mechPitch+(e.clientY-Number(canvas.dataset.y))*.006));canvas.dataset.x=e.clientX;canvas.dataset.y=e.clientY;draw();});['pointerup','pointercancel'].forEach(function(k){canvas.addEventListener(k,function(){canvas.dataset.drag='0';});});

function getBuild(){var g=window.vigilGetMechGarageState&&window.vigilGetMechGarageState();if(!g||!Array.isArray(g.builds))return null;var wanted=String(requestedUnitId||'').toUpperCase();if(/^MECH-/.test(wanted)){var match=g.builds.find(function(b){return String(b.simulationUnitId||'').toUpperCase()===wanted;});if(match)return match;}return g.builds.find(function(b){return b.id===g.selected;})||null;}
function getUnit(){return unitId&&window.vigilGetMechUnitState?window.vigilGetMechUnitState(unitId):null;}
function partLabel(id){return id||'NONE';}

function initEnvironmentRenderer(){if(environmentGL)return true;environmentGL=environmentCanvas&&environmentCanvas.getContext('webgl',{alpha:false,antialias:true});if(!environmentGL)return false;var gl=environmentGL,vs=gl.createShader(gl.VERTEX_SHADER),fs=gl.createShader(gl.FRAGMENT_SHADER);gl.shaderSource(vs,'attribute vec3 p;uniform mat4 m;void main(){gl_Position=m*vec4(p,1.0);}');gl.shaderSource(fs,'precision mediump float;uniform vec4 c;void main(){gl_FragColor=c;}');gl.compileShader(vs);gl.compileShader(fs);environmentProgram=gl.createProgram();gl.attachShader(environmentProgram,vs);gl.attachShader(environmentProgram,fs);gl.linkProgram(environmentProgram);return gl.getProgramParameter(environmentProgram,gl.LINK_STATUS);}
function publishMechSimulationSensors(){
 if(!active||!window.vigilFleetSensorNetwork||typeof window.vigilFleetSensorNetwork.getUnitPackage!=='function'||typeof window.vigilRecordUnitSensorFeed!=='function')return;
 var own=window.vigilGetRegionalSimulationUnit&&window.vigilGetRegionalSimulationUnit(unitId);if(!own||own.deployment_status==='hanger'||own.deployment_status==='docked')return;
 var now=Date.now();if(now-lastMechSensorPublishAt<1200)return;lastMechSensorPublishAt=now;
 var network=window.vigilFleetSensorNetwork,pkg=network.getUnitPackage(unitId),sensors=pkg&&Array.isArray(pkg.sensors)?pkg.sensors:[];
 sensors.forEach(function(sensor){
  if(!Array.isArray(sensor)||!sensor[0])return;
  var frame=network.getFrame&&network.getFrame(unitId,sensor[0]);
  if(frame)window.vigilRecordUnitSensorFeed(frame);
 });

}
function fuseSpatialObservations(snapshot){
 var observations=snapshot&&Array.isArray(snapshot.observations)?snapshot.observations:[],groups=Object.create(null),feeds=snapshot&&Array.isArray(snapshot.feeds)?snapshot.feeds:[];
 observations.forEach(function(o){
  if(!o||o.unit_id!==unitId||o.feed_stale||!Array.isArray(o.normalized_position)||o.normalized_position.length<2)return;
  var x=Number(o.normalized_position[0]),y=Number(o.normalized_position[1]);
  if(!Number.isFinite(x)||!Number.isFinite(y))return;
  var id=String(o.object_id||o.contact_id||'');if(!id)return;
  (groups[id]||(groups[id]=[])).push(o);
 });
 var tracks=Object.keys(groups).map(function(id){
  var rows=groups[id],anchor=rows[0].normalized_position,wx=0,wy=0,total=0,confidence=0,uncertainty=0,uncertaintyWeight=0,modalities=[],sensorIds=[];
  rows.forEach(function(o){
   var p=o.normalized_position,x=Number(p[0])-Number(anchor[0]),y=Number(p[1])-Number(anchor[1]);
   if(x>.5)x-=1;if(x<-.5)x+=1;if(y>.5)y-=1;if(y<-.5)y+=1;
   var c=Math.max(.05,Math.min(.99,Number(o.confidence)||.5)),u=Number(o.uncertainty_m),weight=c/(1+(Number.isFinite(u)&&u>=0?u*u:0));
   wx+=x*weight;wy+=y*weight;total+=weight;confidence+=c*weight;
   if(Number.isFinite(u)&&u>=0){uncertainty+=u*weight;uncertaintyWeight+=weight;}
   var modality=String(o.modality||'unknown');if(modalities.indexOf(modality)<0)modalities.push(modality);
   var sid=String(o.sensor_id||'');if(sid&&sensorIds.indexOf(sid)<0)sensorIds.push(sid);
  });
  var bonus=Math.min(.16,Math.max(0,modalities.length-1)*.055);
  return {track_id:id,classification:String(rows[0].classification||'unclassified contact'),
   normalized_position:[(Number(anchor[0])+wx/Math.max(.0001,total)+1)%1,(Number(anchor[1])+wy/Math.max(.0001,total)+1)%1],
   confidence:Math.min(.98,confidence/Math.max(.0001,total)+bonus),
   uncertainty_m:uncertaintyWeight?uncertainty/uncertaintyWeight:null,
   observation_count:rows.length,modalities:modalities,sensor_ids:sensorIds};
 }).sort(function(a,b){return b.confidence-a.confidence;});
 var csi=observations.filter(function(o){return o&&o.unit_id===unitId&&!o.feed_stale&&o.modality==='wifi_csi';}).slice(-1)[0],csiMeasurements=csi&&csi.measurements||{};
 var sensorFeeds=feeds.filter(function(f){return f&&f.unit_id===unitId&&!f.stale;});
 latestFusedSpatialModel={schema:'vigil.mech.spatial-fusion',version:1,unit_id:unitId,
  captured_at:snapshot&&snapshot.captured_at||new Date().toISOString(),source:'SIMULATION SENSOR REGISTRY',
  sensor_count:sensorFeeds.length,tracks:tracks,
  rf_context:{sensor_id:csi&&csi.sensor_id||null,frequency_ghz:Number(csiMeasurements['RF CENTER FREQUENCY'])||2.4,
   phase_variance:Number(csiMeasurements['CHANNEL PHASE VARIANCE'])||0,
   motion_energy:Number(csiMeasurements['DOPPLER MOTION ENERGY'])||0,
   motion_candidates:Number(csiMeasurements['MOTION CANDIDATES'])||0,
   position_authority:'CONTEXT ONLY // NOT A RANGE FIX'}};
 return latestFusedSpatialModel;
}
window.vigilGetMechFusedSpatialModel=function(){
 if(!latestFusedSpatialModel)return null;
 return JSON.parse(JSON.stringify(latestFusedSpatialModel));
};
function renderFusionCockpit(model){
 var count=root.querySelector('#m3-fusion-count'),sensors=root.querySelector('#m3-fusion-sensors'),csi=root.querySelector('#m3-fusion-csi'),summary=root.querySelector('#m3-fusion-summary'),list=root.querySelector('#m3-fusion-track-list');
 if(!count||!sensors||!csi||!summary||!list)return;
 model=model||latestFusedSpatialModel;
 if(!model){summary.textContent='WAITING FOR SIMULATION SENSOR INPUTS';return;}
 count.textContent=String(model.tracks.length);sensors.textContent=String(model.sensor_count);
 csi.textContent=Number(model.rf_context.motion_energy||0).toFixed(2);
 summary.textContent='SIMULATION-FED MODEL // '+model.tracks.length+' FUSED TRACK(S) // 2.4 GHz CSI MOTION CONTEXT // '+model.rf_context.motion_candidates+' UNRESOLVED MOTION CANDIDATE(S)';
 list.textContent='';
 if(!model.tracks.length){list.textContent='NO POSITIONED TRACKS // RF CSI REMAINS MOTION CONTEXT ONLY';return;}
 model.tracks.slice(0,12).forEach(function(track){
  var item=document.createElement('div');item.className='fusion-track';
  var title=document.createElement('strong');title.textContent=track.track_id+' // '+track.classification;
  var detail=document.createElement('small');detail.textContent='CONF '+Math.round(track.confidence*100)+'% // '+track.observation_count+' OBS // '+track.modalities.join(' + ')+' // '+track.sensor_ids.join(', ');
  item.appendChild(title);item.appendChild(detail);list.appendChild(item);
 });
}
function renderEnvironment(b){
 if(!environmentCanvas)return;
 publishMechSimulationSensors();
 var snapshot=window.vigilGetSensorInputSnapshot&&window.vigilGetSensorInputSnapshot(),model=fuseSpatialObservations(snapshot),own=window.vigilGetRegionalSimulationUnit&&window.vigilGetRegionalSimulationUnit(unitId);
 renderFusionCockpit(model);
 var observations=snapshot&&Array.isArray(snapshot.observations)?snapshot.observations:[],
  activeFeeds=snapshot&&Array.isArray(snapshot.feeds)?snapshot.feeds.filter(function(f){return f&&f.unit_id===unitId&&!f.stale;}):[],
  capabilityNames=activeFeeds.map(function(f){return f.sensor_id+' / '+String(f.modality||'').toUpperCase();});
 if(capabilityNames.indexOf('HOUND 2.4 GHz WI-FI CSI / RF MOTION RADAR')<0)capabilityNames.push('HOUND 2.4 GHz WI-FI CSI / RF MOTION RADAR');
 var status=root.querySelector('#m3-environment-status');
 if(status)status.textContent='ACTIVE SENSOR CAPABILITIES // '+capabilityNames.join(' · ')+' // SENSOR-FUSED MODEL '+model.tracks.length+' TRACK(S) // CSI '+Number(model.rf_context.motion_energy||0).toFixed(2)+' MOTION ENERGY';if(!activeFeeds.length&&status)status.textContent='NO ENVIRONMENT SENSOR FITTED // SENSOR FEED BUS UNAVAILABLE // MECH PILOT VIEW RETAINED';
 if(!initEnvironmentRenderer()){if(status)status.textContent='ENVIRONMENT WEBGL UNAVAILABLE // MECH PILOT VIEW RETAINED';return;}
 var gl=environmentGL,w=environmentCanvas.clientWidth||640,h=environmentCanvas.clientHeight||260,dpr=Math.min(devicePixelRatio||1,2);
 environmentCanvas.width=Math.max(1,Math.floor(w*dpr));environmentCanvas.height=Math.max(1,Math.floor(h*dpr));gl.viewport(0,0,environmentCanvas.width,environmentCanvas.height);
 gl.enable(gl.DEPTH_TEST);gl.clearColor(.006,.018,.012,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(environmentProgram);
 var f=perspective(.92,environmentCanvas.width/environmentCanvas.height,.1,90),
  view=new Float32Array([Math.cos(environmentYaw),Math.sin(environmentPitch)*Math.sin(environmentYaw),Math.cos(environmentPitch)*Math.sin(environmentYaw),0,0,Math.cos(environmentPitch),-Math.sin(environmentPitch),0,-Math.sin(environmentYaw),Math.sin(environmentPitch)*Math.cos(environmentYaw),Math.cos(environmentPitch)*Math.cos(environmentYaw),0,0,-1.05,-8.5,1]),
  vp=mat(f,view),saved=mechProgram;
 mechProgram=environmentProgram;
 function block(x,y,z,sx,sy,sz,c){mechBox(gl,vp,x,y,z,sx,sy,sz,c);}
 var ground=[.10,.17,.12,1],ridge=[.15,.23,.16,1],unknown=[.07,.12,.09,1];
 for(var z=0;z<11;z++){for(var x=0;x<11;x++){
  var wx=(x-5)*1.2,wz=(z-1)*1.2,noise=Math.sin(x*1.71+z*.73)*.22+Math.cos(z*1.31-x*.42)*.16,
   relief=(Math.abs(x-5)<2?Math.sin(z*.9)*.38:0)+noise;
  block(wx,-.62+relief,wz,1.12,.12+Math.max(0,relief*.18),1.12,activeFeeds.length?(Math.abs(relief)>.25?ridge:ground):unknown);
 }}
 for(var i=0;i<7;i++){var rx=Math.sin(i*12.37)*4.8,rz=1.8+(i%5)*1.45,ry=-.35+Math.cos(i*4.1)*.25;block(rx,ry,rz,.32+(i%3)*.18,.35+(i%4)*.16,.35+(i%2)*.22,activeFeeds.length?ridge:unknown);}
 if(own&&Number.isFinite(Number(own.x))&&Number.isFinite(Number(own.y))){
  model.tracks.forEach(function(track){
   var dx=Number(track.normalized_position[0])-Number(own.x),dy=Number(track.normalized_position[1])-Number(own.y);
   if(dx>.5)dx-=1;if(dx<-.5)dx+=1;if(dy>.5)dy-=1;if(dy<-.5)dy+=1;
   var px=dx*95,pz=dy*95;if(Math.abs(px)>7.2||Math.abs(pz)>7.2)return;
   var modalities=track.modalities||[],color=modalities.indexOf('thermal')>=0?[.96,.34,.10,1]:modalities.some(function(v){return ['optical','infrared','camera'].indexOf(v)>=0;})?[.28,.92,.48,1]:[.16,.82,.82,1],
    confidence=Math.max(.2,Math.min(1,Number(track.confidence)||.5));
   block(px,-.28,pz,.24+confidence*.22,.08,.24+confidence*.22,color);
  });
 }
 mechProgram=saved;
 renderWeaponOpticPip();
}
environmentCanvas.addEventListener('pointerdown',function(e){environmentCanvas.dataset.drag='1';environmentCanvas.dataset.x=e.clientX;environmentCanvas.dataset.y=e.clientY;environmentCanvas.setPointerCapture(e.pointerId);});environmentCanvas.addEventListener('pointermove',function(e){if(environmentCanvas.dataset.drag!=='1')return;environmentYaw+=(e.clientX-Number(environmentCanvas.dataset.x))*.006;environmentPitch=Math.max(-.35,Math.min(.65,environmentPitch+(e.clientY-Number(environmentCanvas.dataset.y))*.004));environmentCanvas.dataset.x=e.clientX;environmentCanvas.dataset.y=e.clientY;if(active)renderEnvironment(selectedBuild);});['pointerup','pointercancel'].forEach(function(k){environmentCanvas.addEventListener(k,function(){environmentCanvas.dataset.drag='0';});});
function draw(){if(!active)return;renderMech3D(selectedBuild);renderEnvironment(selectedBuild);}
function renderNavigation(b){
 var controls=root.querySelector('#m3-navigation-controls'),note=root.querySelector('#m3-navigation-note');if(!controls||!note)return;
 var parts=b&&b.parts||{},mob=parts['MOBILITY BASE'],com=parts['SYSTEM COM'],u=getUnit();
 var stowed=!!(u&&['hanger','docked'].indexOf(String(u.deployment_status||'').toLowerCase())>=0);
 var comLabel=com==='COM-M'?'VECTOR CONTROL / MOBILITY ASSIST':com==='COM-W'?'GYRO STABILIZATION / WEAPON ASSIST':com==='COM-S'?'BALANCE MATRIX / STABILITY ASSIST':'BASELINE MOBILITY LINK';
 var state=!mob?'NO MOBILITY BASE INSTALLED // MOVEMENT CONTROLS DISABLED':stowed?'HOUND STOWED // DEPLOY THIS BUILD FROM THE HANGER BEFORE ISSUING NAVIGATION COMMANDS.':'MOBILITY BASE '+mob+' // '+comLabel+' // NAVIGATION LINK READY';
 var signature=[mob||'',com||''].join('|');
 note.textContent=state;
 if(!mob){
  if(controls.dataset.signature!==signature){controls.replaceChildren();controls.dataset.signature=signature;}
  return;
 }
 // A non-mobility COM changes stabilization, not whether an installed chassis
 // can steer. Keep the six controls mounted so telemetry refresh cannot eat clicks.
 if(controls.dataset.signature!==signature||controls.children.length!==6){
  controls.replaceChildren();controls.dataset.signature=signature;
  [['TURN −15°','turn','-15'],['TURN +15°','turn','15'],['NORTH','north',''],['SPEED −','speed','-.002'],['SPEED +','speed','.002'],['STOP','stop','']].forEach(function(item){
   var btn=document.createElement('button');btn.type='button';btn.textContent=item[0];btn.dataset.navControl=item[1];
   if(item[1]==='turn')btn.dataset.turn=item[2];if(item[1]==='speed')btn.dataset.speed=item[2];
   btn.addEventListener('click',function(){
    if(btn.disabled)return;
    if(item[1]==='turn'){var current=getUnit(),h=Number(current&&current.desired_heading_deg);if(!Number.isFinite(h))h=0;send({heading:(h+Number(item[2])+360)%360});}
    else if(item[1]==='speed'){var current=getUnit(),v=Number(current&&current.target_speed)||0;send({speed:Math.max(0,Math.min(Number(current&&current.max_speed)||.03,v+Number(item[2])))});}
    else if(item[1]==='north')send({heading:0});else send({speed:0});
   });
   controls.appendChild(btn);
  });
 }
 Array.prototype.forEach.call(controls.children,function(btn){btn.disabled=stowed;btn.title=stowed?'Deploy this HOUND to enable movement controls':'';});
}
function say(s){var n=root.querySelector('#m3-status');if(n)n.textContent=s;}
function send(changes){var result=window.vigilSetSimulationUnitState&&window.vigilSetSimulationUnitState(unitId,changes);if(result&&result.ok){say('MECH COMMAND ACCEPTED // '+Object.keys(changes).join(', ').toUpperCase());refresh();}else say(result&&result.reason||'MECH CONTROL API UNAVAILABLE');}
function refresh(){if(!active)return;var b=getBuild();if(b){var signature=JSON.stringify({parts:b.parts||{},mounts:b.mounts||{},paint:b.paint||'',equipmentRuntime:b.equipmentRuntime||{},weaponGroups:b.weaponGroups||{},role:b.role||'',cockpitTier:b.cockpitTier||''});if(b.id!==buildId){buildId=b.id;unitId=b.simulationUnitId||'MECH-01';selectedEquipment=null;}if(signature!==buildSignature){buildSignature=signature;selectedBuild=b;renderEquipment();buildWeaponHud(b);}else{selectedBuild=b;updateWeaponHud();}}var u=getUnit();renderNavigation(b);root.querySelector('#m3-unit').textContent=(b&&b.name||unitId)+' // '+unitId;root.querySelector('#m3-heading').textContent=u&&u.heading_deg!=null?String(Math.round(u.heading_deg)).padStart(3,'0')+'°':'---°';root.querySelector('#m3-course').textContent=u&&u.desired_heading_deg!=null?String(Math.round(u.desired_heading_deg)).padStart(3,'0')+'°':'---°';root.querySelector('#m3-speed').textContent=u?Number(u.speed).toFixed(3):'0.000';var actualHeading=Number(u&&u.heading_deg)||0,orderedHeading=Number(u&&u.desired_heading_deg);if(!Number.isFinite(orderedHeading))orderedHeading=actualHeading;var compassNeedle=root.querySelector('#m3-compass-needle'),courseMarker=root.querySelector('#m3-course-marker');if(compassNeedle)compassNeedle.setAttribute('transform','rotate('+actualHeading+' 110 110)');if(courseMarker)courseMarker.setAttribute('transform','rotate('+orderedHeading+' 110 110)');root.querySelector('#m3-loadout').textContent=Object.keys(b&&b.parts||{}).map(function(k){return k+': '+partLabel(b.parts[k]);}).concat(Object.keys(b&&b.mounts||{}).map(function(k){return k+': '+partLabel(b.mounts[k]);})).join('  //  ');draw();}

var weaponCatalog={
 'LA-MG':{name:'Twin Rotary Machine Gun',readout:'TWIN-FEED AMMUNITION // BARREL TEMPERATURE // SPREAD BLOOM',scope:'TRACKING SPREAD',kind:'spread'},
 'LA-SG':{name:'Breach Shotgun',readout:'SHELL MAGAZINE // PUMP CYCLE // PELLET CONE',scope:'NORMAL SCOPE',kind:'normal'},
 'LA-GL':{name:'Programmable Grenade Launcher',readout:'GRENADE COUNT // FUZE MODE // PROJECTILE ARC',scope:'BALLISTIC RANGE SIGHT',kind:'arc'},
 'LA-RK':{name:'Anti-Armor Rocket Pod',readout:'ROCKET STORES // SEEKER STATUS // TRACK ACQUISITION',scope:'MISSILE LOCK BOX',kind:'lock'},
 'LA-SR':{name:'Long-Range Precision Rifle',readout:'PRECISION ROUND // OPTIC STABILITY // RANGE VECTOR',scope:'SNIPER OPTIC',kind:'sniper'},
 'LA-MR':{name:'Automatic Mobile Rifle',readout:'MAGAZINE CAPACITY // FIRE-CYCLE RATE // BARREL HEAT',scope:'TRACKING SPREAD',kind:'spread'},
 'LA-MN':{name:'Scatter Mine Dispenser',readout:'MINE COUNT // PROXIMITY MODE // RELEASE STATE',scope:'DEPLOYMENT SIGHT',kind:'normal'},
 'LA-BM':{name:'Timed Bomb Rack',readout:'BOMB COUNT // FUSE STATE // RELEASE VECTOR',scope:'RELEASE / DROP SIGHT',kind:'arc'},
 'HA-AC':{name:'Heavy Anti-Armor Cannon',readout:'HEAVY SHELL // RECOIL CYCLE // BARREL HEAT',scope:'RANGED BALLISTIC SIGHT',kind:'normal'},
 'HA-ML':{name:'Heavy Missile Launcher',readout:'MISSILE INVENTORY // SEEKER STATUS // TRACK ACQUISITION',scope:'MISSILE LOCK BOX',kind:'lock'},
 'HA-HW':{name:'Long-Range Howitzer',readout:'HOWITZER SHELL // ELEVATION MATRIX // FLIGHT ARC',scope:'HIGH-ANGLE SCOPE',kind:'arc'},
 'HA-MT':{name:'Indirect-Fire Mortar',readout:'MORTAR ROUND // TUBE HEAT // PARABOLIC SOLUTION',scope:'HIGH-ANGLE SCOPE',kind:'arc'},
 'HA-SC':{name:'Heavy Sniper Cannon',readout:'HEAVY PRECISION ROUND // OPTIC STABILITY // RANGE VECTOR',scope:'SNIPER SCOPE',kind:'sniper'},
 'HA-PILE':{name:'Close-Quarters Pile Driver',readout:'ACTUATOR CHARGE // CONTACT ENVELOPE // STRIKE INTERLOCK',scope:'CONTACT ALIGNMENT',kind:'melee'}
};
function installedWeapons(b){
 var out=[],groups=b&&b.weaponGroups||{};
 Object.keys(b&&b.parts||{}).concat(Object.keys(b&&b.mounts||{})).forEach(function(slot,index){
  var id=(b.parts&&b.parts[slot])||(b.mounts&&b.mounts[slot]);
  if(!id||!weaponCatalog[id])return;
  var key=slot+'|'+id,group=Number(groups[key]);
  if(!Number.isInteger(group)||group<0||group>4)group=(out.length%4)+1;
  out.push({slot:slot,id:id,key:key,group:group});
 });
 return out;
}
function weaponGroupEntries(group){return weaponHudEntries.filter(function(e){return e.group===group;});}

function roleReadoutValues(b){
 var role=String(b&&b.role||'SOLDIER'),parts=b&&b.parts||{},all=equipmentEntries(),weapons=weaponHudEntries,states=window.vigilGetMechEquipmentState&&window.vigilGetMechEquipmentState(unitId)||{},keys=Object.keys(states),armed=0,destroyed=0,ammo=0,heat=0,ammoCount=0,conditionTotal=0,conditionCount=0;
 keys.forEach(function(key){var st=states[key]||{};if(st.armed)armed++;if(st.disabled||Number(st.integrity)===0)destroyed++;if(st.magazineRemaining!=null){ammo+=Number(st.magazineRemaining)||0;ammoCount++;}heat=Math.max(heat,Number(st.heat)||0);if(st.integrity!=null){conditionTotal+=Number(st.integrity)||0;conditionCount++;}});
 var nearest=nearestFusedTrack(),manifest=window.vigilMothershipCommand&&window.vigilMothershipCommand.getManifest?window.vigilMothershipCommand.getManifest():[];
 var sensorCount=latestFusedSpatialModel&&latestFusedSpatialModel.sensor_count||0,trackCount=latestFusedSpatialModel&&latestFusedSpatialModel.tracks.length||0,rf=latestFusedSpatialModel&&latestFusedSpatialModel.rf_context||{};
 var artillery=weapons.filter(function(e){return ['HA-HW','HA-MT','HA-ML','HA-AC'].indexOf(e.id)>=0;});
 var roleRows=[];
 function add(label,value){roleRows.push([label,String(value)]);}
 add('COCKPIT / COM',String(parts.COCKPIT||'CP-M')+' / '+String(parts['SYSTEM COM']||'NONE'));
 if(role==='SCOUT'){
  add('ACTIVE SENSOR CHANNELS',sensorCount);add('FUSED CONTACT TRACKS',trackCount);
  add('RF MOTION ENERGY',Number(rf.motion_energy||0).toFixed(2));add('POSITIONED TARGET',nearest?'TRACK '+nearest.distance.toFixed(4)+' MAP UNITS':'NO TRACK');
 }else if(role==='SOLDIER'){
  add('ASSIGNED WEAPON GROUPS',[1,2,3,4].filter(function(g){return weaponGroupEntries(g).length>0;}).length+' / 4');
  add('ARMED MODULES',armed);add('MAGAZINE ROUNDS',ammoCount?ammo:'NO AMMO WEAPONS FITTED');add('MAX WEAPON HEAT',heat.toFixed(0)+'%');
 }else if(role==='DEFENDER'){
  add('REACTIVE ARMOR',all.some(function(e){return e.id==='AS-ARM';})?'FITTED':'NOT FITTED');
  add('MODULE CONDITION',conditionCount?(conditionTotal/conditionCount).toFixed(0)+'% AVG':'NO DAMAGE TELEMETRY');
  add('DESTROYED MODULES',destroyed);add('PROTECTION COM',String(parts['SYSTEM COM']||'NONE'));
 }else if(role==='SNIPER'){
  var optics=weapons.filter(function(e){return e.id==='LA-SR'||e.id==='HA-SC';});
  add('PRECISION OPTICS',optics.length?optics.map(function(e){return e.id;}).join(' / '):'NO TRUE SNIPER PART');
  add('OPTIC GROUP',weaponGroupEntries(activeWeaponGroup).some(function(e){return e.id==='LA-SR'||e.id==='HA-SC';})?'ACTIVE':'SELECT SNIPER GROUP');
  add('NEAREST FUSED TRACK',nearest?nearest.distance.toFixed(4)+' MAP UNITS':'RANGE UNAVAILABLE');
  add('WIND DATA','NO WIND SENSOR INPUT');
 }else if(role==='HEAVY GUNNER'){
  add('ARTILLERY MODULES',artillery.length?artillery.map(function(e){return e.id;}).join(' / '):'NONE FITTED');
  add('HIGH-ANGLE PARTS',weapons.filter(function(e){return e.id==='HA-HW'||e.id==='HA-MT';}).length);
  add('FIRE SOLUTION',nearest?'TRACK '+nearest.distance.toFixed(4)+' MAP UNITS':'AWAITING POSITIONED TRACK');
  add('MAX WEAPON HEAT',heat.toFixed(0)+'%');
 }else if(role==='TACTICS COMMANDER'){
  add('NA MAKER',String(parts['NA MAKER']||'NOT FITTED'));
  add('CARRIER / FLEET MANIFEST',Array.isArray(manifest)?manifest.length+' REGISTERED UNITS':'MANIFEST UNAVAILABLE');
  add('FUSED TRACKS',trackCount);add('CSI MOTION CONTEXT',Number(rf.motion_energy||0).toFixed(2));
 }else{
  add('FUSED TRACKS',trackCount);add('ARMED MODULES',armed);add('MODULE CONDITION',conditionCount?(conditionTotal/conditionCount).toFixed(0)+'% AVG':'—');
 }
 return roleRows;
}
function renderRoleReadouts(b){
 var rootReadouts=root.querySelector('#m3-role-readouts');if(!rootReadouts)return;
 rootReadouts.replaceChildren();
 roleReadoutValues(b).forEach(function(pair){var cell=document.createElement('div');cell.className='m3-role-readout';cell.dataset.roleMetric=pair[0];var label=document.createElement('span');label.textContent=pair[0];var value=document.createElement('strong');value.dataset.roleValue='1';value.textContent=pair[1];cell.appendChild(label);cell.appendChild(value);rootReadouts.appendChild(cell);});
}
function updateRoleReadouts(b){
 var rootReadouts=root.querySelector('#m3-role-readouts');if(!rootReadouts||!b)return;
 var values=roleReadoutValues(b);
 values.forEach(function(pair){var cell=Array.prototype.find.call(rootReadouts.children,function(n){return n.dataset.roleMetric===pair[0];});if(cell){var value=cell.querySelector('[data-role-value]');if(value)value.textContent=pair[1];}});
}

function updateWeaponGroupSelection(){
 root.querySelectorAll('.m3-weapon-group').forEach(function(card){card.classList.toggle('active',Number(card.dataset.group)===activeWeaponGroup);});
 updateWeaponReticle();
}
function buildWeaponHud(b){
 var groupRoot=root.querySelector('#m3-weapon-groups'),unassigned=root.querySelector('#m3-weapon-unassigned');
 if(!groupRoot||!unassigned)return;
 weaponHudEntries=installedWeapons(b);
 var role=String(b&&b.role||'SOLDIER'),cockpit=String(b&&b.cockpitTier||(b&&b.parts&&b.parts.COCKPIT)||'CP-M');
 var signature=JSON.stringify({id:b&&b.id,parts:b&&b.parts,mounts:b&&b.mounts,weaponGroups:b&&b.weaponGroups,role:role,cockpit:cockpit});
 if(signature===weaponHudSignature){updateWeaponHud();return;}
 weaponHudSignature=signature;
 root.dataset.role=role.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
 root.dataset.cockpit=cockpit;
 root.querySelector('#m3-weapon-hud-title').textContent=(b&&b.name||unitId)+' // '+role;
 var tiers={'CP-L':'LIGHT // 2 COM SLOTS','CP-M':'MEDIUM // 3 COM SLOTS','CP-H':'HEAVY // 4 COM SLOTS','CP-XH':'SUPER HEAVY // 5 COM SLOTS'};
 root.querySelector('#m3-cockpit-tier').textContent=tiers[cockpit]||cockpit;
 var roles={
  'SCOUT':'SCOUT // PANORAMIC RECON DISPLAY. High-refresh local mapping, EO / thermal / low-light channels, peripheral contact awareness and RF motion context take priority over dense weapon telemetry.',
  'SOLDIER':'SOLDIER // FRONT-LINE COMBAT DISPLAY. Central sight picture, four weapon-group controls, ammunition, heat, firing state and local target feedback remain in the primary panel.',
  'DEFENDER':'DEFENDER // PROTECTED COMBAT DISPLAY. Armor and module-condition diagnostics sit beside weapon telemetry; fitted reactive armor is shown as a separate subsystem, never assumed.',
  'SNIPER':'SNIPER // PRECISION FIRE CONTROL. The selected precision weapon receives an optic view, range-vector readout, stability status and a low-clutter aiming reticle.',
  'HEAVY GUNNER':'HEAVY GUNNER // INDIRECT-FIRE CONTROL. Artillery groups use elevation and arc readouts, with high-angle reticles for fitted howitzers and mortars.',
  'TACTICS COMMANDER':'TACTICS COMMANDER // NETWORK COMMAND DISPLAY. NA Maker status, fused friendly/contact tracks and team coordination take priority over ordinary lock-on panels.'
 };
 var tierDetails={
  'CP-L':'LIGHT COCKPIT // panoramic, lower-clutter instrument layout',
  'CP-M':'MEDIUM COCKPIT // balanced central sight and multi-function panels',
  'CP-H':'HEAVY COCKPIT // reinforced bezel and expanded structural diagnostics',
  'CP-XH':'SUPER HEAVY COCKPIT // wide command layout and extended system panels'
 };
 root.querySelector('#m3-role-title').textContent=role+' // '+cockpit;
 root.querySelector('#m3-role-detail').textContent=(roles[role]||'ROLE PROFILE UNAVAILABLE.')+' '+(tierDetails[cockpit]||'COCKPIT CONFIGURATION UNAVAILABLE.');
 renderRoleReadouts(b);
 groupRoot.replaceChildren();unassigned.replaceChildren();
 for(var g=1;g<=4;g++){
  var card=document.createElement('section');card.className='m3-weapon-group';card.dataset.group=String(g);
  var head=document.createElement('button');head.type='button';head.className='m3-group-head';head.dataset.group=String(g);
  var label=document.createElement('strong');label.textContent='GROUP '+g+' // '+['X','Y','B','A'][g-1];
  var count=document.createElement('small');count.className='m3-group-count';count.textContent='0 MODULES';head.appendChild(label);head.appendChild(count);
  head.addEventListener('click',function(){activeWeaponGroup=Number(this.dataset.group);updateWeaponGroupSelection();});
  var list=document.createElement('div');list.className='m3-group-list';list.id='m3-group-list-'+g;
  card.appendChild(head);card.appendChild(list);groupRoot.appendChild(card);
 }
 function createModule(entry,target){
  var spec=weaponCatalog[entry.id],row=document.createElement('div');row.className='m3-weapon-module';row.dataset.weaponKey=entry.key;
  var head=document.createElement('div');head.className='m3-weapon-module-head';
  var name=document.createElement('strong');name.className='m3-weapon-name';name.textContent=entry.id+' // '+spec.name;
  var slot=document.createElement('small');slot.textContent=entry.slot;head.appendChild(name);head.appendChild(slot);row.appendChild(head);
  var desc=document.createElement('div');desc.className='m3-weapon-readout-desc';desc.textContent=spec.readout;row.appendChild(desc);
  var assignment=document.createElement('select');assignment.className='m3-weapon-assignment';assignment.setAttribute('aria-label','Weapon group for '+spec.name+' at '+entry.slot);
  [['0','UNASSIGNED'],['1','GROUP 1 // X'],['2','GROUP 2 // Y'],['3','GROUP 3 // B'],['4','GROUP 4 // A']].forEach(function(o){var opt=document.createElement('option');opt.value=o[0];opt.textContent=o[1];assignment.appendChild(opt);});
  assignment.value=String(entry.group);assignment.addEventListener('change',function(){
   var result=window.vigilSetMechWeaponGroup&&window.vigilSetMechWeaponGroup(buildId,entry.slot,entry.id,Number(assignment.value));
   if(!result||!result.ok){say(result&&result.reason||'WEAPON GROUP ASSIGNMENT UNAVAILABLE');return;}
   weaponHudSignature='';var fresh=getBuild();if(fresh){selectedBuild=fresh;buildWeaponHud(fresh);}
  });row.appendChild(assignment);
  var readout=document.createElement('div');readout.className='m3-weapon-readout';
  [['ammo','AMMO / RESERVE'],['heat','THERMAL CORE'],['condition','COMPONENT CONDITION'],['status','FIRING CIRCUIT']].forEach(function(pair){var k=document.createElement('span');k.textContent=pair[1];var v=document.createElement('b');v.dataset.readout=pair[0];v.textContent='—';readout.appendChild(k);readout.appendChild(v);});
  row.appendChild(readout);
  var ammo=document.createElement('div');ammo.className='m3-meter ammo';var ammoFill=document.createElement('span');ammoFill.dataset.meter='ammo';ammo.appendChild(ammoFill);row.appendChild(ammo);
  var heat=document.createElement('div');heat.className='m3-meter heat';var heatFill=document.createElement('span');heatFill.dataset.meter='heat';heat.appendChild(heatFill);row.appendChild(heat);
  var integrity=document.createElement('div');integrity.className='m3-meter integrity';var integrityFill=document.createElement('span');integrityFill.dataset.meter='integrity';integrity.appendChild(integrityFill);row.appendChild(integrity);
  target.appendChild(row);
 }
 weaponHudEntries.forEach(function(entry){createModule(entry,entry.group===0?unassigned:groupRoot.querySelector('#m3-group-list-'+entry.group));});
 if(!weaponHudEntries.length){var none=document.createElement('p');none.className='muted';none.textContent='NO WEAPON MODULES FITTED // INSTALL LA- OR HA- HARDPOINTS IN THE HANGER.';unassigned.appendChild(none);}
 root.querySelectorAll('.m3-weapon-group').forEach(function(card){var n=weaponGroupEntries(Number(card.dataset.group)).length;card.querySelector('.m3-group-count').textContent=n+' MODULE'+(n===1?'':'S');});
 updateWeaponGroupSelection();updateWeaponHud();
}
function updateWeaponHud(){
 var states=window.vigilGetMechEquipmentState&&window.vigilGetMechEquipmentState(unitId)||{};
 updateRoleReadouts(selectedBuild);
 weaponHudEntries.forEach(function(entry){
  var row=Array.prototype.find.call(root.querySelectorAll('.m3-weapon-module'),function(n){return n.dataset.weaponKey===entry.key;});if(!row)return;
  var state=states[entry.key]||{},id=entry.id,ammo=row.querySelector('[data-readout="ammo"]'),heat=row.querySelector('[data-readout="heat"]'),condition=row.querySelector('[data-readout="condition"]'),status=row.querySelector('[data-readout="status"]');
  var hp=Math.max(0,Math.min(100,Number(state.integrity==null?100:state.integrity))),temp=Math.max(0,Math.min(100,Number(state.heat)||0)),mag=Number(state.magazineRemaining),capacity=Number(state.magazineCapacity),reserve=Number(state.reserveRemaining);
  var melee=id==='HA-PILE';
  ammo.textContent=melee?'ACTUATOR // NO MAGAZINE':(Number.isFinite(mag)&&Number.isFinite(capacity)?Math.round(mag)+' / '+Math.round(capacity)+' // RES '+Math.round(reserve||0):'INITIALIZING');
  heat.textContent=melee?'CONTACT ACTUATOR':temp.toFixed(0)+'% / 100%'+(state.overheated?' // LOCKOUT':'');
  condition.textContent=hp.toFixed(0)+'%'+(state.disabled?' // DESTROYED':'');
  status.textContent=state.disabled?'X // OFFLINE':state.overheated?'OVERHEATED':state.armed?'ARMED':(state.mode||'SAFE');
  row.classList.toggle('destroyed',!!state.disabled);
  row.querySelector('[data-meter="ammo"]').style.width=capacity>0?Math.max(0,Math.min(100,mag/capacity*100))+'%':'0%';
  row.querySelector('[data-meter="heat"]').style.width=temp+'%';
  row.querySelector('[data-meter="integrity"]').style.width=hp+'%';
 });
 root.querySelectorAll('.m3-weapon-group').forEach(function(card){var g=Number(card.dataset.group);card.querySelector('.m3-group-count').textContent=weaponGroupEntries(g).length+' MODULE'+(weaponGroupEntries(g).length===1?'':'S');});
 root.querySelector('#m3-group-arm').disabled=!weaponGroupEntries(activeWeaponGroup).length;
 root.querySelector('#m3-group-fire').disabled=!weaponGroupEntries(activeWeaponGroup).length;
 root.querySelector('#m3-group-reload').disabled=!weaponGroupEntries(activeWeaponGroup).length;
 root.querySelector('#m3-group-safe').disabled=!weaponGroupEntries(activeWeaponGroup).length;
 updateWeaponReticle();
}
function nearestFusedTrack(){
 var tracks=latestFusedSpatialModel&&latestFusedSpatialModel.tracks||[],own=window.vigilGetRegionalSimulationUnit&&window.vigilGetRegionalSimulationUnit(unitId);
 if(!own)return null;var best=null;
 tracks.forEach(function(t){var dx=Number(t.normalized_position&&t.normalized_position[0])-Number(own.x),dy=Number(t.normalized_position&&t.normalized_position[1])-Number(own.y);if(dx>.5)dx-=1;if(dx<-.5)dx+=1;if(dy>.5)dy-=1;if(dy<-.5)dy+=1;var d=Math.hypot(dx,dy);if(!best||d<best.distance)best={track:t,distance:d};});
 return best;
}
function updateWeaponReticle(){
 var entries=weaponGroupEntries(activeWeaponGroup),art=root.querySelector('#m3-reticle-art'),title=root.querySelector('#m3-reticle-title'),detail=root.querySelector('#m3-reticle-detail'),pip=root.querySelector('#m3-weapon-pip');
 if(!art||!title||!detail)return;
 if(!entries.length){art.className='m3-reticle-art';art.textContent='＋';title.textContent='NORMAL SCOPE // EMPTY GROUP';detail.textContent='ASSIGN A FITTED WEAPON TO GROUP '+activeWeaponGroup+' TO LOAD ITS RETICLE AND READOUTS.';if(pip)pip.style.display='none';return;}
 var kinds=entries.map(function(e){return weaponCatalog[e.id].kind;}),kind=kinds.indexOf('arc')>=0?'arc':kinds.indexOf('lock')>=0?'lock':kinds.indexOf('sniper')>=0?'sniper':kinds.indexOf('spread')>=0?'spread':kinds.indexOf('melee')>=0?'melee':'normal';
 art.className='m3-reticle-art '+kind;art.textContent=kind==='arc'?'⌁':kind==='lock'?'▣':kind==='sniper'?'⌖':kind==='spread'?'◎':kind==='melee'?'⊕':'＋';
 var scope=kind==='arc'?'HIGH-ANGLE / BALLISTIC SCOPE':kind==='lock'?'MISSILE TRACKING BOX':kind==='sniper'?'SNIPER OPTIC / RANGEFINDER':kind==='spread'?'TRACKING CIRCLE / SPREAD BLOOM':kind==='melee'?'CONTACT ALIGNMENT':'NORMAL SCOPE / DIGITAL ALIGNMENT';
 title.textContent='GROUP '+activeWeaponGroup+' // '+scope;
 var nearest=nearestFusedTrack(),range=nearest?'NEAREST TRACK '+nearest.distance.toFixed(4)+' MAP UNITS // CONF '+Math.round(nearest.track.confidence*100)+'%':'NO POSITIONED TRACK // RANGE UNAVAILABLE';
 var extra=kind==='arc'?'ELEVATION MATRIX // PARABOLIC SOLUTION REQUIRES RANGE INPUT. ':kind==='lock'?'SEEKER ACQUISITION // TRACK DATA IS NOT AN AUTOMATIC WEAPON LOCK. ':kind==='sniper'?'DIGITAL OPTIC // SENSOR-CENTERED PIP // WIND DATA NOT PROVIDED BY CURRENT SENSOR MODEL. ':kind==='spread'?'BLOOM / CONVERGENCE // TRACKING AREA FOLLOWS GROUP TYPE. ':'';
 detail.textContent=entries.map(function(e){return weaponCatalog[e.id].name;}).join(' + ')+' // '+extra+range;
 if(pip)pip.style.display=kind==='sniper'?'block':'none';
}
function renderWeaponOpticPip(){
 var pip=root.querySelector('#m3-weapon-pip');if(!pip||pip.style.display==='none'||!environmentCanvas)return;
 var ctx=pip.getContext('2d');if(!ctx)return;
 var w=pip.width,h=pip.height,sw=environmentCanvas.width,sh=environmentCanvas.height;if(!sw||!sh)return;
 var cropW=sw*.34,cropH=sh*.34,sx=(sw-cropW)/2,sy=(sh-cropH)/2;
 ctx.clearRect(0,0,w,h);ctx.drawImage(environmentCanvas,sx,sy,cropW,cropH,0,0,w,h);
 ctx.strokeStyle='#a8e9c0';ctx.lineWidth=1;ctx.strokeRect(1,1,w-2,h-2);ctx.beginPath();ctx.moveTo(w/2-20,h/2);ctx.lineTo(w/2+20,h/2);ctx.moveTo(w/2,h/2-18);ctx.lineTo(w/2,h/2+18);ctx.stroke();
 ctx.fillStyle='#a8e9c0';ctx.font='12px monospace';ctx.fillText('DIGITAL OPTIC // 3X CENTER CROP',8,15);
}
function commandWeaponGroup(action){
 var entries=weaponGroupEntries(activeWeaponGroup);if(!entries.length){say('GROUP '+activeWeaponGroup+' // NO WEAPONS ASSIGNED');return;}
 var accepted=0,refused=0,last='';
 entries.forEach(function(e){
  var command=action;
  if(e.id==='HA-PILE'){if(action==='RELOAD')return;command=action==='FIRE'?'STRIKE':'LOCK';}
  var result=window.vigilCommandMechEquipment&&window.vigilCommandMechEquipment({unit_id:unitId,build_id:buildId,slot:e.slot,equipment_id:e.id,kind:e.id==='HA-PILE'?'MELEE ACTUATOR':'WEAPON',action:command,mode:equipmentState[e.key+'|mode']||'DEFAULT'});
  if(result&&result.ok){accepted++;last=result.status||result.action;}else{refused++;last=result&&result.reason||'COMMAND API UNAVAILABLE';}
 });
 say('GROUP '+activeWeaponGroup+' // '+action+' // ACCEPTED '+accepted+' / REFUSED '+refused+(last?' // '+last:''));
 updateWeaponHud();
}
function bindWeaponHudControls(){
 [['m3-group-arm','ARM'],['m3-group-fire','FIRE'],['m3-group-reload','RELOAD'],['m3-group-safe','SAFE']].forEach(function(pair){
  var button=root.querySelector('#'+pair[0]);if(button)button.addEventListener('click',function(){commandWeaponGroup(pair[1]);});
 });
}

function actionSpec(id){if(/^LA-|^HA-/.test(id)&&id!=='HA-PILE')return {kind:'WEAPON',actions:[['SAFE','SAFE'],['ARM','ARM'],['FIRE','FIRE / CYCLE'],['RELOAD','RELOAD']],modes:id==='HA-HW'||id==='HA-MT'?['DIRECT','INDIRECT']:id==='HA-ML'||id==='LA-RK'?['SINGLE','SALVO']:['SEMI','BURST']};if(id==='AS-THERM'||id==='AS-NV'||id==='AS-MINE')return {kind:'SENSOR',actions:[['POWER','POWER'],['SCAN','SCAN']],modes:id==='AS-MINE'?['GROUND SWEEP','PROXIMITY']:['WIDE','NARROW','TRACK']};if(id==='AS-JAM')return {kind:'ELECTRONIC WARFARE',actions:[['JAM','JAMMER'],['PULSE','PULSE']]};if(id==='AS-MC')return {kind:'COUNTERMEASURES',actions:[['ARM','ARM'],['RELEASE','RELEASE']]};if(id==='AS-SMOKE')return {kind:'OBSCURANT',actions:[['ARM','ARM'],['DEPLOY','DEPLOY']]};if(id==='AS-ARM')return {kind:'ARMOR',actions:[['ENABLE','ENABLE'],['RESET','RESET']]};if(id==='AS-FUEL')return {kind:'POWER SUPPORT',actions:[['AUX','AUX POWER'],['ISOLATE','ISOLATE']]};if(/^NA-/.test(id))return {kind:'TACTICAL BEACON',actions:[['STANDBY','STANDBY'],['DEPLOY','DEPLOY'],['RECALL','RECALL']]};if(id==='HA-PILE')return {kind:'MELEE ACTUATOR',actions:[['LOCK','LOCK'],['STRIKE','STRIKE']]};return {kind:'EQUIPMENT',actions:[['ENABLE','ENABLE'],['STANDBY','STANDBY']]};}
function equipmentEntries(){var entries=[],b=selectedBuild||{};Object.keys(b.parts||{}).forEach(function(slot){if(b.parts[slot])entries.push({slot:slot,id:b.parts[slot]});});Object.keys(b.mounts||{}).forEach(function(slot){if(b.mounts[slot])entries.push({slot:slot,id:b.mounts[slot]});});return entries;}
function renderEquipment(){var picker=root.querySelector('#m3-equipment-picker'),panel=root.querySelector('#m3-selected-module');picker.innerHTML='';var entries=equipmentEntries();if(!entries.length){picker.textContent='NO INSTALLED COMPONENTS';panel.innerHTML='<h4>EMPTY LOADOUT</h4><p class="muted">Return to the hanger to install equipment.</p>';selectedEquipment=null;return;}if(!selectedEquipment||!entries.some(function(e){return e.slot===selectedEquipment.slot&&e.id===selectedEquipment.id;}))selectedEquipment=entries[0];entries.forEach(function(e){var btn=document.createElement('button');btn.type='button';btn.className=selectedEquipment.slot===e.slot&&selectedEquipment.id===e.id?'active':'';var name=document.createElement('span');name.textContent=e.id;var slot=document.createElement('small');slot.textContent=e.slot;btn.appendChild(name);btn.appendChild(slot);btn.addEventListener('click',function(){selectedEquipment=e;renderEquipment();draw();});picker.appendChild(btn);});panel.innerHTML='';var title=document.createElement('h4');title.textContent=selectedEquipment.slot+' // '+selectedEquipment.id;panel.appendChild(title);var desc=document.createElement('p');desc.className='muted';desc.textContent='CONTROL TARGET LOCKED TO '+unitId+' / '+selectedEquipment.slot+' / '+selectedEquipment.id;panel.appendChild(desc);var spec=actionSpec(selectedEquipment.id),controls=document.createElement('div');controls.className='controls';var modeSelect=null;if(spec.modes){modeSelect=document.createElement('select');modeSelect.setAttribute('aria-label','Operating mode for '+selectedEquipment.id);spec.modes.forEach(function(mode){var option=document.createElement('option');option.value=mode;option.textContent=mode;modeSelect.appendChild(option);});modeSelect.value=equipmentState[selectedEquipment.slot+'|'+selectedEquipment.id+'|mode']||spec.modes[0];modeSelect.addEventListener('change',function(){equipmentState[selectedEquipment.slot+'|'+selectedEquipment.id+'|mode']=modeSelect.value;});controls.appendChild(modeSelect);}spec.actions.forEach(function(a){var btn=document.createElement('button');btn.type='button';btn.textContent=a[1];btn.addEventListener('click',function(){var target={unit_id:unitId,build_id:buildId,slot:selectedEquipment.slot,equipment_id:selectedEquipment.id,kind:spec.kind,action:a[0],mode:modeSelect?modeSelect.value:'DEFAULT'};var result=window.vigilCommandMechEquipment&&window.vigilCommandMechEquipment(target);if(result&&result.ok){equipmentState[selectedEquipment.slot+'|'+selectedEquipment.id]=a[0];var prior=panel.querySelector('.command-feedback');if(prior)prior.remove();var state=document.createElement('p');state.className='muted command-feedback';state.textContent='COMMAND ACCEPTED: '+a[0]+' // '+target.equipment_id+' @ '+target.slot+' // '+(result.status||'');panel.appendChild(state);say('COMMAND ACCEPTED BY '+target.equipment_id+' // '+target.slot);}else say(result&&result.reason||'PART CONTROL INTERFACE UNAVAILABLE');});controls.appendChild(btn);});panel.appendChild(controls);var feedback=document.createElement('p');feedback.className='muted command-feedback';feedback.textContent='LAST COMMAND: '+(equipmentState[selectedEquipment.slot+'|'+selectedEquipment.id]||'NONE');panel.appendChild(feedback);}
function open(requestedUnit){var activeDisplay=window.vigilGetActiveSensorDisplay&&window.vigilGetActiveSensorDisplay(),activeUnit=window.vigilGetActiveSimulationUnit&&window.vigilGetActiveSimulationUnit(),candidate=String(requestedUnit||activeDisplay&&activeDisplay.unit||activeUnit&&activeUnit.id||window.vigilActiveSimulationUnit&&window.vigilActiveSimulationUnit.id||'').toUpperCase();requestedUnitId=/^MECH-/.test(candidate)?candidate:'';var b=getBuild();if(!b){say('SELECT A HOUND IN THE HANGER FIRST');return;}selectedBuild=b;buildId=b.id;unitId=b.simulationUnitId||'MECH-01';selectedEquipment=null;canvas.style.width='100%';canvas.style.height='clamp(300px,58vh,720px)';canvas.style.display='block';canvas.style.touchAction='none';active=true;root.classList.add('open');refresh();draw();say('HOUND WEBGL PILOT STATION ACTIVE // '+unitId);}
function close(){active=false;root.classList.remove('open');canvas.style.height='clamp(300px,58vh,720px)'; }
root.querySelector('#m3-close').addEventListener('click',close);

window.addEventListener('vigil:simulation-unit-state-changed',refresh);window.addEventListener('vigil:mech-loadout-applied',function(){if(active){selectedBuild=getBuild();buildId='';refresh();}});
function installButton(){var garage=document.getElementById('vigil-wy-garage');if(!garage)return;var head=garage.querySelector('.head');if(!head||head.querySelector('#vigil-open-mech-3d'))return;var b=document.createElement('button');b.id='vigil-open-mech-3d';b.type='button';b.textContent='LAUNCH HOUND 3D PILOT VIEW';b.addEventListener('click',open);head.appendChild(b);}
installButton();var count=0;var timer=setInterval(function(){installButton();count++;if(document.getElementById('vigil-open-mech-3d')||count>80)clearInterval(timer);},250);
window.vigilOpenMech3DView=open;window.setInterval(function(){if(active)refresh();},150);window.addEventListener('resize',draw);
})();