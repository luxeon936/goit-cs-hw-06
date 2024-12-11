import os
import asyncio
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from multiprocessing import Process
import websockets
from datetime import datetime
import json
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "message_db")


class LogColors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

logging.basicConfig(level=logging.INFO, format=f"{
                    LogColors.OKCYAN}[%(asctime)s] %(levelname)s{LogColors.ENDC}: %(message)s")

logging.info(f"{LogColors.OKBLUE}Connecting to MongoDB at {
             MONGO_URI}{LogColors.ENDC}")


class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path == "/":
            self.send_html_file("index.html")
        elif parsed_url.path == "/message.html":
            self.send_html_file("message.html")
        elif parsed_url.path == "/logo.png":
            self.send_static_file("logo.png")
        else:
            self.send_html_file("error.html", 404)

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        parsed_data = parse_qs(post_data.decode("utf-8"))
        username = parsed_data.get("username")[0]
        message = parsed_data.get("message")[0]

        message_data = json.dumps({"username": username, "message": message})

        async def send_message():
            uri = "ws://localhost:5000"
            async with websockets.connect(uri) as websocket:
                await websocket.send(message_data)

        asyncio.run(send_message())

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Message successfully sent!")

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(filename, "rb") as file:
            self.wfile.write(file.read())

    def send_static_file(self, filename, status=200):
        try:
            with open(filename, "rb") as file:
                self.send_response(status)
                self.send_header("Content-type", "image/png")
                self.end_headers()
                self.wfile.write(file.read())
        except FileNotFoundError:
            self.send_html_file("error.html", 404)


class WebSocketServer:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[MONGO_DB]
        self.collection = self.db["messages"]

    async def ws_handler(self, websocket):
        async for message in websocket:
            data = json.loads(message)
            logging.info(f"{LogColors.OKGREEN}Received message: {
                         data}{LogColors.ENDC}")
            date = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

            message_data = {
                "date": date,
                "username": data["username"],
                "message": data["message"],
            }
            try:
                self.collection.insert_one(message_data)
                logging.info(f"{LogColors.OKBLUE}Saved message: {
                             message_data}{LogColors.ENDC}")
            except Exception as e:
                logging.error(f"{LogColors.FAIL}Failed to insert message: {
                              e}{LogColors.ENDC}")


async def run_websocket_server():
    server = WebSocketServer()
    async with websockets.serve(server.ws_handler, "0.0.0.0", 5000):
        logging.info(f"{LogColors.OKCYAN}WebSocket server started on port 5000{
                     LogColors.ENDC}")
        await asyncio.Future()


def start_websocket_server():
    asyncio.run(run_websocket_server())


def run_http_server():
    server_address = ("", 3000)
    httpd = HTTPServer(server_address, HttpHandler)
    logging.info(f"{LogColors.OKCYAN}HTTP server started on port 3000{
                 LogColors.ENDC}")
    httpd.serve_forever()


if __name__ == "__main__":
    http_process = Process(target=run_http_server)
    ws_process = Process(target=start_websocket_server)

    http_process.start()
    ws_process.start()

    http_process.join()
    ws_process.join()
