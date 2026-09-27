// Adapted from the bubble.partofem.com archive supplied by the user.
// Original site: © 2026 Partofem. All rights reserved. No open-source license asserted.
// Only the bubble material is reused; no original application, telemetry or account code.
import {MeshPhysicalMaterial,Color,DoubleSide} from '../../vendor/three/three.module.js';
const q=(object,key,value)=>{object[key]=value};
export class SuppliedBubbleMaterial extends MeshPhysicalMaterial{constructor(t={}){super({color:t.color||16777215,transmission:t.transmission??.55,thickness:t.thickness??1.2,attenuationColor:t.attenuationColor??16777215,attenuationDistance:t.attenuationDistance??.8,roughness:t.roughness||0,iridescence:t.iridescence||1,iridescenceIOR:t.iridescenceIOR||1,iridescenceThicknessRange:t.iridescenceThicknessRange||[0,1200],clearcoat:t.clearcoat||1,clearcoatRoughness:t.clearcoatRoughness||0,envMapIntensity:t.envMapIntensity||1.5,reflectivity:1,specularIntensity:1,specularColor:new Color(16777215),transparent:!0,opacity:.45,side:DoubleSide});q(this,"time",0);q(this,"iridescenceMax",1);q(this,"timeUniform",{value:0});q(this,"rainbowUniform",{value:0});q(this,"rimBoostUniform",{value:0});q(this,"wobbleUniform",{value:1});this.onBeforeCompile=i=>{i.uniforms.uTime=this.timeUniform,i.uniforms.uRainbow=this.rainbowUniform,i.uniforms.uRimBoost=this.rimBoostUniform,i.uniforms.uWobble=this.wobbleUniform,i.fragmentShader=i.fragmentShader.replace("#include <common>",`#include <common>
uniform float uTime;
uniform float uRainbow;
uniform float uRimBoost;`).replace("vec4 diffuseColor = vec4( diffuse, opacity );",`vec4 diffuseColor = vec4( diffuse, opacity );
          // Clamp before pow: at the bubble centre n·v rounds past 1.0, making
          // 1-n·v a tiny negative and pow(negative, 2.2) NaN → black pixel.
          float bubbleNdv = clamp(abs(dot(normalize(vNormal), normalize(vViewPosition))), 0.0, 1.0);
          float bubbleFres = pow(1.0 - bubbleNdv, 2.2);
          // atan(0,0) is undefined in GLSL — Apple GPUs return NaN, which
          // poisons the colour (NaN*0 is still NaN) and paints the pixel
          // where the normal faces the camera dead black: the 'blinking
          // black dot' at the bubble centre as the wobble moves it around.
          vec2 bubbleNxy = vNormal.xy;
          float bubbleAng = dot(bubbleNxy, bubbleNxy) < 1e-8 ? 0.0 : atan(bubbleNxy.y, bubbleNxy.x);
          float bubbleHue = fract(bubbleAng * 0.31831 + bubbleFres * 1.4 + uTime * 0.045);
          vec3 bubbleRain = clamp(abs(mod(bubbleHue * 6.0 + vec3(0.0, 4.0, 2.0), 6.0) - 3.0) - 1.0, 0.0, 1.0);
          bubbleRain = mix(vec3(1.0), bubbleRain, 0.75);
          // Tint the film itself with the thin-film color at grazing angles —
          // coloring the rim (instead of adding light) survives bright env
          // reflections that would otherwise blow the rim out to white.
          diffuseColor.rgb *= mix(vec3(1.0), bubbleRain, clamp(bubbleFres * uRainbow * 1.6, 0.0, 1.0));
          diffuseColor.a = clamp(diffuseColor.a + bubbleFres * uRimBoost, 0.0, 1.0);`).replace("#include <emissivemap_fragment>",`#include <emissivemap_fragment>
          if (uRainbow > 0.0) {
            totalEmissiveRadiance += bubbleRain * bubbleFres * uRainbow * 0.45;
          }`),i.vertexShader=i.vertexShader.replace("#include <common>",`#include <common>
uniform float uTime;
uniform float uWobble;`).replace("#include <begin_vertex>",`#include <begin_vertex>
          {
            // Gentle undulation driven by DIRECTION, not raw position, so the
            // number of lobes stays constant at any scale (a 2x bubble stays
            // just as round instead of gaining twice the ripples)
            vec3 bdir = normalize(position);
            float wob =
              sin(bdir.x * 2.2 + uTime * 0.9) * 1.0 +
              sin(bdir.y * 2.6 + uTime * 1.2) * 0.8 +
              sin(bdir.z * 3.0 + uTime * 0.7) * 0.6;
            // Amplitude proportional to radius so all sizes wobble alike
            transformed += bdir * wob * 0.02 * uWobble * length(position);
          }`)},this.customProgramCacheKey=()=>"enhanced-bubble-wobble"}get rainbowStrength(){return this.rainbowUniform.value}set rainbowStrength(t){this.rainbowUniform.value=t}get rimBoost(){return this.rimBoostUniform.value}set rimBoost(t){this.rimBoostUniform.value=t}get wobbleScale(){return this.wobbleUniform.value}set wobbleScale(t){this.wobbleUniform.value=t}updateTime(t){this.time+=t,this.timeUniform.value=this.time;const i=Math.sin(this.time*.5)*.2+.8;this.iridescence=i*this.iridescenceMax}setDistortionStrength(t){}static createTaskBubbleMaterial(t){return new SuppliedBubbleMaterial({color:t||16777215,transmission:.55,thickness:1.2,attenuationColor:t||16777215,attenuationDistance:.8,roughness:0,iridescence:1,iridescenceIOR:1,iridescenceThicknessRange:[0,1200],clearcoat:1,clearcoatRoughness:0,envMapIntensity:1.2})}static createContainerBubbleMaterial(){return new SuppliedBubbleMaterial({color:16777215,transmission:1.05,thickness:-.5,roughness:0,iridescence:1,iridescenceIOR:1,iridescenceThicknessRange:[0,1200],clearcoat:1,clearcoatRoughness:0,envMapIntensity:1.5})}}
