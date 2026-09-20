import React, { useState, useEffect, useRef, useMemo } from 'react';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer, ArcLayer, TextLayer } from '@deck.gl/layers';
import { Map as MapLibreMap } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

import rawCpseData from '../data/cpseLocations.json';
import RawCard from '../components/RawCard';
import RawButton from '../components/RawButton';

// Sovereign basemap using ESRI World Gray Canvas (Free, no API key required, no watermark)
const MAP_STYLES = {
  light: {
    version: 8,
    sources: {
      'esri-light': {
        type: 'raster',
        tiles: [
          'https://services.arcgisonline.com/arcgis/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        ],
        tileSize: 256,
        attribution: '© Esri, Garmin, © OpenStreetMap contributors',
      },
    },
    layers: [{ id: 'esri-light-layer', type: 'raster', source: 'esri-light' }],
  },
  dark: {
    version: 8,
    sources: {
      'esri-dark': {
        type: 'raster',
        tiles: [
          'https://services.arcgisonline.com/arcgis/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        ],
        tileSize: 256,
        attribution: '© Esri, Garmin, © OpenStreetMap contributors',
      },
    },
    layers: [{ id: 'esri-dark-layer', type: 'raster', source: 'esri-dark' }],
  },
};

// Great-circle Haversine formula
function calculateDistanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c);
}

// Initial center over Central India
const INITIAL_VIEW_STATE = {
  longitude: 78.9629,
  latitude: 22.5937,
  zoom: 4.8,
  pitch: 30,
  bearing: 0,
  maxZoom: 16,
  minZoom: 3,
};

const SECTORS = ['All', 'Oil & Gas', 'Power', 'Steel', 'Mining', 'Heavy Engineering'];

export default function GeoRadarView({ onViewChange }) {
  const [viewState, setViewState] = useState(INITIAL_VIEW_STATE);
  const [mapTheme, setMapTheme] = useState('light');
  const [selectedSector, setSelectedSector] = useState('All');
  
  // CPSE and Facility selection state
  const [selectedCpse, setSelectedCpse] = useState('ONGC');
  const [selectedFacilityId, setSelectedFacilityId] = useState('');
  
  // Nearest stocking facilities state
  const [showNearestStocking, setShowNearestStocking] = useState(false);
  const [radarRadiusKm, setRadarRadiusKm] = useState(250);
  const [showTypeLabels, setShowTypeLabels] = useState(true);

  // Tooltip state
  const [hoverInfo, setHoverInfo] = useState(null);

  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);

  // List of distinct CPSE companies
  const cpseCompanies = useMemo(() => {
    const set = new Set(rawCpseData.map((d) => d.company));
    return Array.from(set).sort();
  }, []);

  // Filter facilities by active CPSE or sector
  const availableFacilitiesForCpse = useMemo(() => {
    return rawCpseData.filter((d) => d.company === selectedCpse);
  }, [selectedCpse]);

  // Set default facility when CPSE changes
  useEffect(() => {
    if (availableFacilitiesForCpse.length > 0) {
      setSelectedFacilityId(availableFacilitiesForCpse[0].id);
    }
  }, [selectedCpse, availableFacilitiesForCpse]);

  // The active facility object
  const currentSelectedFacility = useMemo(() => {
    return (
      rawCpseData.find((d) => d.id === selectedFacilityId) ||
      availableFacilitiesForCpse[0] ||
      rawCpseData[0]
    );
  }, [selectedFacilityId, availableFacilitiesForCpse]);

  // Filter facilities by sector
  const filteredFacilities = useMemo(() => {
    if (selectedSector === 'All') return rawCpseData;
    return rawCpseData.filter((d) => d.sector.toLowerCase().includes(selectedSector.toLowerCase()));
  }, [selectedSector]);

  // Calculate nearest stocking facilities from sister CPSEs
  const nearestStockingFacilities = useMemo(() => {
    if (!currentSelectedFacility) return [];
    const [cLon, cLat] = currentSelectedFacility.coordinates;

    const list = rawCpseData
      .filter((d) => d.id !== currentSelectedFacility.id)
      .map((d) => {
        const [fLon, fLat] = d.coordinates;
        const dist = calculateDistanceKm(cLat, cLon, fLat, fLon);
        const estTransitHrs = Math.max(1, Math.round(dist / 42)); // ~42 km/h heavy freight speed
        return {
          ...d,
          distanceKm: dist,
          transitHours: estTransitHrs,
          isSisterCpse: d.company !== currentSelectedFacility.company,
        };
      })
      .filter((d) => d.distanceKm <= radarRadiusKm)
      .sort((a, b) => a.distanceKm - b.distanceKm);

    return list;
  }, [currentSelectedFacility, radarRadiusKm]);

  // Dynamically compute real transit statistics across all matched sister units
  const transitStats = useMemo(() => {
    if (nearestStockingFacilities.length === 0) {
      return { avg: 0, min: 0, max: 0, avgDistance: 0 };
    }
    const totalHrs = nearestStockingFacilities.reduce((sum, f) => sum + f.transitHours, 0);
    const totalDist = nearestStockingFacilities.reduce((sum, f) => sum + f.distanceKm, 0);
    const minHrs = Math.min(...nearestStockingFacilities.map((f) => f.transitHours));
    const maxHrs = Math.max(...nearestStockingFacilities.map((f) => f.transitHours));
    const avgHrs = Math.round((totalHrs / nearestStockingFacilities.length) * 10) / 10;
    const avgDist = Math.round(totalDist / nearestStockingFacilities.length);
    return {
      avg: avgHrs,
      min: minHrs,
      max: maxHrs,
      avgDistance: avgDist,
    };
  }, [nearestStockingFacilities]);

  // Fly to selected facility
  const handleFlyToFacility = (fac) => {
    if (!fac) return;
    setSelectedFacilityId(fac.id);
    setSelectedCpse(fac.company);
    setViewState((prev) => ({
      ...prev,
      longitude: fac.coordinates[0],
      latitude: fac.coordinates[1],
      zoom: 8.5,
      pitch: 45,
      transitionDuration: 1200,
    }));
  };

  // Initialize MapLibre GL Basemap
  useEffect(() => {
    if (!mapContainerRef.current) return;

    const map = new MapLibreMap({
      container: mapContainerRef.current,
      style: MAP_STYLES[mapTheme],
      center: [INITIAL_VIEW_STATE.longitude, INITIAL_VIEW_STATE.latitude],
      zoom: INITIAL_VIEW_STATE.zoom,
      bearing: INITIAL_VIEW_STATE.bearing,
      pitch: INITIAL_VIEW_STATE.pitch,
      interactive: false, // Deck.gl handles interactions
      attributionControl: false,
    });

    mapRef.current = map;

    return () => {
      map.remove();
    };
  }, []);

  // Update MapLibre style on theme change
  useEffect(() => {
    if (mapRef.current) {
      mapRef.current.setStyle(MAP_STYLES[mapTheme]);
    }
  }, [mapTheme]);

  // Synchronize MapLibre with Deck.gl viewState
  const handleViewStateChange = ({ viewState: newViewState }) => {
    setViewState(newViewState);
    if (mapRef.current) {
      mapRef.current.jumpTo({
        center: [newViewState.longitude, newViewState.latitude],
        zoom: newViewState.zoom,
        bearing: newViewState.bearing,
        pitch: newViewState.pitch,
      });
    }
  };

  // Deck.gl Layers
  const layers = [
    // 1. Point / Facility Scatterplot Layer
    new ScatterplotLayer({
      id: 'cpse-facilities-points',
      data: filteredFacilities,
      pickable: true,
      opacity: 0.9,
      stroked: true,
      filled: true,
      radiusScale: 1,
      radiusMinPixels: 5,
      radiusMaxPixels: 24,
      lineWidthMinPixels: 2,
      getPosition: (d) => d.coordinates,
      getRadius: (d) =>
        d.id === currentSelectedFacility?.id
          ? 26000
          : d.psu_tier === 'Maharatna'
          ? 14000
          : 9000,
      getFillColor: (d) =>
        d.id === currentSelectedFacility?.id ? [250, 204, 21, 255] : d.color,
      getLineColor: (d) =>
        d.id === currentSelectedFacility?.id ? [0, 0, 0, 255] : [255, 255, 255, 230],
      onClick: (info) => {
        if (info.object) {
          handleFlyToFacility(info.object);
        }
      },
      onHover: (info) => setHoverInfo(info),
      updateTriggers: {
        getFillColor: [currentSelectedFacility?.id],
        getLineColor: [currentSelectedFacility?.id],
        getRadius: [currentSelectedFacility?.id],
      },
    }),

    // 2. Labels according to type of CPSE on map with visualization
    showTypeLabels &&
      new TextLayer({
        id: 'cpse-type-labels',
        data: filteredFacilities,
        pickable: true,
        getPosition: (d) => d.coordinates,
        getText: (d) => `${d.company} [${d.type_label}]`,
        getSize: 11,
        getColor: [255, 255, 255, 255],
        getTextAnchor: 'start',
        getAlignmentBaseline: 'center',
        getPixelOffset: [12, 0],
        background: true,
        getBackgroundColor: (d) =>
          d.id === currentSelectedFacility?.id
            ? [15, 23, 42, 240]
            : [d.color[0], d.color[1], d.color[2], 220],
        getBackgroundPadding: [5, 3, 5, 3],
        sizeMinPixels: 9,
        sizeMaxPixels: 14,
        fontFamily: 'monospace',
        fontWeight: 'bold',
        onHover: (info) => setHoverInfo(info),
        onClick: (info) => {
          if (info.object) handleFlyToFacility(info.object);
        },
        updateTriggers: {
          getBackgroundColor: [currentSelectedFacility?.id],
        },
      }),

    // 3. Inter-CPSE Transfer Arcs (when 'View Nearest Stocking Facilities' is enabled)
    showNearestStocking &&
      currentSelectedFacility &&
      new ArcLayer({
        id: 'inter-cpse-stock-arcs',
        data: nearestStockingFacilities,
        pickable: true,
        getSourcePosition: () => currentSelectedFacility.coordinates,
        getTargetPosition: (d) => d.coordinates,
        getSourceColor: [249, 115, 22, 255], // Energetic source orange
        getTargetColor: [16, 185, 129, 255], // Green stocking destination
        getWidth: 3.5,
        getHeight: 0.6,
        onHover: (info) => setHoverInfo(info),
        updateTriggers: {
          getSourcePosition: [currentSelectedFacility.id],
        },
      }),
  ].filter(Boolean);

  return (
    <div className="flex flex-col min-h-screen bg-raw-white text-raw-black">
      {/* Top Banner: Context & Problem Statement */}
      <div className="border-b-3 border-raw-black bg-raw-sunken px-4 sm:px-6 py-3">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="bg-raw-black text-raw-white text-xs font-headline px-2 py-0.5 tracking-wider">
                GEO-LOGISTICS LAYER
              </span>
              <h1 className="text-xl sm:text-2xl font-headline tracking-tighter uppercase font-black">
                [CPSE GEO-RADAR] Inter-Enterprise Spares Network
              </h1>
            </div>
            <p className="text-xs font-mono text-gray-700 mt-1 max-w-3xl">
              Tackling the <strong>₹15,000 Cr dead buffer inventory trap</strong>. Standardized CNMC parts can be transferred between adjacent sister CPSE units in hours instead of waiting for <strong>9-month foreign import replenishment</strong>.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="border-2 border-raw-black bg-raw-white px-3 py-1 text-right">
              <div className="text-[10px] font-mono text-gray-500 uppercase">Geocoded Assets</div>
              <div className="font-headline font-bold text-sm">383 Facilities / 15 CPSEs</div>
            </div>
            <button
              onClick={() => onViewChange('landing')}
              className="font-headline text-xs uppercase px-3 py-2 border-2 border-raw-black bg-raw-white hover:bg-raw-black hover:text-raw-white"
            >
              ← Back
            </button>
          </div>
        </div>
      </div>

      {/* Main Interactive Work Area */}
      <div className="flex-1 flex flex-col lg:flex-row relative">
        {/* Left Control Sidebar */}
        <div className="w-full lg:w-96 border-b-3 lg:border-b-0 lg:border-r-3 border-raw-black bg-raw-white p-4 overflow-y-auto max-h-[85vh] lg:max-h-none z-10">
          {/* Section 1: User's CPSE Selection */}
          <div className="mb-5 pb-5 border-b-2 border-raw-black">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-headline uppercase tracking-wider font-bold">
                1. Select Your Enterprise
              </label>
              <span className="bg-raw-black text-raw-white text-[10px] px-1.5 font-mono">
                {currentSelectedFacility?.psu_tier?.toUpperCase() || 'MAHARATNA'}
              </span>
            </div>

            <select
              value={selectedCpse}
              onChange={(e) => setSelectedCpse(e.target.value)}
              className="w-full bg-raw-sunken text-raw-black font-mono text-sm p-2.5 border-2 border-raw-black mb-3 focus:outline-none focus:border-raw-black"
            >
              {cpseCompanies.map((c) => (
                <option key={c} value={c}>
                  {c} ({rawCpseData.find((d) => d.company === c)?.sector})
                </option>
              ))}
            </select>

            <label className="block text-xs font-headline uppercase tracking-wider font-bold mb-1">
              Active Operational Unit / Plant
            </label>
            <select
              value={selectedFacilityId}
              onChange={(e) => {
                const fac = rawCpseData.find((d) => d.id === e.target.value);
                if (fac) handleFlyToFacility(fac);
              }}
              className="w-full bg-raw-sunken text-raw-black font-mono text-xs p-2.5 border-2 border-raw-black focus:outline-none focus:border-raw-black"
            >
              {availableFacilitiesForCpse.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name} ({f.state})
                </option>
              ))}
            </select>

            {/* Current Plant Detail Card */}
            {currentSelectedFacility && (
              <div className="mt-3 p-2.5 bg-raw-sunken border-2 border-raw-black text-xs font-mono">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-raw-black">{currentSelectedFacility.name}</span>
                  <span
                    className="w-2.5 h-2.5 rounded-full inline-block border border-black"
                    style={{ backgroundColor: currentSelectedFacility.hex }}
                  />
                </div>
                <div className="text-gray-600 mt-1">
                  Type: <strong>{currentSelectedFacility.type_label}</strong>
                </div>
                <div className="text-gray-600">
                  State: {currentSelectedFacility.state}
                </div>
                {currentSelectedFacility.capacity && (
                  <div className="text-gray-600 truncate">
                    Capacity/Spec: {currentSelectedFacility.capacity}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Section 2: Non-Blocking Interactive Badge */}
          <div className="mb-5 pb-5 border-b-2 border-raw-black bg-raw-sunken p-3 border-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-headline font-bold uppercase">
                2. Emergency Spare Sharing Radar
              </span>
              <span className="animate-pulse inline-block w-2.5 h-2.5 bg-emerald-500 rounded-full border border-black" />
            </div>

            {/* Non-Blocking Badge requested by User */}
            <button
              onClick={() => setShowNearestStocking(!showNearestStocking)}
              className={`w-full py-2.5 px-3 border-2 border-raw-black font-headline text-xs uppercase tracking-wider flex items-center justify-between transition-none shadow-sm ${
                showNearestStocking
                  ? 'bg-emerald-500 text-black font-black hover:bg-emerald-400'
                  : 'bg-raw-black text-raw-white hover:bg-gray-800'
              }`}
            >
              <span className="flex items-center gap-1.5">
                <span className="text-sm">📍</span>
                <span>View Nearest Stocking Facilities</span>
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 border border-black bg-raw-white text-black font-bold">
                {showNearestStocking ? 'ACTIVE' : 'OFF'}
              </span>
            </button>

            {showNearestStocking && (
              <div className="mt-3 pt-3 border-t border-dashed border-gray-400">
                <div className="flex items-center justify-between text-xs font-mono mb-1">
                  <span>Proximity Search Radius:</span>
                  <strong className="text-raw-black">{radarRadiusKm} km</strong>
                </div>
                <input
                  type="range"
                  min="50"
                  max="600"
                  step="25"
                  value={radarRadiusKm}
                  onChange={(e) => setRadarRadiusKm(Number(e.target.value))}
                  className="w-full accent-raw-black cursor-pointer"
                />
                <div className="flex justify-between text-[10px] font-mono text-gray-500">
                  <span>50 km</span>
                  <span>250 km (Regional)</span>
                  <span>600 km</span>
                </div>

                <div className="mt-2 text-[11px] font-mono bg-white p-2 border border-raw-black">
                  Found <strong>{nearestStockingFacilities.length}</strong> sister facilities within {radarRadiusKm} km!
                </div>
              </div>
            )}
          </div>

          {/* Section 3: Sector Layer Filters */}
          <div className="mb-5 pb-5 border-b-2 border-raw-black">
            <div className="text-xs font-headline uppercase font-bold tracking-wider mb-2">
              3. Filter Industry Sectors
            </div>
            <div className="flex flex-wrap gap-1.5">
              {SECTORS.map((sec) => (
                <button
                  key={sec}
                  onClick={() => setSelectedSector(sec)}
                  className={`text-[11px] font-headline uppercase px-2.5 py-1 border border-raw-black transition-none ${
                    selectedSector === sec
                      ? 'bg-raw-black text-raw-white font-bold'
                      : 'bg-raw-white text-raw-black hover:bg-gray-200'
                  }`}
                >
                  {sec}
                </button>
              ))}
            </div>
          </div>

          {/* Section 4: Visual Legend & Toggles */}
          <div className="mb-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-headline uppercase font-bold tracking-wider">
                Type Labels & Basemap
              </span>
              <label className="flex items-center gap-1 text-[11px] font-mono cursor-pointer">
                <input
                  type="checkbox"
                  checked={showTypeLabels}
                  onChange={(e) => setShowTypeLabels(e.target.checked)}
                  className="accent-raw-black"
                />
                <span>Map Labels</span>
              </label>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setMapTheme('light')}
                className={`flex-1 py-1 text-xs font-mono uppercase border border-raw-black ${
                  mapTheme === 'light' ? 'bg-raw-black text-raw-white' : 'bg-raw-white'
                }`}
              >
                Light Map
              </button>
              <button
                onClick={() => setMapTheme('dark')}
                className={`flex-1 py-1 text-xs font-mono uppercase border border-raw-black ${
                  mapTheme === 'dark' ? 'bg-raw-black text-raw-white' : 'bg-raw-white'
                }`}
              >
                Dark Map
              </button>
            </div>
          </div>
        </div>

        {/* Center: Interactive Maplibre + Deck.gl Viewport */}
        <div className="flex-1 relative h-[550px] lg:h-[calc(100vh-140px)] bg-gray-100 overflow-hidden">
          {/* MapLibre Container (Basemap) */}
          <div ref={mapContainerRef} className="absolute inset-0 w-full h-full" />

          {/* Deck.gl Canvas Layer */}
          <DeckGL
            viewState={viewState}
            onViewStateChange={handleViewStateChange}
            controller={{ doubleClickZoom: false, dragRotate: true }}
            layers={layers}
            getCursor={({ isHovering }) => (isHovering ? 'pointer' : 'default')}
          />

          {/* Floating Proximity Radar Status Overlay on Map */}
          {showNearestStocking && (
            <div className="absolute top-4 left-4 z-20 bg-raw-white border-3 border-raw-black p-3 shadow-lg max-w-sm">
              <div className="flex items-center gap-2 font-headline text-xs font-bold uppercase">
                <span className="w-3 h-3 bg-emerald-500 border border-black inline-block" />
                <span>Inter-CPSE Stock Sharing Corridor Active</span>
              </div>
              <p className="text-[11px] font-mono mt-1 text-gray-700">
                Green arcs show sister CPSE warehouses holding common engineering spares for <strong>{currentSelectedFacility.name}</strong>.
              </p>
              <div className="mt-2 flex items-center justify-between text-[11px] font-mono bg-raw-sunken p-1.5 border border-raw-black">
                <span>Max Radius:</span>
                <span className="font-bold">{radarRadiusKm} km</span>
                <span className="text-gray-400">|</span>
                <span>Avg Transit:</span>
                <span className="font-bold">
                  {nearestStockingFacilities.length > 0
                    ? `~${transitStats.avg} hrs (${transitStats.min === transitStats.max ? transitStats.min : `${transitStats.min}–${transitStats.max}`} hrs)`
                    : 'N/A'}
                </span>
              </div>
            </div>
          )}

          {/* Hover Tooltip */}
          {hoverInfo && hoverInfo.object && (
            <div
              className="absolute z-30 pointer-events-none bg-raw-black text-raw-white p-3 border-2 border-white shadow-2xl font-mono text-xs max-w-xs"
              style={{ left: hoverInfo.x + 12, top: hoverInfo.y + 12 }}
            >
              <div className="flex items-center justify-between border-b border-gray-600 pb-1 mb-1">
                <span className="font-bold text-yellow-300 font-headline uppercase">
                  {hoverInfo.object.company}
                </span>
                <span className="text-[10px] bg-white text-black px-1 font-bold">
                  {hoverInfo.object.psu_tier}
                </span>
              </div>

              <div className="font-bold text-sm">{hoverInfo.object.name}</div>
              <div className="text-gray-300 mt-1">
                Type: <strong className="text-white">{hoverInfo.object.type_label}</strong>
              </div>
              <div className="text-gray-400 text-[11px]">
                Sector: {hoverInfo.object.sector} • {hoverInfo.object.state}
              </div>

              {hoverInfo.object.distanceKm !== undefined && (
                <div className="mt-2 pt-1.5 border-t border-gray-600 flex items-center justify-between text-yellow-300">
                  <span>Proximity:</span>
                  <span className="font-bold">{hoverInfo.object.distanceKm} km (~{hoverInfo.object.transitHours}h road transit)</span>
                </div>
              )}
            </div>
          )}

          {/* Map Compass / Instructions Watermark */}
          <div className="absolute bottom-4 right-4 z-20 bg-raw-white/90 border-2 border-raw-black px-3 py-1.5 text-[10px] font-mono">
            Drag to pan • Scroll to zoom • Shift + Drag to tilt 3D
          </div>
        </div>

        {/* Right Drawer: List of Nearest Stocking Facilities */}
        {showNearestStocking && (
          <div className="w-full lg:w-96 border-t-3 lg:border-t-0 lg:border-l-3 border-raw-black bg-raw-white flex flex-col max-h-[60vh] lg:max-h-none z-10">
            <div className="p-3 border-b-2 border-raw-black bg-raw-sunken flex items-center justify-between">
              <div>
                <div className="text-xs font-headline uppercase font-bold">
                  Sister Stocking Units ({nearestStockingFacilities.length})
                </div>
                <div className="text-[10px] font-mono text-gray-600">
                  Ranked by road transit time from {currentSelectedFacility.company}
                </div>
              </div>
              <button
                onClick={() => setShowNearestStocking(false)}
                className="font-mono text-xs border border-black px-2 py-0.5 bg-white hover:bg-black hover:text-white"
              >
                ✕ Close
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-3">
              {nearestStockingFacilities.length === 0 ? (
                <div className="p-4 text-center font-mono text-xs text-gray-500">
                  No sister facilities located within {radarRadiusKm} km. Try expanding the search radius slider.
                </div>
              ) : (
                nearestStockingFacilities.map((fac) => (
                  <div
                    key={fac.id}
                    onClick={() => handleFlyToFacility(fac)}
                    className="p-3 border-2 border-raw-black bg-raw-white hover:bg-raw-sunken cursor-pointer transition-none group"
                  >
                    <div className="flex items-start justify-between gap-1">
                      <div>
                        <span className="font-headline font-bold text-xs uppercase group-hover:underline">
                          {fac.name}
                        </span>
                        <div className="text-[10px] font-mono text-gray-500">
                          {fac.company} • {fac.state}
                        </div>
                      </div>
                      <span
                        className="text-[9px] font-mono px-1 py-0.5 border border-black font-bold text-white whitespace-nowrap"
                        style={{ backgroundColor: fac.hex }}
                      >
                        {fac.type_label}
                      </span>
                    </div>

                    {/* Distance and Transit savings */}
                    <div className="mt-2 flex items-center justify-between text-xs font-mono bg-raw-sunken p-1.5 border border-gray-300">
                      <div>
                        <span className="text-gray-500">Distance: </span>
                        <strong className="text-raw-black">{fac.distanceKm} km</strong>
                      </div>
                      <div>
                        <span className="text-gray-500">Transit: </span>
                        <strong className="text-emerald-700">~{fac.transitHours} hrs</strong>
                      </div>
                    </div>

                    {/* Dynamic Logistics Delivery Window Callout */}
                    <div className="mt-1.5 pt-1.5 border-t border-gray-200 flex flex-wrap items-center justify-between gap-1 text-[10px] font-mono">
                      <span
                        className={`px-1.5 py-0.5 font-bold uppercase ${
                          fac.transitHours <= 3
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                            : fac.transitHours <= 8
                            ? 'bg-blue-100 text-blue-800 border border-blue-300'
                            : 'bg-amber-100 text-amber-800 border border-amber-300'
                        }`}
                      >
                        {fac.transitHours <= 3
                          ? '⚡ Same-Day Emergency Dispatch'
                          : fac.transitHours <= 8
                          ? '🚚 Overnight Road Freight'
                          : '📦 Inter-State Corridor'}
                      </span>
                      <span className="text-gray-600 font-medium">
                        ~{fac.transitHours}h haul vs 270d import
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
