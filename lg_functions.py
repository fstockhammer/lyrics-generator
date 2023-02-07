import numpy as np
import pandas as pd
pd.options.mode.chained_assignment = None # to avoid warning for setting a column to np.NaN

import lyricsgenius

# Genius API
# needs access token to run!
client_access_token = "xxx"
api = lyricsgenius.Genius(client_access_token, 
                                    retries = 3, # if first connection attempt fails, try again, max 3
                                    remove_section_headers = True, # remove patterns like [chorus], [verse1], ...
                                    verbose = False, # no status update messages on console (some functions use them)
                                    skip_non_songs = True # skip lyric results that are not lyrics but eg. tracklistings
                                    )

# Spotify API
# needs ID and SECRET to run!
SPOTIPY_CLIENT_ID = "xxx"
SPOTIPY_CLIENT_SECRET = "xxx"

# library spotipy to work with the spotify API
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET),
                    backoff_factor = 0.1)



# search for url of the song on genius
def search_url(songs):

    print("number of songs processed: (in 500 steps)")

    # create empty column for url
    songs["url"] = np.NaN

    # loop over songs and attach url
    for index, song in songs.iterrows():

        if index % 500 == 0: print(index)

        res = api.search_songs(song["song"] + " " + song["artist"][0], per_page = 1)["hits"]

        if len(res) == 0:
            songs.loc[index, "url"] = np.NaN
        
        # else, take first result and take its url
        else:
            songs.loc[index, "url"] = res[0]["result"]["url"]

    return(songs)



# function for downloading lyrics of songs when knowing the url of the song
def lyrics_from_url(songs):

    print("number of songs processed: (in 500 steps)")

    # add empty column
    songs["lyrics"] = np.NaN

    # maybe filter so that non-NaNs are remaining
    for index, song in songs.iterrows():
        
        if index % 500 == 0: print(index)

        # try if lyrics can be found
        try:
            songs.loc[index, "lyrics"] = api.lyrics(song_url = song["url"], remove_section_headers = True)

        except:
            songs.loc[index, "lyrics"] = "none"

    return(songs)



# search for song lyrics and its genius url using the artist and the song title
def search_lyrics_and_url(songs):

    print("number of songs processed: (in 500 steps)")

    # create empty column for url and lyrics
    songs["lyrics"] = np.NaN
    songs["url"] = np.NaN

     # loop over songs and attach lyrics and url
    for index, song in songs.iterrows():
        
        if index % 500 == 0: print(index)

        res = api.search_songs(song["song"] + " " + song["artist"][0], per_page = 1)["hits"]

        if len(res) == 0:
            songs.loc[index, "url"] = np.NaN
            songs.loc[index, "lyrics"] = np.NaN
        
        # else, take first result and take its url
        else:
            url = res[0]["result"]["url"]
            songs.loc[index, "url"] = url
            songs.loc[index, "lyrics"] = api.lyrics(song_url = url)

    return(songs)



# function for attaching spotify id to songs in dataframe
def search_sp_id(songs):

    print("number of songs processed: (in 500 steps)")
    
    # add empty column
    songs["sp_id"] = np.NaN

    # use artist and title to find the song on spotify, then take its id
    for index, song in songs.iterrows():
        
        if index % 500 == 0: print(index)

        # take first artist if multiple artists worked on the song
        # Note: as of 2022-06-18, spotipy might have changed it's methodology and now returns an error when no song is found
        #  therefore, first try to find the song using artist and title, if that doesn't work search only for the title
        # Note: error occured first when trying to search for "Perry Como And The Fontane Sisters With Mitchell Ayres And His Orchestra It's Beginning To Look A Lot Like Christmas"
        try:
            res = sp.search(q = song["artist"][0] + " " + song["title"])["tracks"]["items"]
        
        except:
            res = sp.search(q = song["title"])["tracks"]["items"]

        # if nothing is found, set to "none"
        # Note: don't set to NaN, as this leads to problems later on
        # we need "none" as sp.audio_features("none") == [None] is used later, we need the [None] as a result
        if len(res) == 0:
            songs.loc[index, "sp_id"] = "none"
        
        # else, take first result and take its id
        else:
            songs.loc[index, "sp_id"] = res[0]["id"]

    return(songs)




# function for finding the genre that is related to the primary artist of a song
def create_artists_genres(songs):

    print("number of songs processed: (in 500 steps)")

    song_ids = songs["sp_id"]

    # initialize df
    artists = pd.DataFrame(song_ids)

    #for song in song_ids:
    for index, song in enumerate(song_ids):
        
        if index % 500 == 0: print(index) 

        # if there is no spotify id, skip
        if song == "none":
            artists.loc[index, "art_id"] = "none"
            artists.loc[index, "genres"] = "none"

        # else, search artist and his genres, then append to df
        else:
            artist_id = sp.track(song)["artists"][0]["id"]
            # artist_id is the artist id of the primary artist of the song

            #new_df = pd.DataFrame(res)
            # new_df = pd.DataFrame(sp.audio_features(song))
            artists.loc[index, "art_id"] = artist_id
            artists.loc[index, "genres"] = ", ".join(sp.artist(artist_id)["genres"])

    
    artists = pd.merge(songs, artists, on = "sp_id")
    artists = artists.reset_index(drop = True)
    return(artists)




# function for creating a df with audio features of songs
def create_audio_features(songs):

    # Note: sp.audio_features can take a maximum of 100 ids per call, so do them seperately
    song_ids = songs["sp_id"]

    # initialize df
    audio = pd.DataFrame(sp.audio_features(song_ids.iloc[0]))

    for song in song_ids[1:]:
        res = sp.audio_features(song)

        # if result is empty -> sp_id is empty, skip
        if res == [None]:
            next
        
        # else, append to df
        else:
            # audio = pd.concat([audio, pd.DataFrame(sp.audio_features(song))])
            audio = pd.concat([audio, pd.DataFrame(res)])

    # drop columns that are not used
    audio = audio.drop(["type", "uri", "track_href", "analysis_url", "duration_ms", "time_signature"], axis = 1)

    audio = audio.reset_index(drop = True)
    return(audio)