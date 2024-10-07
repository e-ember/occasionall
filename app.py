from flask import Flask, render_template, request, redirect
from dotenv import load_dotenv
import random, string, urllib.parse, os
from spotipy import oauth2, client
import spotipy
import google.generativeai as ggai
import requests
import random

#pull request testing

app = Flask(__name__)

#load environment variables
load_dotenv()



#---------------- spotify portion ----------------------
#set default index html page
@app.route("/", methods=['GET', 'POST'])
def index():


    return render_template("index.html")

#create a random state string to secure user information
state = ""
for i in range(15):
    state += random.choice(string.ascii_letters)

# redirect user to login page
@app.route("/login", methods=['GET', 'POST'])
def login():
        
    #create url to send user to login to the spotify account
    #after, redirect to redirect_uri (currently set as /callback)
    login_url = 'https://accounts.spotify.com/authorize?'+urllib.parse.urlencode({'response_type':'code', 'client_id':os.getenv('CLIENT_ID'),'scope':'user-read-playback-position user-top-read user-read-recently-played playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public user-library-modify user-library-read', 'redirect_uri':os.getenv('REDIRECT_URI'), 'state':state})

    # print(login_url)


    return redirect(login_url)

#BTS work.
@app.route("/callback", methods=["POST", "GET"])
def callback():
    


    #Retrieve the code given when user signed in, verifying that it is them.
    code = request.args.get('code')
    #Use OAuth2. Create a spotify OAuth2 object using the spotipy library
    spotipy_obj = spotipy.oauth2.SpotifyOAuth(client_id=os.getenv('CLIENT_ID'), client_secret=os.getenv('CLIENT_SECRET'), redirect_uri=os.getenv('REDIRECT_URI'), state=state,scope='user-read-playback-position user-top-read user-read-recently-played playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public user-library-modify user-library-read')
    
    #use object to obtain an access token, if it exists, or get a new one if it doesn't exist
    token = spotipy_obj.get_access_token(code=code, as_dict=False)

    # print(token)

    #create a spotify object to retrieve data specifically from user using the accessed token
    sp = spotipy.Spotify(auth=token)

    #THIS IS USER DATA
    #----------------- ai portion --------------------------
    #https://ai.google.dev/
    ggai.configure(api_key=os.getenv('GEMINI_API'))

    model = ggai.GenerativeModel(model_name="gemini-1.5-flash")

    prompt = "This is the description of my event: " + str(request.form.get("eventdetails")) + ". Consider the combination of the factors acoustiness, danceability, energy, instrumentalness, liveliness, loudness, speechiness, tempo, and valence to form the music best suited for this event. Between 0 to 1, what float most represents the acousticness, danceability, energy, instrumentalness, liveliness, loudness, speechiness, tempo, and valence best suited for this event? What is a Spotify genre best suited for this event? Return your data, one number for each factor, in the format of acousticness, danceability, energy, instrumentalness, liveliness, loudness, speechiness, tempo, valence, genre, and nothing else."

    output = model.generate_content(prompt)
    characters = str(output.text)[:-1].split(", ")

    headers={"Authorization": "Bearer " + token}


    user_tracks = requests.get("https://api.spotify.com/v1/me/tracks/?limit=50", headers=headers).json()
    inspo_songs_ids = []
    

    for i in range(4):
        random_user_track = user_tracks['items'][random.randrange(1,50)]
        inspo_songs_ids.append(random_user_track['track']['id'])
        print(random_user_track['track']['name'])
    
    string_ids = ','.join(inspo_songs_ids)


    url_parts = {"seed_genres":characters[9], 
                 "seed_tracks":string_ids, 
                 "target_acousticness":float(characters[0]), 
                 "target_danceability":float(characters[1]), 
                 "target_energy":float(characters[2]), 
                 "target_instrumentalness":float(characters[3]), 
                 "target_liveness":float(characters[4]), 
                 "target_loudness":float(characters[5]), 
                 "target_speechiness":float(characters[6]), 
                 "target_tempo":float(characters[7]), 
                 "target_valence": float(characters[8])}

    access_url = "https://api.spotify.com/v1/recommendations?" + urllib.parse.urlencode(url_parts)

    response = requests.get(access_url, headers=headers)

    data = response.json()


    song_recs = []

    for track in data['tracks']:
        # song_recs.append(track['external_urls']['spotify'])
        song_recs.append(track['name']+" "+track['artists'][0]['name'])

    

    return render_template("results.html", recommendations=song_recs)

