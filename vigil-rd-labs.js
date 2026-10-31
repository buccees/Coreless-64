(function(){
'use strict';
function boot(){
 var host=document.getElementById('rd-active-labs');
 if(!host||host.dataset.ready)return;host.dataset.ready='1';
 var esc=function(s){return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});};
 host.innerHTML=
 '<div class="rd-lab-heading"><div><span class="rd-lab-kicker">CORELESS-64 // VIGIL RESEARCH DIVISION</span><h3>ACTIVE ENGINEERING LABORATORIES</h3><p>Interactive instruments with live calculations. Change an input and the readout recalculates immediately. Simulated specimen and sensor observations are labeled; engineering models use stated physical equations.</p></div><div class="rd-lab-live"><i></i> LOCAL SIMULATION / LIVE CALCULATION</div></div>'+
 '<div class="rd-lab-tabs" role="tablist" aria-label="Research laboratory workspaces">'+
 '<button type="button" class="active" data-lab="optics" role="tab" aria-selected="true">01 OPTICS</button>'+
 '<button type="button" data-lab="specimen" role="tab" aria-selected="false">02 SPECIMEN</button>'+
 '<button type="button" data-lab="materials" role="tab" aria-selected="false">03 MATERIALS</button>'+
 '<button type="button" data-lab="fusion" role="tab" aria-selected="false">04 SENSOR FUSION</button></div>'+
 '<section class="rd-lab-panel active" data-panel="optics"><div class="rd-lab-panel-head"><div><h4>PHOTONICS / OPTICAL BENCH</h4><p>Ray geometry, refraction, total internal reflection, absorption and photodetection.</p></div><span class="rd-lab-status">OPTICAL PATH SOLVER</span></div>'+
 '<div class="rd-lab-grid"><div class="rd-lab-controls">'+
 '<label>LASER WAVELENGTH<select id="rd-opt-wave"><option value="405">405 nm // VIOLET</option><option value="450">450 nm // BLUE</option><option value="532" selected>532 nm // GREEN</option><option value="650">650 nm // RED</option><option value="850">850 nm // NEAR IR</option><option value="1064">1064 nm // IR</option></select></label>'+
 '<label>INPUT POWER <output id="rd-opt-power-v">1.00 mW</output><input id="rd-opt-power" type="range" min="0.05" max="20" step="0.05" value="1"></label>'+
 '<label>INCIDENCE ANGLE <output id="rd-opt-inc-v">35°</output><input id="rd-opt-inc" type="range" min="0" max="89" step="1" value="35"></label>'+
 '<label>MIRROR NORMAL ANGLE <output id="rd-opt-mirror-v">20°</output><input id="rd-opt-mirror" type="range" min="-90" max="90" step="1" value="20"></label>'+
 '<label>OPTICAL MEDIUM<select id="rd-opt-medium"><option value="air" data-n="1.000" data-a="0.0001">AIR // n 1.000</option><option value="water" data-n="1.333" data-a="0.004">WATER // n 1.333</option><option value="glass" data-n="1.500" data-a="0.015">CROWN GLASS // n 1.500</option><option value="acrylic" data-n="1.490" data-a="0.025">ACRYLIC // n 1.490</option></select></label>'+
 '<label>PATH THROUGH MEDIUM <output id="rd-opt-dist-v">0.50 m</output><input id="rd-opt-dist" type="range" min="0" max="5" step="0.05" value="0.5"></label>'+
 '<label>DETECTOR RESPONSIVITY <output id="rd-opt-resp-v">0.30 A/W</output><input id="rd-opt-resp" type="range" min="0.05" max="1.2" step="0.01" value="0.3"></label></div>'+
 '<div class="rd-lab-visual"><svg id="rd-opt-svg" viewBox="0 0 520 250" role="img" aria-label="Live optical path diagram"><defs><marker id="rd-opt-arrow" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0 0L6 3L0 6" fill="#8cf5b7"/></marker></defs><path d="M20 210H500M20 35V210" stroke="#285b43" fill="none"/><path id="rd-opt-ray-in" d="M40 185L250 105" stroke="#54e89b" stroke-width="3" marker-end="url(#rd-opt-arrow)"/><path id="rd-opt-ray-out" d="M250 105L455 25" stroke="#54e89b" stroke-width="3" stroke-dasharray="7 4" marker-end="url(#rd-opt-arrow)"/><path d="M235 120L265 90" stroke="#e9e2ba" stroke-width="6"/><circle cx="455" cy="25" r="9" fill="#8cf5b7" stroke="#e7fff0" stroke-width="2"/><text x="25" y="228" fill="#82aa94" font-size="10">EMITTER</text><text x="272" y="88" fill="#d8e9dc" font-size="10">MIRROR</text><text x="410" y="15" fill="#d8e9dc" font-size="10">DETECTOR</text><text id="rd-opt-angle-label" x="275" y="145" fill="#9dcbb1" font-size="11">REFLECTION</text></svg><div class="rd-lab-readout" id="rd-opt-readout" aria-live="polite"></div></div></div>'+
 '<p class="rd-lab-note">MODEL: vector reflection, Snell’s law, Beer–Lambert attenuation and detector responsivity. Medium coefficients are illustrative selectable values; real optical hardware requires wavelength-specific calibration and measured component data.</p></section>'+
 '<section class="rd-lab-panel" data-panel="specimen" hidden><div class="rd-lab-panel-head"><div><h4>XENOBIOLOGY / DIGITAL SPECIMEN WORKSTATION</h4><p>Inspect a synthetic specimen, isolate tissue layers and record measurable morphology.</p></div><span class="rd-lab-status">SYNTHETIC SPECIMEN DATA</span></div>'+
 '<div class="rd-lab-grid"><div class="rd-lab-controls"><label>SPECIMEN<select id="rd-specimen"><option value="xn01">XN-01 // CRANIAL COMPLEX</option><option value="xn02">XN-02 // LIMB SEGMENT</option><option value="bio03">BIO-03 // COMPARATIVE TISSUE</option></select></label><label>SECTION<select id="rd-spec-layer"><option value="all">FULL CROSS-SECTION</option><option value="outer">OUTER CUTICLE</option><option value="vascular">VASCULAR / FLUID CHANNEL</option><option value="neural">NEURAL / SIGNAL TISSUE</option><option value="support">STRUCTURAL SUPPORT</option></select></label><label>MICROSCOPE MAGNIFICATION <output id="rd-mag-v">40×</output><input id="rd-mag" type="range" min="10" max="400" step="10" value="40"></label><label>SCAN MODE<select id="rd-spec-mode"><option value="bright">BRIGHTFIELD</option><option value="fluorescence">FLUORESCENCE</option><option value="density">DENSITY MAP</option></select></label><button type="button" id="rd-spec-scan">ACQUIRE SPECIMEN SCAN</button></div>'+
 '<div class="rd-lab-visual"><svg id="rd-spec-svg" viewBox="0 0 520 250" role="img" aria-label="Schematic specimen cross section"><ellipse cx="260" cy="125" rx="205" ry="95" fill="#244c3b" stroke="#9bd9ad" stroke-width="5"/><ellipse cx="260" cy="125" rx="185" ry="78" fill="#47765a" stroke="#b5d7a9" stroke-width="2"/><path d="M90 130Q170 65 250 130T430 120" fill="none" stroke="#e1bd79" stroke-width="10"/><path d="M105 145Q180 190 250 140T415 145" fill="none" stroke="#e58d79" stroke-width="7"/><g fill="#91d9ed" stroke="#d9f7ff" stroke-width="2"><circle cx="205" cy="110" r="11"/><circle cx="245" cy="145" r="8"/><circle cx="300" cy="105" r="12"/><circle cx="340" cy="145" r="9"/></g><path d="M160 125Q260 40 360 125Q260 210 160 125Z" fill="none" stroke="#a9a0e8" stroke-width="4" stroke-dasharray="5 4"/></svg><div class="rd-lab-readout" id="rd-spec-readout" aria-live="polite"></div></div></div><p class="rd-lab-note">This is an editable research model, not a claim about a real organism. Measurements are synthetic training values. Scan mode and selected tissue change the displayed observations; this is not medical or biological diagnostic software.</p></section>'+
 '<section class="rd-lab-panel" data-panel="materials" hidden><div class="rd-lab-panel-head"><div><h4>MATERIALS SCIENCE / MECHANICAL &amp; ELECTRICAL TEST</h4><p>Apply load to a specimen and calculate stress, strain, elastic extension and electrical resistance.</p></div><span class="rd-lab-status">CONTINUUM MODEL</span></div>'+
 '<div class="rd-lab-grid"><div class="rd-lab-controls"><label>TEST MATERIAL<select id="rd-mat"><option value="steel">STAINLESS STEEL</option><option value="aluminum">ALUMINUM 6061-T6</option><option value="titanium">TITANIUM ALLOY</option><option value="copper">COPPER</option><option value="carbon">CARBON-FIBER COMPOSITE // AXIAL</option><option value="polymer">ENGINEERING POLYMER</option></select></label><label>APPLIED FORCE <output id="rd-force-v">1,000 N</output><input id="rd-force" type="range" min="0" max="100000" step="100" value="1000"></label><label>CROSS-SECTION AREA <output id="rd-area-v">100 mm²</output><input id="rd-area" type="range" min="1" max="2000" step="1" value="100"></label><label>GAUGE LENGTH <output id="rd-length-v">100 mm</output><input id="rd-length" type="range" min="10" max="500" step="5" value="100"></label><label>CONDUCTOR LENGTH <output id="rd-wire-v">1.00 m</output><input id="rd-wire" type="range" min="0.1" max="10" step="0.1" value="1"></label></div><div class="rd-lab-visual"><div class="rd-material-bar"><div id="rd-material-specimen"></div></div><div class="rd-lab-readout" id="rd-mat-readout" aria-live="polite"></div></div></div><p class="rd-lab-note">Linear elastic Hooke-law model with material reference properties. It does not model yielding, fatigue, anisotropy beyond the listed axial composite approximation, temperature dependence or fracture. Use certified material data for real design.</p></section>'+
 '<section class="rd-lab-panel" data-panel="fusion" hidden><div class="rd-lab-panel-head"><div><h4>SENSOR ENGINEERING / CALIBRATION &amp; FUSION</h4><p>Combine independent range observations using uncertainty-weighted estimation.</p></div><span class="rd-lab-status">WEIGHTED ESTIMATOR</span></div>'+
 '<div class="rd-lab-grid"><div class="rd-lab-controls">'+
 '<label>SONAR RANGE <output id="rd-sonar-v">12.4 m</output><input id="rd-sonar" type="range" min="0" max="100" step="0.1" value="12.4"></label><label>SONAR 1σ UNCERTAINTY <output id="rd-sonar-s-v">0.60 m</output><input id="rd-sonar-s" type="range" min="0.05" max="10" step="0.05" value="0.6"></label>'+
 '<label>OPTICAL RANGE <output id="rd-optical-v">12.1 m</output><input id="rd-optical" type="range" min="0" max="100" step="0.1" value="12.1"></label><label>OPTICAL 1σ UNCERTAINTY <output id="rd-optical-s-v">0.20 m</output><input id="rd-optical-s" type="range" min="0.05" max="10" step="0.05" value="0.2"></label>'+
 '<label>ACOUSTIC RANGE <output id="rd-acoustic-v">12.8 m</output><input id="rd-acoustic" type="range" min="0" max="100" step="0.1" value="12.8"></label><label>ACOUSTIC 1σ UNCERTAINTY <output id="rd-acoustic-s-v">1.10 m</output><input id="rd-acoustic-s" type="range" min="0.05" max="10" step="0.05" value="1.1"></label><button type="button" id="rd-fusion-reset">RESTORE TEST OBSERVATIONS</button></div><div class="rd-lab-visual"><div class="rd-fusion-bars" id="rd-fusion-bars"></div><div class="rd-lab-readout" id="rd-fusion-readout" aria-live="polite"></div></div></div><p class="rd-lab-note">Assumes independent, unbiased Gaussian range errors. Estimate = Σ(xᵢ/σᵢ²) / Σ(1/σᵢ²); fused variance = 1 / Σ(1/σᵢ²). Real sensor fusion must account for correlated errors, calibration bias, timing, coordinate frames and outlier rejection.</p></section>';
 var tabs=Array.from(host.querySelectorAll('[data-lab]')),panels=Array.from(host.querySelectorAll('[data-panel]'));
 tabs.forEach(function(t){t.addEventListener('click',function(){tabs.forEach(function(b){var on=b===t;b.classList.toggle('active',on);b.setAttribute('aria-selected',on?'true':'false');});panels.forEach(function(p){var on=p.dataset.panel===t.dataset.lab;p.hidden=!on;p.classList.toggle('active',on);});});});
 function el(id){return host.querySelector('#'+id);}
 function val(id){return Number(el(id).value);}
 function fmt(n,d){return Number.isFinite(n)?n.toFixed(d):'—';}
 function label(id,text){el(id).textContent=text;}
 function readout(id,rows){el(id).innerHTML=rows.map(function(r){return '<div><span>'+esc(r[0])+'</span><b>'+esc(r[1])+'</b></div>';}).join('');}
 function optical(){
  var wave=val('rd-opt-wave'),power=val('rd-opt-power'),inc=val('rd-opt-inc'),normal=val('rd-opt-mirror'),dist=val('rd-opt-dist'),resp=val('rd-opt-resp'),med=el('rd-opt-medium').selectedOptions[0],n=Number(med.dataset.n),alpha=Number(med.dataset.a);
  label('rd-opt-power-v',fmt(power,2)+' mW');label('rd-opt-inc-v',inc+'°');label('rd-opt-mirror-v',normal+'°');label('rd-opt-dist-v',fmt(dist,2)+' m');
  var reflected=(2*normal-inc+3600)%360,theta=inc*Math.PI/180,trans=Math.asin(Math.min(1,Math.sin(theta)/n))*180/Math.PI,critical=Math.asin(1/n)*180/Math.PI;
  var fresnel=((1-n)/(1+n))**2,mirrorOut=power*.96,transmit=mirrorOut*Math.exp(-alpha*dist),current=transmit/1000*resp,photon=6.62607015e-34*299792458/(wave*1e-9),flux=transmit/1000/photon;
  var tir=inc>critical&&n>1.0001;
  var x1=40,y1=185,xm=250,ym=105,a=reflected*Math.PI/180,x2=xm+185*Math.cos(a),y2=ym-185*Math.sin(a);
  el('rd-opt-ray-in').setAttribute('d','M'+x1+' '+y1+'L'+xm+' '+ym);el('rd-opt-ray-out').setAttribute('d','M'+xm+' '+ym+'L'+Math.max(300,Math.min(490,x2))+' '+Math.max(20,Math.min(210,y2)));
  var color=wave<430?'#c79cff':wave<490?'#69aaff':wave<570?'#54e89b':wave<700?'#ff7777':'#f4b56b';
  ['rd-opt-ray-in','rd-opt-ray-out'].forEach(function(id){el(id).setAttribute('stroke',color);});
  label('rd-opt-angle-label',tir?'TOTAL INTERNAL REFLECTION':'θt '+fmt(trans,1)+'°');
  readout('rd-opt-readout',[['SOURCE',wave+' nm / '+fmt(power,2)+' mW'],['REFLECTED ANGLE',fmt(reflected,1)+'°'],['MEDIUM REFRACTIVE INDEX',fmt(n,3)],['SNELL REFRACTION',tir?'TIR / NO TRANSMITTED RAY':fmt(trans,2)+'°'],['BEAM POWER AT DETECTOR',fmt(transmit,4)+' mW'],['PHOTODETECTOR CURRENT',fmt(current*1e6,2)+' µA'],['PHOTON FLUX',fmt(flux,3)+' photons/s'],['FRESNEL NORMAL-INCIDENCE REFLECTANCE',fmt(fresnel,4)]]);
 }
 function opticalSafe(){try{optical();}catch(e){label('rd-opt-readout','OPTICAL MODEL ERROR // '+e.message);}}

 var specimen={
  xn01:{name:'XN-01 CRANIAL COMPLEX',length:184,width:126,mass:2.84,density:1.04,outer:3.2,vascular:14.6,neural:22.1,support:60.1,notes:{outer:'Layered keratin-like protective plate; synthetic morphology.',vascular:'Branching fluid-channel network; synthetic segmentation.',neural:'High-density signal-bearing tissue region; synthetic morphology.',support:'Load-bearing internal struts; synthetic morphology.'}},
  xn02:{name:'XN-02 LIMB SEGMENT',length:312,width:74,mass:1.92,density:1.11,outer:5.8,vascular:8.2,neural:4.4,support:81.6,notes:{outer:'Thick external cuticle around articulated segment.',vascular:'Longitudinal fluid channels.',neural:'Peripheral nerve bundle distribution.',support:'Dense axial support fibers.'}},
  bio03:{name:'BIO-03 COMPARATIVE TISSUE',length:96,width:88,mass:.64,density:1.02,outer:8.1,vascular:31.4,neural:18.5,support:42,notes:{outer:'Surface epithelial layer.',vascular:'Capillary-like channels.',neural:'Signal-rich cellular region.',support:'Collagen-like structural matrix.'}}
 };
 var layerNames={outer:'OUTER CUTICLE',vascular:'VASCULAR / FLUID CHANNEL',neural:'NEURAL / SIGNAL TISSUE',support:'STRUCTURAL SUPPORT'};
 function specimenDraw(){
  var s=specimen[el('rd-specimen').value],layer=el('rd-spec-layer').value,mag=val('rd-mag'),mode=el('rd-spec-mode').value;
  label('rd-mag-v',mag+'×');
  var shapes=host.querySelectorAll('#rd-spec-svg ellipse,#rd-spec-svg path,#rd-spec-svg circle');
  shapes.forEach(function(n){n.style.opacity=layer==='all'?1:(n.getAttribute('stroke')===(layer==='outer'?'#9bd9ad':layer==='vascular'?'#e58d79':layer==='neural'?'#a9a0e8':'#e1bd79')?1:.12);});
  if(mode==='fluorescence')shapes.forEach(function(n){n.style.filter='drop-shadow(0 0 4px #8cf5b7)';});
  else if(mode==='density')shapes.forEach(function(n){n.style.filter='saturate(1.8) contrast(1.25)';});
  else shapes.forEach(function(n){n.style.filter='none';});
  var tissue=layer==='all'?'ALL SEGMENTED REGIONS':layerNames[layer],area=s.length*s.width/100,volume=area*(s.width*.35)/1000;
  readout('rd-spec-readout',[['SPECIMEN',s.name],['SCAN MODE',mode.toUpperCase()],['SELECTED REGION',tissue],['MAGNIFICATION',mag+'×'],['LENGTH / WIDTH',s.length+' / '+s.width+' mm'],['MASS / BULK DENSITY',fmt(s.mass,2)+' kg / '+fmt(s.density,3)+' g/cm³'],['REGION FRACTION',layer==='all'?'100%':fmt(s[layer],1)+'%'],['SEGMENTED OBSERVATION',layer==='all'?'4 regions detected':s.notes[layer]||'Region selected']]);
 }
 function specimenScan(){specimenDraw();var r=el('rd-spec-readout');r.insertAdjacentHTML('beforeend','<div><span>ACQUISITION</span><b>SCAN COMPLETE // SYNTHETIC DATASET</b></div>');}
 var materials={
  steel:{name:'STAINLESS STEEL',E:193e9,rho:7.9e-7,res:7.2e-7,yield:215e6},
  aluminum:{name:'ALUMINUM 6061-T6',E:68.9e9,rho:2.7e-7,res:3.99e-8,yield:276e6},
  titanium:{name:'TITANIUM ALLOY',E:114e9,rho:4.43e-7,res:1.7e-6,yield:880e6},
  copper:{name:'COPPER',E:117e9,rho:8.96e-7,res:1.68e-8,yield:70e6},
  carbon:{name:'CARBON-FIBER COMPOSITE / AXIAL',E:135e9,rho:1.6e-7,res:1e-5,yield:600e6},
  polymer:{name:'ENGINEERING POLYMER',E:2.4e9,rho:1.18e-6,res:1e12,yield:55e6}
 };
 function materialTest(){
  var m=materials[el('rd-mat').value],F=val('rd-force'),A=val('rd-area')*1e-6,L=val('rd-length')/1000,wire=val('rd-wire'),stress=F/A,strain=stress/m.E,extension=strain*L,R=m.rho*wire/A;
  label('rd-force-v',F.toLocaleString('en-US')+' N');label('rd-area-v',val('rd-area')+' mm²');label('rd-length-v',val('rd-length')+' mm');label('rd-wire-v',fmt(wire,2)+' m');
  el('rd-material-specimen').style.transform='scaleY('+Math.max(.25,1-Math.min(.7,Math.abs(strain)*20))+')';
  readout('rd-mat-readout',[['MATERIAL',m.name],['YOUNG MODULUS',fmt(m.E/1e9,2)+' GPa'],['APPLIED LOAD',F.toLocaleString('en-US')+' N'],['ENGINEERING STRESS',fmt(stress/1e6,3)+' MPa'],['ELASTIC STRAIN',fmt(strain*1e6,2)+' µε'],['ELASTIC EXTENSION',fmt(extension*1000,5)+' mm'],['REFERENCE YIELD STRENGTH',fmt(m.yield/1e6,1)+' MPa'],['YIELD UTILIZATION',fmt(stress/m.yield*100,2)+' %'],['WIRE RESISTANCE',fmt(R,6)+' Ω']]);
 }
 function fusion(){
  var items=[['SONAR',val('rd-sonar'),val('rd-sonar-s')],['OPTICAL',val('rd-optical'),val('rd-optical-s')],['ACOUSTIC',val('rd-acoustic'),val('rd-acoustic-s')]],sumW=0,sum=0;
  items.forEach(function(x){sumW+=1/(x[2]*x[2]);sum+=x[1]/(x[2]*x[2]);label('rd-'+x[0].toLowerCase()+'-v',fmt(x[1],2)+' m');label('rd-'+x[0].toLowerCase()+'-s-v',fmt(x[2],2)+' m');});
  var mean=sum/sumW,sigma=Math.sqrt(1/sumW),min=Math.min.apply(null,items.map(function(x){return x[1];})),max=Math.max.apply(null,items.map(function(x){return x[1];}));
  el('rd-fusion-bars').innerHTML=items.map(function(x){return '<div class="rd-fusion-row"><span>'+x[0]+'</span><div><i style="width:'+Math.max(2,Math.min(100,x[1]))+'%"></i></div><b>'+fmt(x[1],2)+' m</b><small>σ '+fmt(x[2],2)+' m</small></div>';}).join('');
  readout('rd-fusion-readout',[['FUSED RANGE',fmt(mean,3)+' m'],['FUSED 1σ UNCERTAINTY',fmt(sigma,3)+' m'],['95% INTERVAL',fmt(mean-1.96*sigma,3)+' – '+fmt(mean+1.96*sigma,3)+' m'],['INPUT SPREAD',fmt(max-min,3)+' m'],['ESTIMATOR', 'INVERSE-VARIANCE WEIGHTED'],['OBSERVATIONS', '3 / 3 AVAILABLE']]);
 }
 function bind(ids,fn){ids.forEach(function(id){var n=el(id);if(n)n.addEventListener('input',fn),n.addEventListener('change',fn);});}
 bind(['rd-opt-wave','rd-opt-power','rd-opt-inc','rd-opt-mirror','rd-opt-medium','rd-opt-dist','rd-opt-resp'],opticalSafe);
 bind(['rd-specimen','rd-spec-layer','rd-mag','rd-spec-mode'],specimenDraw);el('rd-spec-scan').addEventListener('click',specimenScan);
 bind(['rd-mat','rd-force','rd-area','rd-length','rd-wire'],materialTest);
 bind(['rd-sonar','rd-sonar-s','rd-optical','rd-optical-s','rd-acoustic','rd-acoustic-s'],fusion);
 el('rd-fusion-reset').addEventListener('click',function(){[['rd-sonar',12.4],['rd-sonar-s',.6],['rd-optical',12.1],['rd-optical-s',.2],['rd-acoustic',12.8],['rd-acoustic-s',1.1]].forEach(function(x){el(x[0]).value=x[1];});fusion();});
 opticalSafe();specimenDraw();materialTest();fusion();
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();