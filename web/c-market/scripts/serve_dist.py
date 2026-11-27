"""Serve frozen build and one private snapshot on localhost, no external dependencies."""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
import argparse
R=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(R/'dist'),**kw)
 def do_GET(self):
  if urlsplit(self.path).path=='/favicon.ico':
   self.send_response(204);self.end_headers();return
  super().do_GET()
 def translate_path(self,path):
  if urlsplit(path).path=='/data/market.json':return str(R/'public/data/market.json')
  return super().translate_path(path)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=4194);args=p.parse_args()
 assert (R/'dist/index.html').is_file() and (R/'public/data/market.json').is_file(),'Build and private snapshot required'
 print(f'C V2 offline preview: http://127.0.0.1:{args.port}',flush=True)
 ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
