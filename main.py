import os
import time
import requests
import subprocess
import random
import bz2
import logging
from datetime import date

today = date.today()
formatted_date = today.strftime("%Y-%m-%d")
print(formatted_date)
logging.basicConfig(filename=f'{formatted_date}.log',
                    level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Dota 2 API credentials
try:
    from local_settings import DOTA2_CLIENT_PATH, REPLAY_PATH
except ImportError:
    logger.error("Could not import local settings")

def download_replay(replay_url, match_id):
    response = requests.get(replay_url, stream=True)

    if response.status_code != 200:
        logger.error(f"Error fetching replay from url {replay_url}. Status code: {response.status_code}")
        return None

    replay_download_path = f"{REPLAY_PATH}\\{match_id}.dem.bz2"
    with open(replay_download_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    # Extract the replay file
    extracted_replay_path = f"{REPLAY_PATH}\\{match_id}.dem"
    with bz2.open(replay_download_path, 'rb') as source_file, open(extracted_replay_path, 'wb') as dest_file:
        for data in iter(lambda: source_file.read(8192), b''):
            dest_file.write(data)

    delete_file(f"{match_id}.dem.bz2")

    return f"{match_id}.dem"

def play_replay(replay_file_name):
    command = f"{DOTA2_CLIENT_PATH} -console -novid +playdemo /replays/{replay_file_name} +demo_quitafterplayback 1"
    process = subprocess.Popen(command, shell=True)
    process.wait()

def delete_file(replay_file_name):
    os.remove(f"{REPLAY_PATH}\\{replay_file_name}")

def main():
    latest_match_id = None
    while True:
        # Download a Dota 2 replay
        match_id, replay_url = get_random_match_id_and_replay_url(latest_match_id)  # Implement this function to get a random match_id and replay_url
        if not match_id or not replay_url:
            continue

        replay_file_name = download_replay(replay_url, match_id)

        if not replay_file_name:
            latest_match_id = match_id
            continue

        # Play the downloaded replay
        logger.debug(f"Successfully downloaded replay. Playing {replay_file_name}")
        play_replay(replay_file_name)

        # Delete the replay file
        delete_file(replay_file_name)

def get_lowest_average_rank_match(last_match_id=None):
    url = "https://api.opendota.com/api/publicMatches"
    matches = []

    while not matches:
        params = {}
        if last_match_id:
            params['less_than_match_id'] = last_match_id

        response = requests.get(url, params=params).json()

        if not response:
            break

        for match in response:
            last_match_id = match['match_id']
            
            if (match.get('lobby_type') == 7 and
                    match.get('avg_mmr') is not None and
                    match['avg_mmr'] < 500):
                matches.append(match)

        matches = sorted(matches, key=lambda x: x['avg_mmr'])

        # Avoid making too many requests in a short period
        time.sleep(1)

    if not matches:
        return None

    return matches[0]

def get_random_match_id_and_replay_url(latest_match_id):
    
    match_id = latest_match_id
    replayResponse = []
    while not replayResponse:
        match = get_lowest_average_rank_match(match_id)
        match_id = match['match_id']
        cluster = match.get('cluster')

        saltUrl = "https://api.opendota.com/api/replays"
        payload = {"match_id": match_id}
        replayResponse = requests.get(saltUrl, params=payload).json()
        
    replay = replayResponse[0]




    replay_salt = replay.get('replay_salt')

    if not cluster or not replay_salt:
        return None, None

    replay_url = f"http://replay{cluster}.valve.net/570/{match_id}_{replay_salt}.dem.bz2"
    return match_id, replay_url

if __name__ == '__main__':
    main()