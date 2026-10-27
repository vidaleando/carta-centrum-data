// Small GeoJSON helpers, so we don't need turf for a few hundred points.

/** Plain data-centre record from a GeoJSON (or MapLibre query) point feature. */
export function toDc(feature) {
  const p = feature.properties || {};
  return {
    id: p.id ?? null,
    name: p.name || null,
    operator: p.operator || null,
    coordinates: feature.geometry.coordinates.slice(0, 2)
  };
}

export function dcLabel(props) {
  return props.name || props.operator || 'Unnamed data centre';
}

export function pointFeature(coordinates) {
  return {
    type: 'FeatureCollection',
    features: [{ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates } }]
  };
}

export const EMPTY = { type: 'FeatureCollection', features: [] };

/** [[west, south], [east, north]] for a FeatureCollection, or null if it has no coordinates. */
export function boundsOf(collection) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  const visit = (coords) => {
    if (typeof coords[0] === 'number') {
      minX = Math.min(minX, coords[0]); maxX = Math.max(maxX, coords[0]);
      minY = Math.min(minY, coords[1]); maxY = Math.max(maxY, coords[1]);
    } else {
      coords.forEach(visit);
    }
  };
  collection.features.forEach((f) => f.geometry && visit(f.geometry.coordinates));
  return minX === Infinity ? null : [[minX, minY], [maxX, maxY]];
}

// Ray casting; ring is [[x, y], ...].
function inRing([x, y], ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function inPolygon(point, rings) {
  return inRing(point, rings[0]) && !rings.slice(1).some((hole) => inRing(point, hole));
}

export function containsPoint(geometry, point) {
  if (geometry.type === 'Polygon') return inPolygon(point, geometry.coordinates);
  if (geometry.type === 'MultiPolygon') return geometry.coordinates.some((poly) => inPolygon(point, poly));
  return false;
}
