function initGLSLCore() {
    const bg = document.getElementById('virtual-bg');
    if (!bg) return;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
    camera.position.z = 3;
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    bg.appendChild(renderer.domElement);

    const vertexShader = `
        varying vec2 vUv;
        varying vec3 vPosition;
        uniform float time;
        
        // Simplex 3D Noise
        vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x, 289.0);}
        vec4 taylorInvSqrt(vec4 r){return 1.79284291400159 - 0.85373472095314 * r;}
        float snoise(vec3 v){ 
          const vec2  C = vec2(1.0/6.0, 1.0/3.0) ;
          const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);
          vec3 i  = floor(v + dot(v, C.yyy) );
          vec3 x0 = v - i + dot(i, C.xxx) ;
          vec3 g = step(x0.yzx, x0.xyz);
          vec3 l = 1.0 - g;
          vec3 i1 = min( g.xyz, l.zxy );
          vec3 i2 = max( g.xyz, l.zxy );
          vec3 x1 = x0 - i1 + 1.0 * C.xxx;
          vec3 x2 = x0 - i2 + 2.0 * C.xxx;
          vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;
          i = mod(i, 289.0 ); 
          vec4 p = permute( permute( permute( 
                     i.z + vec4(0.0, i1.z, i2.z, 1.0 ))
                   + i.y + vec4(0.0, i1.y, i2.y, 1.0 )) 
                   + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));
          float n_ = 1.0/7.0; // N=7
          vec3  ns = n_ * D.wyz - D.xzx;
          vec4 j = p - 49.0 * floor(p * ns.z *ns.z);  //  mod(p,N*N)
          vec4 x_ = floor(j * ns.z);
          vec4 y_ = floor(j - 7.0 * x_ );    // mod(j,N)
          vec4 x = x_ *ns.x + ns.yyyy;
          vec4 y = y_ *ns.x + ns.yyyy;
          vec4 h = 1.0 - abs(x) - abs(y);
          vec4 b0 = vec4( x.xy, y.xy );
          vec4 b1 = vec4( x.zw, y.zw );
          vec4 s0 = floor(b0)*2.0 + 1.0;
          vec4 s1 = floor(b1)*2.0 + 1.0;
          vec4 sh = -step(h, vec4(0.0));
          vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy ;
          vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww ;
          vec3 p0 = vec3(a0.xy,h.x);
          vec3 p1 = vec3(a0.zw,h.y);
          vec3 p2 = vec3(a1.xy,h.z);
          vec3 p3 = vec3(a1.zw,h.w);
          vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
          p0 *= norm.x;
          p1 *= norm.y;
          p2 *= norm.z;
          p3 *= norm.w;
          vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
          m = m * m;
          return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), 
                                        dot(p2,x2), dot(p3,x3) ) );
        }

        void main() {
            vUv = uv;
            float noise = snoise(position * 2.0 + time * 0.5);
            vec3 displacedPosition = position + normal * noise * 0.3;
            vPosition = displacedPosition;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(displacedPosition, 1.0);
        }
    `;

    const fragmentShader = `
        varying vec2 vUv;
        varying vec3 vPosition;
        uniform float time;
        
        void main() {
            // Calculate color based on displacement and time
            float intensity = length(vPosition) - 1.0;
            vec3 color = vec3(0.0, 0.8, 1.0) * (0.5 + intensity * 2.0);
            // Add a purple core
            color += vec3(0.5, 0.0, 0.8) * smoothstep(1.3, 0.8, length(vPosition));
            
            float alpha = smoothstep(0.0, 0.5, intensity + 0.8);
            gl_FragColor = vec4(color, alpha * 0.8);
        }
    `;

    const uniforms = {
        time: { value: 0.0 }
    };
    const material = new THREE.ShaderMaterial({
        uniforms: uniforms,
        vertexShader: vertexShader,
        fragmentShader: fragmentShader,
        transparent: true,
        wireframe: false
    });

    const geometry = new THREE.IcosahedronGeometry(1.2, 64);
    const orb = new THREE.Mesh(geometry, material);
    scene.add(orb);

    // Add some orbiting particles
    const partGeo = new THREE.BufferGeometry();
    const pos = new Float32Array(500 * 3);
    for(let i=0; i<500*3; i++){ pos[i] = (Math.random()-0.5)*12; }
    partGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const partMat = new THREE.PointsMaterial({color: 0x00ffff, size: 0.03, transparent: true, opacity: 0.6});
    const particles = new THREE.Points(partGeo, partMat);
    scene.add(particles);

    // Add outer rings
    const rings = [];
    for(let i=0; i<3; i++) {
        const rGeo = new THREE.TorusGeometry(1.8 + i*0.4, 0.015, 16, 100);
        const rMat = new THREE.MeshBasicMaterial({ color: 0x00ffff, transparent: true, opacity: 0.4 });
        const r = new THREE.Mesh(rGeo, rMat);
        r.rotation.x = Math.random()*Math.PI;
        r.rotation.y = Math.random()*Math.PI;
        scene.add(r);
        rings.push(r);
    }

    // Mouse parallax
    let mouseX = 0, mouseY = 0;
    document.addEventListener('mousemove', e => {
        mouseX = (e.clientX - window.innerWidth/2) * 0.001;
        mouseY = (e.clientY - window.innerHeight/2) * 0.001;
    });

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });

    function animate() {
        requestAnimationFrame(animate);
        uniforms.time.value += 0.02;
        orb.rotation.y += 0.002;
        
        rings[0].rotation.x += 0.005;
        rings[1].rotation.y += 0.004;
        rings[2].rotation.z += 0.003;

        particles.rotation.y -= 0.001;

        scene.rotation.x += 0.05 * (mouseY - scene.rotation.x);
        scene.rotation.y += 0.05 * (mouseX - scene.rotation.y);

        renderer.render(scene, camera);
    }
    animate();
}
initGLSLCore();
