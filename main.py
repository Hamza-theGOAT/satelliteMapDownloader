import os
import math
import json
import time
from PIL import Image
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
