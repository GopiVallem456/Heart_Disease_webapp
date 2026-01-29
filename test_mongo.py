from pymongo import MongoClient

uri = "mongodb+srv://gopi:gopi0530@cluster-1.y6kcqaj.mongodb.net/heart_app?retryWrites=true&w=majority"
client = MongoClient(uri)

client.admin.command("ping")
print("MongoDB connected successfully")
