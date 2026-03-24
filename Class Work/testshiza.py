import asyncio
from shazamio import Shazam


async def recognize_song(file_path):
    shazam = Shazam()
    result = await shazam.recognize_song(file_path)

    if result.get('track'):
        track = result['track']
        print(f"Название: {track.get('title')}")
        print(f"Исполнитель: {track.get('subtitle')}")
        return track
    else:
        print("Песня не найдена")
        return None


# Использование
asyncio.run(recognize_song('徳永英明 - BIRDS.flac'))