/** Camera metadata may be incomplete; Leaflet requires finite coordinate pairs. */
export function hasCoordinates<T extends {
    lat: number | null;
    lng: number | null;
}>(value: T): value is T & {
    lat: number;
    lng: number;
} {
    return typeof value.lat === 'number' && Number.isFinite(value.lat)
        && typeof value.lng === 'number' && Number.isFinite(value.lng);
}
