import os
import pymongo

mongo = pymongo.MongoClient(os.environ['MONGO_HOST'])
db = mongo.todayinfaces
