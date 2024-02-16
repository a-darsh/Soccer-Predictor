import pandas as pd
from datetime import datetime
from transformers import AutoTokenizer, TFAutoModelForSequenceClassification
import tensorflow as tf
import numpy as np
from tqdm import tqdm
import requests
import pandas as pd
from bs4 import BeautifulSoup
from src.scrapers.reddit_scraper import search_reddit
from joblib import load

# Code to load the models
def load_model(file_name):
    return load(file_name)

def load_scaler(file_name):
    return load(file_name)

# Bets Odd Scrapper Function
def oddsScrapper():
  URL = "https://www.betexplorer.com/football/england/premier-league/"
  response = requests.get(URL)
  soup = BeautifulSoup(response.text, 'lxml')

  # Find the correct table using the provided class
  table_matches = soup.find('table', {'class': 'table-main table-main--leaguefixtures h-mb15'})
  rows = table_matches.find_all('tr') if table_matches else []
  data = []
  # Iterate over each row except for the header row
  for row in rows[1:]:
      try:
        cols = row.find_all('td')
        match_info = {
            'Teams': cols[1].get_text(strip=True),
            '1': cols[5].button['data-odd'],
            'X': cols[6].button['data-odd'],
            '2': cols[7].button['data-odd'],
            'Date': cols[8].get_text(strip=True)
        }
        data.append(match_info)
      except:
        continue

  # Create a DataFrame
  df = pd.DataFrame(data)
  return df

# Specific Match odds extraction
def get_match_odds(df, home_team, away_team):
    """
    Extracts the betting odds for a specific match.

    Parameters:
    df (DataFrame): DataFrame containing odds data.
    home_team (str): Name of the home team.
    away_team (str): Name of the away team.

    Returns:
    dict: Odds for Home Win, Draw, and Away Win.
    """
    # Format the team names to match the DataFrame format
    match_identifier = f"{home_team}-{away_team}"

    # Find the row with the matching teams
    match_row = df[df['Teams'].str.contains(match_identifier, case=False, na=False)]

    if not match_row.empty:
        return {
            'AvgOdds_HomeWin': match_row['1'].values[0],
            'AvgOdds_Draw': match_row['X'].values[0],
            'AvgOdds_AwayWin': match_row['2'].values[0]
        }
    else:
        return None

# Reddit Data team util function
def get_reddit_data_for_team(team_name):
    # team_name = team_name + " FC"
    reddit_data = search_reddit(team_name, None, 10)
    return reddit_data

# Extracting Reddit Data to required form
def extract_comments_and_scores(reddit_data):
    # Your extract_comments_and_scores function as provided.
    comment_bodies = []
    comment_scores = []

    for post in reddit_data.get('posts', []):
        for comment in post.get('comments', []):
            if comment_body := comment.get('body'):
                comment_bodies.append(comment_body)
                comment_scores.append(comment.get('score', 0))

    print(f"Extracted {len(comment_bodies)} comments from query '{reddit_data.get('term')}'")

    return comment_bodies, comment_scores


# Batching and predcting sentiments and scores for reddit comments 
def batch_predict(texts, tokenizer, model, batch_size=1000):
    # Your batch_predict function as provided.
    predictions = []
    for i in tqdm(range(0, len(texts), batch_size)):
        batch = texts[i:i+batch_size]
        encoded_batch = tokenizer(batch, padding=True, truncation=True, max_length=128, return_tensors="tf")
        outputs = model(encoded_batch['input_ids'], attention_mask=encoded_batch['attention_mask'])
        batch_predictions = tf.nn.softmax(outputs.logits, axis=-1)
        predictions.extend(batch_predictions.numpy().tolist())
    return predictions


# Calculating overall positive, negative, neutral sentiments scores 
def calculate_sentiment_scores(sentiments):
    # Adjusted function to work with sentiment predictions directly.
    positive_sum = neutral_sum = negative_sum = 0

    for sentiment_score in sentiments:
        positive_sum += sentiment_score[2]
        neutral_sum += sentiment_score[1]
        negative_sum += sentiment_score[0]

    return positive_sum, neutral_sum, negative_sum

# Sentiments prediction - util function
def perform_sentiment_analysis(team_name, start_date):
    reddit_data = get_reddit_data_for_team(team_name)
    comment_bodies, _ = extract_comments_and_scores(reddit_data)
    sentiments = batch_predict(comment_bodies)
    return calculate_sentiment_scores(sentiments, start_date)

# Function to normalize sentiments Score
def normalize_score(scores):
    max_score = max(scores)
    # return [(score - min_score) / (max_score - min_score) for score in scores]
    return [score/max_score for score in scores]

# Adding weight factor based on odds 
def weight_factor(input_df, home=False):
    
    if home:
      weight = 1/input_df['AvgOdds_HomeWin'].values[0]
    else:
      weight = 1/input_df['AvgOdds_AwayWin'].values[0]
  
    return weight

# Prediction function using the loaded xgboost models
def predict_match_result(input_data, model_home, model_away, scaler):
    """
    Predicts Home Goals, Away Goals, and the match result.

    Parameters:
    input_data (dict): Match data containing features but not the goals.
    model_home (model): Trained model for predicting Home Goals.
    model_away (model): Trained model for predicting Away Goals.
    scaler (StandardScaler): Scaler used for standardizing features.
    label_encoder (LabelEncoder): Encoder used for categorical variables.

    Returns:
    dict: Predicted Home Goals, Away Goals, and match result.
    """

    # Convert input data to DataFrame
    input_df = pd.DataFrame([input_data])
    home_team = input_df['Home'].values[0]
    away_team = input_df['Away'].values[0]

    # Handle missing values
    input_df = input_df[['HomeTeam_PositiveSentiment','HomeTeam_NeutralSentiment','HomeTeam_NegativeSentiment','AwayTeam_PositiveSentiment','AwayTeam_NeutralSentiment','AwayTeam_NegativeSentiment','AvgOdds_HomeWin','AvgOdds_Draw','AvgOdds_AwayWin']]

    # Standardize numerical features
    numerical_cols = ['HomeTeam_PositiveSentiment', 'HomeTeam_NeutralSentiment', 'HomeTeam_NegativeSentiment',
                      'AwayTeam_PositiveSentiment', 'AwayTeam_NeutralSentiment', 'AwayTeam_NegativeSentiment',
                      'AvgOdds_HomeWin', 'AvgOdds_Draw', 'AvgOdds_AwayWin']
    input_df[numerical_cols] = scaler.transform(input_df[numerical_cols])

    # Predict Home and Away Goals
    predicted_home_goals = round(weight_factor(input_df, True)*model_home.predict(input_df)[0])
    predicted_away_goals = round(weight_factor(input_df)*model_away.predict(input_df)[0])


    # Determine match result
    if predicted_home_goals > predicted_away_goals:
        result = 'Home Win'
    elif predicted_home_goals < predicted_away_goals:
        result = 'Away Win'
    else:
        result = 'Draw'

    return {
        'Predicted Home Goals': predicted_home_goals,
        'Predicted Away Goals': predicted_away_goals,
        'Match Result': result,
        'Home Team': home_team,
        'Away Team': away_team
    }