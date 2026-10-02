import { expect, it } from 'vitest';
import { hasCoordinates } from './coordinates';

it('keeps zero coordinates and excludes missing or non-finite map points', () => {
  const points = [
    { lat: 0, lng: 0 }, { lat: 23.0225, lng: 72.5714 },
    { lat: null, lng: 72 }, { lat: 23, lng: null },
    { lat: NaN, lng: 72 }, { lat: 23, lng: Infinity },
  ];
  expect(points.filter(hasCoordinates)).toEqual(points.slice(0, 2));
});
