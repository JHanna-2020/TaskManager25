from pymongo import MongoClient

client = MongoClient("mongodb+srv://jh:YOUR_PASSWORD@taskmanger.3gfydvt.mongodb.net/?retryWrites=true&w=majority")
client.admin.command("ping")