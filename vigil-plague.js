/* VIGIL / PLAGUE — nanoscale world + instrument-limited observation model.
 * Fictional hardware simulation. Instrument limits are simplified reference assumptions,
 * not certified specifications or proof of real-world nanobot feasibility.
 */
(function () {
  'use strict';
  if (window.__vigilPlagueBooted) return;
  window.__vigilPlagueBooted = true;

  var root = document.getElementById('plague-station');
  if (!root) return;

  var css = document.createElement('style');
  css.textContent = `
    #plague-station{--pg:#29f5b2;--pd:#59bda3;--pb:#03120e;color:#6df6db}
    #plague-station .plague-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
    #plague-station .plague-card{border:1px solid #0b9b78;background:#03120e;padding:12px;min-width:0}
    #plague-station h3{color:#29f5b2;margin:3px 0 9px;font-size:13px}
    #plague-station label{display:grid;gap:5px;color:#59bda3;font-size:11px;margin:8px 0}
    #plague-station select,#plague-station input{width:100%;min-height:36px;background:#010604;color:#6df6db;border:1px solid #168b70;padding:7px;font:inherit}
    #plague-station button{background:#06251b;color:#29f5b2;border:1px solid #168b70;padding:9px 12px;min-height:38px;font:inherit;cursor:pointer}
    #plague-station button:hover{background:#0a3a2a;border-color:#29f5b2}
    #plague-station .plague-readout{background:#010604;border:1px solid #12664f;padding:10px;white-space:pre-wrap;line-height:1.55;overflow-wrap:anywhere}
    #plague-station .plague-status{font-weight:bold;color:#29f5b2}
    #plague-station canvas{display:block;width:100%;height:300px;background:radial-gradient(ellipse,#06271d,#010604 72%);border:1px solid #12664f}
    #plague-station .plague-small{font-size:11px;color:#59bda3;line-height:1.5}
    #plague-station .plague-metric{font-size:19px;color:#29f5b2}
    #plague-station .plague-tabs{display:flex;gap:5px;flex-wrap:wrap;margin:10px 0}
    #plague-station .plague-tabs button[aria-pressed="true"]{background:#0a3a2a;border-color:#29f5b2}
    @media(max-width:760px){#plague-station .plague-grid{grid-template-columns:1fr}#plague-station canvas{height:250px}}
  `;
  document.head.appendChild(css);

  root.innerHTML = `
    <h2>PLAGUE // NANOSCALE RESEARCH &amp; OBSERVATION</h2>
    <div class="content">
      <div class="rd-banner"><span>PROJECT FILE: P-16 / RECOVERED NANOTECHNOLOGY</span><b>PLAGUE RESEARCH STATION</b><span>SIMULATION: ACTIVE</span></div>
      <p>Recovered Daedalus material once mistaken for mold-like growth is being modelled as a nanotechnological system. The bots exist at their simulated physical scale whether or not an instrument can observe them. The world model is ground truth; every instrument receives only the evidence its modeled capabilities permit.</p>
      <div class="plague-tabs" role="group" aria-label="PLAGUE research views">
        <button type="button" data-plague-view="world" aria-pressed="true">01 / NANO WORLD</button>
        <button type="button" data-plague-view="instrument" aria-pressed="false">02 / INSTRUMENT BAY</button>
        <button type="button" data-plague-view="evidence" aria-pressed="false">03 / OBSERVATION RECORD</button>
      </div>
      <section data-plague-page="world">
        <div class="plague-grid">
          <div class="plague-card">
            <h3>LIVE NANOSCALE ASSEMBLY // WEBGL VIEW</h3>
            <canvas id="plague-webgl" aria-label="Interactive nanoscale nanobot assembly. Drag to rotate; use wheel or magnification control to zoom."></canvas>
            <label>DISPLAY MAGNIFICATION <input id="plague-zoom" type="range" min="1" max="1000000" value="100000" step="1"><span id="plague-zoom-label">100,000× (view transform only)</span></label>
            <p class="plague-small">Magnification changes only the view. It never changes bot dimensions, distances, mass, speed, or physical interactions. Drag to rotate; mouse wheel to zoom.</p>
          </div>
          <div class="plague-card">
            <h3>CANONICAL PHYSICAL MODEL</h3>
            <div class="plague-readout" id="plague-physical-readout"></div>
            <h3>ENTITY REGISTER</h3>
            <div class="plague-readout" id="plague-entity-register"></div>
          </div>
        </div>
      </section>
      <section data-plague-page="instrument" hidden>
        <div class="plague-grid">
          <div class="plague-card">
            <h3>SELECT OBSERVATION INSTRUMENT</h3>
            <label>INSTRUMENT
              <select id="plague-instrument">
                <option value="camera">Conventional camera / visible light</option>
                <option value="optical">Optical microscope</option>
                <option value="afm">Atomic force microscope (AFM)</option>
                <option value="sem">Scanning electron microscope (SEM)</option>
                <option value="tem">Transmission electron microscope (TEM)</option>
                <option value="field">Specialized swarm-field detector (fictional)</option>
              </select>
            </label>
            <label>SPECIMEN PREPARATION
              <select id="plague-prep"><option value="none">Unprepared / in-situ</option><option value="prepared">Prepared microscopy specimen</option></select>
            </label>
            <label>ACCESS / GEOMETRY
              <select id="plague-access"><option value="bulk">Bulk / enclosed assembly</option><option value="surface">Accessible exposed surface</option></select>
            </label>
            <label>INSTRUMENT CONDITION <input id="plague-condition" type="range" min="10" max="100" value="100" step="5"><span id="plague-condition-label">100%</span></label>
            <button type="button" id="plague-run-scan">RUN INSTRUMENT OBSERVATION</button>
          </div>
          <div class="plague-card">
            <h3>INSTRUMENT LIMITS / MODEL ASSUMPTIONS</h3>
            <div class="plague-readout" id="plague-instrument-spec"></div>
            <p class="plague-small">Reference values are intentionally simplified. Real performance depends on wavelength, numerical aperture, detector, working distance, vacuum, sample preparation, substrate, environment, noise, and instrument configuration. SEM/TEM generally require specimen preparation and vacuum; they are not universal live, in-situ detectors. AFM requires an accessible surface and probe interaction.</p>
          </div>
        </div>
      </section>
      <section data-plague-page="evidence" hidden>
        <div class="plague-card">
          <h3>OBSERVATION RECORD // INSTRUMENT OUTPUT ONLY</h3>
          <div class="plague-readout" id="plague-observation">NO SCAN RUN // SELECT AN INSTRUMENT IN THE INSTRUMENT BAY</div>
          <p class="plague-small">Detection, localization, classification, and resolving individual bots are separate outcomes. The instrument never receives hidden entity labels or exact ground-truth coordinates. Uncertainty and false-positive risk are reported separately.</p>
        </div>
      </section>
      <div class="plague-grid" style="margin-top:10px">
        <div class="plague-card"><h3>SIMULATION INTEGRITY</h3><div class="plague-readout">WORLD STATE ≠ SENSOR OUTPUT<br>TRUE SCALE: NANOMETERS (nm)<br>RENDER SCALE: VIEW-ONLY<br>HIDDEN TRUTH: NOT EXPOSED TO SENSOR ADAPTERS</div></div>
        <div class="plague-card"><h3>MODEL VALIDITY</h3><div class="plague-readout">FICTIONAL NANOBOT DESIGN / SIMULATED PHYSICS<br>Instrument limits: simplified reference model<br>Not validated engineering data; not a claim that present-day nanobots can perform these tasks.</div></div>
      </div>
    </div>`;

  var nmBots = [
    {id:'PB-001',x:-130,y:0,z:0,diameter:80,feature:18,ax:-130,ay:0,az:0,vx:0,vy:5,vz:0,phase:0.2,heading:0,tilt:0},
    {id:'PB-002',x:0,y:0,z:0,diameter:80,feature:18,ax:0,ay:0,az:0,vx:4,vy:0,vz:2,phase:1.4,heading:0,tilt:0},
    {id:'PB-003',x:130,y:0,z:0,diameter:80,feature:18,ax:130,ay:0,az:0,vx:0,vy:-4,vz:1,phase:2.6,heading:0,tilt:0},
    {id:'PB-004',x:0,y:120,z:0,diameter:80,feature:18,ax:0,ay:120,az:0,vx:-3,vy:0,vz:-2,phase:3.8,heading:0,tilt:0},
    {id:'PB-005',x:0,y:-120,z:0,diameter:80,feature:18,ax:0,ay:-120,az:0,vx:2,vy:1,vz:3,phase:5.0,heading:0,tilt:0}
  ];
  var instruments = {
    camera:{name:'Conventional camera / visible light',resolution:100000,detectMin:100000,mode:'optical',prep:false,surface:false,notes:'Typical imaging systems cannot resolve nanometer-scale individual bots. No individual detection expected.'},
    optical:{name:'Optical microscope',resolution:200,detectMin:200,mode:'optical',prep:false,surface:false,notes:'Approximate diffraction-limited reference resolution: about 200 nm for a conventional visible-light setup. A sub-resolution swarm may appear only as a blurred aggregate if signal is sufficient.'},
    afm:{name:'Atomic force microscope (AFM)',resolution:10,detectMin:10,mode:'surface',prep:false,surface:true,notes:'Simplified lateral-resolution assumption: 10 nm. Requires an accessible surface and probe interaction; it does not freely image an enclosed bulk volume.'},
    sem:{name:'Scanning electron microscope (SEM)',resolution:5,detectMin:5,mode:'electron',prep:true,surface:false,notes:'Simplified 5 nm reference. Requires appropriate specimen preparation and vacuum; surface/topography-sensitive.'},
    tem:{name:'Transmission electron microscope (TEM)',resolution:0.2,detectMin:0.2,mode:'electron',prep:true,surface:false,notes:'Simplified 0.2 nm high-end reference. Requires an electron-transparent prepared specimen and vacuum; not live in-situ observation.'},
    field:{name:'Specialized swarm-field detector (fictional)',resolution:null,detectMin:null,mode:'field',prep:false,surface:false,notes:'Fictional sensor detects only a modeled aggregate field signature above its noise floor. It cannot resolve or identify individual bots.'}
  };
  var scanRecord = null;
  var state = {yaw:0.35,pitch:0.25,zoom:2.4,drag:false,lastX:0,lastY:0};
  var canvas = document.getElementById('plague-webgl');
  var gl = canvas.getContext('webgl', {antialias:true,alpha:false});
  var program = null, buffers = [];
  function shader(type, source){var sh=gl.createShader(type);gl.shaderSource(sh,source);gl.compileShader(sh);if(!gl.getShaderParameter(sh,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(sh));return sh;}
  function initGL(){
    if(!gl){canvas.insertAdjacentHTML('afterend','<p class="plague-small">WebGL is unavailable in this browser. Physical model and instrument calculations remain active.</p>');return;}
    var vs=shader(gl.VERTEX_SHADER,'attribute vec3 p;uniform mat4 m;void main(){gl_Position=m*vec4(p,1.0);gl_PointSize=5.0;}');
    var fs=shader(gl.FRAGMENT_SHADER,'precision mediump float;uniform vec4 c;void main(){gl_FragColor=c;}');
    program=gl.createProgram();gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);
    if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);gl.enable(gl.DEPTH_TEST);gl.clearColor(.004,.018,.012,1);
    var geom=[];
    function line(a,b){geom.push(a[0],a[1],a[2],b[0],b[1],b[2]);}
    // Central engineered chassis, ring and four articulated tool arms.
    var r=0.45,n=24;
    for(var i=0;i<n;i++){var a=i*2*Math.PI/n,b=(i+1)*2*Math.PI/n;line([Math.cos(a)*r,Math.sin(a)*r,0],[Math.cos(b)*r,Math.sin(b)*r,0]);}
    line([-.22,0,0],[.22,0,0]);line([0,-.22,0],[0,.22,0]);line([0,0,-.25],[0,0,.25]);
    [[1,0,0],[-1,0,0],[0,1,0],[0,-1,0]].forEach(function(v){var p=[v[0]*.42,v[1]*.42,0],q=[v[0]*.85,v[1]*.85,.08];line(p,q);line(q,[q[0]*1.14,q[1]*1.14,q[2]]);line([q[0]-.05,q[1],q[2]],[q[0]+.05,q[1],q[2]]);});
    var data=new Float32Array(geom),buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,data,gl.STATIC_DRAW);
    var loc=gl.getAttribLocation(program,'p');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,0,0);buffers.push({buf:buf,count:data.length/3});
    drawGL();
  }
  function mat(bot){
    var yaw=state.yaw+(bot?bot.heading:0),pitch=state.pitch+(bot?bot.tilt:0);
    var cy=Math.cos(yaw),sy=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch),z=state.zoom;
    return new Float32Array([cy/z,sy*sp/z,sy*cp/z,0,0,cp/z,-sp/z,0,-sy/z,cy*sp/z,cy*cp/z,0,0,0,0,1]);
  }
  function drawGL(){if(!gl||!program)return;gl.viewport(0,0,canvas.width,canvas.height);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(program);var ml=gl.getUniformLocation(program,'m'),cl=gl.getUniformLocation(program,'c');gl.uniform4f(cl,.16,1,.68,1);nmBots.forEach(function(bot){var m=mat(bot);m[12]=bot.x/260/state.zoom;m[13]=bot.y/260/state.zoom;m[14]=bot.z/260/state.zoom;gl.uniformMatrix4fv(ml,false,m);gl.drawArrays(gl.LINES,0,buffers[0].count);});}
  // Simplified fictional nanoscale dynamics: damped inertia, spring-guided
  // motion, pairwise collision avoidance, and a bounded operating volume.
  var simClock=0,lastFrame=0,lastTelemetry=0;
  function updateSimulation(dt){
    simClock+=dt;
    nmBots.forEach(function(b){
      var phase=simClock*.72+b.phase;
      var tx=b.ax+Math.cos(phase)*34,ty=b.ay+Math.sin(phase*1.17)*30,tz=b.az+Math.sin(phase*.83)*24;
      var fx=(tx-b.x)*.16-b.vx*.72,fy=(ty-b.y)*.16-b.vy*.72,fz=(tz-b.z)*.16-b.vz*.72;
      nmBots.forEach(function(o){
        if(o===b)return;
        var dx=b.x-o.x,dy=b.y-o.y,dz=b.z-o.z,d2=dx*dx+dy*dy+dz*dz;
        if(d2>0&&d2<10000){var d=Math.sqrt(d2),push=(100-d)*.10/d;fx+=dx*push;fy+=dy*push;fz+=dz*push;}
      });
      b.vx+=fx*dt;b.vy+=fy*dt;b.vz+=fz*dt;
      var speed=Math.sqrt(b.vx*b.vx+b.vy*b.vy+b.vz*b.vz);
      if(speed>28){var k=28/speed;b.vx*=k;b.vy*=k;b.vz*=k;}
      b.x+=b.vx*dt;b.y+=b.vy*dt;b.z+=b.vz*dt;
      [['x','vx'],['y','vy'],['z','vz']].forEach(function(pair){
        var p=pair[0],v=pair[1];
        if(b[p]>225){b[p]=225;b[v]=-Math.abs(b[v])*.65;}
        if(b[p]<-225){b[p]=-225;b[v]=Math.abs(b[v])*.65;}
      });
      if(Math.abs(b.vx)+Math.abs(b.vy)+Math.abs(b.vz)>.01){
        b.heading=Math.atan2(b.vy,b.vx);
        b.tilt=Math.atan2(b.vz,Math.sqrt(b.vx*b.vx+b.vy*b.vy));
      }
    });
  }
  function animatePlague(now){
    if(!gl||!program)return;
    var dt=lastFrame?Math.min(.04,(now-lastFrame)/1000):.016;
    lastFrame=now;
    updateSimulation(dt);
    drawGL();
    if(now-lastTelemetry>600){
      var register=document.getElementById('plague-entity-register');
      if(register)register.textContent=nmBots.map(function(b){
        var speed=Math.sqrt(b.vx*b.vx+b.vy*b.vy+b.vz*b.vz);
        return b.id+' // '+b.diameter+' nm envelope // position ('+b.x.toFixed(1)+','+b.y.toFixed(1)+','+b.z.toFixed(1)+') nm // speed '+speed.toFixed(1)+' nm/s';
      }).join('\\n');
      lastTelemetry=now;
    }
    window.requestAnimationFrame(animatePlague);
  }
  function resizeGL(){var d=window.devicePixelRatio||1;canvas.width=Math.max(1,Math.floor(canvas.clientWidth*d));canvas.height=Math.max(1,Math.floor(canvas.clientHeight*d));drawGL();}
  canvas.addEventListener('pointerdown',function(e){state.drag=true;state.lastX=e.clientX;state.lastY=e.clientY;canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener('pointermove',function(e){if(!state.drag)return;state.yaw+=(e.clientX-state.lastX)*.008;state.pitch=Math.max(-1.3,Math.min(1.3,state.pitch+(e.clientY-state.lastY)*.008));state.lastX=e.clientX;state.lastY=e.clientY;drawGL();});
  ['pointerup','pointercancel','lostpointercapture'].forEach(function(ev){canvas.addEventListener(ev,function(){state.drag=false;});});
  canvas.addEventListener('wheel',function(e){e.preventDefault();state.zoom=Math.max(.7,Math.min(8,state.zoom+(e.deltaY>0?.15:-.15)));drawGL();},{passive:false});
  document.getElementById('plague-zoom').addEventListener('input',function(e){var v=Number(e.target.value);document.getElementById('plague-zoom-label').textContent=v.toLocaleString()+'× (view transform only)';state.zoom=Math.max(.7,Math.min(8,8-Math.log10(v)*.65));drawGL();});
  window.addEventListener('resize',resizeGL);

  function renderPhysical(){
    document.getElementById('plague-physical-readout').textContent =
      'BOT ENVELOPE: 80 nm diameter\nMINIMUM MODELLED FEATURE: 18 nm\nENTITY COUNT: '+nmBots.length+' individually tracked bots\nBOT CENTRE SPACING: 120–130 nm\nCOORDINATE FRAME: local nanoscale SI frame\nPOSITION UNIT: nm (1 nm = 10⁻⁹ m)\nDISPLAY SCALE: independent of physical scale\n\nThese are fictional design parameters for this simulation, not measured hardware.';
    document.getElementById('plague-entity-register').textContent = nmBots.map(function(b){return b.id+' // '+b.diameter+' nm envelope // feature '+b.feature+' nm // position ('+b.x+','+b.y+','+b.z+') nm';}).join('\n');
  }
  function specs(){var inst=instruments[document.getElementById('plague-instrument').value];document.getElementById('plague-instrument-spec').textContent=inst.name+'\n'+(inst.resolution===null?'RESOLUTION: NOT APPLICABLE (aggregate signal only)':'REFERENCE RESOLUTION: '+inst.resolution+' nm')+'\nPREPARATION REQUIRED: '+(inst.prep?'YES':'not intrinsically required')+'\nSURFACE ACCESS REQUIRED: '+(inst.surface?'YES':'not for this simplified model')+'\n\n'+inst.notes;}
  document.getElementById('plague-instrument').addEventListener('change',specs);
  document.getElementById('plague-prep').addEventListener('change',specs);
  document.getElementById('plague-access').addEventListener('change',specs);
  document.getElementById('plague-condition').addEventListener('input',function(e){document.getElementById('plague-condition-label').textContent=e.target.value+'%';});
  function scan(){
    var key=document.getElementById('plague-instrument').value,inst=instruments[key],prep=document.getElementById('plague-prep').value==='prepared',surface=document.getElementById('plague-access').value==='surface',condition=Number(document.getElementById('plague-condition').value)/100;
    var blocked=(inst.prep&&!prep)||(inst.surface&&!surface);
    var botSize=80,feature=18,clusterSpan=520;
    var snr=key==='field'?condition*1.4:condition*(key==='optical'?1.05:.9);
    var detected=false,localized=false,classified=false,individual=false,reason='';
    if(blocked){reason=inst.prep&&!prep?'Specimen preparation and vacuum conditions are not satisfied.':'No accessible surface for probe interaction.';}
    else if(key==='field'){detected=snr>=1;localized=snr>=1.25;classified=false;individual=false;reason='Aggregate field signature only; individual bot resolution is unavailable.';}
    else {
      detected=clusterSpan>=inst.detectMin&&snr>=.55;
      individual=botSize>=inst.resolution&&feature>=inst.resolution&&snr>=.65;
      localized=detected&&snr>=.75&&(inst.resolution===null||clusterSpan>=inst.resolution*2);
      classified=individual&&feature>=inst.resolution*3&&snr>=.8;
      reason=detected?'Observed signal is consistent with a nanoscale aggregate.':'Signal below modeled detection threshold or feature below instrument capability.';
    }
    var uncertainty=detected?Math.round((1-condition)*35+(individual?5:25)):'—';
    scanRecord={instrument:inst.name,detected:detected,localized:localized,classified:classified,individual:individual,reason:reason,uncertainty:uncertainty,prep:prep,surface:surface,condition:condition};
    var out='INSTRUMENT: '+inst.name+'\nDETECTION: '+(detected?'AGGREGATE SIGNATURE DETECTED':'NOT DETECTED')+'\nLOCALIZATION: '+(localized?'COARSE LOCATION ESTIMATE':'NOT LOCALIZED')+'\nCLASSIFICATION: '+(classified?'FEATURES CLASSIFIED':'NOT CLASSIFIED')+'\nINDIVIDUAL BOT RESOLUTION: '+(individual?'RESOLVED':'NOT RESOLVED')+'\nUNCERTAINTY: '+(detected?uncertainty+'% (simplified model)':'not estimable')+'\n\nOBSERVED EVIDENCE: '+(detected?(individual?'Resolved nanoscale features':'Blurred/aggregate response; no individual bot identities'):'No qualifying signal returned')+'\nLIMITATION: '+reason+'\n\nGROUND TRUTH IS WITHHELD FROM THIS OUTPUT. This is an instrument-limited simulated observation, not direct access to the entity register.';
    document.getElementById('plague-observation').textContent=out;
    document.getElementById('plague-physical-readout').textContent+='\n\nLAST SCAN: '+inst.name+' // '+(detected?'AGGREGATE DETECTED':'NO DETECTION')+' // INDIVIDUALS '+(individual?'RESOLVED':'UNRESOLVED');
  }
  document.getElementById('plague-run-scan').addEventListener('click',scan);
  document.querySelectorAll('[data-plague-view]').forEach(function(btn){btn.addEventListener('click',function(){var v=btn.getAttribute('data-plague-view');document.querySelectorAll('[data-plague-view]').forEach(function(b){b.setAttribute('aria-pressed',String(b===btn));});document.querySelectorAll('[data-plague-page]').forEach(function(p){p.hidden=p.getAttribute('data-plague-page')!==v;});if(v==='instrument')specs();if(v==='world')resizeGL();});});
  initGL();renderPhysical();specs();resizeGL();if(gl&&program)window.requestAnimationFrame(animatePlague);
  window.VIGIL_PLAGUE = {getPhysicalEntities:function(){return nmBots.map(function(b){return Object.assign({},b);});},getLastObservation:function(){return scanRecord?Object.assign({},scanRecord):null;},getInstrumentProfiles:function(){return JSON.parse(JSON.stringify(instruments));}};
})();
