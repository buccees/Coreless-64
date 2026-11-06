/* Independent pilot displays for non-mech, non-submersible VIGIL craft.
   Each craft class owns its own DOM, WebGL context, geometry and controls. */
(function(){
'use strict';
if(window.vigilOtherVehicleViewsLoaded)return;window.vigilOtherVehicleViewsLoaded=true;
var root=null,canvas=null,canvases={},renderers={},gl=null,program=null,activeType='',yaw=-.55,pitch=.12,drag=null,raf=0,activeSensor='';
var specs={
 ship:{title:'DDG-51 // GUIDED-MISSILE DESTROYER',environment:'SURFACE NAVIGATION',speedLabel:'KNOTS',body:[3.25,.48,.78],color:[.39,.47,.43,1]},
 submarine:{title:'SSN-774 // ATTACK SUBMARINE',environment:'SUBSURFACE NAVIGATION',speedLabel:'KNOTS',body:[2.9,.58,.72],color:[.34,.43,.4,1]},
 drone:{title:'DRONE-01 // RECONNAISSANCE AIRCRAFT',environment:'AERIAL FLIGHT',speedLabel:'AIR SPEED',body:[1.35,.24,.24],color:[.43,.55,.42,1]},
 mothership:{title:'DAEDALUS-01 // ORBITAL MOTHERSHIP',environment:'ORBITAL FLIGHT',speedLabel:'ORBITAL VELOCITY',body:[3.6,.5,1.05],color:[.52,.57,.48,1]}
};
function el(tag,attrs,parent){var n=document.createElement(tag);Object.keys(attrs||{}).forEach(function(k){if(k==='text')n.textContent=attrs[k];else n.setAttribute(k,attrs[k]);});(parent||root).appendChild(n);return n;}
function build(){if(root)return;root=document.createElement('section');root.id='vigil-independent-vehicle-view';root.style.cssText='display:none;position:fixed;inset:0;z-index:2147483001;background:#020906;color:#c5f2d4;font:12px/1.45 Courier New,monospace;overflow:auto;padding:12px;box-sizing:border-box';document.body.appendChild(root);
var style=document.createElement('style');style.textContent='#vigil-independent-vehicle-view *{box-sizing:border-box}#vigil-independent-vehicle-view.open{display:block!important}#vigil-independent-vehicle-view button{background:#0a2417;color:#c5f2d4;border:1px solid #397b56;padding:8px 12px;font:inherit;cursor:pointer}#vigil-independent-vehicle-view button:active{background:#24623e}#vigil-independent-vehicle-view .iv-head{display:flex;gap:10px;justify-content:space-between;align-items:center;flex-wrap:wrap;border-bottom:1px solid #397b56;padding:8px}#vigil-independent-vehicle-view .iv-grid{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(240px,.7fr);gap:12px;margin-top:12px}#vigil-independent-vehicle-view canvas{display:block;width:100%;height:clamp(320px,62vh,720px);border:1px solid #397b56;background:radial-gradient(ellipse,#123522,#010604 75%);touch-action:none}#vigil-independent-vehicle-view .iv-pane{border:1px solid #28533a;background:#041009;padding:12px;margin-bottom:10px}#vigil-independent-vehicle-view .iv-controls{display:flex;flex-wrap:wrap;gap:7px;margin:8px 0}#vigil-independent-vehicle-view .iv-stat{display:grid;grid-template-columns:1fr 1fr;gap:7px}#vigil-independent-vehicle-view .iv-stat div{border:1px solid #234531;padding:8px}#vigil-independent-vehicle-view strong{color:#e0ffe9}@media(max-width:760px){#vigil-independent-vehicle-view .iv-grid{grid-template-columns:1fr}}';document.head.appendChild(style);
var head=el('div',{class:'iv-head'});el('strong',{id:'iv-title',text:'VEHICLE PILOT STATION'},head);var close=el('button',{text:'CLOSE PILOT VIEW'},head);close.addEventListener('click',shut);
var grid=el('div',{class:'iv-grid'});var left=el('div',{},grid);Object.keys(specs).forEach(function(type){var c=el('canvas',{id:'vigil-'+type+'-pilot-canvas',width:'1200',height:'800'},left);c.style.display='none';canvases[type]=c;c.addEventListener('pointerdown',function(e){drag={x:e.clientX,y:e.clientY};c.setPointerCapture(e.pointerId);});c.addEventListener('pointermove',function(e){if(!drag)return;yaw+=(e.clientX-drag.x)*.008;pitch=Math.max(-.8,Math.min(.8,pitch+(e.clientY-drag.y)*.006));drag={x:e.clientX,y:e.clientY};render();});['pointerup','pointercancel'].forEach(function(k){c.addEventListener(k,function(){drag=null;});});});var right=el('div',{},grid);
var nav=el('div',{class:'iv-pane'},right);el('strong',{text:'FLIGHT / NAVIGATION CONTROL'},nav);var controls=el('div',{class:'iv-controls'},nav);
[['−15°','turnL'],['+15°','turnR'],['NORTH','north'],['SPEED −','slower'],['SPEED +','faster'],['STOP','stop']].concat(activeType==='submarine'?[['ASCEND +5m','depthUp'],['DESCEND +5m','depthDown']]:[]).forEach(function(a){var b=el('button',{text:a[0]},controls);b.addEventListener('click',function(){command(a[1]);});});
var stats=el('div',{class:'iv-pane'},right);el('strong',{text:'LIVE SIMULATION TELEMETRY'},stats);var statGrid=el('div',{class:'iv-stat'},stats);['HEADING','SPEED','DEPLOYMENT','UNIT ID','DEPTH'].forEach(function(k){var d=el('div',{},statGrid);el('small',{text:k},d);el('strong',{id:'iv-'+k.toLowerCase().replace(' ','-'),text:'—'},d);});
var sensors=el('div',{class:'iv-pane'},right);el('strong',{text:'PLATFORM SENSOR SUITE // UNIT-OWNED CHANNELS'},sensors);el('div',{id:'iv-sensor-list',class:'iv-controls'},sensors);el('div',{id:'iv-sensor-readout',text:'SELECT AN INSTALLED SENSOR TO REQUEST A SIMULATED MEASUREMENT.'},sensors);
var status=el('div',{class:'iv-pane',id:'iv-status',text:'SIMULATION LINK STANDBY'},right);

}
function shader(type,src){var s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
function initGL(){gl=canvas.getContext('webgl',{antialias:true,alpha:false});if(!gl)return false;var v=shader(gl.VERTEX_SHADER,'attribute vec3 p;uniform mat4 mvp;void main(){gl_Position=mvp*vec4(p,1.0);}'),f=shader(gl.FRAGMENT_SHADER,'precision mediump float;uniform vec4 col;void main(){gl_FragColor=col;}');program=gl.createProgram();gl.attachShader(program,v);gl.attachShader(program,f);gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))return false;renderers[activeType]={canvas:canvas,gl:gl,program:program};return true;}
function mul(a,b){var o=new Float32Array(16);for(var c=0;c<4;c++)for(var r=0;r<4;r++)o[c*4+r]=a[r]*b[c*4]+a[4+r]*b[c*4+1]+a[8+r]*b[c*4+2]+a[12+r]*b[c*4+3];return o;}
function persp(f,a,n,z){var q=1/Math.tan(f/2),v=1/(n-z),m=new Float32Array(16);m[0]=q/a;m[5]=q;m[10]=(z+n)*v;m[11]=-1;m[14]=2*z*n*v;return m;}
function rotY(a){return new Float32Array([Math.cos(a),0,-Math.sin(a),0,0,1,0,0,Math.sin(a),0,Math.cos(a),0,0,0,0,1]);}
function rotX(a){return new Float32Array([1,0,0,0,0,Math.cos(a),Math.sin(a),0,0,-Math.sin(a),Math.cos(a),0,0,0,0,1]);}
function drawBox(vp,x,y,z,sx,sy,sz,color){var p=[-.5,-.5,-.5,.5,-.5,-.5,.5,.5,-.5,-.5,.5,-.5,-.5,-.5,.5,.5,-.5,.5,.5,.5,.5,-.5,.5,.5],ix=[0,1,2,0,2,3,4,6,5,4,7,6,0,4,5,0,5,1,3,2,6,3,6,7,1,5,6,1,6,2,0,3,7,0,7,4],a=[];ix.forEach(function(i){a.push(p[i*3],p[i*3+1],p[i*3+2]);});var b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(a),gl.STREAM_DRAW);var model=new Float32Array([sx,0,0,0,0,sy,0,0,0,0,sz,0,x,y,z,1]);gl.uniformMatrix4fv(gl.getUniformLocation(program,'mvp'),false,mul(vp,model));gl.uniform4fv(gl.getUniformLocation(program,'col'),color);var loc=gl.getAttribLocation(program,'p');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,0,0);gl.drawArrays(gl.TRIANGLES,0,36);gl.deleteBuffer(b);}
function drawHull(vp,length,height,beam,color){
 /* Tapered multi-ring hull mesh: pointed bow/stern, not a stack of rectangular blocks. */
 var rings=[[-.5,.025,.025],[-.39,.31,.24],[.22,.5,.5],[.43,.34,.3],[.5,.015,.015]],segments=10,verts=[];
 for(var r=0;r<rings.length-1;r++)for(var j=0;j<segments;j++){
  var a=j/segments*Math.PI*2,b=(j+1)/segments*Math.PI*2,A=rings[r],B=rings[r+1];
  function v(R,T){return [R[0]*length,Math.cos(T)*R[1]*height,Math.sin(T)*R[2]*beam];}
  var p1=v(A,a),p2=v(A,b),p3=v(B,b),p4=v(B,a);
  verts.push.apply(verts,p1.concat(p2,p3,p1,p3,p4));
 }
 var buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(verts),gl.STREAM_DRAW);
 gl.uniformMatrix4fv(gl.getUniformLocation(program,'mvp'),false,vp);gl.uniform4fv(gl.getUniformLocation(program,'col'),color);
 var loc=gl.getAttribLocation(program,'p');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,0,0);gl.drawArrays(gl.TRIANGLES,0,verts.length/3);gl.deleteBuffer(buf);
}
function render(){if(!gl||!root.classList.contains('open'))return;var d=Math.min(devicePixelRatio||1,2),w=canvas.clientWidth,h=canvas.clientHeight;canvas.width=Math.max(1,w*d);canvas.height=Math.max(1,h*d);gl.viewport(0,0,canvas.width,canvas.height);gl.enable(gl.DEPTH_TEST);gl.clearColor(.004,.018,.01,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(program);var view=mul(rotX(pitch),rotY(yaw)),translate=new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,-7.4,1]),vp=mul(persp(.75,canvas.width/canvas.height,.1,80),mul(translate,view)),sp=specs[activeType],c=sp.color;
function box(x,y,z,a,b,q,col){drawBox(vp,x,y,z,a,b,q,col||c);}
if(activeType==='ship'){
/* DDG-51 surface combatant: long tapered hull, raised foredeck, bridge, aft hangar and mast. */
drawHull(vp,4.15,.48,.92,c);box(-.62,.2,0,1.1,.28,.58,[.55,.61,.53,1]);box(.42,.43,0,.92,.78,.58,[.48,.55,.48,1]);box(.28,.88,-.02,.12,.72,.12,[.65,.72,.62,1]);box(.28,1.28,-.02,.52,.08,.52,[.65,.72,.62,1]);box(1.42,.22,0,.62,.48,.54,[.48,.55,.48,1]);box(1.7,.52,0,.36,.24,.38,[.62,.68,.58,1]);box(-1.4,.22,0,.34,.22,.34,[.72,.72,.58,1]);box(-1.68,.12,0,.28,.18,.28,[.72,.72,.58,1]);
}
else if(activeType==='submarine'){drawHull(vp,3.75,.72,.82,c);box(0,.52,-.08,.85,.48,.62,[.28,.36,.34,1]);box(0,.86,-.08,.18,.28,.2,[.65,.72,.62,1]);box(-1.45,-.05,0,.38,.16,1,[.23,.31,.29,1]);box(1.45,-.05,0,.38,.16,1,[.23,.31,.29,1]);box(0,0,.52,.7,.08,.08,[.68,.72,.58,1]);}
else if(activeType==='drone'){drawHull(vp,2.45,.24,.28,c);box(0,0,0,.38,.2,3.2,[.36,.47,.39,1]);box(0,.12,-.82,.5,.12,.85,[.6,.68,.5,1]);box(0,.1,1.1,.35,.12,.7,[.6,.68,.5,1]);[-1,1].forEach(function(s){box(s*.8,.18,0,.08,.08,1.3,[.68,.72,.58,1]);box(s*.8,.25,0,.8,.035,.08,[.72,.78,.65,1]);});}
else if(activeType==='mothership'){box(0,0,0,4.2,.52,1.1,c);box(0,.32,0,2.5,.18,.72,[.68,.67,.49,1]);[-1,1].forEach(function(s){box(s*1.45,-.12,0,.9,.18,2.2,[.36,.45,.38,1]);box(s*1.45,-.08,-1.15,.48,.3,.45,[.65,.7,.55,1]);box(s*1.45,-.08,1.15,.48,.3,.45,[.65,.7,.55,1]);});box(0,.5,-.15,.6,.32,.55,[.78,.72,.5,1]);}
}
function command(action){var u=window.vigilGetRegionalSimulationUnit&&window.vigilGetRegionalSimulationUnit(activeType);if(!u){document.getElementById('iv-status').textContent='NO FRIENDLY '+activeType.toUpperCase()+' ENTITY ASSIGNED';return;}var h=Number(u.desired_heading_deg==null?u.heading_deg:u.desired_heading_deg)||0,s=Number(u.target_speed==null?u.speed:u.target_speed)||0,max=Number(u.max_speed)||0,change={};if(action==='turnL')change.heading=h-15;if(action==='turnR')change.heading=h+15;if(action==='north')change.heading=0;if(action==='slower')change.speed=Math.max(0,s-max*.1);if(action==='faster')change.speed=Math.min(max,s+max*.1);if(action==='stop')change.speed=0;if(action==='depthUp'||action==='depthDown'){var depth=Number(u.target_depth_meters==null?u.depth_meters:u.target_depth_meters)||0;change.depth=Math.max(0,Math.min(30000,depth+(action==='depthDown'?5:-5)));}var result=window.vigilSetSimulationUnitState&&window.vigilSetSimulationUnitState(activeType,change);document.getElementById('iv-status').textContent=result&&result.ok?'COMMAND ACCEPTED // SIMULATION PHYSICS APPLYING':'COMMAND REJECTED // '+(result&&result.reason||'SIMULATION CONTROL LINK UNAVAILABLE');refresh();}
function renderSensors(){
 var list=document.getElementById('iv-sensor-list'),readout=document.getElementById('iv-sensor-readout'),net=window.vigilFleetSensorNetwork;
 if(!list||!readout)return;list.innerHTML='';
 var pkg=net&&net.getUnitPackage?net.getUnitPackage(activeType):null,items=pkg&&pkg.sensors||[];
 if(!items.length){readout.textContent='NO SENSOR PACKAGE AVAILABLE FOR THIS PLATFORM.';return;}
 items.forEach(function(sensor){
  var b=document.createElement('button');b.type='button';b.textContent=sensor[0];b.style.borderColor=activeSensor===sensor[0]?'#d9c17c':'';
  b.addEventListener('click',function(){activeSensor=sensor[0];var frame=net&&net.getFrame?net.getFrame(activeType,activeSensor):null;renderSensors();if(!frame){readout.textContent='SENSOR FRAME UNAVAILABLE // '+activeSensor;return;}
   readout.innerHTML='';var heading=document.createElement('strong');heading.textContent=frame.sensor_name+' // '+frame.provenance;readout.appendChild(heading);
   (frame.measurements||[]).forEach(function(m){var row=document.createElement('div');row.textContent=m.label+': '+m.value+(m.units?' '+m.units:'');readout.appendChild(row);});
   var hits=document.createElement('p');hits.textContent='CONTACT RETURNS: '+((frame.detected_contacts||[]).length);readout.appendChild(hits);
   if(window.vigilRecordUnitSensorFeed)window.vigilRecordUnitSensorFeed(frame);
  });list.appendChild(b);
 });
 if(!activeSensor||!items.some(function(s){return s[0]===activeSensor;}))activeSensor=items[0][0];
 if(!readout.textContent||readout.textContent.indexOf('SELECT AN INSTALLED')===0)readout.textContent='SELECT A SENSOR CHANNEL TO REQUEST A LIVE SIMULATION FRAME // '+items.length+' CHANNELS AVAILABLE.';
}
function refresh(){if(!root||!activeType)return;var u=window.vigilGetRegionalSimulationUnit&&window.vigilGetRegionalSimulationUnit(activeType);if(!u)return;document.getElementById('iv-heading').textContent=(Math.round(Number(u.desired_heading_deg==null?u.heading_deg:u.desired_heading_deg)||0)+'°');document.getElementById('iv-speed').textContent=(Number(u.target_speed==null?u.speed:u.target_speed)||0).toFixed(4);document.getElementById('iv-deployment').textContent=u.deployment_status||'DEPLOYED';document.getElementById('iv-unit-id').textContent=u.id;var depth=document.getElementById('iv-depth');if(depth)depth.textContent=u.depth_meters==null?'N/A':Number(u.depth_meters).toFixed(1)+' m';}
function open(type){if(!specs[type])return false;if(type==='mothership'){var orbital=document.getElementById('vigil-daedalus-orbital-launch');if(orbital&&!orbital.hidden){orbital.click();return true;}document.getElementById('iv-status')&&(document.getElementById('iv-status').textContent='DAEDALUS ORBITAL SENSOR SUITE IS STILL INITIALIZING');return false;}build();activeType=type;Object.keys(canvases).forEach(function(k){canvases[k].style.display=k===type?'block':'none';});canvas=canvases[type];root.classList.add('open');document.body.style.overflow='hidden';document.getElementById('iv-title').textContent=specs[type].title+' // '+specs[type].environment;if(renderers[type]){gl=renderers[type].gl;program=renderers[type].program;}else if(!initGL()){document.getElementById('iv-status').textContent='WEBGL CONTEXT UNAVAILABLE FOR THIS VEHICLE';return false;}refresh();renderSensors();render();if(!raf)raf=setInterval(function(){refresh();render();},180);return true;}
function shut(){if(root)root.classList.remove('open');document.body.style.overflow='';}
window.vigilOpenOtherVehicle3DView=open;window.vigilCloseOtherVehicle3DView=shut;
})();
