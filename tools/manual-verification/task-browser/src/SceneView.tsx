import { useEffect, useRef } from "react";
import * as THREE from "three";
import { ViewHelper } from "three/addons/helpers/ViewHelper.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { ScenePayload } from "./types";

export function SceneView({ scene }: { scene: ScenePayload | null }) {
  const container = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const element = container.current;
    if (!element || scene === null) return;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0xf7f7f9, 1);
    renderer.autoClear = false;
    element.appendChild(renderer.domElement);

    const world = new THREE.Scene();
    world.background = new THREE.Color(0xf7f7f9);
    const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 100_000);
    camera.up.set(0, 0, 1);

    const bounds = new THREE.Box3(
      new THREE.Vector3(...scene.bounds_min),
      new THREE.Vector3(...scene.bounds_max),
    );
    const center = bounds.getCenter(new THREE.Vector3());
    const size = bounds.getSize(new THREE.Vector3());
    const extent = Math.max(size.x, size.y, size.z, 0.5);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.copy(center);
    controls.enableDamping = false;
    controls.screenSpacePanning = true;
    camera.position
      .copy(center)
      .add(new THREE.Vector3(1.3, 1.0, 1.1).normalize().multiplyScalar(extent * 2.4));
    camera.near = Math.max(extent / 1000, 0.01);
    camera.far = extent * 100;
    camera.updateProjectionMatrix();
    controls.update();

    world.add(new THREE.HemisphereLight(0xffffff, 0x445566, 1.5));
    const key = new THREE.DirectionalLight(0xffffff, 2.0);
    key.position.copy(camera.position);
    world.add(key);

    const geometries: THREE.BufferGeometry[] = [];
    const materials: THREE.Material[] = [];
    for (const part of scene.parts) {
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.Float32BufferAttribute(part.positions, 3));
      geometries.push(geometry);
      const color = new THREE.Color(...part.color);
      if (part.primitive_kind === "triangles") {
        geometry.computeVertexNormals();
        const material = new THREE.MeshStandardMaterial({
          color,
          side: THREE.DoubleSide,
          metalness: 0.0,
          roughness: 0.65,
        });
        materials.push(material);
        world.add(new THREE.Mesh(geometry, material));
      } else {
        const material = new THREE.LineBasicMaterial({ color });
        materials.push(material);
        world.add(new THREE.LineSegments(geometry, material));
      }
    }

    const viewHelper = new ViewHelper(camera, renderer.domElement);
    viewHelper.setLabels("X", "Y", "Z");

    const render = () => {
      renderer.clear();
      renderer.render(world, camera);
      viewHelper.render(renderer);
    };
    const resize = () => {
      const width = Math.max(1, element.clientWidth);
      const height = Math.max(1, element.clientHeight);
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      render();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    controls.addEventListener("change", render);
    resize();

    return () => {
      observer.disconnect();
      controls.removeEventListener("change", render);
      controls.dispose();
      for (const geometry of geometries) geometry.dispose();
      for (const material of materials) material.dispose();
      viewHelper.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === element) {
        element.removeChild(renderer.domElement);
      }
    };
  }, [scene]);

  return (
    <div className="scene-view" ref={container}>
      {scene === null ? (
        <p className="scene-empty">Select a task to load its final solid state.</p>
      ) : null}
    </div>
  );
}
