"""
    Title layout with shader background: 
    Animated Brownian motion WebGL shader rendered on an absolutely-positioned <canvas> behind the text
"""

# Colors as (R, G, B) floats 0–1
COLOR1 = (0.996, 0.851, 0.04)
COLOR2 = (0.988, 0.525, 0.000)

# Animation speed multiplier (>1 = faster, <1 = slower)
TRANSFORM_SPEED = 0.1

# Octave detail multiplier (>1 = more turbulent, <1 = smoother)
OCTAVES = 1.0

# GLSL frag
_FRAG = r"""
#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2  u_resolution;
uniform vec3  u_color1;
uniform vec3  u_color2;
uniform float u_transformSpeedMultiplier;
uniform float u_octavesMultiplier;

float rand(vec2 n){
    return fract(sin(dot(n,vec2(12.9898,4.1414)))*43758.5453);
}
float noise(vec2 p){
    vec2 ip=floor(p),u=fract(p);
    u=u*u*(3.0-2.0*u);
    float res=mix(mix(rand(ip),rand(ip+vec2(1,0)),u.x),
                  mix(rand(ip+vec2(0,1)),rand(ip+vec2(1,1)),u.x),u.y);
    return res*res;
}
const mat2 mtx=mat2(0.80,0.60,-0.60,0.80);
float fbm(vec2 p){
    float f=0.0;
    f+=0.500000*noise(p+u_time*u_transformSpeedMultiplier); p=mtx*p*2.02*u_octavesMultiplier;
    f+=0.031250*noise(p); p=mtx*p*2.01;
    f+=0.250000*noise(p); p=mtx*p*2.03;
    f+=0.125000*noise(p); p=mtx*p*2.01;
    f+=0.062500*noise(p); p=mtx*p*2.04;
    f+=0.015625*noise(p+sin(u_time/2.0*u_octavesMultiplier));
    return f/0.96875;
}
float pattern(vec2 p){ return fbm(p+fbm(p+fbm(p))); }
vec4 colormap(float x){
    float r=clamp(mix(u_color1.r,u_color2.r,x*2.0),0.0,1.0);
    float g=clamp(mix(u_color1.g,u_color2.g,x*2.0),0.0,1.0);
    float b=clamp(mix(u_color1.b,u_color2.b,x*2.0),0.0,1.0);
    return vec4(r,g,b,1.0);
}
void main(){
    vec2 uv=gl_FragCoord.xy/u_resolution.x;
    float shade=pattern(uv);
    gl_FragColor=vec4(colormap(shade).rgb,shade);
}
"""


# JS init code template
# Includes placeholders which are replaced when generating the snippet
# And this code is base64-encoded and injected into an <img> onerror handler
# so it only runs when the slide is in the DOM
_JS_INIT = r"""(function(){
  var c = document.getElementById('__CANVAS_ID__');
  if(!c) return;
  var gl = c.getContext('webgl') || c.getContext('experimental-webgl');
  if(!gl) return;
  function resize(){
    var dpr=window.devicePixelRatio||1;
    var w=Math.max(1,Math.floor(c.clientWidth*dpr));
    var h=Math.max(1,Math.floor(c.clientHeight*dpr));
    if(c.width!==w||c.height!==h){c.width=w;c.height=h;}
  }
  var VERT='attribute vec2 a_pos;void main(){gl_Position=vec4(a_pos,0.0,1.0);}';
  var FRAG=__FRAG__;
  function mk(gl,type,src){
    var s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)){console.error(gl.getShaderInfoLog(s));return null;}
    return s;
  }
  var vs=mk(gl,gl.VERTEX_SHADER,VERT), fs=mk(gl,gl.FRAGMENT_SHADER,FRAG);
  if(!vs||!fs) return;
  var prog=gl.createProgram();
  gl.attachShader(prog,vs);gl.attachShader(prog,fs);gl.linkProgram(prog);
  if(!gl.getProgramParameter(prog,gl.LINK_STATUS)) return;
  var buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);
  gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
  var aPos=gl.getAttribLocation(prog,'a_pos');
  gl.enableVertexAttribArray(aPos);gl.vertexAttribPointer(aPos,2,gl.FLOAT,false,0,0);
  gl.useProgram(prog);
  var uT=gl.getUniformLocation(prog,'u_time');
  var uR=gl.getUniformLocation(prog,'u_resolution');
  var uC1=gl.getUniformLocation(prog,'u_color1');
  var uC2=gl.getUniformLocation(prog,'u_color2');
  var uS=gl.getUniformLocation(prog,'u_transformSpeedMultiplier');
  var uO=gl.getUniformLocation(prog,'u_octavesMultiplier');
  if(uC1) gl.uniform3f(uC1,__C1__);
  if(uC2) gl.uniform3f(uC2,__C2__);
  if(uS)  gl.uniform1f(uS,__SPD__);
  if(uO)  gl.uniform1f(uO,__OCT__);
  var t0=performance.now()-1500, raf=null, visible=false;
  function render(){
    if(!visible){raf=null;return;}
    resize();
    gl.viewport(0,0,c.width,c.height);
    var t=(performance.now()-t0)/1000;
    if(uT) gl.uniform1f(uT,t);
    if(uR) gl.uniform2f(uR,c.width,c.height);
    gl.drawArrays(gl.TRIANGLES,0,6);
    raf=requestAnimationFrame(render);
  }
  var io=new IntersectionObserver(function(entries){
    entries.forEach(function(e){
      visible=e.isIntersecting;
      if(visible&&!raf) raf=requestAnimationFrame(render);
    });
  },{threshold:0.1});
  io.observe(c);
})();"""


def _make_shader_html(canvas_id: str) -> str:
    """Return a tag-only HTML snippet that initialises WebGL with no <script> elements."""
    import base64, json
    js = (
        _JS_INIT
        .replace('__CANVAS_ID__', canvas_id)
        .replace('__FRAG__', json.dumps(_FRAG))
        .replace('__C1__',   ','.join(f'{v:.4f}' for v in COLOR1))
        .replace('__C2__',   ','.join(f'{v:.4f}' for v in COLOR2))
        .replace('__SPD__',  f'{TRANSFORM_SPEED:.4f}')
        .replace('__OCT__',  f'{OCTAVES:.4f}')
    )
    b64 = base64.b64encode(js.encode()).decode()
    onerror = "new Function(atob('" + b64 + "'))();"
    return '<img src="x" onerror="' + onerror + '" style="display:none" aria-hidden="true">'


def match(slide) -> bool:
    """Claim title slides (1 or 2 heading lines, no body)."""
    lines = [l for l in slide.content.strip().splitlines() if l.strip()]
    heading_lines = [l for l in lines if l.startswith("#")]
    body_lines = [l for l in lines if not l.startswith("#")]
    return bool(heading_lines and not body_lines and len(heading_lines) <= 2)


def html(slide, md) -> str:
    import uuid
    cid = 'pf-shader-' + uuid.uuid4().hex
    return (
        '<div class="slide-layout title" style="position:relative;overflow:hidden;">'
        '<canvas id="' + cid + '" class="pf-shader-bg" style="position:absolute;inset:0;width:100%;height:100%;z-index:0;display:block;"></canvas>'
        '<div style="position:relative;z-index:1;">'
        + md(slide.content) +
        '</div>'
        '</div>'
        + _make_shader_html(cid)
    )