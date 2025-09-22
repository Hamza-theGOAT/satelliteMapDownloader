import os
import math
import json
import time
import requests
from PIL import Image
from io import BytesIO
from typing import Tuple, List


class SatelliteMapDownloader:
    """Downloads and manages satellite map tiles for offline use"""

    def __init__(self, mapsFolder="maps"):
        self.mapsFolder = mapsFolder
        self.ensureMapsFolder()

        # Tile servers (you can add more providers)
        self.tileServers = {
            'openstreetmap': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            'satellite': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            'hybrid': 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            'googleSat': 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        }

        # Default to Google satellite for better quanlity
        self.currentServer = 'googleSat'

    def ensureMapsFolder(self):
        """Create maps folder if it doesn't exist"""
        if not os.path.exists(self.mapsFolder):
            os.makedirs(self.mapsFolder)

    def deg2num(self, latDeg: float, lonDeg: float, zoom: int) -> Tuple[int, int]:
        """Convert lat/lon to tile numbers"""
        latRad = math.radians(latDeg)
        n = 2.0 ** zoom
        x = int((lonDeg+180.0)/360.0*n)
        y = int((1.0-math.asinh(math.tan(latRad))/math.pi)/2.0*n)
        return (x, y)

    def num2deg(self, x: int, y: int, zoom: int) -> Tuple[float, float]:
        """Convert tile numbers to lat/lon"""
        n = 2.0 ** zoom
        lonDeg = x/n*360.0 - 180.0
        latRad = math.atan(math.sinh(math.pi*(1-2*y/n)))
        latDeg = math.degrees(latRad)
        return (latDeg, lonDeg)

    def calculateZoomLvl(self, bounds: dict, maxTiles: int = 20) -> int:
        """Calculate appropriate zoom level based on area size"""
        latDiff = abs(bounds['north'] - bounds['south'])
        lonDiff = abs(bounds['east'] - bounds['west'])

        # Start with a reasonable zoom level and adjust
        for zoom in range(10, 18):
            minX, minY = self.deg2num(bounds['north'], bounds['west'], zoom)
            maxX, maxY = self.deg2num(bounds['south'], bounds['east'], zoom)

            tilesX = maxX - minX + 1
            tilesY = maxY - minY + 1
            totalTiles = tilesX * tilesY

            if totalTiles <= maxTiles:
                return zoom

        return 15  # Default zoom if calculation fails

    def downloadTile(self, x: int, y: int, zoom: int, serverKey: str = None) -> Image.Image:
        """Download a single map tile"""
        if serverKey is None:
            serverKey = self.currentServer

        url = self.tileServers[serverKey].format(x=x, y=y, z=zoom)

        try:
            response = requests.get(url, headers={
                'User-Agent': 'Python Map Downloader 1.0'
            }, timeout=10)
            response.raise_for_status()

            # Convert to PIL Image
            return Image.open(BytesIO(response.content))

        except Exception as e:
            print(f"Error Downloading tile {x}/{y}/{zoom}: {e}")
            return Image.new('RGB', (256, 256), color='lightgray')

    def downloadArea(self, bounds: dict, zoom: int = None, mapName: str = 'satelliteSnippet') -> dict:
        """
        Download satellite imagery for a rectangular area

        Args:
            bounds: Dictionary with keys 'north', 'south', 'east', 'west' (in decimal degrees)
            zoom: Zoom level (calculated automatically if None)
            mapName: Name for the saved map files

        Returns:
            Dictionary with map information and file paths
        """
        print(f"Downloading map area: {bounds}")

        # Calculate zoom level if not provided
        if zoom is None:
            zoom = self.calculateZoomLvl(bounds)

        # Calculate tile boundaries
        minX, minY = self.deg2num(bounds['north'], bounds['west'], zoom)
        maxX, maxY = self.deg2num(bounds['south'], bounds['east'], zoom)

        print(f"Tiles needed: X({minX}-{maxX}), Y({minY}-{maxY})")

        tilesX = maxX - minX + 1
        tilesY = maxY - minY + 1
        totalTiles = tilesX * tilesY

        print(f"Total tiles to download: {totalTiles}")

        # Create final image
        finalWidth = tilesX*256
        finalHeight = tilesY*256
        finalImage = Image.new('RGB', (finalWidth, finalHeight))

        # Download and stitch tiles
        downloaded = 0
        for x in range(minX, maxX+1):
            for y in range(minY, maxY+1):
                # Download tile
                tile = self.downloadTile(x, y, zoom)

                # Calculate position in final image
                posX = (x - minX) * 256
                posY = (y - minY) * 256

                # Paste tile into final image
                finalImage.paste(tile, (posX, posY))

                downloaded += 1
                print(f"Download tile {downloaded}/{totalTiles}")

                # Be nice to servers
                time.sleep(0.1)

        # Save the stitched image
        imagePath = os.path.join(self.mapsFolder, f"{mapName}.png")
        finalImage.save(imagePath, "PNG")

        # Calculate actual bounds of the downloaded area (tile boundaries)
        actualNorth, actualWest = self.num2deg(minX, minY, zoom)
        actualSouth, actualEast = self.num2deg(maxX+1, maxY+1, zoom)

        # Create metadata
        mapInfo = {
            'name': mapName,
            'imagePath': imagePath,
            'bounds': {
                'north': actualNorth,
                'south': actualSouth,
                'east': actualEast,
                'west': actualWest,
                'requestedNorth': bounds['north'],
                'requestedSouth': bounds['south'],
                'requestedEast': bounds['east'],
                'requestedWest': bounds['west']
            },
            'zoom': zoom,
            'imageSize': {
                'tilesX': tilesX,
                'tilesY': tilesY,
                'minX': minX,
                'minY': minY,
                'maxX': maxX,
                'maxY': maxY
            }
        }

        # Save metadata
        metadataPath = os.path.join(self.mapsFolder, f"{mapName}_info.json")
        with open(metadataPath, 'w') as f:
            json.dump(mapInfo, f, indent=2)

        print(f"Map saved: {imagePath}")
        print(f"Metadata saved: {metadataPath}")

        return mapInfo

    def downloadFromCorners(self, corners: List[Tuple[float, float]], zoom: int = None, mapName: str = 'satelliteSnippet') -> dict:
        """
        Download area defined by 4 corner points

        Args:
            corners: List of (lat, lon) tuples for the 4 corners
            mapName: Name for the saved map

        Returns:
            Dictionary with map information
        """
        # Calculate bounding box from corners
        lats = [corner[0] for corner in corners]
        lons = [corner[1] for corner in corners]

        bounds = {
            'north': max(lats),
            'south': min(lats),
            'east': max(lons),
            'west': min(lons)
        }

        return self.downloadArea(bounds, zoom=zoom, mapName=mapName)


def main():
    """Use case for SatelliteMapDownloader class"""

    downloader = SatelliteMapDownloader()

    # Download an area around Central Park, NYC
    exampleBounds = {
        'north': 40.7829,   # Northern boundary
        'south': 40.7489,   # Southern boundary
        'east': -73.9441,   # Eastern boundary
        'west': -73.9734    # Western boundary
    }

    # Downloading with fix bounds directly
    mapInfo = downloader.downloadArea(
        exampleBounds, zoom=17, mapName='exampleBounds')

    # Example with corner points
    corners = [
        (40.7829, -73.9734),  # Northwest corner
        (40.7829, -73.9441),  # Northeast corner
        (40.7489, -73.9441),  # Southeast corner
        (40.7489, -73.9734)   # Southwest corner
    ]

    mapInfo = downloader.downloadFromCorners(
        corners, zoom=17, mapName='cornerBounds')


if __name__ == '__main__':
    main()
