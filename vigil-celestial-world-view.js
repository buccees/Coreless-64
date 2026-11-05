(function(){
'use strict';
function boot(){
  var mount=document.getElementById('vigil-map-tab-mount');
  var atlas=document.getElementById('vigil-cosmic-atlas');
  var core=window.VigilNirnGravityCore;
  if(!mount||!atlas||!core||mount.querySelector('#vigil-celestial-world-panel'))return;
  var bodies=core.cloneBodies();
  var byId=Object.create(null);bodies.forEach(function(b){byId[b.id]=b;});
  var panel=document.createElement('section');panel.id='vigil-celestial-world-panel';panel.className='vigil-celestial-world-panel';
  panel.innerHTML='<div class="vigil-celestial-head"><div><strong>SELECTED WORLD // WEBGL SURFACE OBSERVATORY</strong><small>MODEL-DERIVED BODY PROFILE · INDEPENDENT MAPS RENDERER</small></div><label>BODY <select id="vigil-celestial-body"></select></label></div><div class="vigil-celestial-layout"><div class="vigil-celestial-viewport"><canvas id="vigil-celestial-world-canvas" width="1200" height="720" aria-label="Three-dimensional generated surface view of the selected celestial body"></canvas><div id="vigil-celestial-world-status">WEBGL INITIALIZING</div></div><aside class="vigil-celestial-readout"><div class="vigil-celestial-name" id="vigil-celestial-name">NIRN</div><div id="vigil-celestial-class" class="vigil-celestial-class">PLANET</div><dl><dt>MODEL RADIUS</dt><dd id="vigil-celestial-radius">—</dd><dt>MODEL MASS</dt><dd id="vigil-celestial-mass">—</dd><dt>AXIAL DAY</dt><dd id="vigil-celestial-spin">—</dd><dt>ORBITAL PARENT</dt><dd id="vigil-celestial-parent">—</dd></dl><p id="vigil-celestial-lore"></p><p class="vigil-celestial-caveat">SURFACE RENDER STATUS: PROCEDURAL VISUALIZATION PROXY. The shared model supplies body identity, classification, mass, radius, spin, parent and lore. It does not specify measured surface maps or canonical geology for most bodies; terrain appearance is illustrative, not a new physical claim.</p></aside></div>';
  mount.appendChild(panel);
  var select=panel.querySelector('#vigil-celestial-body'),canvas=panel.querySelector('#vigil-celestial-world-canvas'),status=panel.querySelector('#vigil-celestial-world-status');
  bodies.forEach(function(b){var o=document.createElement('option');o.value=b.id;o.textContent=(b.kind==='MOON'?'MOON // ':'')+b.name;select.appendChild(o);});
  var gl=canvas.getContext('webgl',{alpha:false,antialias:true,depth:true});
  if(!gl){status.textContent='WEBGL UNAVAILABLE // SURFACE OBSERVATORY CANNOT START';return;}
  var vs='attribute vec3 aPosition;attribute vec3 aColor;uniform mat4 uMatrix;varying vec3 vColor;varying vec3 vNormal;void main(){gl_Position=uMatrix*vec4(aPosition,1.0);vColor=aColor;vNormal=normalize(aPosition);}';
  var fs='precision mediump float;varying vec3 vColor;varying vec3 vNormal;uniform vec3 uLight;void main(){float d=.24+.76*max(dot(normalize(vNormal),normalize(uLight)),0.0);float rim=pow(1.0-max(dot(normalize(vNormal),vec3(0.0,0.0,1.0)),0.0),2.0);gl_FragColor=vec4(vColor*d+vec3(.02,.11,.07)*rim,1.0);}';
  function shader(type,src){var s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;}
  var program=gl.createProgram(),vsh=shader(gl.VERTEX_SHADER,vs),fsh=shader(gl.FRAGMENT_SHADER,fs);gl.attachShader(program,vsh);gl.attachShader(program,fsh);gl.linkProgram(program);
  if(!gl.getProgramParameter(program,gl.LINK_STATUS)){status.textContent='WEBGL LINK ERROR // '+gl.getProgramInfoLog(program);return;}
  gl.deleteShader(vsh);gl.deleteShader(fsh);
  var posLoc=gl.getAttribLocation(program,'aPosition'),colLoc=gl.getAttribLocation(program,'aColor'),matrixLoc=gl.getUniformLocation(program,'uMatrix'),lightLoc=gl.getUniformLocation(program,'uLight');
  var vertexBuffer=gl.createBuffer(),indexBuffer=gl.createBuffer(),indexCount=0,angle=0,last=0,activeId='nirn',raf=0;
  function hash(x,y,seed){var n=Math.sin(x*127.1+y*311.7+seed*74.7)*43758.5453;return n-Math.floor(n);}
  function smooth(a,b,x){var t=Math.max(0,Math.min(1,(x-a)/(b-a)));return t*t*(3-2*t);}
  function makeSurface(body){
    var rows=80,cols=160,positions=[],colors=[],indices=[],seed=body.id.split('').reduce(function(n,c){return n+c.charCodeAt(0);},0);
    var base=[.25,.55,.38];try{var h=body.color.replace('#','');base=[parseInt(h.slice(0,2),16)/255,parseInt(h.slice(2,4),16)/255,parseInt(h.slice(4,6),16)/255];}catch(e){}
    for(var y=0;y<=rows;y++)for(var x=0;x<=cols;x++){
      var u=x/cols,v=y/rows,lat=(v-.5)*Math.PI,lon=u*Math.PI*2;
      var n1=hash(Math.floor(u*38),Math.floor(v*20),seed),n2=hash(Math.floor(u*91),Math.floor(v*47),seed+13),ridge=1-Math.abs(2*n2-1);
      var wave=Math.sin(lon*3+seed*.1)*Math.cos(lat*5)+Math.sin(lon*8-lat*4+seed)*.35;
      var elevation=(n1-.5)*.018+(n2-.5)*.009+wave*.003;
      var nx=Math.cos(lat)*Math.cos(lon),ny=Math.sin(lat),nz=Math.cos(lat)*Math.sin(lon);
      positions.push(nx*(1+elevation),ny*(1+elevation),nz*(1+elevation));
      if(body.id==='nirn'){
        var continent=(n1*.58+n2*.28+ridge*.14);
        if(continent>.59){var green=.28+smooth(.59,.82,continent)*.32;colors.push(.07,green,.19+green*.22);}
        else{var deep=.25+(1-v)*.12;colors.push(.012,.11+deep*.16,.13+deep*.18);}
      }else if(body.kind==='MOON'){
        var crater=1-smooth(.12,.34,Math.abs(wave+n1*.7-.45));
        colors.push(Math.min(1,base[0]*(.58+ridge*.34)+crater*.08),Math.min(1,base[1]*(.58+ridge*.32)+crater*.075),Math.min(1,base[2]*(.58+ridge*.30)+crater*.07));
      }else{
        var band=.82+.12*Math.sin(lat*11+seed*.03)+.08*(n1-.5);
        colors.push(Math.min(1,base[0]*band),Math.min(1,base[1]*band),Math.min(1,base[2]*band));
      }
    }
    for(var j=0;j<rows;j++)for(var i=0;i<cols;i++){var a=j*(cols+1)+i,b=a+1,c=a+cols+1,d=c+1;indices.push(a,b,c,b,d,c);}
    gl.bindBuffer(gl.ARRAY_BUFFER,vertexBuffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(positions.concat(colors)),gl.STATIC_DRAW);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,indexBuffer);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(indices),gl.STATIC_DRAW);indexCount=indices.length;
  }
  function setBody(id){
    var body=byId[id]||byId.nirn;activeId=body.id;select.value=body.id;makeSurface(body);
    panel.querySelector('#vigil-celestial-name').textContent=body.name;
    panel.querySelector('#vigil-celestial-class').textContent=body.kind+(body.kind==='MOON'?' // NATURAL SATELLITE':'');
    panel.querySelector('#vigil-celestial-radius').textContent=Number(body.radius).toLocaleString()+' km';
    panel.querySelector('#vigil-celestial-mass').textContent=(body.mass/5.9722e24).toExponential(3)+' Earth masses';
    panel.querySelector('#vigil-celestial-spin').textContent=body.spin+' hours';
    var parent=body.parent?byId[body.parent]:null;panel.querySelector('#vigil-celestial-parent').textContent=parent?parent.name:'SYSTEM REFERENCE';
    panel.querySelector('#vigil-celestial-lore').textContent=body.lore||'No additional lore description in the current model.';
    status.textContent='WEBGL ONLINE // '+body.kind+' // MODEL ID: '+body.id.toUpperCase();
  }
  function matrix(){
    var c=Math.cos(angle),s=Math.sin(angle),f=1.75,aspect=canvas.width/canvas.height;
    return new Float32Array([f/aspect*c,0,-s,0,0,f,0,0,s,0,c,0,0,0,-2.8,1]);
  }
  function draw(now){
    if(!canvas.isConnected)return;
    var rect=canvas.getBoundingClientRect(),dpr=Math.min(2,window.devicePixelRatio||1),w=Math.max(480,Math.floor(rect.width*dpr)),h=Math.max(300,Math.floor(rect.height*dpr));
    if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
    gl.viewport(0,0,w,h);gl.clearColor(.002,.012,.009,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);gl.enable(gl.CULL_FACE);gl.cullFace(gl.BACK);gl.useProgram(program);
    var stride=24;gl.bindBuffer(gl.ARRAY_BUFFER,vertexBuffer);gl.enableVertexAttribArray(posLoc);gl.vertexAttribPointer(posLoc,3,gl.FLOAT,false,12,0);
    // Repack attributes into an interleaved stream for the shader.
    var body=byId[activeId],rows=80,cols=160,positions=[],colors=[],seed=body.id.split('').reduce(function(n,c){return n+c.charCodeAt(0);},0),base=[.25,.55,.38];try{var hx=body.color.slice(1);base=[parseInt(hx.slice(0,2),16)/255,parseInt(hx.slice(2,4),16)/255,parseInt(hx.slice(4,6),16)/255;}catch(e){}
    // Buffers are stored as positions followed by colors; use separate attribute offsets.
    var vertexCount=(rows+1)*(cols+1);gl.vertexAttribPointer(posLoc,3,gl.FLOAT,false,0,0);
    gl.enableVertexAttribArray(colLoc);gl.vertexAttribPointer(colLoc,3,gl.FLOAT,false,0,vertexCount*3*4);
    gl.uniformMatrix4fv(matrixLoc,false,matrix());gl.uniform3f(lightLoc,-.45,.7,1);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,indexBuffer);gl.drawElements(gl.TRIANGLES,indexCount,gl.UNSIGNED_SHORT,0);
    angle+=Math.min(.04,((now-last)||16)/1000)*.12;last=now;raf=window.requestAnimationFrame(draw);
  }
  select.addEventListener('change',function(){setBody(select.value);});
  window.addEventListener('vigil:cosmic-body-selected',function(e){if(e.detail&&e.detail.id)setBody(e.detail.id);});
  atlas.addEventListener('click',function(e){
    if(!window.vigilCosmicBodyScreenPoints)return;
    var rect=atlas.getBoundingClientRect(),x=(e.clientX-rect.left)*atlas.width/rect.width,y=(e.clientY-rect.top)*atlas.height/rect.height;
    var nearest=null,distance=Infinity;
    Object.keys(window.vigilCosmicBodyScreenPoints).forEach(function(id){var p=window.vigilCosmicBodyScreenPoints[id],d=Math.hypot(p[0]-x,p[1]-y);if(d<distance){distance=d;nearest=id;}});
    if(nearest&&distance<26){var focus=document.getElementById('vigil-cosmic-focus');if(focus){focus.value=nearest;focus.dispatchEvent(new Event('change',{bubbles:true}));}}
  });
  setBody('nirn');draw(0);
  window.vigilSelectCelestialBody=function(id){if(!byId[id])return false;setBody(id);return true;};
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();