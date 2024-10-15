from flask import Flask, render_template, request, redirect, jsonify, url_for, session
from dotenv import load_dotenv
import random, string, urllib.parse, os
from spotipy import oauth2, client
import spotipy
import google.generativeai as ggai
import requests
import random
import secrets

app = Flask(__name__)

#load environment variables
load_dotenv()

#make a secret key for session
app.secret_key=secrets.token_hex(16)

#set default index html page
@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == "POST":
        return redirect(url_for('login'))

    return render_template("index.html")

#create a random state string to secure user information
state = ""
for i in range(15):
    state += random.choice(string.ascii_letters)

#redirect user to login page
@app.route("/login", methods=['GET', 'POST'])
def login():
        
    #create url to send user to login to the spotify account
    #after, redirect to redirect_uri (currently set as /callback)
    event_details = request.form.get("eventdetails")
    session['eventdetails'] = event_details
    
    login_url = 'https://accounts.spotify.com/authorize?'+urllib.parse.urlencode({'response_type':'code', 'client_id':os.getenv('CLIENT_ID'),'scope':'user-read-playback-position user-top-read user-read-recently-played playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public user-library-modify user-library-read', 'redirect_uri':os.getenv('REDIRECT_URI'), 'state':state})

    return redirect(login_url)

#BTS work.
@app.route("/callback", methods=["POST", "GET"])
def callback():
    #Retrieve the code given when user signed in, verifying that it is them.
    code = request.args.get('code')

    #Use OAuth2. Create a spotify OAuth2 object using the spotipy library
    spotipy_obj = spotipy.oauth2.SpotifyOAuth(client_id=os.getenv('CLIENT_ID'), client_secret=os.getenv('CLIENT_SECRET'), redirect_uri=os.getenv('REDIRECT_URI'), state=state,scope='user-read-playback-position user-top-read user-read-recently-played playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public user-library-modify user-library-read')

   
    #use object to obtain an access token, if it exists, or get a new one if it doesn't exist
    if os.path.exists(".cache"):
        os.remove(".cache")
    token = spotipy_obj.get_access_token(code=code, as_dict=False)


    #create a spotify object to retrieve data specifically from user using the accessed token
    sp = spotipy.Spotify(auth=token)

    #----------------- ai portion --------------------------
    #Credit: https://ai.google.dev/
    ggai.configure(api_key=os.getenv('GEMINI_API'))

    model = ggai.GenerativeModel(model_name="gemini-1.5-flash")

    event_details = session['eventdetails']

    #Create prompt with user details
    prompt = "This is the description of my event: " + event_details + ". What are three Spotify musical genres best suited for this event? Return only the genre names in the format genre1 genre2 genre3 and nothing else. If the description of the event includes a musical genre, include that as one of the three genres returned."

    #Get Gemini's output 
    genres_output = model.generate_content(prompt)

    #Create headers for Spotify API calls and authorization
    headers={"Authorization": f"Bearer {token}"}

    #Search Spotify for genres produced
    search_url = "https://api.spotify.com/v1/search?"+urllib.parse.urlencode({"q":"genre"+str(genres_output.text)+"vibes", "type":"track", "limit":30})

    #Get returned songs of the API call
    response = requests.get(search_url, headers=headers)
    data = response.json()

    recommendations = []
    for track in data['tracks']['items']:
        recommendations.append(track['id'])
    
    #Create Spotify playlist bio
    prompt = "Make a short three-word-or-less name summarizing: " + event_details + ". Return only those three words"
    pname_output = model.generate_content(prompt)
    body = {"name":str(pname_output.text), "description":event_details+ " - generated by OccasionAll "}

    #Create playlist on user profile
    user_id = requests.get("https://api.spotify.com/v1/me/", headers=headers).json()['id']
    playlist = requests.post(f"https://api.spotify.com/v1/users/{user_id}/playlists/", headers=headers, json=body).json()

    songs = []

    for id in recommendations:
        songs.append("spotify:track:"+id)

    songs_data = {"uris":songs}


    #Get playlist link and redirect to playlist
    add_songs = requests.post(f"https://api.spotify.com/v1/playlists/{playlist['id']}/tracks", headers=headers, json=songs_data)

    return redirect(playlist['external_urls']['spotify'])
