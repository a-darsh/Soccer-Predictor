import redis
from pymongo import MongoClient, ASCENDING
from src.scrapers.reddit_scraper import search_reddit


#Redis data
redis_host = 'redis-19598.c274.us-east-1-3.ec2.cloud.redislabs.com'  
redis_port = 19598  
redis_password = 'TA5BGHTTiJytnI3bFTcIjYnumPLA13JW'  
redis_client = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True, )


#Mongo data
mongo_uri = "mongodb+srv://scrapper:VeryDifficultPassword@jallu.idz53kd.mongodb.net/?retryWrites=true&w=majority"
mongo_client = MongoClient(mongo_uri)
database_name = 'jallu'


#Clear any pre-existing data on redis
def clear_redis_data(redis_client):
    redis_client.flushall()


#Clear pre-existing home or away team from mongodb
def clear_mongodb_collection(mongo_client, collection_name):
    if collection_name in mongo_client.list_database_names():
        mongo_client[collection_name].drop()


# Scrape data from redit and push it to mongodb
def get_reddit_data_for_team(team_name, group):
    reddit_data = search_reddit(team_name, None, 10)
    comment_bodies = []
    comment_scores = []

    for post in reddit_data.get('posts', []):
        for comment in post.get('comments', []):
            if comment_body := comment.get('body'):
                comment_bodies.append(comment_body)
                comment_scores.append(comment.get('score', 0))

    dump_data_to_redis_and_mongodb(comment_bodies, comment_scores, group)


#Send redit to mongo through Redis
def dump_data_to_redis_and_mongodb(bodies,scores,group):
    global redis_client
    global mongo_client
    if group=='home':
        collection_name = 'home'
    else:
        collection_name='away'

    push_lists_to_redis(bodies, scores, redis_client)
    transfer_from_redis_to_mongo(redis_client, mongo_client, collection_name)


#Send the processed lists to Redis
def push_lists_to_redis(list1, list2, redis_client):
    clear_redis_data(redis_client)
    list1_filtered = [item if item is not None else 'None' for item in list1]
    list2_filtered = [item if item is not None else 'None' for item in list2]

    redis_client.lpush("comment_bodies", *list1_filtered)
    redis_client.lpush("comment_scores", *list2_filtered)

    
#Send the processed lists from Redis to MongoDB
def transfer_from_redis_to_mongo(redis_client, mongo_client, collection):
    global database_name
    clear_mongodb_collection(mongo_client, collection)

    list1_from_redis = redis_client.lrange("comment_bodies", 0, -1)
    list2_from_redis = redis_client.lrange("comment_scores", 0, -1)

    db = mongo_client[database_name]
    collection = db[collection]
    data_to_insert = {"comment_bodies": list1_from_redis, "comment_scores": list2_from_redis}
    collection.insert_one(data_to_insert)


#Querying the data on MongoDB
def extract_data_from_mongo(collection_name):
    global mongo_client
    global database_name
    
    db = mongo_client[database_name]
    collection = db[collection_name]

     # Fetch all documents from the collection
    all_data = collection.find()

    # Extract lists from each document
    bodies = []
    scores = []

    for document in all_data:
        
        list1 = document.get("comment_bodies", [])
        list2 = document.get("comment_scores", [])

        bodies.extend(list1)
        scores.extend(list2)
    
    return bodies, scores


