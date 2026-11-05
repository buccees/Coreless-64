(function(root){
'use strict';
var G=6.67430e-20;
function finite(v,fallback){v=Number(v);return Number.isFinite(v)?v:fallback;}
function add(a,b){return {x:a.x+b.x,y:a.y+b.y,z:a.z+b.z};}
function sub(a,b){return {x:a.x-b.x,y:a.y-b.y,z:a.z-b.z};}
function scale(a,s){return {x:a.x*s,y:a.y*s,z:a.z*s};}
function dot(a,b){return a.x*b.x+a.y*b.y+a.z*b.z;}
function cross(a,b){return {x:a.y*b.z-a.z*b.y,y:a.z*b.x-a.x*b.z,z:a.x*b.y-a.y*b.x};}
function length(a){return Math.hypot(a.x,a.y,a.z);}
function unit(a){var n=length(a)||1;return scale(a,1/n);}
function rotate(v,axis,angle){
 var n=unit(axis),c=Math.cos(angle),s=Math.sin(angle);
 return add(add(scale(v,c),scale(cross(n,v),s)),scale(n,dot(n,v)*(1-c)));
}
function bodyAxis(body){var a=body.spinAxis||[0,0,1];return unit({x:finite(a[0],0),y:finite(a[1],0),z:finite(a[2],1)});}
function bodyOmega(body){return scale(bodyAxis(body),2*Math.PI/(Math.max(1,finite(body.spin,24))*3600));}
function bodyPosition(body){return {x:finite(body.x,0),y:finite(body.y,0),z:finite(body.z,0)};}
function bodyVelocity(body){return {x:finite(body.vx,0),y:finite(body.vy,0),z:finite(body.vz,0)};}
function surfaceBasis(latitude,longitude){
 var cl=Math.cos(latitude),sl=Math.sin(latitude),co=Math.cos(longitude),so=Math.sin(longitude);
 return {
  up:{x:cl*so,y:sl,z:cl*co},
  east:{x:co,y:0,z:-so},
  north:{x:-sl*so,y:cl,z:-sl*co}
 };
}
function surfaceToInertial(body,latitude,longitude,altitudeKm,localVelocity){
 var basis=surfaceBasis(finite(latitude,0),finite(longitude,0)),angle=finite(body.spinAngle,0),axis=bodyAxis(body);
 var up=rotate(basis.up,axis,angle),east=rotate(basis.east,axis,angle),north=rotate(basis.north,axis,angle);
 var radius=finite(body.radius,6371)+finite(altitudeKm,0),offset=scale(up,radius),omega=bodyOmega(body);
 var velocity=add(bodyVelocity(body),cross(omega,offset));
 localVelocity=localVelocity||{};
 velocity=add(velocity,add(add(scale(east,finite(localVelocity.east,0)),scale(north,finite(localVelocity.north,0))),scale(up,finite(localVelocity.up,0))));
 return {position:add(bodyPosition(body),offset),velocity:velocity,basis:{east:east,north:north,up:up},surfaceRadiusKm:radius};
}
function inertialToSurface(body,position,velocity){
 var axis=bodyAxis(body),angle=finite(body.spinAngle,0),relative=sub(position,bodyPosition(body));
 var fixed=rotate(relative,axis,-angle),r=length(fixed)||1,basis=surfaceBasis(Math.asin(Math.max(-1,Math.min(1,fixed.y/r))),Math.atan2(fixed.x,fixed.z));
 var inertialBasis={east:rotate(basis.east,axis,angle),north:rotate(basis.north,axis,angle),up:rotate(basis.up,axis,angle)};
 var omega=bodyOmega(body),surfaceVelocity=add(bodyVelocity(body),cross(omega,relative)),relativeVelocity=sub(velocity,surfaceVelocity);
 return {
  latitudeRad:Math.asin(Math.max(-1,Math.min(1,fixed.y/r))),
  longitudeRad:Math.atan2(fixed.x,fixed.z),
  altitudeKm:r-finite(body.radius,6371),
  eastMps:dot(relativeVelocity,inertialBasis.east)*1000,
  northMps:dot(relativeVelocity,inertialBasis.north)*1000,
  upMps:dot(relativeVelocity,inertialBasis.up)*1000
 };
}
function gravityAt(position,bodies){
 var acceleration={x:0,y:0,z:0};
 (bodies||[]).forEach(function(body){
  var delta=sub(bodyPosition(body),position),r2=dot(delta,delta),mass=finite(body.mass,0);
  if(mass<=0||r2<1)return;
  acceleration=add(acceleration,scale(delta,G*mass/(r2*Math.sqrt(r2))));
 });
 return acceleration;
}
function effectiveSurfaceGravity(body,latitude,longitude,bodies){
 var state=surfaceToInertial(body,latitude,longitude,0,{});
 var omega=bodyOmega(body),centrifugal=scale(cross(omega,cross(omega,sub(state.position,bodyPosition(body)))), -1);
 var effective=add(gravityAt(state.position,bodies),centrifugal);
 return {vector:effective,magnitude:length(effective),up:dot(effective,state.basis.up),east:dot(effective,state.basis.east),north:dot(effective,state.basis.north)};
}
function createActor(body,latitude,longitude,altitudeKm,localVelocity){
 var state=surfaceToInertial(body,latitude,longitude,altitudeKm,localVelocity);
 return {position:state.position,velocity:state.velocity,referenceBodyId:body.id||'nirn'};
}
function stepActor(actor,bodies,dtSeconds,controlAcceleration){
 dtSeconds=finite(dtSeconds,0);
 if(dtSeconds<=0||dtSeconds>10)throw new RangeError('Actor integration step must be greater than 0 and no more than 10 seconds.');
 controlAcceleration=controlAcceleration||{};
 var nearest=null,nearestDistance=Infinity;
 (bodies||[]).forEach(function(body){var d=length(sub(actor.position,bodyPosition(body)))-finite(body.radius,0);if(d<nearestDistance){nearestDistance=d;nearest=body;}});
 var local=nearest?inertialToSurface(nearest,actor.position,actor.velocity):null;
 var control={x:finite(controlAcceleration.x,0),y:finite(controlAcceleration.y,0),z:finite(controlAcceleration.z,0)};
 var a0=add(gravityAt(actor.position,bodies),control);
 var nextPosition=add(add(actor.position,scale(actor.velocity,dtSeconds)),scale(a0,.5*dtSeconds*dtSeconds));
 var a1=add(gravityAt(nextPosition,bodies),control);
 var nextVelocity=add(actor.velocity,scale(add(a0,a1),.5*dtSeconds));
 if(nearest&&local){
  var nextLocal=inertialToSurface(nearest,nextPosition,nextVelocity),surfaceRadius=finite(nearest.radius,6371);
  if(nextLocal.altitudeKm<0){
   var corrected=surfaceToInertial(nearest,nextLocal.latitudeRad,nextLocal.longitudeRad,0,{east:nextLocal.eastMps,north:nextLocal.northMps,up:Math.max(0,nextLocal.upMps)});
   nextPosition=corrected.position;nextVelocity=corrected.velocity;
  }
 }
 actor.position=nextPosition;actor.velocity=nextVelocity;
 return actor;
}
var api={G:G,surfaceBasis:surfaceBasis,surfaceToInertial:surfaceToInertial,inertialToSurface:inertialToSurface,gravityAt:gravityAt,effectiveSurfaceGravity:effectiveSurfaceGravity,createActor:createActor,stepActor:stepActor};
if(root){root.VigilNirnCoupledWorld=api;}
if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
