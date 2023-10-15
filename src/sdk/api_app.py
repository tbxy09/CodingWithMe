# curl 'http://127.0.0.1:8000/ap/v1/agent/tasks' \
#   -X 'OPTIONS' \
#   -H 'Accept: */*' \
#   -H 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6' \
#   -H 'Access-Control-Request-Headers: content-type' \
#   -H 'Access-Control-Request-Method: POST' \
#   -H 'Connection: keep-alive' \
#   -H 'Origin: http://localhost:8000' \
#   -H 'Referer: http://localhost:8000/' \
#   -H 'Sec-Fetch-Dest: empty' \
#   -H 'Sec-Fetch-Mode: cors' \
#   -H 'Sec-Fetch-Site: cross-site' \
#   -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0' \
#   --compressed ;
# create a app flask to able to handle the above request with payload
# payload
# {
#   "input": "helo",
#   "additional_input": null
# }
# tests/test_some_endpoint.py
# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def create_app():
    from sdk import router
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    
    return app
