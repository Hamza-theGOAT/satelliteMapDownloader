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
        x = int((latDeg+180.0)/360.0*n)
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


if __name__ == '__main__':
    main()
