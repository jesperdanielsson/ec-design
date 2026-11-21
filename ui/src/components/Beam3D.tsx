import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";

interface Props {
  span_m: number;
  b_mm: number;
  h_mm: number;
  cover_mm: number;
}

// Enkel 3D-vy: genomskinlig betong med längsarmering. Byglar kommer i steg 8.
export function Beam3D({ span_m, b_mm, h_mm, cover_mm }: Props) {
  const L = span_m;
  const b = b_mm / 1000;
  const h = h_mm / 1000;
  const c = cover_mm / 1000;
  const r = 0.008;
  const xs = [-b / 2 + c + r, 0, b / 2 - c - r];
  return (
    <div className="view3d">
      <Canvas camera={{ position: [L * 0.55, L * 0.3, L * 0.6], fov: 40 }}>
        <ambientLight intensity={0.7} />
        <directionalLight position={[5, 8, 5]} intensity={1.2} />
        <mesh>
          <boxGeometry args={[L, h, b]} />
          <meshStandardMaterial color="#b9bec7" transparent opacity={0.35} />
        </mesh>
        {xs.map((z, i) => (
          <mesh key={i} position={[0, -h / 2 + c + r, z]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[r, r, L - 2 * c, 12]} />
            <meshStandardMaterial color="#c2410c" />
          </mesh>
        ))}
        <OrbitControls makeDefault />
      </Canvas>
      <div className="view3d-hint">Dra för att rotera, scrolla för att zooma</div>
    </div>
  );
}
